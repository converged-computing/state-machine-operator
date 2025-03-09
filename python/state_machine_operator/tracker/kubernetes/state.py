from logging import getLogger

from kubernetes import client, config

from .job import Job, get_namespace

LOGGER = getLogger(__name__)

# This assumes the wfmanager running inside the cluster
config.load_incluster_config()


def list_jobs(namespace=None):
    """
    List jobs. If no namespace is provided, use the current.
    """
    namespace = namespace or get_namespace()
    batch_api = client.BatchV1Api()
    return batch_api.list_namespaced_job(namespace=namespace)


def queued_jobs(namespace=None):
    """
    A queued job is not active and doesn't have a completion time.
    """
    jobs = list_jobs(namespace)
    return [
        x.metadata.name
        for x in jobs.items
        if x.status.completion_time is None and x.status.active == 0
    ]


def running_jobs(namespace=None):
    """
    A running job is active and doesn't have a completion time.
    """
    jobs = list_jobs(namespace)
    return [
        x.metadata.name
        for x in jobs.items
        if x.status.completion_time is None and x.status.active == 1
    ]


def list_jobs_by_status(label_name="app", label_value=None):
    """
    Return a lookup of jobs by status

    If label is provided, filter down to that
    """
    jobs = list_jobs().items

    if label_name is not None and label_value is not None:
        jobs = [x for x in jobs if x.metadata.labels.get(label_name) == label_value]

    # These are the lists we will populate.
    states = {"success": [], "failed": [], "running": [], "queued": [], "unknown": []}

    for job in jobs:
        # Success means we finished with succeeded condition
        if job.status.succeeded == 1 and job.status.completion_time is not None:
            states["success"].append(Job(job))
            continue

        # Failure means we finished with failed condition
        if job.status.failed == 1:
            states["failed"].append(Job(job))
            continue

        # Not active, and not finished is queued
        if not job.status.active and not job.status.completion_time:
            states["queued"].append(Job(job))
            continue

        # Active, and not finished is running
        if job.status.active == 1 and not job.status.completion_time:
            states["running"].append(Job(job))
            continue

        # If it didn't fail or succeed, let it keep going to timeout (duration/walltime)
        states["unknown"].append(Job(job))
    return states
