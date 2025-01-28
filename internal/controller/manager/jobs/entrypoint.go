package jobs

import (
	_ "embed"
	"fmt"
	"text/template"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
)

//go:embed templates/job.yaml
var jobTemplate string

//go:embed templates/components.sh
var components string

// ServiceTemplate is for a separate service container
type JobTemplate struct {
	Job          *api.JobStep
	Spec         *api.StateMachineSpec
	StateMachine *api.StateMachine
}

// combineTemplates into one common start
func combineTemplates(listing ...string) (t *template.Template, err error) {
	t = template.New("start")

	for i, templ := range listing {
		_, err = t.New(fmt.Sprint("_", i)).Parse(templ)
		if err != nil {
			return t, err
		}
	}
	return t, nil
}
