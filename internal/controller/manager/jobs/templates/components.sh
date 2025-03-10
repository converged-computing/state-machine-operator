{{ define "job-config" }}
config:
  nnodes:           {{ if .Job.Config.Nodes }}{{ .Job.Config.Nodes }}{{ else }}1{{ end }}
  cores_per_task:   {{ if .Job.Config.CoresPerTask }}{{ .Job.Config.CoresPerTask }}{{ else }}6{{ end }}
  ngpus:            {{ .Job.Config.Gpus }}
  {{ if .Job.Config.Walltime }}walltime:         '{{ .Job.Config.Walltime }}'{{ end }}
  # Kubernetes specific settings
  {{ if .Job.Config.GPULabel }}gpulabel:         {{ .Job.Config.GPULabel }}{{ end }}
  pull_policy:      {{ .Job.Config.PullPolicy }}
  retry_failure:    {{ if .Job.Config.RetryFailure }}true{{ else }}false{{ end }}
  subdomain: {{ .Spec.Manager.Subdomain }}
  {{ if .Job.Config.Command }}command: {{ .Job.Config.Command }}{{ end }}
{{end}}
