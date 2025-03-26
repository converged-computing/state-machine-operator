import matplotlib
import matplotlib.pyplot as plt
import pandas
import seaborn as sns

import state_machine_operator.utils as utils


class NodesTimesParser:
    """
    Nodes Times Parser
    parser=NodesTimesParser(node_filter=["t3.large"])
    """

    def __init__(
        self, node_filter=None, label_name="node.kubernetes.io/instance-type", palette="muted"
    ):
        """
        Create a nodes time parser.
        """
        self.total_times = {}
        self.palette = palette
        self.node_filter = node_filter
        # Label to filter by using listing above
        self.label_name = label_name
        self.df = pandas.DataFrame(
            columns=[
                "instance",
                "experiment",
                "iteration",
                "start_time",
                "down_time",
                "uptime",
                "workflow_start",
                "workflow_end",
            ]
        )
        self.idx = 0

    def update_times_inventory(self, experiment, iteration):
        if experiment not in self.total_times:
            self.total_times[experiment] = {}
        if iteration not in self.total_times[experiment]:
            self.total_times[experiment][iteration] = []

    def generate_colors(self, items):
        """
        Generate some number of colors for a lookup.
        """
        colors = {}
        palette = sns.color_palette(self.palette, len(items))
        hexcolors = palette.as_hex()
        for item in items:
            colors[item] = hexcolors.pop(0)
        return colors

    def to_gantt(self, outfile, title="Node Uptimes for Static vs Autoscaling", colors=None):
        """
        Make a gantt chart of nodes over time
        """
        # Normalize
        self.df["start_time_normalized"] = [
            row[1].start_time - row[1].workflow_start for row in self.df.iterrows()
        ]

        self.df["end_time_normalized"] = [
            row[1].down_time - row[1].workflow_start for row in self.df.iterrows()
        ]

        # We need the maximum end time to make all the axis the same
        max_end_time = self.df.end_time_normalized.max()
        number_plots = 0
        for experiment in self.df.experiment.unique():
            subset = self.df[self.df.experiment == experiment]
            for iteration in subset.iteration.unique():
                number_plots += 1

        # Colors based on experiment type
        colors = colors or self.generate_colors(self.df.experiment.unique())

        patches = []
        for color in colors.values():
            patches.append(matplotlib.patches.Patch(color=color))

        # Each needs its own plot
        fig, axs = plt.subplots(number_plots, figsize=(8, 20))
        idx = 0
        for experiment in self.df.experiment.unique():
            exp_subset = self.df[self.df.experiment == experiment]
            iterations = exp_subset.iteration.unique()
            iterations.sort()
            for iteration in iterations:
                subset = exp_subset[exp_subset.iteration == iteration]
                for index, row in subset.iterrows():
                    axs[idx].barh(
                        y=row.instance,
                        width=row.uptime,
                        left=row.start_time_normalized,
                        color=colors[row.experiment],
                    )
                axs[idx].set_xlim(0, max_end_time)
                axs[idx].xaxis.grid(True, alpha=0.5)
                axs[idx].set_title(f"{experiment.capitalize()} cluster iteration {iteration}")
                plt.tight_layout()
                idx += 1

        plt.subplots_adjust(top=0.95)
        fig.suptitle(title, fontsize=11)
        fig.legend(handles=patches, labels=colors.keys(), fontsize=11)
        plt.savefig(outfile)

    def add_nodes(self, node_file, workflow_start, workflow_end, experiment="default", iteration=0):
        """
        Add a set of cluster nodes to the timing set.

        The workflow start time is required to calculate the node up/down time.
        The workflow end time is needed to do the same.
        """
        cluster_nodes = utils.read_json(node_file)
        self.update_times_inventory(experiment, iteration)
        for node_name, nodemeta in cluster_nodes.items():

            # Filter nodes to just include those that are for compute (not sticky)
            if (
                self.node_filter is not None
                and self.label_name in nodemeta["labels"]
                and nodemeta["labels"][self.label_name] not in self.node_filter
            ):
                continue

            # Did a node go away and came up during the experiment? This might
            # happen with an aggressive autoscaling policy.
            first_event = nodemeta["conditions"][0]["last_transition_time"]

            # Check if the first event was before the cluster was created
            node_start_time = workflow_start
            node_end_time = workflow_end

            # Did the node report ready the first time after the experiment started?
            if first_event > node_start_time:
                print(f"Found node {node_name} that came up during experiment")
                node_start_time = first_event

            # If the last event posted had the node not ready, it was removed at some point.
            if not nodemeta["is_ready"]:
                last_event = nodemeta["conditions"][-1]
                workflow_end = last_event["last_transition_time"]
                assert last_event["type"] == "Ready" and last_event["status"] is False

            # If the node remained ready, it was up the duration of the experiment
            # This is the implied else
            node_uptime = node_end_time - node_start_time
            self.total_times[experiment][iteration].append(node_uptime)
            self.df.loc[self.idx, :] = [
                node_name,
                experiment,
                iteration,
                node_start_time,
                node_end_time,
                node_uptime,
                workflow_start,
                workflow_end,
            ]
            self.idx += 1


