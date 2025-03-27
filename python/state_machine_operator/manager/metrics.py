from river import stats

import state_machine_operator.utils as utils

model_inits = {
    "variance": stats.Var,
    "mean": stats.Mean,
    "iqr": stats.IQR,
    "max": stats.Max,
    "min": stats.Min,
    "mad": stats.MAD,
}


class WorkflowMetrics:
    """
    WorkflowMetrics store high level metrics
    about groups of jobs in the state machine.
    We use river.xyx stats functions:

    https://riverml.xyz/latest/api/stats/Mean
    """

    def __init__(self):
        # Generate lookup of river models above
        self.models = {name: {} for name, _ in model_inits.items()}

        # Counters are separate
        self.models["count"] = {}

        # Cache for all group model keys
        self.keys = set()

    def summarize_all(self):
        """
        Summarize all models
        """
        for key in self.keys:
            self.summary(key)

    def summary(self, key):
        """
        Summarize currently known models under a key
        """
        print(f"🌊 Streaming ML Model Summary {key}: ", end="")
        items = {}
        for model_name in model_inits:
            models = self.models[model_name]
            if key not in models:
                continue
            model = models[key]
            items[model_name] = model.get()
        print(utils.pretty_print_list(items))
        return items

    def increment_counter(self, key, step=None):
        """
        Increment the count of a metric.

        step: can scope to a specific job step.
        key: the name of the counter to increment.
        """
        # No step is global for the entire workflow
        step = step or "global"
        if step not in self.models["count"]:
            self.models["count"][step] = {}
        if key not in self.models["count"][step]:
            self.models["count"][step][key] = stats.Count()
        self.models["count"][step][key].update()

    def add_model_entry(self, key, value, model_name=None):
        """
        Record a datum for one or more models.

        If model_name is not set, add to add models.
        """
        self.keys.add(key)

        # This should be all models except for counts
        model_names = list(model_inits)
        if model_name is not None:
            model_names = [model_name]

        for model_name in model_names:
            if key not in self.models[model_name]:
                self.models[model_name][key] = model_inits[model_name]()
            self.models[model_name][key].update(value)
