#!/usr/bin/env bash

# Clean up previous workflow config and jobs, copy over new.
rm -rf /opt/jobs
cp -R /state_machine_operator /opt/jobs

# Write the new config file there
cat <<EOF > /opt/jobs/state-machine-workflow.yaml
workflow:
  completed: {{ .Spec.Workflow.Completed }}
  {{ if .Spec.Workflow.Prefix }}prefix: {{ .Spec.Workflow.Prefix }}{{ end }}{{ if .Spec.Workflow.Events }}
  events: {{ range .Spec.Workflow.Events }}
    - action: {{ .Action }}
      when: "{{ if .When }}{{ .When }}{{ else }}> 0{{ end }}"
      metric: {{ .Metric }}
{{ end }}{{ end }}
cluster:
  max_size: {{ .Spec.Cluster.MaxSize }}
  autoscale: {{ .Spec.Cluster.Autoscale }}
jobs:
{{ range $index, $jobfile := .Spec.Jobs }} - config: jobs_{{ $index }}.yaml
{{ end }}
EOF

# Parameters for state machine manager
workflow_config="/opt/jobs/state-machine-workflow.yaml"
config_dir="/opt/jobs"
scheduler="kubernetes"
registry="{{ .StateMachine.RegistryHost }}"
cmd="state-machine-manager start ${workflow_config} --config-dir=${config_dir} --scheduler ${scheduler} --registry ${registry} {{ if .Spec.Registry.PlainHttp }}--plain-http{{ end }}"

# Trigger interactive mode here so we have files staged above
echo "$cmd"
{{ if .Spec.Manager.Interactive }}sleep infinity{{ end }}

# Run the manager
$cmd

# We want to keep the deployment container running, otherwise it will restart
echo "Workflow is complete. You can delete the deployment to clean up."
sleep infinity
