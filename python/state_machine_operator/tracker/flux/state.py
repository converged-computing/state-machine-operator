from logging import getLogger

import flux
import flux.job

from .handle import get_handle
from .job import FluxJob as Job

LOGGER = getLogger(__name__)


def get_job_info(handle, jobid):
    """
    Get details for a job
    """
    jobid = flux.job.JobID(jobid)
    return flux.job.get_job(handle, jobid)


def list_jobs(*args, **kwargs):
    """
    List jobs. Flux doesn't have namespaces, but we might replace
    with another abstraction (if it makes sense).
    """
    handle = get_handle()
    listing = flux.job.job_list(handle)
    ids = listing.get()["jobs"]
    jobs = {}
    flux_ids = []
    for job in ids:
        try:
            jobinfo = get_job_info(handle, job["id"])
            flux_ids.append(jobinfo["id"])

            # This will trigger a data table warning
            for needed in ["ranks", "expiration"]:
                if needed not in jobinfo:
                    jobinfo[needed] = ""
            jobs[jobinfo["id"]] = jobinfo
        except Exception:
            pass

    rpc = flux.job.kvslookup.JobKVSLookup(
        handle, ids=flux_ids, keys=["jobspec"], decode=True, original=False, base=False
    )
    for job in rpc.data():
        jobid = job["id"]
        # Race between two calls
        if jobid not in jobs:
            continue
        jobs[jobid]["kvs"] = job

    return list(jobs.values())


def queued_jobs(namespace=None):
    """
    A queued job is not active and doesn't have a completion time.

    We haven't used this yet so it should throw up if we do
    (and then we will write it :)
    """
    print("flux queued jobs")
    import IPython

    IPython.embed()

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
    print("flux running jobs")
    import IPython

    IPython.embed()

    jobs = list_jobs(namespace)
    return [
        x.metadata.name
        for x in jobs.items
        if x.status.completion_time is None and x.status.active == 1
    ]


def filter_jobs(jobs, label_key, label_value):
    """
    Filter jobs by a label, which is typically in the user space.
    """
    updated = []
    for job in jobs:
        user_data = job["kvs"]["jobspec"]["attributes"].get("user")
        if not user_data:
            continue
        if user_data.get(label_key) != label_value:
            continue
        updated.append(job)
    return updated


def list_jobs_by_status(label_name="app", label_value=None):
    """
    Return a lookup of jobs by status

    If label is provided, filter down to that
    """
    jobs = list_jobs()

    # Only consider jobs that are part of this workflow
    jobs = filter_jobs(jobs, "workflow", "state-machine")

    if label_name is not None and label_value is not None:
        jobs = filter_jobs(jobs, label_name, label_value)

    # These are the lists we will populate.
    states = {"success": [], "failed": [], "running": [], "queued": [], "unknown": []}
    for job in jobs:
        if job["status"] == "COMPLETED":
            states["success"].append(Job(job))
            continue

        # Failure means we finished with failed condition
        if job["status"] == "FAILED":
            states["failed"].append(Job(job))
            continue

        # Pending or queued
        if job["state"] in ["NEW", "DEPEND", "PRIORITY", "SCHED"]:
            states["queued"].append(Job(job))
            continue

        # Active and running
        if job["state"] == "RUN":
            states["running"].append(Job(job))
            continue

        # If it didn't fail or succeed, let it keep going to timeout (duration/walltime)
        states["unknown"].append(Job(job))
    return states
