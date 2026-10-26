"""One loader per defense, so the native harness can drive all of them.

Until now the top-k harness hardcoded ParamMute and CK-PLUG in an if/else,
and the other defenses were each driven by their own script against the
chunk-replacement dosing we invented. Porting them here is what lets every
retrieval result come from the attacks' own protocol.

Each loader returns an object with

    .arms                              the arm names it produces
    .answer(question, passages, gold)  -> {arm: prediction}

`passages` is the list of retrieved passages, poisoned or not. It is a LIST
rather than a joined string because the methods do not agree on what to do
with it: DyPRAG encodes each passage separately and never puts any of them in
the prompt, and RobustRAG answers over each in isolation. Joining first would
quietly change two of the methods.

Several defenses return their own undefended arm from the same forward pass -
COIECD's model_answer, ACD's contrast modes, SpARE's two steering directions.
Where a method does that we take its arm rather than running a separate
baseline, because its baseline is the one its authors compare against.

Nothing here reimplements a method. Each loader imports the authors' module
from third_party/ and calls it.
"""
from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TP = REPO / "third_party"
BASE = "NousResearch/Meta-Llama-3-8B-Instruct"


def _ctx(passages):
    """How every prompt-level defense sees the retrieved set."""
    return "\n".join(passages)


class Defense:
    name: str = ""
    arms: tuple = ()

    def answer(self, question, passages, gold=None) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------- COIECD
class COIECD(Defense):
    """Entropy-constrained decoding. model_answer returns both arms at once."""
    name, arms = "coiecd", ("base_rag", "coiecd", "closedbook")

    def __init__(self, base=BASE):
        sys.path.insert(0, str(TP / "COIECD"))
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import decoding as CO                   # their code
        self.CO = CO
        self.tok = AutoTokenizer.from_pretrained(base)
        # Llama-3 ships no pad token and their decoding.py pads. The original
        # runner sets eos rather than their tokenizer.pad_token_id = 0, which
        # would pad with a real token id.
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        # their loop tokenises [with_context, without_context] as one padded
        # batch and reads logits[:, -1, :] for both rows. Right padding would
        # read the shorter row off a PAD and compute the constraint on noise.
        self.tok.padding_side = "left"
        self.model = AutoModelForCausalLM.from_pretrained(
            base, torch_dtype=torch.bfloat16, device_map="auto",
            low_cpu_mem_usage=True)
        self.model.eval()
        # decoding.py sets `device` only inside one function, so the module
        # global the others use is unbound until we set it. The original
        # runner does the same.
        CO.device = "cuda"
        CO.tokenizer = self.tok

    def answer(self, question, passages, gold=None):
        # their protocol generates exactly as many tokens as the gold answer
        n = max(1, len(self.tok.encode(gold or "x", add_special_tokens=False)))
        defended, base, _ = self.CO.model_answer(
            self.model, self.tok, question, _ctx(passages), n)
        # The no-retrieval arm, through their own entry point with an empty
        # context. Section 9 asks every paper to report one, and a defense
        # that is inert on accuracy cannot be read without it.
        _, closed, _ = self.CO.model_answer(
            self.model, self.tok, question, _ctx([]), n)
        return {"coiecd": defended.strip(), "base_rag": base.strip(),
                "closedbook": closed.strip()}


