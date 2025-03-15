from logging import getLogger

import flux
import flux.job

from .handle import get_handle
from .job import FluxJob as Event

LOGGER = getLogger(__name__)

# We will likely want to inspect some of these when we add elasticity
# We use "start" (after submit) instead of submit
skip_events = [
    "submit",
    "validate",
    "depend",
    "priority",
    "annotations",
    "alloc",
    "release",
    "free",
    "finish",
]

# We use start and clean, as start is when the job actually starts, but clean is the last job event.


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
        yield Event(event)
