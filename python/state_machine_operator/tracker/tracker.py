import importlib
import json
import logging
import os
import shutil

import state_machine_operator.utils as utils
from state_machine_operator.tracker.types import SubmissionCode

# Print debug for now
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class Job:
    """
    Base class for a job (with shared functions)
    """

    def __init__(self, job_desc, workflow, **kwargs):
        # The copy is important since we modify the dict
        self.job_desc = job_desc
        self.workflow = workflow

        # Load custom module
        self.load_custom_events()

        # Allow for arbitrary extra key value arguments
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def config(self):
        return self.job_desc["config"]

    @property
    def extra_environment(self):
        """
        Get extra environment variables from the job description,
        """
        environment = self.job_desc.get("environment") or {}
        environ = []
        for key, value in environment.items():
            environ.append({"name": key, "value": value})
        return environ

    def load_custom_events(self):
        """
        Add (parse) custom job events.
        """
        tmpdir = utils.get_tmpdir()
        script_path = os.path.join(tmpdir, self.job_desc["name"] + ".py")

        # Parse custom job functions.
        event = self.job_desc.get("events") or {}
        script = event.get("script")
        self.module = None
        if not script:
            return

        utils.write_file(script, script_path)

        # module will have custom functions
        spec = importlib.util.spec_from_file_location(self.job_desc["name"], script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module
        shutil.rmtree(tmpdir)

    @property
    def properties(self):
        """
        Properties are attributes that are specific to a tracker.
        """
        # Properties can be provided as a string to json load
        props = self.job_desc.get("properties", {})
        if isinstance(props, str):
            props = json.loads(props)
        return props

    @property
    def always_succeed(self):
        """
        Should the job always be marked as successful?
        """
        props = self.properties or {}
        return props.get("always-succeed") in utils.true_values or False


class BaseTracker:
    """
    Base Job Tracker
    """

    def __init__(self, job_name, workflow):
        self.job_desc = workflow.get_job(job_name)

        # This is the workflow with rules for scaling, etc.
        self.workflow = workflow
        self.check_resources()

        # We retrieve custom metrics from the log and deliver to the manager
        self.metrics = []

    @property
    def total_nodes(self):
        return self.workflow.get("cluster", {}).get("max_nodes") or 1

    def __str__(self):
        return f"Tracker[{self.type}]"

    def __repr__(self):
        return str(self)

    @property
    def config(self):
        return self.job_desc["config"]

    @property
    def type(self):
        return self.job_desc["name"]

    @property
    def nnodes(self):
        return int(self.config.get("nnodes", 1))

    @property
    def tasks(self):
        tasks = self.config.get("tasks")
        if tasks is not None:
            return int(tasks)

    @property
    def ncores(self):
        return int(self.config.get("cores_per_task", 1))

    @property
    def ngpus(self):
        return int(self.config.get("ngpus", 0))

    def cleanup(self, jobid=None):
        pass

    def check_resources(self):
        """
        Sanity check resources are reasonable. Har har har.
        """
        assert self.nnodes >= 1
        assert self.ncores >= 1
        assert self.ngpus >= 0

    @property
    def name(self):
        """
        Get the job description name
        """
        return self.job_desc["name"]

    @property
    def save_path(self):
        return (self.properties or {}).get("save-path")

    def save_log(self, job=None):
        """
        Save a log for a job to a user-specified location.
        """
        pass

    @property
    def properties(self):
        """
        Properties are attributes that are specific to a tracker.
        """
        # Properties can be provided as a string to json load
        props = self.job_desc.get("properties", {})
        if isinstance(props, str):
            props = json.loads(props)
        return props

    @property
    def registry_host(self):
        """
        First defalt to registry host set by job, fall back to workflow.
        """
        registry_host = self.job_desc.get("registry", {}).get("host")
        if registry_host is not None:
            return registry_host
        return self.workflow.registry_host

    @property
    def registry_plain_http(self):
        """
        First defalt to registry plain-http set by job, fall back to workflow.
        """
        plain_http = self.job_desc.get("registry", {}).get("plain_http")
        if plain_http is not None:
            return plain_http
        return self.workflow.registry_plain_http

    @property
    def push_to(self):
        return self.job_desc.get("registry", {}).get("push")

    @property
    def pull_from(self):
        return self.job_desc.get("registry", {}).get("pull")

    def submit_job(self, jobid, repeat=False):
        """
        Submit a job to a tracker adapter.
        """
        step = self.create_step(jobid)
        LOGGER.debug(f"[{self.type}] submitting job {jobid}")
        submit_record = self.adapter.submit(step, jobid, repeat=repeat)

        # A conflcit means the job is already running. We don't want to count
        # it as a new submit (it will already be represented in the state)
        if submit_record.status == SubmissionCode.CONFLICT:
            LOGGER.error(
                f"[{self.type}] Found already running {self.type} job (Conflict) for job {jobid}"
            )

        # Allow it to fail and attempt cleanup
        elif not submit_record or submit_record.status != SubmissionCode.OK:
            LOGGER.error(f"[{self.type}] Failed to submit a {self.type} job for {jobid}")
            self.adapter.cleanup(step.name)

        else:
            LOGGER.debug(f"[{self.type}] Started job {jobid}")
        return submit_record
