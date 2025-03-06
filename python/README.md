# state machine operator

> state machine orchestrator for the Mummi workflow

![PyPI - Version](https://img.shields.io/pypi/v/state-machine-operator)

An HPC ensemble is an orchestration of jobs that can ideally be controlled by an algorithm. Most resource managers expect workflows that have resource needs hard-coded, and a lot of manual orchestration. This effort aims to design a workflow tool that is more akin to a state machine, and responds to different events. Instead of hard coding specific applications, we allow for them to be defined dynamically. Some assumptions we make:

- An order of steps, A->B, understands how to handle output from the previous step. E.g., if we package up the output of A and give it to B in a known working directory, B knows what to do.
- Similarly, B knows that whatever is placed in that working directory will be provided to the next step.

This project will be intended to run in Kubernetes, because we are developing user-space Kubernetes for our HPC clusters and I want to start simple.


## License

HPCIC DevTools is distributed under the terms of the MIT license.
All new contributions must be made under this license.

See [LICENSE](https://github.com/converged-computing/cloud-select/blob/main/LICENSE),
[COPYRIGHT](https://github.com/converged-computing/cloud-select/blob/main/COPYRIGHT), and
[NOTICE](https://github.com/converged-computing/cloud-select/blob/main/NOTICE) for details.

SPDX-License-Identifier: (MIT)

LLNL-CODE- 842614
