from statemachine import State, StateMachine
from statemachine.factory import StateMachineMetaclass

import state_machine_operator.tracker as tracker


def create_state_machine_job(definition: dict, **extra_kwargs):
    """
    Create a JobStateMachine state machine.

    This tracks and orchestrates one full job.
    """
    states_instances = {
        state_id: State(**state_kwargs) for state_id, state_kwargs in definition["states"].items()
    }
    events = {}
    for event_name, transitions in definition["events"].items():
        for transition_data in transitions:
            source = states_instances[transition_data["from"]]
            target = states_instances[transition_data["to"]]
            transition = source.to(
                target,
                event=event_name,
                cond=transition_data.get("cond"),
                unless=transition_data.get("unless"),
            )
            if event_name in events:
                events[event_name] |= transition
            else:
                events[event_name] = transition

    attrs_mapper = {**extra_kwargs, **states_instances, **events}
    return StateMachineMetaclass("JobStateMachine", (StateMachine,), attrs_mapper)


def next_step_config(self, current_name):
    """
    Get the config for the next step.
    """
    # If we are completed or at start, go back to first step
    if current_name == "complete" or current_name == "start":
        next_step = self.workflow.first_step
    else:
        next_step = self.workflow.get_next_step(current_name)

    # Otherwise get next step
    return self.workflow.config_for_step(next_step)


def on_enter_start(self):
    """
    On start, prepare to keep track of jobs completed
    """
    # Each tracker is just for one job of each type
    if not hasattr(self, "trackers"):
        self.init_trackers()


def init_trackers(self):
    """
    Create a job tracker for each job.
    """
    self.trackers = {}
    for state_name, _ in self.states_map.items():
        if state_name in ["start", "complete"]:
            continue
        self.trackers[state_name] = self.tracker.Tracker(state_name, self.workflow)


def is_running(self, state_name=None):
    """
    Check if a state is active (running job) (defaults to current)
    """
    state_name = state_name or self.current_state.id
    return state_name == self.current_state.id


def is_failed(self, state_name=None):
    """
    Check if a state is failed (defaults to current)
    """
    state_name = state_name or self.current_state.id
    return getattr(self, f"{state_name}_failure", False) is True


def is_succeeded(self, state_name=None):
    """
    Check if a state is succeeded (defaults to current)
    """
    state_name = state_name or self.current_state.id
    return getattr(self, f"{state_name}_success", False) is True


def mark_succeeded(self, job=None, state_name=None):
    """
    Mark the current state succeeded (default) or another specific state.
    """
    tracker = self.trackers[self.current_state.id]
    tracker.save_log(job)
    state_name = state_name or self.current_state.id
    setattr(self, f"{state_name}_success", True)


def mark_failed(self, job=None, state_name=None):
    """
    Mark the current state failed (default) or another specific state.
    """
    tracker = self.trackers[self.current_state.id]
    tracker.save_log(job)
    state_name = state_name or self.current_state.id
    setattr(self, f"{state_name}_failure", True)


def mark_running(self, running_state):
    """
    Loop through states until we get to the running.
    Mark previous states as successful / completed.
    """
    for state in self.states:
        # This is based on logic we cannot get to a running state
        # unless the previous state was successful. It also assumes
        # "state" is input from a job, the name of a job step (and
        # not start or complete that are abstract).
        if state == running_state:
            return
        # If we get here, we have not hit the running state
        # We assume we completed previous states with success
        self.mark_succeeded(state_name=state)


def on_change(self):
    """
    Call to change to submit new jobs, etc.

    If a state has been marked as completed (success) we don't
    continue to run it.
    """
    # First check if this state already had success
    # If yes, we return early (and don't submit the job again)
    if self.is_succeeded():
        print(f"Stage {self.current_state.id} for job {self.jobid} is marked as successful.")
        return

    # If we failed, we also return. The required condition is not true so
    # it cannot cycle. We will want to remove these state machines.
    if self.is_failed():
        print(f"Stage {self.current_state.id} for job {self.jobid} is marked as failed.")
        return

    # We are completed, we don't submit a job but we complete the workflow
    if self.current_state.id == "complete":
        print(f"Job {self.jobid} is complete.")
        self.is_complete = True
        return

    # We haven't succeeded or failed - submit a new job!
    tracker = self.trackers[self.current_state.id]
    tracker.submit_job(self.jobid)


def cleanup(self):
    """
    Cleanup an entire state machine, meaning all jobs.
    """
    for step_name, step in self.trackers.items():
        try:
            step.cleanup(self.jobid)
        except Exception as e:
            print(f"Issue cleaning up tracker {step_name}: {e}")


def new_state_machine(config, jobid, tracker_type="kubernetes"):
    """
    New state machine creates a new JobStateMachine.

    It's a dynamic state machine, so we start at the step that needs
    to be submit.
    """
    states = {
        "start": {"initial": True, "final": False},
        "complete": {"initial": False, "final": True},
    }
    events = {"change": []}

    # Extra kwargs here are class functions and "on_enter_<state>" functions
    # TODO should we have on_enter_completed that deletes jobs?
    extra_kwargs = {
        "on_enter_start": on_enter_start,
        # Actions to mark as running, succeeded, or failed
        "mark_running": mark_running,
        "mark_succeeded": mark_succeeded,
        "mark_failed": mark_failed,
        # Booleans to check state
        "is_failed": is_failed,
        "is_succeeded": is_succeeded,
        "is_running": is_running,
        "is_complete": False,
        "jobid": jobid,
        "init_trackers": init_trackers,
        "workflow": config,
        "cleanup": cleanup,
        "tracker": tracker.load(tracker_type),
        "next_step_config": next_step_config,
    }

    last = None
    for i, job in enumerate(config.jobs):
        states[job] = {"initial": False, "final": False}
        if i != 0:
            # These booleans determine succcess (or TBA failure)
            # It is a condition on the change
            extra_kwargs[f"{last}_success"] = False
            extra_kwargs[f"{last}_failure"] = False
            events["change"].append({"from": last, "to": job, "cond": f"{last}_success"})
        else:
            # This is the first step, so not conditional,
            # But the next step will need to know this condition
            extra_kwargs[f"{job}_success"] = False
            extra_kwargs[f"{job}_failure"] = False
            events["change"].append({"from": "start", "to": job})

        # This ensures we run a function to submit the job when
        # we change state, which means we successfully finished
        # the previous step
        extra_kwargs[f"on_enter_{job}"] = on_change
        last = job

    # A boolean to indicate the sample has failed at some step
    # We don't retry because we assume a bad starting data point
    extra_kwargs["simulation_failed"] = False

    # Add last state (completed) and transition to it
    states["complete"] = {"initial": False, "final": True}
    events["change"].append({"from": job, "to": "complete", "cond": f"{job}_success"})
    extra_kwargs[f"{job}_success"] = False
    extra_kwargs[f"{job}_failure"] = False

    definition = {
        "states": states,
        "events": events,
    }
    return create_state_machine_job(definition, **extra_kwargs)
