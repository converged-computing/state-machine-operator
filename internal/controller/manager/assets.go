package wfmanager

import (
	_ "embed"
	"fmt"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
	"github.com/converged-computing/state-machine-operator/internal/controller/manager/jobs"
	"github.com/converged-computing/state-machine-operator/internal/controller/utils"
)

//go:embed templates/entrypoint.sh
var entrypointTemplate string

// NewEntrypoint generates the entrypoint.sh and kubernetes_start.sh
// as data for a config map
func NewEntrypoint(spec *api.StateMachine) (map[string]string, error) {
	data := map[string]string{}

	// This list will go into the statemachine workflow config
	jobFiles := []string{}

	// Populate jobs into config map
	for i, job := range spec.Spec.Jobs {
		jobTemplated, err := jobs.TemplateJob(spec, &job)
		if err != nil {
			return data, nil
		}
		jobFile := fmt.Sprintf("job_%d.yaml", i)
		data[jobFile] = jobTemplated
		jobFiles = append(jobFiles, jobFile)
	}

	entrypoint, err := utils.PopulateTemplate(spec, entrypointTemplate)
	if err != nil {
		return data, err
	}
	data["entrypoint.sh"] = entrypoint

	// Prepare the workflow file
	return data, nil
}
