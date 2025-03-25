# The manager is intended to be run in a container (as a service) to orchestrate
# a workflow.

import json
import logging
import math
import os
import random
import sys
import tempfile
import time

import state_machine_operator.defaults as defaults
import state_machine_operator.tracker as tracker
import state_machine_operator.utils as utils
from state_machine_operator.machine import new_state_machine

from .utils import timed

# Print debug for now
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class WorkflowManager:
    def __init__(
        self,
        workflow,
        scheduler=None,
        filesystem=None,
        workdir=None,
        registry=None,
        plain_http=False,
        quiet=False,
    ):
        """
        Initialize the WorkflowManager. Much of this logic used to be in setup,
        but it makes sense to be on the class instance init. State is derived
        from the Kubernetes cluster, and a state machine is created for each
        job sequence.
        """
        self.workflow = workflow

        # Set any defaults if needed
        self.scheduler = scheduler or defaults.scheduler
        self.prefix = self.workflow.prefix or defaults.prefix
        filesystem = filesystem or self.workflow.filesystem is not None

        # Working directory = first preference to command line
        self.workflow.set_workdir(workdir)
        self.quiet = quiet

        # Running modes (we only allow kubernetes for now)
        LOGGER.info(f" Job Prefix: [{self.prefix}]")
        LOGGER.info(f"  Scheduler: [{self.scheduler}]")

        # Keep a record of times and timestamps
        self.times = {}
        self.timestamps = {}

        if not filesystem:
            self.init_registry(registry, plain_http)
            LOGGER.info(f"   Registry: [{self.registry}]")
        else:
            # We want a filesystem but need to create a temporary location
            if not self.workflow.filesystem:
                filesystem = self.workflow.workdir or tempfile.mkdtemp()
                self.workflow.set_filesystem(filesystem)
            LOGGER.info(f"   Filesystem: [{filesystem}]")

        if self.scheduler not in defaults.supported_schedulers:
            raise ValueError(
                f"{self.scheduler} is not valid, please choose from {defaults.supported_schedulers}"
            )

        # Prepare tracker, an event driven workload manager
        self.setup_tracker()

    def setup_tracker(self):
        """
        Initialize tracker class and associated watchers
        """
        # This currently assumes one kind of tracker (flux or kubernetes)
        self.tracker = tracker.load(self.scheduler)

        # This is an empty (faux) watcher
        self.watcher = tracker.Watcher()

        # Does our tracker have a custom watchers?
        if hasattr(self.tracker, "Watcher"):
            self.watcher = self.tracker.Watcher()

    def init_registry(self, registry, plain_http=None):
        """
        Initialize the registry if it isn't defined in the workflow config
        """
        # Tack the registry into the workflow config to pass on to jobs
        self.registry = registry or defaults.registry
        self.plain_http = plain_http if plain_http is not None else True
        self.workflow.set_registry(self.registry, self.plain_http)

    def generate_id(self):
        """
        Generate a job id
        """
        number = random.choice(range(0, 99999999))
        jobid = self.prefix + str(number).zfill(9)
        # This is hugely unlikely to happen, but you never know!
        if jobid in self.trackers:
            return self.generate_id()
        return jobid

    @property
    def stages(self):
        """
        Return stages of workflow.
        """
        return list(self.workflow.jobs.keys())

    @timed
    def list_jobs_by_status(self):
        """
        Wrapper to tracker list jobs by status to allow timing
        """
        return self.tracker.list_jobs_by_status()

    def get_current_state(self):
        """
        Get the number of active and completed jobs.

        We assume any active or pending job in a sequence counts 1 toward
        the job. If all steps are completed, the workflow is complete.
        We always get the state directly from the cluster, because any
        other method might not be accurate. We don't want to submit
        new jobs over that. We also return all jobs to have if needed
        that coincide with the same data the states were derived from.
        """
        # Get jobs that are in the first stage to determine sequences active
        jobs = self.list_jobs_by_status()

        # Give a warning about unknown jobs
        # In practice, this is a state not properly accounted for
        if jobs["unknown"]:
            LOGGER.warning(f"Found {len(jobs['unknown'])} unknown jobs to investigate.")

        active_jobs = set()
        completions = set()
        failed_jobs = set()

        # The last step as success is a completion
        last_step = self.workflow.last_step

        # Any failed jobs are not considered further
        for job in jobs["failed"]:
            if job.jobid:
                failed_jobs.add(job.jobid)

        # First assess completions - the last step that is completed
        for job in jobs["success"]:

            # Unknown to this tracker or is completed/failed (a global state)
            if not job.jobid or not job.step_name or job.jobid in failed_jobs:
                continue

            # Completed
            if job.step_name == last_step:
                completions.add(job.jobid)

        # Queued jobs and running jobs indicate the active jobs
        for job in jobs["queued"] + jobs["running"]:
            if not job.jobid or job.jobid in completions or job.jobid in failed_jobs:
                continue
            active_jobs.add(job.jobid)

        # Finally, successful jobs that are not the last step
        # and haven't had their next state kicked off... we assume a failure
        # at once step is a failure in the entire job
        for job in jobs["success"]:
            if (
                job.step_name != last_step
                and job.jobid not in completions
                and job.jobid not in failed_jobs
            ):
                active_jobs.add(job.jobid)

        return {
            "completed": completions,
            "active": active_jobs,
            "jobs": jobs,
            "failed": failed_jobs,
        }

    def init_state(self):
        """
        Look at the state of the cluster and initialize trackers to match it.
        """
        self.trackers = {}

        # Determine current state of cluster, create state machine for each job
        # Note this will return steps from across a single state machine. If job:
        #    Successful (at the end) we have the result pushed
        #    Failed we won't continue (and shouldn't make a state machine
        #    Unknown (this shouldn't happen, let's show these)
        #    Running: we assume previous steps successful
        current_state = self.get_current_state()
        completed_jobs = current_state["completed"]
        jobs = current_state["jobs"]
        active_jobs = jobs["running"] + jobs["queued"]

        # Create a new state machine per active job. By the time we get here,
        # we already know there is a step name and jobid
        for job in active_jobs:
            # Get existing or new state machine for it
            state_machine = self.get_state_machine(job)
            # The job is active, kick off the next steps
            state_machine.mark_running(job.step_name)
            self.trackers[job.jobid] = state_machine

        # A succeeded job not in the last step needs to be monitored
        last_step = self.workflow.last_step
        for job in jobs["success"]:
            # Don't monitor if it's completed or we are already tracking
            if job.step_name == last_step or job.jobid in self.trackers:
                continue
            state_machine = self.get_state_machine(job)
            # This will mark all steps up to this one as succeeded
            state_machine.mark_running(job.step_name)
            # Transition to the next step. This will error if we already have
            try:
                state_machine.change()
                self.trackers[job.jobid] = state_machine
            except Exception:
                LOGGER.info(f"Step {job.step_name} for job {job.jobid} already transitioned")

        LOGGER.info(f"Manager running with {len(completed_jobs)} job sequence completions.")
        # TODO we likely want some logic to cleanup failed
        # But this might not always be desired

    def get_state_machine(self, job):
        """
        Generate a new state machine. This shouldn't take long.
        """
        if job.jobid in self.trackers:
            state_machine = self.trackers[job.jobid]
        else:
            state_machine = new_state_machine(self.workflow, job.jobid, self.scheduler)()
        return state_machine

    def check_complete(self):
        """
        Check if the entire workflow is complete.

        Here we just exit, and don't stop jobs from running, but eventually
        we can cleanup, etc.
        """
        current_state = self.get_current_state()
        completions = len(current_state["completed"])
        jobs_needed = self.workflow.completions_needed - completions
        if jobs_needed <= 0:
            LOGGER.info(
                f"Workflow is complete - {completions}/{self.workflow.completions_needed} are done"
            )
            self.add_timestamp("workflow_complete")

            # Stop the watcher and save output
            self.watcher.stop()
            self.watcher.save(self.save_dir)

            self.save_times()

            # For extra files to write
            time.sleep(5)
            sys.exit(0)

    @property
    def save_dir(self):
        return self.workflow.workdir or os.getcwd()

    def save_times(self):
        """
        Print final times and timestamps to the console, and
        also save to file in the working directory.
        """
        times = {"times": self.times, "timestamps": self.timestamps}
        print("=== times\n" + json.dumps(times) + "\n===")
        utils.write_json(times, os.path.join(self.save_dir, "workflow-times.json"))

    def new_jobs(self):
        """
        New jobs creates new jobs to track based on space available.

        This assumes that one sequence of steps takes up one cluster "slot"
        and that we can submit up to a maximum number of slots. This works
        well given that each job takes one node, but will need to be tweaked
        if that is not the case. TLDR: this algorithm that can be improved upon.
        """
        # Start by getting the current state of the cluster
        current_state = self.get_current_state()
        completions = len(current_state["completed"])
        active_jobs = len(current_state["active"])

        # These start at "start" stage (is_started should be false)
        # We will pack into the number nodes available
        step = self.workflow.config_for_step(self.workflow.first_step)
        nodes_needed = step.get("nnodes", 1)
        jobs_needed = self.workflow.completions_needed - completions

        # This is the maximum number of nodes we could use
        nodes_allowed = math.floor(self.workflow.max_size / nodes_needed)

        # and we need to adjust the jobs we will submit to be in that limit
        jobs_allowed = min(nodes_allowed, jobs_needed)

        # Account for active sequences (we already accounted for completions)
        submit_n = jobs_allowed - active_jobs

        # We just do this so we don't report a negative number to user
        # submit_n negative would be OK, a 0-> negative range is empty
        submit_n = max(submit_n, 0)

        logfn = LOGGER.info
        if self.quiet:
            logfn = LOGGER.debug

        logfn(f"\n> 🌀 Starting step {step['name']}")
        logfn("> Workflow needs")
        logfn(f"  > total completions           {self.workflow.completions_needed} ")
        logfn(f"  > max nodes allowed use       {self.workflow.max_size}\n")
        logfn("> Current state")
        logfn(f"  > nodes / step                {nodes_needed} ")
        logfn(f"  > jobs needed                 {jobs_needed} ")
        logfn(f"  > nodes allowed               {nodes_allowed} ")
        logfn(f"  > jobs allowed                {jobs_allowed}\n")
        logfn("> Workflow progress")
        logfn(f"  > Completions                 {completions}")
        logfn(f"  > In progress                 {active_jobs}")
        logfn(f"  > New job sequences submit    {submit_n} ")

        # If submit is > than completions needed, we don't need that many
        # TODO we would also downscale the cluster here
        submit_n = min(jobs_needed, submit_n)
        for _ in range(0, submit_n):
            jobid = self.generate_id()

            # Create a new state machine with job trackers, and change
            # change goes into the first state (the first step to submit)
            state_machine = new_state_machine(self.workflow, jobid, self.scheduler)()
            state_machine.change()
            self.trackers[jobid] = state_machine

    @timed
    def start(self):
        """
        Start the workflow manager state machine.

        This previously was run_workflow. Simple algorithm to start:

        1. Populate state machines that match current cluster.
           One state machine is a sequence of jobs. We only care about
           queued and running jobs. Any failure of a job will not continue
           and we don't need to track or care about it (we should cleanup)
        2. Submit new jobs up to a max allowed scaling size.
           This coincides with new state machines, one per submit.
        3. Monitor for changes by watching events.
        4. Each state machine acts independently
        5. A tracker can optionally monitor (watch) more events.

        This timed function should capture the entire workflow execution.
        """
        self.add_timestamp("workflow_start")

        # Each tracker is a state machine for one job sequence
        # Here we assess the current state of the cluster (jobs)
        # and fill the self.trackers lookup with state machines
        self.init_state()

        # You never know - we could restore and be done!
        self.check_complete()

        # At this point, we have 1:1 mapping of state machines to job sequences
        # We can now submit new simulations with the space we have. We assume
        # each sequence gets one job running at once (one slot in the cluster)
        # and can submit up to the max size. This algorithm can change.
        self.new_jobs()

        # Does our tracker have watchers?
        self.watcher.start()

        # Now we watch for changes.
        self.watch()

    def add_timestamp(self, name, timestamp=None):
        """
        Add a timestamp to times. This assumes unique names.
        """
        if name in self.timestamps:
            raise ValueError(f"Already seen {name}, this should not happen.")
        self.timestamps[name] = timestamp or time.time()

    def succeed_job(self, job, state_machine):
        """
        A state machine can succeed if it exits with 0 or is marked to always succeed
        """
        self.add_timestamp(f"{job.label}_succeeded")
        LOGGER.debug(f"Job {job.jobid} completed stage '{state_machine.current_state.id}'")
        state_machine.mark_succeeded(job)
        # Only change if we aren't complete
        if state_machine.current_state.id != "complete":
            state_machine.change()

    def add_timestamp_first_seen(self, label):
        """
        Record first event for a job. This is considered the start.
        If we've seen it, ignore.
        """
        label = f"{label}_start"
        if label in self.timestamps:
            return

        # This will only have one entry
        self.timestamps[label] = time.time()

    def watch(self):
        """
        Watch is an event driven means to watch for changes and update job states
        accordingly.
        """
        for job in self.tracker.stream_events():

            # Not a job associated with the workflow, or is ignored
            if not job.jobid or not job.step_name or job.jobid not in self.trackers:
                continue

            # Record first seen (if not seen yet) for jobid and step
            self.add_timestamp_first_seen(job.label)

            # Get the state machine for the job
            state_machine = self.trackers[job.jobid]

            # The job is active and not finished, keep going
            # This status will trigger when it's created (after submit)
            if job.is_active() and not job.is_completed():
                continue

            # This is a case where the job failed, but we allow failure and keep going
            if job.is_failed() and job.always_succeed:
                self.succeed_job(job, state_machine)

            # The job ran successfully, trigger the next step
            if job.is_succeeded() and job.is_completed():
                self.succeed_job(job, state_machine)

            # The job just completed and failed, clean up.
            if job.is_failed():
                self.add_timestamp(f"{job.label}_failed")
                LOGGER.debug(f"Job {job.jobid} failed stage '{state_machine.current_state.id}'")
                # Marking a job failed deletes all Kubernetes objects associated across stages.
                # We do this because we assume no step should be retried, etc.
                state_machine.mark_failed(job)
                # If we get here, the job has already done retries for the step
                # We need to cancel the state machine (all associated jobs)
                state_machine.cleanup()
                # Deleting the state machine means we stop tracking it
                if job.jobid in self.trackers:
                    del self.trackers[job.jobid]

            # Check if the workflow is complete
            self.check_complete()

            # Check to see if we should submit new jobs
            self.new_jobs()
