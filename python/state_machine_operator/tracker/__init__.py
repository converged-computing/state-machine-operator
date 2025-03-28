import state_machine_operator.defaults as defaults

from .watcher import Watcher


def load(name):
    """
    Get a tracker module. We put imports here in case we don't
    need / want to import the scheduler-specific libraries.
    """
    tracker = None
    if name not in defaults.supported_schedulers:
        raise ValueError(f"{name} is not valid, please choose from {defaults.supported_schedulers}")

    name = name.lower()
    if name == "kubernetes":
        import state_machine_operator.tracker.kubernetes as tracker
    elif name == "flux":
        import state_machine_operator.tracker.flux as tracker
    if tracker is None:
        raise ValueError(f"Cannot match tracker to scheduler {name}")
    return tracker
