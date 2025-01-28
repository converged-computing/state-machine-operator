{{ define "job-config" }}
config:
  nnodes:           {{ if .Job.Config.Nodes }}{{ .Job.Config.Nodes }}{{ else }}1{{ end }}
  nprocs:           {{ if .Job.Config.Nproc }}{{ .Job.Config.Nproc }}{{ else }}1{{ end }}
  cores per task:   {{ if .Job.Config.CoresPerTask }}{{ .Job.Config.CoresPerTask }}{{ else }}6{{ end }}
  ngpus:            {{ .Job.Config.Gpus }}
  {{ if .Job.Config.Walltime }}walltime:         '{{ .Job.Config.Walltime }}{{ end }}
  # Kubernetes specific settings
  {{ if .Job.Config.GPULabel }}gpulabel:         {{ .Job.Config.GPULabel }}{{ end }}
  pull_policy:      {{ .Job.Config.PullPolicy }}
  retry_failure:    {{ if .Job.Config.RetryFailure }}true{{ else }}false{{ end }}
  subdomain: {{ .Spec.Manager.Subdomain }}
{{end}}


{{ define "oras-pull" }}
  echo "Looking for $simname with oras repo list"
  # Check 1: The repo (sim name) must exist in the registry
  oras repo list $registry {{ if .Spec.Registry.PlainHttp }}--plain-http{{ end }} {{ if .Spec.Registry.TLSVerify }}{{ else }}--insecure{{ end }} | grep $simname
  if [ $? -ne 0 ];
    then
      echo "Cannot find $simname in $registry listing"
      exit 1
  fi
  # Check 2: The tag for the previous step must exist
  oras repo tags $registry/$simname {{ if .Spec.Registry.PlainHttp }}--plain-http{{ end }} {{ if .Spec.Registry.TLSVerify }}{{ else }}--insecure{{ end }} | grep $tag
  if [ $? -ne 0 ];
    then
      echo "Cannot find $tag in $registry/$simname"
      exit 1
  fi

  # Check 3: The pull must succeed
  echo "Pulling oras artifact to $locpath"
  oras pull $uri {{ if .Spec.Registry.PlainHttp }}--plain-http{{ end }} {{ if .Spec.Registry.TLSVerify }}{{ else }}--insecure{{ end }}
  if [ $? -ne 0 ];
    then
      echo "Cannot pull $uri"
      exit 1
  fi
{{ end }}

{{ define "mummi-vars" }}
  MUMMI_APP={{ if .Spec.Paths.MummiRoot }}{{ .Spec.Paths.MummiRoot }}{{ else }}/opt/clones/mummi-ras{{ end }}
  export MUMMI_ROOT=$MUMMI_APP
  export MUMMI_RESOURCES={{ if .Spec.Paths.MummiResources }}{{ .Spec.Paths.MummiResources }}{{ else }}/opt/clones/mummi_resources{{ end }}
  export MUMMI_APP
{{ end }}
