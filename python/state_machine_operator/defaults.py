scheduler = "kubernetes"
registry = "registry-0.state-machine.default.svc.cluster.local:5000"

# Operator label for the jobid
operator_label = "jobid"
workdir = "/tmp/out"

# Prefix for job names
prefix = "job_"
supported_schedulers = [scheduler, "flux"]
