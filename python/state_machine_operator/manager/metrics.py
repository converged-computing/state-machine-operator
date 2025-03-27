import json

from river import stats

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

    def summarize_all(self):
        """
        Summarize all models
        """
        print("🌊 Streaming ML Model Summary: ", end="")
        items = {}
        for model_name, models in self.models.items():
            if model_name not in items:
                items[model_name] = {}
            for step_name, keys in models.items():
                if step_name not in items[model_name]:
                    items[model_name][step_name] = {}
                for key, model in keys.items():
                    items[model_name][step_name] = round(model.get(), 3)
        print(json.dumps(items))
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

    def add_model_entry(self, key, value, step=None, model_name=None):
        """
        Record a datum for one or more models.

        If model_name is not set, add to add models.
        """
        step = step or "global"

        # This should be all models except for counts
        model_names = list(model_inits)
        if model_name is not None:
            model_names = [model_name]

        for model_name in model_names:
            if step not in self.models[model_name]:
                self.models[model_name][step] = {}
            if key not in self.models[model_name][step]:
                self.models[model_name][step][key] = model_inits[model_name]()
            self.models[model_name][step][key].update(value)
