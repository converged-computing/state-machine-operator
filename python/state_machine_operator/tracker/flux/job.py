class Event:
    """
    An event wraps a job event.
    """

    def __init__(self, job):
        self.job = job

    @property
    def data(self):
        return self.job.__dict__

    @property
    def jobid(self):
        return self.data["jobid"]

    @property
    def step_name(self):
        return self.job.jobspec["attributes"]["user"].get("app")

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


class Job:
    """
    Each returned job needs to expose a common interface
    """

    def __init__(self, job):
        self.job = job

    @property
    def jobid(self):
        return self.job["id"]

    @property
    def step_name(self):
        return self.job["kvs"]["jobspec"]["attributes"]["system"].get("app")

    def is_active(self):
        """
        Determine if a job is active
        """
        return self.job["state"] != "INACTIVE"

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
        return self.is_completed and self.state["returncode"] != 0
