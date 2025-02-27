import flux
import flux.job

from .handle import get_handle

handle = get_handle()


class Event:
    """
    An event wraps a job event.
    """

    def __init__(self, job):
        self.job = job

        # This is parsed from the state.py, slightly differently
        # but we can resolve it here
        if "kvs" in self.job:
            jobspec = self.job["kvs"]["jobspec"]
            jobid = self.job["id"]

        elif hasattr(job, "jobspec") and job.jobspec is not None:
            jobspec = job.jobspec
            jobid = job.jobid

        # If we don't have a jobspec, we need that too
        else:
            jobspec = flux.job.job_kvs(handle, self.job.jobid).get("jobspec")
            jobid = job.jobid

        # Set the jobspec
        self.jobspec = jobspec
        self.fluxid = jobid

    @property
    def state(self):
        """
        State must always be retrieved dynamically
        """
        return flux.job.get_job(handle, self.fluxid)

    @property
    def jobid(self):
        """
        Return the state machine job id
        """
        return self.jobspec["attributes"]["user"].get("jobname")

    def fluxid(self):
        return self.fluxid

    @property
    def step_name(self):
        return self.jobspec["attributes"]["user"].get("app")

    def is_active(self):
        """
        Determine if a job is active
        """
        return self.state["state"] != "INACTIVE"

    def is_completed(self):
        """
        Determine if a job is completed
        """
        return self.state["status"] == "COMPLETED"

    def is_failed(self):
        """
        Determine if a job is failed
        """
        return self.is_completed and self.state["returncode"] != 0

    def is_succeeded(self):
        """
        Determine if a job has succeeded
        """
        return self.is_completed and self.state["returncode"] == 0
