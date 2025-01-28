package jobs

import (
	"bytes"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
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
