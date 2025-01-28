package jobs

import (
	"bytes"
	"strings"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
)

var (
	install_oras = `
# Install oras
cd /tmp
VERSION="1.2.2"
curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz"
mkdir -p oras-install/
tar -zxf oras_${VERSION}_*.tar.gz -C oras-install/
mv oras-install/oras /usr/local/bin/ || sudo mv oras-install/oras /usr/local/bin/
rm -rf oras_${VERSION}_*.tar.gz oras-install/
cd -

`

	preamble = `
jobid="{{ jobid }}"
outpath="{{ outpath }}"
registry="{{ registry }}"

echo ">> jobid        = $jobid"
echo ">> outpath      = $outpath"
echo ">> registry     = $registry"
echo ">> hostname     = "$(hostname)

mkdir -p -v $outpath; cd $outpath
`

	pull_oras = `
{% if pull %}
echo "Looking for $jobid with oras repo list"
oras repo list $registry {% if plain_http %}--plain-http{% endif %} | grep ${jobid}
echo "Pulling oras artifact to $locpath"
oras pull $registry/${jobid}:{{ pull }} {% if plain_http %}--plain-http{% endif %}
{% endif %}
`

	push_oras = `
{% if push %}
retval=$?
if [ $retval -eq 0 ];
  then
      # TODO add granularity of what result file to push
      echo "Job was successful, pushing result to $registry/${jobid}:{{ push }}"
	  oras push {% if plain_http %}--plain-http{% endif %} $registry/${jobid}:{{ push }} .
  else
    echo "Job was not successful"
    exit 1
  fi
{% endif %}
`
)

// PopulateCreateSim populates a newly provided MummiJob with defaults, etc.
func populateJobDefaults(job *api.JobStep) {

	// We don't allow nodes, procs, or cores per task to be 0
	if job.Config.Nodes == 0 {
		job.Config.Nodes = defaultNodes
	}
	// Createsim defaults to 6 cores per task
	if job.Config.CoresPerTask == 0 {
		job.Config.CoresPerTask = 6
	}
	// Number of processes, nproc
	if job.Config.Nproc == 0 {
		job.Config.Nproc = defaultNumberProcs
	}
	// No default walltime set

	// Add space in front of each line of the script
	// This is needed so it renders into the yaml
	if job.Script != "" {
		job.Script = preamble + install_oras + pull_oras + job.Script + push_oras
		job.Script = strings.ReplaceAll(job.Script, "\n", "\n  ")
	}
}

// TemplateCreateSim prepares the template for the config file mount
func TemplateJob(spec *api.StateMachine, job *api.JobStep) (string, error) {

	// populate defaults for createsim
	populateJobDefaults(job)

	subs := JobTemplate{
		Job:          job,
		Spec:         &spec.Spec,
		StateMachine: spec,
	}

	// Wrap the named template to identify it later
	startTemplate := `{{define "start"}}` + jobTemplate + "{{end}}"

	// We assemble different strings (including the components) into one!
	template, err := combineTemplates(components, startTemplate)
	if err != nil {
		return "", err
	}
	var output bytes.Buffer
	if err := template.ExecuteTemplate(&output, "start", subs); err != nil {
		return "", err
	}
	return output.String(), nil
}