class WorkflowTimesParser:
    """
    Workflow Times Parser

    parser = WorkflowTimesParser()
    parser.add_experiment("workflow-times.json", 'cpu-static', 0)
    """

    def __init__(self):
        self.workflow_starts = {}
        self.workflow_ends = {}
        self.df = pandas.DataFrame(
            columns=["experiment", "jobid", "step", "duration", "event", "iteration"]
        )
        self.idx = 0

    def add_experiment(self, times_file, experiment="default", iteration=0):
        """
        Helper function to parse a workflow-times.json file
        and return a pandas data frame. An experiment name
        and iteration are suggested.
        """
        times = utils.read_json(times_file)
        self.update_times_inventory(experiment, iteration)

        for name, timestamp in times["timestamps"].items():
            if "workflow_start" in name:
                self.workflow_starts[experiment][iteration] = timestamp
                workflow_end = times["timestamps"]["workflow_complete"]
                self.workflow_ends[experiment][iteration] = workflow_end
                duration = workflow_end - timestamp
                self.df.loc[self.idx, :] = [
                    experiment,
                    None,
                    name,
                    duration,
                    "workflow_complete",
                    iteration,
                ]
                self.idx += 1
                continue

            # Everything else should be a structure event, and we derive
            # other events (succeeded, failed) from the start
            if "_start" not in name:
                continue

            event = name.replace("_start", "")
            jobid, step_name = event.rsplit("_", 1)

            # The job will either have failed or succeeded
            success_ts = f"{event}_succeeded"
            failure_ts = f"{event}_failed"
            if success_ts in times["timestamps"]:
                duration = times["timestamps"][success_ts] - timestamp
                self.df.loc[self.idx, :] = [
                    experiment,
                    jobid,
                    step_name,
                    duration,
                    f"{step_name}_success",
                    iteration,
                ]
                self.idx += 1

            elif failure_ts in times["timestamps"]:
                duration = times["timestamps"][failure_ts] - timestamp
                self.df.loc[self.idx, :] = [
                    experiment,
                    jobid,
                    step_name,
                    duration,
                    f"{step_name}_failure",
                    iteration,
                ]
                self.idx += 1

    def update_times_inventory(self, experiment, iteration):
        """
        Update starts and ends, if defined
        """
        if experiment not in self.workflow_starts:
            self.workflow_starts[experiment] = {}
        if experiment not in self.workflow_ends:
            self.workflow_ends[experiment] = {}

        if iteration not in self.workflow_starts[experiment]:
            self.workflow_starts[experiment][iteration] = {}
        if iteration not in self.workflow_ends[experiment]:
            self.workflow_ends[experiment][iteration] = {}
