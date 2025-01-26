# state-machine-operator

> State machines in Kubernetes 🐦‍🔥

![img/state-machine-operator.png](img/state-machine-operator.png)

The operator (Kubernetes) part will be added soon! Right now we have the configs that create the state machine and orchestrate the work.

## Usage

### Prerequisites

- go version v1.22.0+
- docker version 17.03+.
- kubectl version v1.11.3+.
- Access to a Kubernetes v1.11.3+ cluster.

### 1. Create Cluster

You can create a cluster locally (if your computer is chonky and can handle it) or use AWS. Here is locally:

```bash
kind create cluster --config ./examples/kind-config.yaml
```

### 2. State Machine Workflow

#### Prototype Config

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

#### Containers

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

### 3. Install the Operator

The operator is built via its manifest in dist. For development:

```bash
make test-deploy-recreate
```

For non-development:

```bash
kubectl apply -f examples/dist/state-machine-operator.yaml
```

## Design

These are some design decisions I've made (of course open to discussion):

### Initial Design

 - The workflow model is a state machine - state is derived from Kubernetes, always
 - The state machine manager manages units of job sequences (each a state machine) and each state machine orchestrates the logic of the jobs within it.
 - No application code (the jobs) is tangled with the state machine or manager
 - We assume jobs don't need to be paused / resumed / reclaimed like on HPC
 - Jobs are modular units with a config known how to be parsed by the manager, and the rest is provided to them.

### TODO

- We likely want to test with a real registry OR allow a volume bind (existing data) to the registry.
  - Otherwise, artifacts deleted on cleanup. We could also have an option that allows keeping the ephemeral registry.

### Questions

- Under what conditions do we cancel / cleanup jobs?
- I haven't tested a failure yet (or need to cleanup / delete)
- We might want to do other cleanup (e.g., config maps)

## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
