import state_machine_operator.defaults as defaults
import state_machine_operator.utils as utils
from state_machine_operator.tracker.job import BaseJob


class Job(BaseJob):
    """
    Each returned job needs to expose a common interface
    """

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
        return self.job.status.active == 1

    def is_completed(self):
        """
        Determine if a job is completed
        """
        return self.job.status.completion_time is not None

    def is_failed(self):
        """
        Determine if a job is failed.
        """
        return not self.is_succeeded()

    def is_succeeded(self):
        """
        Determine if a job has succeeded
        We need to have a completion time and no failed indices.
        """
        return self.is_completed and not self.job.status.failed

    def duration(self):
        """
        Get the job duration, if supported.

        This should be total seconds.
        """
        # Cut out early if we haven't started and finished!
        if self.job.status.completion_time is None or self.job.status.start_time is None:
            return
        return (self.job.status.completion_time - self.job.status.start_time).total_seconds()
