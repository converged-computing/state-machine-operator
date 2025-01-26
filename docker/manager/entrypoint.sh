#!/usr/bin/env bash

workflow_config="${1:-/opt/jobs/state-machine-workflow.yaml}"
config_dir="${2:-/opt/jobs}"
manager_config="${3:-/manager.yaml}"

echo "(`hostname`: `date`) --> Launching State Machine Manager"

# state-machine-manager start /opt/jobs/state-machine-workflow.yaml --config-dir=/opt/jobs
cmd="state-machine-manager start ${workflow_config} --config-dir=${config_dir} --manager-config=${manager_config}"
echo $cmd
$cmd
