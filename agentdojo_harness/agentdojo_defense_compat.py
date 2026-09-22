"""Fix AgentDojo's `spotlighting_with_delimiting` defense, which cannot run.

AgentDojo 0.1.33 builds the defense's tool-output formatter like this
(agent_pipeline.py:239):

    tool_output_formatter = lambda result: f"<<{tool_output_formatter(result)}>>"

The name inside the lambda resolves at call time to the lambda itself, not to
the formatter it was meant to wrap, so the first tool output recurses until
`RecursionError: maximum recursion depth exceeded`. The pipeline constructs
fine; it dies on use.

The practical consequence is worth stating: **Spotlighting cannot be evaluated
in stock AgentDojo 0.1.33 at all.** It is one of the better-known prompt-
injection defenses (Hines et al., arXiv 2403.14720) and a registry entry in this
SoK, and any study that selected defenses by "what runs in AgentDojo" would have
silently dropped it -- not because it failed, but because the harness crashed.
That is the same class of problem as the transport bug in local_llm_compat.py:
an infrastructure fault that presents as a result about a defense.

The fix wraps `tool_result_to_str`, which is what the original clearly intended,
and rebinds it on the constructed pipeline's ToolsExecutor.

Import before building a pipeline; patches on import.
"""
from __future__ import annotations

from agentdojo.agent_pipeline import agent_pipeline as _ap
from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, tool_result_to_str

_original_from_config = _ap.AgentPipeline.from_config


def _spotlight(result):
    return f"<<{tool_result_to_str(result)}>>"


def _find_executors(element, found=None):
    """Walk a pipeline's nested elements for ToolsExecutor instances."""
    found = [] if found is None else found
    if isinstance(element, ToolsExecutor):
        found.append(element)
    for attr in ("elements", "pipeline"):
        sub = getattr(element, attr, None)
        if isinstance(sub, (list, tuple)):
            for e in sub:
                _find_executors(e, found)
        elif sub is not None:
            _find_executors(sub, found)
    return found


def _patched_from_config(cls, config):
    pipeline = _original_from_config(config)
    if getattr(config, "defense", None) == "spotlighting_with_delimiting":
        for ex in _find_executors(pipeline):
            ex.output_formatter = _spotlight
    return pipeline


if not getattr(_ap.AgentPipeline.from_config, "_spotlighting_patched", False):
    _patched_from_config._spotlighting_patched = True
    _ap.AgentPipeline.from_config = classmethod(_patched_from_config)
