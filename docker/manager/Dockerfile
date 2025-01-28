FROM rockylinux:9

# docker build -f docker/manager/Dockerfile -t ghcr.io/converged-computing/state-machine-operator:manager .
# kind load docker-image ghcr.io/converged-computing/state-machine-operator:manager

RUN yum update -y && yum install -y gcc-g++ git which python3-pip && \
    dnf update -y && dnf install -y epel-release && \
    dnf install -y which vim htop

COPY ./docker/manager/entrypoint.sh /
COPY ./examples/jobs /opt/jobs
COPY ./python /opt/state-machine-operator
RUN cd /opt/state-machine-operator && \
    pip install -e . && \
    pip install IPython
