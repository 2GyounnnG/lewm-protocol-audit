"""Runtime patch for the Revision-3 Reacher rerun.

The D1 full-budget harness set the returned ``terminated`` flag to false, but
that is too late for dm_control: ``control.Environment`` has already marked
the next call as a reset when the task's ``get_termination`` returned 0.0.
This small adapter preserves the task's qpos predicate while making the
dm_control task non-terminating.  It records the predicate at every internal
action-repeat call, so the outer harness can still emit one success label per
recorded planning step.

The module is intentionally dependency-light.  It is copied to the GPU
container together with the frozen D1 code and imported by the patched worker.
It does not alter the threshold, target, action, dynamics, or reset method.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np


@dataclass
class ReacherSuccessTracker:
    """Collect qpos-match results for one high-level wrapper step."""

    predicate: Callable[[Any], bool]
    events: list[bool] = field(default_factory=list)
    _cursor: int = 0
    reset_calls: int = 0
    internal_reset_events: list[dict[str, Any]] = field(default_factory=list)
    physics_steps: list[dict[str, Any]] = field(default_factory=list)
    step_any_labels: list[bool] = field(default_factory=list)
    step_end_labels: list[bool] = field(default_factory=list)
    snapshotter: Callable[[Any], dict[str, Any]] | None = None

    def record(self, physics: Any) -> bool:
        value = bool(self.predicate(physics))
        self.events.append(value)
        if self.snapshotter is not None:
            self.physics_steps.append(self.snapshotter(physics))
        return value

    def consume_step(self) -> bool:
        """Return whether the current wrapper step reached the target.

        The wrapper's native ``action_repeat`` is normally two.  We do not
        hard-code that number: every predicate event since the previous call
        belongs to this high-level step.  An empty slice is treated as a
        conservative predicate check at the current physics state.
        """

        recent = self.events[self._cursor :]
        self._cursor = len(self.events)
        if recent:
            any_label = bool(any(recent))
            end_label = bool(recent[-1])
        else:
            any_label = bool(self.predicate(None))
            end_label = any_label
        self.step_any_labels.append(any_label)
        self.step_end_labels.append(end_label)
        return any_label


def install_nonterminating_reacher(wrapper: Any) -> ReacherSuccessTracker:
    """Disable dm_control's implicit success reset and retain the predicate.

    ``wrapper`` must be the unwrapped
    ``ReacherDMControlWrapper(task='qpos_match')``.  The original bound
    ``task.get_termination`` is captured before replacement.  The wrapper's
    ``_is_terminated`` is replaced only to record a predicate result and
    always return ``False``; this lets ``DMControlWrapper.step`` finish its
    normal action-repeat loop without changing physics or action scaling.
    """

    if getattr(wrapper, "_revision3_tracker", None) is not None:
        return wrapper._revision3_tracker
    task = wrapper.env.task
    if getattr(wrapper, "_task_name", None) != "qpos_match":
        raise ValueError("Revision-3 patch requires Reacher qpos_match")
    original = task.get_termination

    def predicate(physics: Any) -> bool:
        # ``original`` is a bound method and must see the live physics object.
        # The fallback is used only by a zero-event synthetic test; runtime
        # calls always pass a physics object from _is_terminated.
        if physics is None:
            physics = wrapper.env.physics
        return original(physics) is not None

    def snapshot(physics: Any) -> dict[str, Any]:
        data = getattr(physics, 'data', None)
        task_obj = wrapper.env.task
        target = getattr(task_obj, 'target_qpos', None)
        return {
            "physics.time": float((getattr(physics, "time")() if callable(getattr(physics, "time", None)) else getattr(physics, "time", np.nan))),
            'qpos': np.asarray(getattr(data, 'qpos', []), dtype=np.float64).copy().tolist(),
            'qvel': np.asarray(getattr(data, 'qvel', []), dtype=np.float64).copy().tolist(),
            'target_qpos': np.asarray(target if target is not None else [], dtype=np.float64).copy().tolist(),
        }

    tracker = ReacherSuccessTracker(predicate=predicate, snapshotter=snapshot)

    # The method worker binds (and therefore resets) before installing this
    # adapter, while the LeWM worker installs it before World.evaluate.  Count
    # wrapper-level resets when the method exists, and separately detect a
    # dm_control call that entered Environment.step with _reset_next_step set.
    if hasattr(wrapper, "reset"):
        native_reset = wrapper.reset

        def counted_reset(*args: Any, **kwargs: Any):
            tracker.reset_calls += 1
            return native_reset(*args, **kwargs)

        wrapper.reset = counted_reset
    if hasattr(wrapper.env, "step"):
        native_dm_step = wrapper.env.step
        control_env = getattr(wrapper.env, "_env", wrapper.env)

        def monitored_dm_step(action: Any, *args: Any, **kwargs: Any):
            pending = bool(getattr(control_env, "_reset_next_step", False))
            result = native_dm_step(action, *args, **kwargs)
            if pending:
                tracker.internal_reset_events.append(
                    {"kind": "dm_control_pending_reset", "step_count": int(getattr(control_env, "_step_count", -1))}
                )
            return result

        wrapper.env.step = monitored_dm_step

    def nonterminating_get_termination(_physics: Any) -> None:
        # dm_control uses this result to set _reset_next_step.  Returning None
        # is the critical fix; success is recorded independently below.
        return None

    def recording_is_terminated(_step: Any) -> bool:
        tracker.record(wrapper.env.physics)
        return False

    task.get_termination = nonterminating_get_termination
    wrapper._is_terminated = recording_is_terminated
    wrapper._revision3_original_get_termination = original
    wrapper._revision3_tracker = tracker
    return tracker


def patch_metadata(wrapper: Any) -> dict[str, Any]:
    """Return auditable runtime facts after installation."""

    task = wrapper.env.task
    target = getattr(task, "target_qpos", None)
    return {
        "task_name": getattr(wrapper, "_task_name", None),
        "qpos_threshold": float(getattr(task, "qpos_threshold", np.nan)),
        "target_qpos_shape": None if target is None else list(np.asarray(target).shape),
        "task_get_termination_returns": task.get_termination(wrapper.env.physics),
        "wrapper_action_repeat": int(getattr(wrapper, "action_repeat", -1)),
        "tracker_installed": getattr(wrapper, "_revision3_tracker", None) is not None,
    }

