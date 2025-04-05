FROM gcr.io/k8s-staging-jobset/pytorch-resnet:latest
# docker build -t ghcr.io/converged-computing/mummi-experiments:cifar .
RUN /bin/bash -c "curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -"
# RUN apt-get update && apt-get install -y curl wget iputils-ping
COPY ./resnet.py /resnet.py
