class Watcher:
    """
    Watcher base (abstract class) that provides useless functions.
    This is only if a tracker doesn't have a watcher class, it can
    expose the same (empty) interface.
    """

    def __init__(self):
        # Any watcher can provide custom metrics
        self.metrics = []

    def start(self):
        pass

    def stop(self):
        pass

    def save(self, outdir):
        pass

    def results(self, outdir):
        pass
