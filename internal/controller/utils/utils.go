package utils

import (
	"bytes"
	"text/template"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
)

// TemplateSubs are currently just the spec
type TemplateSubs struct {
	Spec         *api.StateMachineSpec
	StateMachine *api.StateMachine
}

// PopulateTemplate is a generic template to provide the spec to populate a template
func PopulateTemplate(spec *api.StateMachine, templateString string) (string, error) {

	// Parse the entrypoint into a template
	tmpl, err := template.New("script").Parse(templateString)
	if err != nil {
		return "", err
	}

	// We can write into a bytes buffer (and return as string)
	var out bytes.Buffer

	// Data for the template (redundant, but provided for convenience)
	subs := TemplateSubs{Spec: &spec.Spec, StateMachine: spec}

	// Execute the template and write output to stdout
	err = tmpl.Execute(&out, subs)
	if err != nil {
		return "", err
	}
	return out.String(), nil

}
