class Watcher:
    """
    Watcher base (abstract class) that provides useless functions.
    This is only if a tracker doesn't have a watcher class, it can
    expose the same (empty) interface.
    """

    def start(self):
        pass

    def stop(self):
        pass

    def save(self, outdir):
        pass

    def results(self, outdir):
        pass
