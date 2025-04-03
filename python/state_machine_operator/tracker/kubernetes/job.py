from kubernetes import client

import state_machine_operator.defaults as defaults
import state_machine_operator.utils as utils
from state_machine_operator.tracker.job import BaseJob


class Job(BaseJob):
    """
    Each returned job needs to expose a common interface
    """

    def __init__(self, job):
        self.job = job

    def update_status(self):
        """
        Get an updated status for a job
        """
        batch_v1 = client.BatchV1Api()
        try:
            self.job = batch_v1.read_namespaced_job_status(
                name=self.job.metadata.name, namespace=self.job.metadata.namespace
            )
        except Exception as e:
            print(f"Issue getting updated job status: {e}")

    @property
    def jobid(self):
        return self.job.metadata.labels.get(defaults.operator_label)

    @property
    def label(self):
        return f"{self.jobid}_{self.step_name}"

    @property
    def step_name(self):
        return self.job.metadata.labels.get("app")

    @property
    def always_succeed(self):
        return self.job.metadata.labels.get("always-succeed") in utils.true_values

    def is_active(self):
        """
        Determine if a job is active
        """
        return self.job.status.active is not None and self.job.status.active > 0

    def is_completed(self):
        """
        Determine if a job is completed
        """
        if self.has_succeeded_condition():
            return True
        return self.job.status.completion_time is not None

    def is_failed(self):
        """
        Determine if a job is failed.
        """
        return self.is_completed() and self.job.status.failed is not None

    def is_succeeded(self):
        """
        Determine if a job has succeeded
        We need to have a completion time and no failed indices.
        """
        if self.has_succeeded_condition():
            return True
        return self.is_completed() and self.job.status.failed is None

    def has_succeeded_condition(self):
        """
        Jobs can miss a completion timestamp but have this
        """
        # Note that the previous criteria will be "success criteria met" and
        # we can't have that be the success condition or this triggers twice
        if self.job.status.conditions is not None:
            for condition in self.job.status.conditions:
                if condition.type == "Complete":
                    return True
        return False

    def duration(self):
        """
        Get the job duration, if supported.

        This should be total seconds.
        """
        # Cut out early if we haven't started and finished!
        if self.job.status.completion_time is None or self.job.status.start_time is None:
            return
        return (self.job.status.completion_time - self.job.status.start_time).total_seconds()
