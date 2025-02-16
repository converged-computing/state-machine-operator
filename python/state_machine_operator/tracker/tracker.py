import os


class Job:
    """
    Base class for a job (with shared functions)
    """

    def __init__(self, job_desc):
        self.job_desc = job_desc

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


class BaseTracker:
    """
    Base Job Tracker
    """

    def __init__(self, job_name, workflow):
        self.job_desc = workflow.get_job(job_name)

        # This is the workflow with rules for scaling, etc.
        self.workflow = workflow
        self.check_resources()

        # TODO this envrionment variable has the max nodes we will allow to autoscale to
        # We can use this later...
        self.max_nodes_autoscale = (
            os.environ.get("STATE_MACHINE_MAX_NODES", self.total_nodes) or self.total_nodes
        )

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
    def nprocs(self):
        return int(self.config.get("nprocs", 1))

    @property
    def ncores(self):
        return int(self.config.get("cores per task", 1))

    @property
    def ngpus(self):
        return int(self.config.get("ngpus", 0))

    def check_resources(self):
        """
        Sanity check resources are reasonable. Har har har.
        """
        assert self.nnodes >= 1
        assert self.nprocs >= 1
        assert self.ncores >= 1
        assert self.ngpus >= 0

    @property
    def name(self):
        """
        Get the job description name
        """
        return self.job_desc["name"]

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
