import copy
import json
import os
import threading
import time
from logging import getLogger

from kubernetes import client, config, watch

import state_machine_operator.utils as utils

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


class Watcher:
    """
    Kubernetes watchers deliver pod and node events.
    """

    def __init__(self):
        self.threads = {}
        self.stop_event = threading.Event()
        self.prepare_watchers()

        # These should only be accessed by one thread each
        # We want to capture pod pulling times and initial nodes (and changes) after that.
        # Not doing pulling times for now.
        self.nodes = {}
        self.pods = {}

    def results(self):
        return {"nodes": self.nodes}

    def save(self, outdir):
        print("=== nodes\n" + json.dumps(self.nodes) + "\n===")
        utils.write_json(self.nodes, os.path.join(outdir, "cluster-nodes.json"))

    def prepare_watchers(self):
        """
        Prepare watchers for pods and nodes.
        """
        for function in ["watch_nodes"]:
            thread = threading.Thread(target=getattr(self, function))
            thread.daemon = True
            self.threads[function] = thread

    def start(self):
        """
        The pods thread looks for pulled pods in the namespace, and
        the nodes thread starts with existing nodes, and then records
        subsequent events.
        """
        for function, thread in self.threads.items():
            LOGGER.debug(f"Starting thread watcher for {function}")
            thread.start()

    def stop(self):
        """
        We have a stop event, but in practice we don't wait for it to stop
        """
        self.stop_event.set()

    def watch_pods(self):
        """
        We aren't watching pods for now, don't need metadata.
        """
        pass

    def find_ready_condition(self, node):
        """
        Determine if a node is ready
        """
        condition = self.find_condition(node, "Ready")
        if not condition:
            return
        condition = copy.deepcopy(condition.to_dict())
        condition["status"] = True if condition["status"] == "True" else False
        # These two are usually the same, and we are interested in the transition
        condition["last_transition_time"] = condition["last_transition_time"].timestamp()
        del condition["last_heartbeat_time"]
        condition["recorded_at"] = time.time()
        return condition

    def find_condition(self, node, condition_name, state=None):
        """
        Find a condition by name and return it
        """
        for condition in node.status.conditions:
            if condition.type == condition_name:
                if state is not None and condition.status != state:
                    continue
                return condition

    def new_node_event(self, node):
        """
        When a node has not been seen before, record basic metadata
        """
        ready = self.find_ready_condition(node)
        return {
            "created": node.metadata.creation_timestamp.timestamp(),
            "labels": node.metadata.labels,
            "conditions": [self.find_ready_condition(node)],
            "is_ready": ready["status"],
        }

    def parse_node_event(self, event):
        """
        Parse a node event. Wrapped to handle any error.
        """
        node = event["object"]
        if node.metadata.name not in self.nodes:
            self.nodes[node.metadata.name] = self.new_node_event(node)

        # The node was deleted (so the object was too)
        if node.metadata.deletion_timestamp:
            self.nodes[node.metadata.name]["deleted"] = node.metadata.deletion_timestamp.timestamp()

        # Has the node readiness changed? Only save conditions on changes
        ready = self.find_ready_condition(node)
        if self.nodes[node.metadata.name]["is_ready"] != ready["status"]:
            self.nodes[node.metadata.name]["conditions"].append(ready)
            self.nodes[node.metadata.name]["is_ready"] = ready["status"]

    def watch_nodes(self):
        """
        Collect list of nodes at experiment start, and then watch for changes.
        """
        api = client.CoreV1Api()

        # Get starting state of the cluster - we care about ready nodes, timestamps
        for node in api.list_node().items:
            self.nodes[node.metadata.name] = self.new_node_event(node)

        # For now, assume that nodes are added and removed.
        # https://github.com/kubernetes/kubernetes/blob/master/pkg/apis/core/types.go
        w = watch.Watch()
        for event in w.stream(api.list_node):
            try:
                self.parse_node_event(event)
            except Exception as e:
                LOGGER.warning(f"Issue with Kubernetes event: {e}")

            # Stop event
            if self.stop_event.is_set():
                w.stop()
                return
