#!/usr/bin/env bash

workflow_config="${1:-/opt/jobs/state-machine-workflow.yaml}"
config_dir="${2:-/opt/jobs}"
scheduler="${3:-kubernetes}"
registry="${4:-registry}"

echo "(`hostname`: `date`) --> Launching State Machine Manager"

# state-machine-manager start /opt/jobs/state-machine-workflow.yaml --config-dir=/opt/jobs
cmd="state-machine-manager start ${workflow_config} --config-dir=${config_dir} --scheduler ${scheduler} --registry ${registry}"
echo $cmd
$cmd
