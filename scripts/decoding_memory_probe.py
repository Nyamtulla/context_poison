"""Where does llama2-13b x DecodingAgg spend 47 GB?

KeywordAgg runs this model fine. DecodingAgg OOMs on the first item, the same
way four times, with the card to itself. Two guesses were wrong by arithmetic:
the KV cache over 11 passages is ~6 GB at 13B, and preprocess_input's
all-positions softmax costs the same at 13B as at 7B because the vocabulary is
the same size. So measure each stage instead.
"""
import json, pathlib, sys
REPO = pathlib.Path(__file__).resolve().parents[0]
CS = pathlib.Path("/home/n646s681/context_sok")
sys.path.insert(0, str(CS / "third_party" / "RobustRAG"))
sys.path.insert(0, str(CS / "scripts"))
import torch
from src import models as rr_models
from src.defense import DecodingAgg
from src.models import HFModel
from src.prompt_template import LLAMA_TMPL
from poisonedrag_transfer import build_poisoned
import robustrag_matrix  # stop-token patch

RRAG = CS / "third_party" / "RobustRAG"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "NousResearch/Llama-2-13b-chat-hf"

def gb(): return torch.cuda.memory_allocated() / 1e9
def peak(): return torch.cuda.max_memory_allocated() / 1e9
def mark(tag): print(f"  {tag:<34} now {gb():6.2f} GB   peak {peak():6.2f} GB", flush=True)

rr_models.CONTEXT_MAX_TOKENS.setdefault(MODEL, 4096)
print(f"== {MODEL}", flush=True)
llm = HFModel(MODEL, LLAMA_TMPL)
mark("after model load")

class A: eta = 0.0; subsample_iter = 1
d = DecodingAgg(llm, A())
mark("after DecodingAgg init")

data = json.loads((RRAG / "data" / "open_nq.json").read_text())[:1]
it = data[0]
item = {"question": it["question"], "answer": it["correct answer"],
        "topk_content": build_poisoned(it, 10, 9, attack="badrag_dos"),
        "incorrect_answer": it.get("incorrect answer", []),
        "incorrect_context": it.get("incorrect_context", [])}

prompts = llm.wrap_prompt(item, as_multi_choice=False, seperate=True)
tl = [len(llm.tokenizer(p).input_ids) for p in prompts]
print(f"  per-passage prompt tokens: n={len(tl)} min={min(tl)} max={max(tl)}", flush=True)

try:
    torch.cuda.reset_peak_memory_stats()
    out = d.preprocess_input(item)
    mark("after preprocess_input")
except torch.cuda.OutOfMemoryError as e:
    print(f"  OOM inside preprocess_input at {gb():.2f} GB (peak {peak():.2f})", flush=True)
    raise SystemExit(1)

try:
    torch.cuda.reset_peak_memory_stats()
    pred, _ = d.query(item)
    mark("after full query")
    print(f"  pred: {str(pred)[:120]!r}", flush=True)
except torch.cuda.OutOfMemoryError:
    print(f"  OOM inside query at {gb():.2f} GB (peak {peak():.2f})", flush=True)
    raise SystemExit(1)
