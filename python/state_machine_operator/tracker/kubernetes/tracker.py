import json
import os
import shlex
from logging import getLogger

from jinja2 import Template
from kubernetes import client, config

import state_machine_operator.defaults as defaults
import state_machine_operator.utils as utils
from state_machine_operator.tracker.tracker import BaseTracker, Job
from state_machine_operator.tracker.types import (
    CancelCode,
    JobSetup,
    JobSubmission,
    SubmissionCode,
    true_options,
)
from state_machine_operator.tracker.utils import convert_walltime_to_seconds

LOGGER = getLogger(__name__)


# This assumes the wfmanager running inside the cluster
config.load_incluster_config()

# Container name for job step
container_name = "step"


class KubernetesJob(Job):
    """
    Interface class for Kubernetes.
    """

    @property
    def namespace(self):
        return self.job_desc.get("namespace") or "default"

    def create_configmap(self, name, content):
        """
        Create a ConfigMap (jobscript) for Kubernetes

        This includes the entrypoint, along with the entire
        script (config) that is provided for the app to use.
        """
        config = json.dumps(self.job_desc, indent=4)
        app_config = self.job_desc.get("app-config") or ""
        cm = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(name=name, namespace=self.namespace),
            data={"entrypoint": content, "config": config, "app-config": app_config},
        )
        with client.ApiClient() as api_client:
            api = client.CoreV1Api(api_client)
            try:
                api.create_namespaced_config_map(namespace=self.namespace, body=cm)
            except Exception as e:
                if e.reason == "Conflict":
                    self.delete_configmap(name)
                    return self.create_configmap(name, content)
                else:
                    raise ValueError(f"Unexpected error with configmap creation: {e.reason}")

    def cleanup(self, jobid):
        """
        Try cleaning up the entirety of a job
        """
        name = jobid.lower().replace("_", "-")
        try:
            self.delete_configmap(name)
        except Exception as e:
            LOGGER.warning(f"Issue cleaning up configmap {name}: {e}")

        # Use kubernetes API to cancel jobs (delete)
        batch_api = client.BatchV1Api()

        # Derive the job name
        step_name = self.job_desc["name"]
        job_name = (f"{step_name}-{name}").replace("_", "-")
        try:
            batch_api.delete_namespaced_job(name=job_name, namespace=self.namespace)
        except Exception as e:
            LOGGER.warning(f"Issue deleting {name}: {e}")

    def delete_configmap(self, name):
        """
        Delete a ConfigMap from Kubernetes

        We allow flexibility here, meaning an ability to allow
        failure of the deletion, assuming a user / another
        entity deleted it first.
        """
        with client.ApiClient() as api_client:
            api = client.CoreV1Api(api_client)
            try:
                api.delete_namespaced_config_map(namespace=self.namespace, name=name)
            except Exception as e:
                LOGGER.warning(f"Issue deleting configmap {name}: {e}")

    def get_node_selector(self):
        """
        Node selector is in properties -> node-selector
        """
        return self.properties.get("node-selector")

    def generate_batch_job(self, step, jobid):
        """
        Generate the job CRD assuming the config map entrypoint.
        """
        step_name = self.job_desc["name"]
        # Underscores are not allowed
        job_name = (f"{step_name}-{step.name}").replace("_", "-")
        walltime = convert_walltime_to_seconds(step.walltime or 0)
        metadata = client.V1ObjectMeta(name=job_name)

        # Command should just execute entrypoint - keep it simple for now
        ncores = (step.cores_per_task or 1) * step.nodes

        # Raise an exception if ncores is 0
        if ncores <= 0:
            msg = "Invalid number of cores specified. " "Aborting. (ncores = {})".format(ncores)
            LOGGER.error(msg)
            raise ValueError(msg)

        # Job resources, we care about cores and GPU
        # Note that this is PER container, not across entire job
        # We could add memory here if needed
        resources = {"cpu": step.cores_per_task}

        # Assume for now nvidia, this can be changed
        if step.gpus > 0:
            gpu_label = self.config.get("gpulabel", "nvidia.com/gpu")
            resources[gpu_label] = step.gpus

        # Wrap as requests and limits
        resources = {"requests": resources, "limits": resources}

        # Container image pull policy
        pull_policy = self.config.get("pull_policy", "IfNotPresent")

        # Subdomain for any kubernetes network
        subdomain = self.config.get("subdomain", "r")
        command = self.command

        # Job container to run the script
        container = client.V1Container(
            image=self.job_desc["image"],
            name=container_name,
            command=[command[0]],
            args=command[1:],
            image_pull_policy=pull_policy,
            volume_mounts=[
                client.V1VolumeMount(
                    mount_path="/workdir",
                    name="entrypoint-mount",
                ),
            ],
            env=self.extra_environment,
            resources=resources,
        )

        # Prepare volumes (with config map)
        volumes = [
            client.V1Volume(
                name="entrypoint-mount",
                config_map=client.V1ConfigMapVolumeSource(
                    name=step.name,
                    items=[
                        client.V1KeyToPath(
                            key="entrypoint",
                            path="entrypoint.sh",
                        ),
                        client.V1KeyToPath(
                            key="config",
                            path="config.json",
                        ),
                        client.V1KeyToPath(
                            key="app-config",
                            path="app-config",
                        ),
                    ],
                ),
            ),
        ]

        # Job template. The app label will be used to filter later
        template = {
            "metadata": {
                "labels": {
                    "app": step_name,
                    defaults.operator_label: jobid,
                },
            },
            "spec": {
                "containers": [container],
                "restartPolicy": "Never",
                "volumes": volumes,
                "subdomain": subdomain,
            },
        }

        # Should the job always succeed?
        if self.always_succeed:
            template["metadata"]["labels"]["always-succeed"] = "1"

        # Add node selectors? E.g.,
        # node.kubernetes.io/instance-type: c7a.4xlarge
        node_selector = self.get_node_selector()
        if node_selector is not None:
            template["spec"]["nodeSelector"] = node_selector

        # Only add walltime if it's > 0 and not None
        if walltime:
            template["spec"]["activeDeadlineSeconds"] = int(walltime)

        # Do we want the job to terminate after failure?
        backoff_limit = 0
        if self.config.get("retry_failure") in true_options:
            backoff_limit = 6

        spec = client.V1JobSpec(
            parallelism=step.nodes,
            completions=step.nodes,
            suspend=False,
            template=template,
            backoff_limit=backoff_limit,
        )

        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=metadata,
            spec=spec,
        )

    @property
    def command(self):
        """
        Derive the application command, falling back to the entrypoint.sh
        """
        command = self.config.get("command")
        if command is not None and isinstance(command, list):
            command = " ".join(command)

        command = command or "/bin/bash /workdir/entrypoint.sh"
        return shlex.split(command)

    def submit(self, step, jobid):
        """
        Submit a job to Kubernetes

        :param step: The JobSetup data.
        """
        # Create a config map (mounted read only script to run sim)
        self.create_configmap(step.name, step.script)

        # Generate the kubernetes batch job!
        job = self.generate_batch_job(step, jobid)
        batch_api = client.BatchV1Api()

        retcode = -1
        try:
            batch_api.create_namespaced_job(self.namespace, job)
            retcode = 0
            submit_status = SubmissionCode.OK

        except Exception as e:
            # This means it was submit twice (should not happen, but let's check)
            if e.reason == "Conflict":
                LOGGER.warning(f"Batch job for {step.name} exists, assuming resumed: {e.reason}")
                submit_status = SubmissionCode.CONFLICT
            else:
                LOGGER.info(f"There was a create job error: {e.reason}, {e}")
                submit_status = SubmissionCode.ERROR

        return JobSubmission(submit_status, retcode)

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job. This is not currently use,
        but we might have a use case for it. This is the one place where
        we are still relying on the job identifier lookup. We can remove
        it if we don't need it (and just cancel based on the sim name).
        """
        # If we don"t have any jobs to check, just return status OK.
        if not joblist:
            return CancelCode.OK

        # Use kubernetes API to cancel jobs (delete)
        batch_api = client.BatchV1Api()

        # I'm going to assume a failure to cancel here is OK.
        # Technically if the user cancelled it, it's fine. We can
        # harden this a bit later. The response from the delete namespaced
        # job doesn't seem to have enough information to indicate if it was successful,
        # likely because it's issued and then doesn't confirm deletion (there is a delay)
        # We should look into if there is a parameter like wait or return status.
        for job_name in joblist:
            try:
                batch_api.delete_namespaced_job(name=job_name, namespace=self.namespace)
            except Exception as e:
                LOGGER.warning(f"Issue deleting {job_name}: {e}")

            # Delete the associated config map
            self.delete_configmap(job_name)

        return CancelCode.OK


class KubernetesTracker(BaseTracker):
    """
    Kubernetes single job tracker.

    The adapter_batch group has arguments for our Kubernetes batch job.
    E.g., working directory, container, environment, etc.
    """

    def __init__(self, job_name, workflow):
        super().__init__(job_name, workflow)
        self.adapter = KubernetesJob(self.job_desc, workflow)
        self.validate()

    def validate(self):
        if "image" not in self.job_desc or not self.job_desc["image"]:
            raise ValueError(
                f"The 'image' attribute is required, and not present in {self.adapter.job_name}"
            )

    def save_log(self, job=None):
        """
        Save a log identifier for a finished pod (job)
        """
        if not self.save_path or not Job:
            return
        api = client.CoreV1Api()

        # Get pods associated with the job
        selector = f"batch.kubernetes.io/job-name={job.job.metadata.name}"
        pods = api.list_namespaced_pod(
            label_selector=selector, namespace=job.job.metadata.namespace
        ).items

        # Create the save path
        logs_path = os.path.join(self.save_path, "logs")
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        # We might have one pod, but can't assume
        for i, pod in enumerate(pods):
            print(f"Saving log for {pod.metadata.name}")
            try:
                logs = api.read_namespaced_pod_log(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    container=container_name,
                    follow=False,
                    timestamps=True,
                )
                log_file = os.path.join(
                    logs_path,
                    f"{job.job.metadata.labels['app']}-{job.job.metadata.labels['jobid']}-{i}.out",
                )
                # Don't write twice
                if not os.path.exists(log_file):
                    print(f"Saving log file {log_file}")
                    utils.write_file(logs, log_file)
                else:
                    print(f"Log file {log_file} already exists")

            except client.exceptions.ApiException as e:
                print(f"Error getting logs: {e}")
                return

    def create_step(self, jobid):
        """
        Create job parameters for a Kubernetes Job CRD
        """
        LOGGER.debug(f"[{self.type}] jobid = {jobid}")
        step = JobSetup(
            name=jobid.lower().replace("_", "-"),
            nodes=self.nnodes,
            cores_per_task=self.ncores,
            gpus=self.ngpus,
        )

        # Working directory is created and cd'd to
        workdir = self.job_desc.get("workdir") or defaults.workdir

        if "script" in self.job_desc:
            # This allows the script to be able to handle one or more jobid
            kwargs = {
                "jobids": [jobid],
                "jobid": jobid,
                # This can be in any format.
                "configfile": "/workdir/app-config",
                "workdir": workdir,
                "pull": self.pull_from,
                "push": self.push_to,
                "registry": self.registry_host,
                "plain_http": self.registry_plain_http,
            }
            step.script = Template(self.job_desc["script"]).render(**kwargs)

        # Is there a walltime set?
        step.walltime = self.config.get("walltime", None)
        return step