# ---------------------------------------------------------------- ACD
class ACD(Defense):
    """Contrastive decoding weighted by the entropy the context induces.

    Three arms, all from their LMWrapper.generate_contrast:
        rag         mode='naive', with-context prompt      (defense off)
        closedbook  mode='naive', no-context prompt        (control)
        acd         mode='acd',   no-context + with-context as the positive

    Their prompts are few-shot, built by their `_get_few_shots`. The shots
    are held out of the evaluation slice by the runner and passed in, because
    a shot drawn from the eval items would leak.
    """
    name, arms = "acd", ("rag", "closedbook", "acd")

    def __init__(self, base=BASE, shots=None, max_new_tokens=32):
        sys.path.insert(0, str(TP / "ACD"))
        import torch
        from transformers import AutoTokenizer, GenerationConfig
        from generation.gen_wrapper import LMWrapper      # their code
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(base)
        self.tok.add_special_tokens({"pad_token": "<PAD>"})  # their line
        self.tok.padding_side = "left"                       # their line
        # their signature exactly: no dtype argument, it picks its own
        self.model = LMWrapper(model_name_or_path=base, cache_dir=None,
                               device_map="auto", max_memory={0: "45GiB"},
                               offload_folder=None)
        self.model.gen_model.resize_token_embeddings(len(self.tok))
        self.model.gen_model.config.pad_token = self.tok.pad_token
        self.cfg = GenerationConfig(max_new_tokens=max_new_tokens,
                                    pad_token_id=self.tok.pad_token_id)
        self.fs = build_acd_fewshots(shots or [])

    def _gen(self, prompt, prompt_pos, mode):
        dev = self.model.gen_model.device
        ids = self.tok(prompt, return_tensors="pt").to(dev).input_ids
        ids_pos = (self.tok(prompt_pos, return_tensors="pt").to(dev).input_ids
                   if prompt_pos is not None else None)
        with self.torch.no_grad():
            out = self.model.generate_contrast(
                ids, ids_pos, num_beams=1, do_sample=False,
                generation_config=self.cfg, mode=mode)
        return self.tok.decode(out[0][len(ids[0]):],
                               skip_special_tokens=True).strip()

    def answer(self, question, passages, gold=None):
        p_ctx = acd_prompt(self.fs["with_context"], question, _ctx(passages))
        p_no = acd_prompt(self.fs["without_context"], question, None)
        return {"rag": self._gen(p_ctx, None, "naive"),
                "closedbook": self._gen(p_no, None, "naive"),
                "acd": self._gen(p_no, p_ctx, "acd")}


def build_acd_fewshots(shots):
    """Their `_get_few_shots`, reproduced."""
    def block(with_context):
        out = ["Answer the following questions:\n\n"]
        for s in shots:
            ctx = s["context"]
            ctx = ctx + "..." if ctx[-1] != "." else ctx          # their line
            ans = s["answers"][0] if isinstance(s["answers"], list) else s["answers"]
            out.append(f"Context: {ctx}\nQuestion: {s['question']}\nAnswer: {ans}\n"
                       if with_context else
                       f"Question: {s['question']}\nAnswer: {ans}\n")
        j = "\n".join(out)
        return j if j[-1] == "\n" else j + "\n"
    return {"with_context": block(True), "without_context": block(False)}


def acd_prompt(fewshots, question, context):
    """Their `get_dataset_for_generation`, base-model branch."""
    body = (f"Context: {context}\nQuestion: {question}\n" if context is not None
            else f"Question: {question}\n")
    nl = "\n" if fewshots[-2:] != "\n\n" else ""
    return fewshots + nl + body


