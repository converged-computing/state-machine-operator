import os
import shlex
import sys
from logging import getLogger

from jinja2 import Template

import state_machine_operator.utils as utils
from state_machine_operator.tracker.template import job_script
from state_machine_operator.tracker.tracker import BaseTracker, Job
from state_machine_operator.tracker.types import JobSetup, JobSubmission, SubmissionCode
from state_machine_operator.tracker.utils import convert_walltime_to_seconds

from .handle import get_handle

LOGGER = getLogger(__name__)


try:
    import flux
    import flux.constants
    import flux.job
    import flux.message
except ImportError:
    sys.exit("flux python is required to use the flux tracker")


class FluxJob(Job):
    """
    Interface class for Kubernetes.
    """

    def cleanup(self, jobid):
        """
        Try cleaning up the entirety of a job
        """
        flux.job.cancel(self.handle, jobid)

    def generate_flux_job(self, step, jobid):
        """
        Generate the job CRD assuming the config map entrypoint.
        """
        step_name = (f"{self.job_desc['name']}").replace("-", "_")
        walltime = convert_walltime_to_seconds(step.walltime or 0)

        # Command should just execute entrypoint - keep it simple for now
        ncores = (step.cores_per_task or 1) * step.nodes

        # Raise an exception if ncores is 0
        if ncores <= 0:
            msg = "Invalid number of cores specified. " "Aborting. (ncores = {})".format(ncores)
            LOGGER.error(msg)
            raise ValueError(msg)

        # Command and entrypoint script
        entrypoint = f"{step.workdir}/entrypoint.sh"
        command = self.config.get("command") or f"/bin/bash {entrypoint}"
        command = shlex.split(command)

        # Create the structure for the output
        # /<tmp>/<jobid>/<step>/<script>
        dirname = os.path.dirname(entrypoint)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if not os.path.exists(entrypoint):
            utils.write_file(step.script, entrypoint)

        exclusive = self.config.get("exclusive") in utils.true_values
        num_tasks = max(1, self.config.get("tasks") or 1)
        jobspec = flux.job.JobspecV1.from_command(
            command=command,
            num_nodes=step.nodes,
            num_tasks=num_tasks,
            cores_per_task=step.cores_per_task,
            gpus_per_task=step.gpus,
            exclusive=exclusive,
        )

        # Set user attribute we can later retrieve to identify group
        jobspec.attributes["user"] = {
            "workflow": "state-machine",
            "app": step_name,
            "jobname": jobid,
        }

        # Add the job name
        # TODO: ideally we can have the jobid and step
        # The issue here is the terminal can't show them both
        jobspec.attributes["system"]["job"] = {"name": step_name}

        # Do we have a working directory?
        if step.workdir:
            jobspec.cwd = step.workdir

        # Use direction or default to 0, unlimited
        # TODO we will want to consider how containers fit here.
        jobspec.duration = walltime
        return jobspec

    def submit(self, step, jobid):
        """
        Submit a job to Kubernetes

        :param step: The JobSetup data.
        """
        # Generate the flux jobspec
        jobspec = self.generate_flux_job(step, jobid)
        jobid = flux.job.submit(self.handle, jobspec)
        submit_status = SubmissionCode.ERROR
        retcode = -1
        if jobid is not None:
            submit_status = SubmissionCode.OK
            retcode = 0
        return JobSubmission(submit_status, retcode)


class FluxTracker(BaseTracker):
    """
    Flux single job tracker.

    The adapter_batch group has arguments for our Kubernetes batch job.
    E.g., working directory, container, environment, etc.
    """

    def __init__(self, job_name, workflow):
        super().__init__(job_name, workflow)
        self.handle = get_handle()
        self.adapter = FluxJob(self.job_desc, workflow, handle=self.handle)

    def workdir(self, jobid):
        """
        Working directory that is created and cd'd to
        """
        workdir = self.job_desc.get("workdir") or self.workflow.filesystem
        return os.path.join(workdir, jobid, self.job_desc["name"])

    def create_step(self, jobid):
        """
        Create job parameters for a Kubernetes Job CRD
        """
        LOGGER.debug(f"[{self.type}] jobid = {jobid}")
        workdir = self.workdir(jobid)

        step = JobSetup(
            name=jobid,
            nodes=self.nnodes,
            cores_per_task=self.ncores,
            gpus=self.ngpus,
            workdir=workdir,
        )

        configfile = os.path.join(workdir, "app-config")

        if "script" in self.job_desc:

            # Add some space to the script
            script = "\n".join(["  " + x for x in self.job_desc["script"].split("\n")]).strip("  ")

            # This allows the script to be able to handle one or more jobid
            kwargs = {
                "jobids": [jobid],
                "jobid": jobid,
                # This can be in any format.
                "configfile": configfile,
                "workdir": workdir,
                "config": self.config,
                "pull": self.pull_from,
                "push": self.push_to,
                "registry": self.registry_host if not self.workflow.filesystem else None,
                "plain_http": self.registry_plain_http,
                "script": script,
            }
            step.script = Template(job_script).render(**kwargs)

        # Is there a walltime set?
        step.walltime = self.config.get("walltime", None)
        return step
