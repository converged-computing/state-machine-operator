scheduler = "kubernetes"
registry = "registry-0.state-machine.default.svc.cluster.local:5000"
service_account_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"

# Insance select server
workers = 8
port = 8080

# Operator label for the jobid
operator_label = "jobid"
workdir = "/tmp/out"

# Workflow
workflow_actions = ["grow", "shrink", "finish-workflow"]
state_machine_actions = ["repeat"]
all_actions = state_machine_actions + workflow_actions
workflow_events = ["failure", "success", "duration"]

# Custom metrics annotation
metrics_key = "state-machine-metrics"

# Prefix for job names
prefix = "job_"
supported_schedulers = [scheduler, "flux"]
