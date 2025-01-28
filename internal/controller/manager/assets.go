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

// NewEntrypoint generates the entrypoint.sh and jobs
func NewEntrypoint(spec *api.StateMachine) (map[string]string, error) {
	data := map[string]string{}
	mLog.Info("Creating state machine manager configMap for: ", spec.ManagerName(), spec.Namespace)

	// Populate jobs into config map
	for i, job := range spec.Spec.Jobs {
		jobTemplated, err := jobs.TemplateJob(spec, &job)
		if err != nil {
			return data, err
		}
		jobFile := fmt.Sprintf("jobs_%d.yaml", i)
		data[jobFile] = jobTemplated
	}

	entrypoint, err := utils.PopulateTemplate(spec, entrypointTemplate)
	if err != nil {
		return data, err
	}
	fmt.Println(entrypoint)
	data["entrypoint.sh"] = entrypoint

	// Prepare the workflow file
	return data, nil
}
