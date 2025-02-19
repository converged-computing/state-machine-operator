from logging import getLogger

import flux
import flux.job

from .handle import get_handle
from .job import Event

LOGGER = getLogger(__name__)

# We will likely want to inspect some of these when we add elasticity
skip_events = ["validate", "depend", "priority", "annotations", "alloc", "finish"]

# Mostly interested in final and start


def stream_events():
    """
    Stream jobs based on events.

    A returned job object should be a generic job.
    """
    handle = get_handle()
    consumer = flux.job.JournalConsumer(handle).start()
    while True:
        event = consumer.poll(timeout=-1)
        if event["name"] in skip_events:
            continue
        # We need to pass forward the current state, which
        # isn't always in the event
        event.state = flux.job.get_job(handle, event.jobid)

        # flux.job.get_job(handle, event.jobid)
        yield Event(event)
