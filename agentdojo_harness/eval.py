"""Minimal reimplementation of the `AgentTask` wrapper the transfer runners import.

The original lived in the IPIGuard reconstruction checkout's `run/` directory,
which no longer exists on this machine. Rather than recreate that whole checkout,
this reimplements the one thing the runners actually use against the installed
AgentDojo, so `agentdojo_harness/` is self-contained.

Scoring is AgentDojo's own, not ours. `TaskSuite.run_task_with_pipeline` returns

    (task_successful, injection_successful)

i.e. (utility, security). The runners expect

    (security, utility, token_usage)

so the order is swapped here, deliberately and in one place. Getting this
backwards would silently report a defense's utility as its attack-success rate,
which is exactly the kind of error that reads as a plausible result.

`security=True` means the injection task's goal was actually carried out, as
judged by the suite's own checker against the final environment state -- not a
regex over the reply.
"""
from __future__ import annotations


class AgentTask:
    """Namespace matching the original wrapper's call signature."""

    @staticmethod
    def run(pipeline, suite, injections, user_task, injection_task, token_usage=None):
        """Run one (user task, injection task) pair.

        Args:
            pipeline: the AgentPipeline to run.
            suite: the TaskSuite the tasks belong to.
            injections: placeholder -> injected text mapping, as produced by
                an attack's `.attack(user_task, injection_task)`.
            user_task / injection_task: the pair to run.
            token_usage: accepted and ignored. The original threaded a token
                counter through; AgentDojo does not surface per-call usage at
                this level, so it is returned unchanged rather than faked.

        Returns:
            (security, utility, token_usage) -- security first, matching the
            runners. See module docstring on the order swap.
        """
        utility, security = suite.run_task_with_pipeline(
            pipeline, user_task, injection_task, injections
        )
        return bool(security), bool(utility), (token_usage or {})
