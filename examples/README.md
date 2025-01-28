# Manual Example

This is a manual example for deploying a state machine to Kubernetes for those that want to understand the abstractions better. Note that this example assumes a kind cluster (or similar) running, and the context is from the [root](../) of the repository.

## Prototype Config

Here is an example config to provide to the state machine manager `state-machine-manager`. The steps should be provided in their expected order.

```yaml
# state-machine-workflow.yaml
workflow:
  completed: 4
cluster:
  max_size: 6
  autoscale: False
jobs:
  - config: jobs_a.yaml
  - config: jobs_b.yaml
  - config: jobs_c.yaml
```

Each configuration file has a format that is expected by the manager, and anything else is passed to the workflow entrypoint `script` to use. You can find this along with the job steps in [examples/jobs](examples/jobs)

## Containers

Containers are defined for the workflow manager in [examples/jobs](examples/jobs). We build them from this context to add in the state-machine-operator code.

```bash
kind create cluster --config ./kind-config.yaml

# This builds the image and loads into kind
make kind
```

This is how I'm testing. Note that for more customization we likely can use the operator.

```bash
kubectl apply -f ./examples/manual
```

This has an added oras client (in Python) for pushing artifacts. Note that the entrypoint is set to sleep for interactive start, so you can shell in and do:

```bash
bash /entrypoint.sh
```

Or restore the automated entrypoint for an automated run.
