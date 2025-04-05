FROM rockylinux:9

# docker build -f docker/manager/Dockerfile -t ghcr.io/converged-computing/state-machine-operator:manager .
# kind load docker-image ghcr.io/converged-computing/state-machine-operator:manager

RUN yum update -y && yum install -y gcc-g++ git which python3-pip && \
    dnf update -y && dnf install -y epel-release && \
    dnf install -y which vim htop

# Install oras for easy interaction with registry
RUN cd /tmp && VERSION="1.2.2" && \
    curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz" && \
    mkdir -p oras-install/ && \
    tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/ && \
    mv oras-install/oras /usr/local/bin/ && \
    rm -rf oras_${VERSION}_*.tar.gz oras-install/

COPY ./docker/manager/entrypoint.sh /
COPY ./examples/jobs /opt/jobs
COPY ./python /opt/state-machine-operator
RUN cd /opt/state-machine-operator && \
    pip install -e . && \
    pip install IPython
