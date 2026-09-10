"""The SoK's own defenses, wired in as AgentDojo pipeline elements.

AgentDojo ships six defenses of its own. Neither of the two whose transfer
queues this project cares about - DataSentinel and RobustRAG - is among them,
which is what blocked running the corpus mechanisms against them in an agent
setting. This module supplies both, and is explicit about how faithful each one
is, because they are not equally faithful.

  DataSentinelElement   GENUINE. Calls the authors' released LoRA checkpoint
                        through their own unmodified detect(), over a local
                        sidecar (see datasentinel_service.py for why a process
                        boundary rather than an import). Nothing about the
                        defense is reimplemented.

  RobustRAGElement      A PORT, and labelled as one. The keyword extraction and
                        filtering are the authors' released code, imported
                        directly. The substrate mapping - what counts as an
                        independently-retrieved "passage" inside an agent
                        trajectory - is ours, and RobustRAG's certifiable
                        robustness argument does NOT survive it. See the class
                        docstring.
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Literal

from agentdojo.agent_pipeline.pi_detector import PromptInjectionDetector


class DataSentinelElement(PromptInjectionDetector):
    """DataSentinel as an AgentDojo tool-output detector.

    DataSentinel's interface is already exactly what this hook wants: text in,
    contaminated/clean out. Detection is behavioural rather than pattern-based -
    the data is wrapped in an instruction to repeat a secret key, and failing to
    repeat it is the detection signal - which is worth keeping in mind when
    reading results, because it is why the defense is sensitive to whether a
    payload hijacks *the current turn*.
    """

    def __init__(self, endpoint: str = "http://127.0.0.1:1112/detect",
                 mode: Literal["message", "full_conversation"] = "message",
                 raise_on_injection: bool = False, timeout: float = 120.0):
        super().__init__(mode=mode, raise_on_injection=raise_on_injection)
        self.endpoint = endpoint
        self.timeout = timeout

    def detect(self, tool_output: str) -> bool:
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps({"text": tool_output or ""}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            body = json.loads(r.read())
        if "error" in body:
            # Never silently treat a detector failure as "clean" - that would
            # quietly turn a broken run into a defense-fails result.
            raise RuntimeError(f"DataSentinel sidecar error: {body['error']}")
        return bool(body["contaminated"])


class RobustRAGElement(PromptInjectionDetector):
    """RobustRAG's isolate-then-aggregate, ported onto agent tool outputs.

    **This is a port, not a reconstruction, and the difference is load-bearing.**

    RobustRAG answers a question over k independently-retrieved passages: it
    queries the LLM on each passage alone, extracts keywords from each isolated
    response, keeps only phrases appearing in at least min(beta, alpha*k) of
    them, and re-answers with those as hints. Its certifiable-robustness
    guarantee rests on the passages being interchangeable evidence for one
    question, so that corrupting a bounded number of them cannot swing the
    aggregate.

    An agent trajectory does not satisfy that. Tool outputs are sequential and
    dependent - the result of step 2 is meaningful only given step 1 - so
    isolating them destroys the task rather than protecting it, and the
    certification argument does not carry over at all.

    What DOES satisfy it is a single tool output that returns k independent
    items: a search over emails, files or messages. That is a genuine
    isolate-then-aggregate substrate, and it is the only place this element
    applies. It splits such an output into items, keeps the phrases that recur
    across at least the threshold fraction of them, and drops the rest - so an
    injected instruction sitting in one item of many is filtered out, while
    content corroborated across items survives.

    Consequences to state when reporting anything from this element:
      * no certificate. Certified robustness is not being measured here.
      * it is a filter over multi-item outputs, not an answer aggregator.
      * on single-item tool outputs it is a no-op by construction, and those
        runs must not be read as the defense holding.
    """

    #: Splits a multi-item tool output. AgentDojo's search-style tools return
    #: newline-separated records; a blank line or a leading "- " both mark an
    #: item boundary in the suites' formatting.
    _ITEM_SPLIT = re.compile(r"\n\s*\n|\n(?=- )")

    def __init__(self, endpoint: str = "http://127.0.0.1:1113/aggregate",
                 relative_threshold: float = 0.3, absolute_threshold: int = 3,
                 min_items: int = 3, timeout: float = 60.0,
                 mode: Literal["message", "full_conversation"] = "message"):
        super().__init__(mode=mode, raise_on_injection=False)
        self.endpoint = endpoint
        self.relative = relative_threshold
        self.absolute = absolute_threshold
        self.min_items = min_items
        self.timeout = timeout
        self.applied = 0
        self.skipped_single_item = 0

    def _aggregate(self, items: list[str]) -> list[str]:
        """Defer to the sidecar running the authors' keyword machinery."""
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps({"items": items, "relative": self.relative,
                             "absolute": self.absolute}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            body = json.loads(r.read())
        if "error" in body:
            raise RuntimeError(f"RobustRAG sidecar error: {body['error']}")
        return body["kept"]

    def detect(self, tool_output: str) -> bool:
        # This element rewrites rather than flags, so detect() always reports
        # False and the filtering happens in transform(). Keeping the flag off
        # matters: a True here would blank the whole message, which is the
        # opposite of what isolate-then-aggregate does.
        return False

    def transform(self, tool_output: str) -> str:  # pragma: no cover - not reached
        return tool_output

    def query(self, query, runtime, env=None, messages=(), extra_args=None):
        messages = list(messages)
        if messages and messages[-1].get("role") == "tool":
            content = messages[-1].get("content") or ""
            items = [i for i in self._ITEM_SPLIT.split(content) if i.strip()]
            if len(items) >= self.min_items:
                kept = self._aggregate(items)
                messages[-1]["content"] = "\n\n".join(kept) if kept else content
                self.applied += 1
            else:
                self.skipped_single_item += 1
        return query, runtime, env, messages, (extra_args or {})
