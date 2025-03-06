import os

import state_machine_operator.defaults as defaults


class Job:
    """
    Each returned job needs to expose a common interface
    """

    def __init__(self, job):
        self.job = job

    @property
    def jobid(self):
        return self.job.metadata.labels.get(defaults.operator_label)

    @property
    def label(self):
        return f"{self.jobid}_{self.step_name}"

    @property
    def step_name(self):
        return self.job.metadata.labels.get("app")

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
        Determine if a job is failed
        """
        return self.job.status.failed == 1

    def is_succeeded(self):
        """
        Determine if a job has succeeded
        """
        return self.job.status.succeeded == 1


def get_namespace():
    """
    Get the current namespace the workflow manager is running in.
    """
    ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    if os.path.exists(ns_path):
        with open(ns_path) as f:
            return f.read().strip()
