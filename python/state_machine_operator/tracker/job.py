class BaseJob:
    """
    A BaseJob to wrap a Job for some tracker
    """

    def __init__(self, job):
        self.job = job

    @property
    def jobid(self):
        raise NotImplementedError

    @property
    def step_name(self):
        raise NotImplementedError

    @property
    def always_succeed(self):
        return False

    def is_active(self):
        """
        Determine if a job is active
        """
        raise NotImplementedError

    def is_completed(self):
        """
        Determine if a job is completed
        """
        raise NotImplementedError

    def is_failed(self):
        """
        Determine if a job is failed
        """
        raise NotImplementedError

    def is_succeeded(self):
        """
        Determine if a job has succeeded
        """
        raise NotImplementedError
