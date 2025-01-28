{{ define "job-config" }}
config:
  nnodes:           {{ if .Job.Config.Nodes }}{{ .Job.Config.Nodes }}{{ else }}1{{ end }}
  nprocs:           {{ if .Job.Config.Nproc }}{{ .Job.Config.Nproc }}{{ else }}1{{ end }}
  cores per task:   {{ if .Job.Config.CoresPerTask }}{{ .Job.Config.CoresPerTask }}{{ else }}6{{ end }}
  ngpus:            {{ .Job.Config.Gpus }}
  {{ if .Job.Config.Walltime }}walltime:         '{{ .Job.Config.Walltime }}{{ end }}
  # Kubernetes specific settings
  {{ if .Job.Config.GPULabel }}gpulabel:         {{ .Job.Config.GPULabel }}{{ end }}
  pull_policy:      {{ .Job.PullPolicy }}
  retry_failure:    {{ if .Job.Config.RetryFailure }}true{{ else }}false{{ end }}
  subdomain: {{ .Spec.Name }}
{{end}}


name: job_a
config:
  nnodes:         1
  nprocs:         1
  cores per task: 6
  ngpus:          0
  subdomain: "state-machine-operator"

image: rockylinux:9
namespace: default

{{ define "install-oras" }}
# Install oras
cd /tmp
VERSION="1.2.2"
curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz"
mkdir -p oras-install/
tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/
mv oras-install/oras /usr/local/bin/ || sudo mv oras-install/oras /usr/local/bin/
rm -rf oras_${VERSION}_*.tar.gz oras-install/
cd -
{{ end }}

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
