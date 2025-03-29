
from kubernetes import client
import os

def get_namespace():
    """
    Get the current namespace the workflow manager is running in.
    """
    ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    if os.path.exists(ns_path):
        with open(ns_path) as f:
            return f.read().strip()
    
def get_manager_pod():
    """
    Get the currently running manager pod.
    """
    v1 = client.CoreV1Api()

    # Get the manager pod
    label_selector = "component=state-machine-manager"
    pods = v1.list_namespaced_pod(namespace=get_namespace(), label_selector=label_selector)
    assert len(pods.items) == 1
    return pods.items[0]

