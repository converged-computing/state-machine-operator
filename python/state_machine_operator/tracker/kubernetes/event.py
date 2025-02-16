from logging import getLogger

from kubernetes import client, config, watch

from .job import Job, get_namespace

LOGGER = getLogger(__name__)

config.load_incluster_config()


def stream_events():
    """
    Stream jobs based on events.

    A returned job object should be a generic job.
    """
    batch_v1 = client.BatchV1Api()
    w = watch.Watch()
    for event in w.stream(batch_v1.list_namespaced_job, namespace=get_namespace()):
        job = event["object"]
        yield Job(job)