# ---------------------------------------------------------------- SCR
class SCR(Defense):
    """Shows the model its closed-book answer and the document, asks it to judge.

    Their Prompter with the naturalqa profile and task_type cot_situated;
    their pipeline takes the final line of the generation.
    """
    name, arms = "scr", ("rag", "closedbook", "scr")

    def __init__(self, base=BASE, n_shot=3, scr_max_new_tokens=256):
        sys.path.insert(0, str(TP / "situated_faithfulness"))
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from prompter import Prompter                      # their code
        self.torch = torch
        self.n = scr_max_new_tokens
        self.tok = AutoTokenizer.from_pretrained(base)
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(
            base, torch_dtype=torch.bfloat16, device_map="auto",
            low_cpu_mem_usage=True)
        self.model.eval()
        self.P = Prompter(model_name=base, dataset_name="naturalqa",
                          n_shot=n_shot)

    def _gen(self, prompt, n=32):
        ids = self.tok(prompt, return_tensors="pt").to(self.model.device)
        with self.torch.no_grad():
            out = self.model.generate(**ids, max_new_tokens=n, do_sample=False,
                                      pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(out[0, ids.input_ids.shape[-1]:],
                               skip_special_tokens=True).strip()

    def _qa_prompt(self, question, context=None):
        """The cell's convention for both baseline arms: their instruction,
        through the model's chat template. A bare Context/Question/Answer
        string scores several points higher and is not what the recorded run
        measured."""
        if context is None:
            user = ("Answer the following question with one or few words.\n\n"
                    f"Question: {question}\nAnswer:")
        else:
            user = (f"Given the following information:\n{context}\n\n"
                    "Answer the following question based on the given "
                    f"information with one or few words.\n\n"
                    f"Question: {question}\nAnswer:")
        return self.tok.apply_chat_template(
            [{"role": "user", "content": user}],
            tokenize=False, add_generation_prompt=True)

    def answer(self, question, passages, gold=None):
        ctx = _ctx(passages)
        closed = self._gen(self._qa_prompt(question))
        rag = self._gen(self._qa_prompt(question, ctx))
        item = {"question": question, "internal_answer": closed,
                "model_doc_answer": rag, "docs": [{"text": ctx}]}
        raw = self._gen(self.P.generate_text_input(
            task_type="cot_situated", eval_item=item), n=self.n)
        return {"closedbook": closed, "rag": rag,
                "scr": raw.split("\n")[-1].strip()}


# ---------------------------------------------------------------- DyPRAG
class DyPRAG(Defense):
    """Passage -> rank-2 adapter, averaged over passages, injected once.

    Their released test.py: one delta per passage, averaged, injected, and
    the passages are then NOT in the prompt. Not a choice of ours, which is
    the whole reason this class exists rather than a guess about top-k.

    Needs the trained projector checkpoint; the runner supplies its path.
    """
    name, arms = "dyprag", ("rag", "closedbook", "dyprag")

    PROJECTOR = TP / "DyPRAG" / "projector_dl" / \
        "llama3-8b-p32-1ep-main-2400sample.pt"

    def __init__(self, base=BASE, projector_path=None):
        path = pathlib.Path(projector_path or self.PROJECTOR)
        if not path.exists():
            raise SystemExit(
                f"DyPRAG needs its parameter translator at {path}. It is a "
                "trained checkpoint, not a prompt. Refusing to run rather "
                "than silently falling back to plain RAG.")
        sys.path.insert(0, str(TP / "DyPRAG" / "src"))
        sys.path.insert(0, str(REPO / "scripts"))
        import torch
        from peft import LoraConfig, TaskType, get_peft_model
        # their modules read ROOT_DIR at import time, and theirs is an
        # absolute path on the authors' machine, so it is set first
        import root_dir_path
        root_dir_path.ROOT_DIR = str(TP / "DyPRAG")
        from utils import get_model, predict               # their code
        from projector import ParameterTranslator          # their code
        import dyprag_vs_corpus_poisoning as DV            # our factored MLP
        self.torch, self.predict = torch, predict
        # their delta_inject/remove, re-expressed for a factored MLP; the
        # original runner documents why. Reused rather than re-derived.
        self.inject = DV.delta_inject_factored
        self.remove = DV.delta_remove_factored
        # their get_model returns three things, and the runner wraps the
        # model with the LoRA layout delta_inject writes into. Skipping the
        # wrap leaves nowhere for the deltas to land.
        self.model, self.tok, self.cfg = get_model(base)
        self.tok.pad_token = self.tok.eos_token
        self.model = get_peft_model(self.model, LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            target_modules=["down_proj", "gate_proj", "up_proj"],
            inference_mode=False, r=2, lora_alpha=32, lora_dropout=0))
        cfgm = self.model.config
        self.projector = ParameterTranslator(
            ["down_proj", "up_proj", "gate_proj"],
            list(range(cfgm.num_hidden_layers)),
            cfgm.hidden_size, cfgm.intermediate_size,
            2, 32).to(self.model.device)       # their lora_rank, projector_p
        ck = torch.load(path, map_location=self.model.device,
                        weights_only=False)
        self.projector.load_state_dict(ck["model_state_dict"])
        self.projector.eval()

    def answer(self, question, passages, gold=None):
        # their test.py: one delta per passage, averaged, injected once
        deltas = []
        for psg in passages:
            tokens = self.tok(psg, padding=True, truncation=True,
                              return_tensors="pt",
                              max_length=3000).to(self.model.device)
            with self.torch.no_grad():
                out = self.model(tokens.input_ids, output_hidden_states=True)
                deltas.append(self.projector(out.hidden_states[-1][:, -1, :]))
        merged = {k: self.torch.stack([d[k] for d in deltas]).mean(dim=0)
                  for k in deltas[0]}
        g = lambda psgs: self.predict(self.model, self.tok, self.cfg, question,
                                      with_cot=False, passages=psgs).strip()
        rag, closed = g(passages), g(None)
        self.inject(self.model, merged)
        try:
            defended = g(None)      # passage is in the weights, not the prompt
        finally:
            self.remove(self.model, merged)
        return {"rag": rag, "closedbook": closed, "dyprag": defended}


LOADERS = {"coiecd": COIECD, "acd": ACD, "scr": SCR, "dyprag": DyPRAG}


def load(name, base=BASE, **kw):
    if name not in LOADERS:
        raise SystemExit(f"unknown defense {name!r}; have {sorted(LOADERS)}")
    return LOADERS[name](base, **kw)
