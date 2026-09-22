"""Make AgentDojo's `local` provider speak the OpenAI content schema.

AgentDojo builds message content as its own block type:

    {"type": "text", "content": "..."}

The OpenAI chat-completions schema wants the text under `text`, not `content`:

    {"type": "text", "text": "..."}

`LocalLLM.query` passes its blocks through untouched, so every request to a
strictly-validating OpenAI-compatible server (vLLM >= 0.19 is strict) returns
HTTP 400 with a pydantic "Field required" error naming `text`. Nothing raises:
AgentDojo catches it, the turn produces no output, and the task scores
`utility=False, security=False`.

That failure mode is dangerous rather than merely annoying. A harness in this
state reports **0% ASR and 0% utility for every condition**, which looks exactly
like "the attack does not land here" or "this defense blocks everything" -- a
plausible, publishable-looking number produced by a transport bug. The floor
check in calibrate_control.py exists to catch this class of thing, and the
utility floor is what caught it.

The fix is applied at the transport boundary rather than by reimplementing
`query`, so AgentDojo's message-construction logic stays authoritative and this
shim keeps working if that logic changes.

Import this module before building a pipeline; it patches on import.
"""
from __future__ import annotations

from agentdojo.agent_pipeline.llms import local_llm as _ll

_original = _ll.chat_completion_request


def _normalise(content):
    """AgentDojo content -> something the OpenAI schema accepts.

    Flattens block lists to a plain string. A plain string is valid `content`
    for every role, avoids guessing at per-part schemas, and cannot silently
    drop a non-text part -- anything unexpected is stringified visibly rather
    than discarded.
    """
    if content is None or isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("content") or content.get("text") or str(content)
    if isinstance(content, (list, tuple)):
        out = []
        for part in content:
            if isinstance(part, str):
                out.append(part)
            elif isinstance(part, dict):
                out.append(part.get("content") or part.get("text") or str(part))
            else:
                out.append(str(part))
        return "".join(out)
    return str(content)


def _patched(client, model, messages, **kwargs):
    fixed = []
    for m in messages:
        m = dict(m)
        m["content"] = _normalise(m.get("content"))
        # tool_calls carry their own schema and must not be touched
        fixed.append(m)
    return _original(client, model=model, messages=fixed, **kwargs)


if getattr(_ll.chat_completion_request, "__name__", "") != "_patched":
    _ll.chat_completion_request = _patched
