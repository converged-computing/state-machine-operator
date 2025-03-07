import os
import sys

import jsonschema

import state_machine_operator.defaults as defaults
import state_machine_operator.utils as utils
from state_machine_operator import schema


def load_workflow_config(config_path, config_dir=None, validate=True):
    """
    Load the workflow config path, validating with the schema
    """
    workflow = WorkflowConfig(config_path, config_dir)
    if validate:
        workflow.validate()
    return workflow


def find_config(config_dir, config_file):
    """
    Find the path of the config file
    """
    config_found = config_file
    if config_dir and not os.path.exists(config_found):
        config_found = os.path.join(config_dir, config_file)
    if not os.path.exists(config_found) and config_dir:
        sys.exit(f"Did not find {config_file} as provided or in {config_dir}")
    elif not os.path.exists(config_found):
        sys.exit(f"Did not find {config_file} as provided")
    return config_found


def load_config(config_dir, config_file):
    """
    Find and load a named configuration file.

    1. First check path provided.
    2. Then check path within context of config directory.
    """
    return utils.read_yaml(find_config(config_dir, config_file))


class WorkflowConfig:
    """
    A State Machine Workflow config holds a series of steps
    """

    def __init__(self, config_path, config_dir=None):
        self.load(config_path, config_dir)
        self.jobs = {}
        self.load_jobs()

    def load(self, config_path, config_dir=None):
        """
        Load the main workflow config
        """
        # If no config path provided, assume alongside jobs
        if config_dir is None:
            config_dir = os.path.dirname(config_path)
        self.filename = find_config(config_dir, config_path)
        self.cfg = utils.read_yaml(self.filename)
        self.config_dir = config_dir

    def get(self, name, default=None):
        return self.cfg.get(name, default)

    def get_job(self, name):
        return self.jobs.get(name)

    @property
    def registry_host(self):
        """
        Get the registry host
        """
        return self.cfg.get("registry", {}).get("host") or defaults.registry

    @property
    def workdir(self):
        """
        Return the working directory, if defined.
        """
        return self.cfg.get("workdir")

    @property
    def registry_plain_http(self):
        """
        Determine if the registry supports plain http.
        """
        plain_http = self.cfg.get("registry", {}).get("plain_http")
        if plain_http is None:
            return True
        return plain_http

    @property
    def push_to(self):
        return self.cfg.get("registry", {}).get("push")

    @property
    def pull_from(self):
        return self.cfg.get("registry", {}).get("pull")

    @property
    def prefix(self):
        return self.cfg["workflow"].get("prefix")

    def set_filesystem(self, path):
        """
        Set a filesystem path in the workflow
        """
        if "filesystem" not in self.cfg:
            self.cfg["filesystem"] = {}
        self.cfg["filesystem"]["path"] = path

    def set_workdir(self, workdir=None):
        """
        Set a new working directory to over-ride the config.

        This is typically done from the command line.
        """
        if not workdir:
            return
        self.cfg["workdir"] = workdir

    @property
    def filesystem(self):
        return self.cfg.get("filesystem", {}).get("path")

    def set_registry(self, registry_host, plain_http=None):
        """
        Set registry host and parameters
        """
        if "registry" not in self.cfg:
            self.cfg["registry"] = {}
        if registry_host is not None:
            self.cfg["registry"]["host"] = registry_host
        if plain_http is not None:
            self.cfg["registry"]["plain_http"] = plain_http

    def load_jobs(self):
        """
        Load jobs into the workflow manager and ensure configs exist.
        """
        if "jobs" not in self.cfg or not self.cfg["jobs"]:
            raise ValueError("Workflow is missing job configs.")

        # As of Python 3.7, dictionaries are ordered
        for job_config in self.cfg["jobs"]:
            # This will fail if config is not found
            job = load_config(self.config_dir, job_config["config"])
            jsonschema.validate(job, schema=schema.state_machine_job_schema)
            # Update the config to also have the name, so we can associate
            # the name with the order.
            job_config["name"] = job["name"]
            job["config"]["name"] = job["name"]
            self.jobs[job["name"]] = job

    def validate(self):
        jsonschema.validate(self.cfg, schema=schema.state_machine_config_schema)

    @property
    def max_size(self):
        return self.cfg.get("cluster", {}).get("max_size")

    @property
    def completions_needed(self):
        return self.cfg.get("workflow", {}).get("completed") or defaults.default_completions

    @property
    def first_step(self):
        return self.cfg["jobs"][0]["name"]

    @property
    def last_step(self):
        return self.cfg["jobs"][-1]["name"]

    def next_step(self, current_name):
        """
        Get the next step based on the current step name.
        """
        last_step = None
        for job in self.cfg["jobs"]:
            if last_step is not None and last_step == current_name:
                return job["name"]

    def config_for_step(self, step_name):
        """
        Get the config for a step
        """
        if step_name not in self.jobs:
            raise ValueError(f"Step {step_name} is not known")
        return self.jobs[step_name].get("config", {})

    def nodes_for_step(self, step_name):
        """
        Get the number of nodes for a step
        """
        return self.config_for_step(step_name).get("nnodes", 1)
