"""Reacher correction with lossless observational evidence for every step.

The only behavioural changes are the original Revision-3 correction: the task
termination hook returns None and the wrapper termination hook returns False.
Every other hook calls its native implementation exactly once. Install before
the case's actual reset; no reset is inferred or manufactured by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


def _array(value: Any):
    return None if value is None else np.asarray(value).copy().tolist()


def _time(physics: Any):
    value = getattr(physics, "time", None)
    return None if value is None else float(value() if callable(value) else value)


def _snapshot(wrapper: Any) -> dict[str, Any]:
    physics = wrapper.env.physics
    task = wrapper.env.task
    return {
        "physics.time": _time(physics),
        "qpos": _array(getattr(physics.data, "qpos", None)),
        "qvel": _array(getattr(physics.data, "qvel", None)),
        "target_qpos": _array(getattr(task, "target_qpos", None)),
        "qpos_threshold": float(getattr(task, "qpos_threshold", np.nan)),
    }


def _control_env(env: Any):
    seen = set()
    while hasattr(env, "_env") and id(env) not in seen:
        seen.add(id(env))
        env = env._env
    return env


def _scalar(value: Any):
    if value is None:
        return None
    if isinstance(value, (bool, str, int, float)):
        return value
    if np.isscalar(value):
        return value.item()
    return repr(value)


@dataclass
class ReacherSuccessTracker:
    predicate: Callable[[Any], bool]
    events: list[bool] = field(default_factory=list)
    _cursor: int = 0
    reset_calls: int = 0
    internal_reset_events: list[dict[str, Any]] = field(default_factory=list)
    wrapper: Any = None
    reset_events: list[dict[str, Any]] = field(default_factory=list)
    dm_reset_events: list[dict[str, Any]] = field(default_factory=list)
    initialize_episode_events: list[dict[str, Any]] = field(default_factory=list)
    micro_steps: list[dict[str, Any]] = field(default_factory=list)
    env_steps: list[dict[str, Any]] = field(default_factory=list)
    task_termination_calls: list[dict[str, Any]] = field(default_factory=list)
    initial_state: Any = None
    inner_bindings: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    _wrapper_reset_depth: int = 0
    _dm_step_depth: int = 0
    _original: Any = None
    _bound_env_id: Any = None
    _bound_task_id: Any = None

    def record(self, physics: Any) -> bool:
        if self.wrapper is None:
            value = bool(self.predicate(physics))
            self.events.append(value)
            return value
        original_result = self._original(physics)
        value = original_result is not None
        state = _snapshot(self.wrapper)
        qpos, target = state["qpos"], state["target_qpos"]
        independent = False if target is None else bool(
            np.all(np.abs(np.asarray(qpos) - np.asarray(target)) < state["qpos_threshold"])
        )
        index = len(self.events)
        self.events.append(bool(value))
        evidence = {
            "event_index": index,
            "predicate": bool(value),
            "independent_predicate": independent,
            "original_termination_result": _scalar(original_result),
            "wrapper_terminated_return": False,
            "state_at_predicate": state,
        }
        if self.micro_steps and "event_index" not in self.micro_steps[-1]:
            self.micro_steps[-1].update(evidence)
        else:
            # Keep synthetic callback evidence, but fail-closed runtime gates
            # must reject any callback that lacks an actual dm_control step.
            self.diagnostics.append({"kind": "predicate_without_dm_step", **evidence})
        return bool(value)

    def consume_step(self) -> bool:
        start, end = self._cursor, len(self.events)
        recent = self.events[start:end]
        if not recent:
            raise RuntimeError("Reacher environment step has no recorded microstep predicate")
        self._cursor = end
        any_label, end_label = bool(any(recent)), bool(recent[-1])
        if self.wrapper is not None:
            self.env_steps.append({
                "env_step": len(self.env_steps) + 1,
                "event_start": start,
                "event_end": end,
                "microstep_count": end - start,
                "success_any_in_step": any_label,
                "success_at_step_end": end_label,
                "state": _snapshot(self.wrapper),
                "reset_calls": self.reset_calls,
                "dm_reset_calls": len(self.dm_reset_events),
                "internal_reset_event_count": len(self.internal_reset_events),
            })
        return any_label

    def export_record(self) -> dict[str, Any]:
        """Return a JSON-ready complete record; this performs no simulation."""
        return {
            "schema_version": "reacher_correction_record_v2",
            "action_repeat": None if self.wrapper is None else int(self.wrapper.action_repeat),
            "initial_state": self.initial_state,
            "events": list(self.events),
            "tracker_events": list(self.events),
            "micro_steps": list(self.micro_steps),
            "env_steps": list(self.env_steps),
            "success_any_in_step": [x["success_any_in_step"] for x in self.env_steps],
            "success_at_step_end": [x["success_at_step_end"] for x in self.env_steps],
            "step_any_labels": [x["success_any_in_step"] for x in self.env_steps],
            "step_end_labels": [x["success_at_step_end"] for x in self.env_steps],
            "physics_steps": [{"env_step": x["env_step"], **x["state"]} for x in self.env_steps],
            "event_offsets": [0] + [x["event_end"] for x in self.env_steps],
            "reset_calls": self.reset_calls,
            "reset_count": self.reset_calls,
            "reset_events": list(self.reset_events),
            "dm_reset_calls": len(self.dm_reset_events),
            "dm_reset_events": list(self.dm_reset_events),
            "initialize_episode_calls": len(self.initialize_episode_events),
            "initialize_episode_events": list(self.initialize_episode_events),
            "internal_reset_events": list(self.internal_reset_events),
            "task_termination_calls": list(self.task_termination_calls),
            "inner_bindings": list(self.inner_bindings),
            "diagnostics": list(self.diagnostics),
            "unconsumed_events": len(self.events) - self._cursor,
            "label_semantics": {
                "success_any_in_step": "OR of original qpos predicates across this environment step",
                "success_at_step_end": "last original qpos predicate in this environment step",
                "predicate": "all(abs(qpos-target_qpos) < qpos_threshold); no angle wrapping",
            },
        }


def install_nonterminating_reacher(wrapper: Any) -> ReacherSuccessTracker:
    """Install before native reset; retain and count all actual reset calls."""
    if getattr(wrapper, "_revision3_tracker", None) is not None:
        return wrapper._revision3_tracker
    if getattr(wrapper, "_task_name", None) != "qpos_match":
        raise ValueError("Revision-3 patch requires Reacher qpos_match")
    tracker = ReacherSuccessTracker(predicate=lambda _physics: False, wrapper=wrapper)

    def phase():
        if tracker._dm_step_depth:
            return "during_action"
        return "explicit_wrapper_reset" if tracker._wrapper_reset_depth else "outside_wrapper_reset"

    def attach_inner():
        env, task = wrapper.env, wrapper.env.task
        if tracker._bound_env_id == id(env) and tracker._bound_task_id == id(task):
            return
        control = _control_env(env)
        tracker._bound_env_id, tracker._bound_task_id = id(env), id(task)
        original = task.get_termination
        tracker._original = original
        tracker.predicate = lambda physics: original(wrapper.env.physics if physics is None else physics) is not None
        tracker.inner_bindings.append({
            "binding_index": len(tracker.inner_bindings),
            "event_count": len(tracker.events),
            "reset_calls": tracker.reset_calls,
            "control_timestep": float(control.control_timestep()) if hasattr(control, "control_timestep") else None,
        })
        wrapper._revision3_original_get_termination = original

        def nonterminating_get_termination(_physics):
            tracker.task_termination_calls.append({
                "call_index": len(tracker.task_termination_calls),
                "physics.time": _time(_physics),
                "returned": None,
            })
            return None

        task.get_termination = nonterminating_get_termination
        if hasattr(task, "initialize_episode"):
            native_initialize = task.initialize_episode

            def initialize_episode(*args, **kwargs):
                entry = {"index": len(tracker.initialize_episode_events), "phase": phase(), "event_count": len(tracker.events)}
                tracker.initialize_episode_events.append(entry)
                return native_initialize(*args, **kwargs)

            task.initialize_episode = initialize_episode
        if hasattr(control, "reset"):
            native_control_reset = control.reset

            def control_reset(*args, **kwargs):
                entry = {"index": len(tracker.dm_reset_events), "phase": phase(), "event_count": len(tracker.events), "before": _snapshot(wrapper)}
                tracker.dm_reset_events.append(entry)
                if tracker._dm_step_depth:
                    tracker.internal_reset_events.append({"kind": "actual_control_reset_during_action", "event_count": len(tracker.events)})
                result = native_control_reset(*args, **kwargs)
                entry["after"] = _snapshot(wrapper)
                return result

            control.reset = control_reset
        if hasattr(env, "step"):
            native_dm_step = env.step

            def monitored_dm_step(action, *args, **kwargs):
                before = _snapshot(wrapper)
                if tracker.initial_state is None:
                    tracker.initial_state = before
                pending = bool(getattr(control, "_reset_next_step", False))
                row = {"micro_step": len(tracker.micro_steps) + 1, "before": before, "pending_reset_before": pending}
                if pending:
                    tracker.internal_reset_events.append({"kind": "dm_control_pending_reset", "micro_step": row["micro_step"], "before": before})
                tracker._dm_step_depth += 1
                try:
                    result = native_dm_step(action, *args, **kwargs)
                finally:
                    tracker._dm_step_depth -= 1
                row.update(after=_snapshot(wrapper), pending_reset_after=bool(getattr(control, "_reset_next_step", False)))
                row["dm_step_type"] = _scalar(getattr(result, "step_type", None))
                row["dm_step_last"] = bool(result.last()) if hasattr(result, "last") else None
                tracker.micro_steps.append(row)
                return result

            env.step = monitored_dm_step

    attach_inner()
    # Reacher.reset can recompile its dm_control object when variations are
    # dirty. Rebind before the replacement object receives its first reset.
    if hasattr(wrapper, "compile_model"):
        native_compile = wrapper.compile_model

        def compile_model(*args, **kwargs):
            result = native_compile(*args, **kwargs)
            attach_inner()
            return result

        wrapper.compile_model = compile_model
    if hasattr(wrapper, "reset"):
        native_reset = wrapper.reset

        def counted_reset(*args, **kwargs):
            tracker.reset_calls += 1
            entry = {"call": tracker.reset_calls, "event_count": len(tracker.events), "before": _snapshot(wrapper)}
            tracker.reset_events.append(entry)
            tracker._wrapper_reset_depth += 1
            try:
                result = native_reset(*args, **kwargs)
            finally:
                tracker._wrapper_reset_depth -= 1
            entry["after"] = _snapshot(wrapper)
            return result

        wrapper.reset = counted_reset

    def recording_is_terminated(_step):
        tracker.record(wrapper.env.physics)
        return False

    wrapper._is_terminated = recording_is_terminated
    wrapper._revision3_tracker = tracker
    return tracker


def patch_metadata(wrapper: Any) -> dict[str, Any]:
    task = wrapper.env.task
    target = getattr(task, "target_qpos", None)
    return {
        "task_name": getattr(wrapper, "_task_name", None),
        "qpos_threshold": float(getattr(task, "qpos_threshold", np.nan)),
        "target_qpos_shape": None if target is None else list(np.asarray(target).shape),
        "task_get_termination_returns": None,
        "wrapper_action_repeat": int(getattr(wrapper, "action_repeat", -1)),
        "tracker_installed": getattr(wrapper, "_revision3_tracker", None) is not None,
        "record_schema": "reacher_correction_record_v2",
    }
