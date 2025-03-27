/*
Copyright 2025.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package v1alpha1

import (
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

var (
	defaultRegistryName       = "registry"
	defaultRegistryPort int32 = 5000
)

// StateMachineSpec defines the desired state of StateMachine
type StateMachineSpec struct {

	// The OCI Registry as Storage configuration
	// This is how to expect to upload artifacts (output) generated
	// This is used in the mlserver, wfmanager, and jobs
	// Registry configuration should go here
	// +optional
	Registry OrasConfig `json:"registry"`

	// Manager is the state machine manager that orchestrates state machines
	Manager Manager `json:"manager,omitempty"`

	// Workflow is the workflow parameters to orchestrate
	Workflow Workflow `json:"workflow"`

	// Cluster defines parameters for the cluster
	Cluster Cluster `json:"cluster"`

	// StateMachine Job interface, each maps to K8s job
	// +optional
	Jobs JobSequence `json:"jobs,omitempty"`
}

type Cluster struct {

	// MaxSize to allow autoscaling up to, or to submit jobs up to
	MaxSize int32 `json:"maxSize"`

	// Autoscale the cluster? (not implemented yet)
	//+optional
	Autoscale bool `json:"autoscale,omitempty"`
}

// Workflow definition - what state consistutes completion?
type Workflow struct {

	// Number of state machine sequences required for completion
	Completed int32 `json:"completed"`

	// Prefix for jobs (e.g., structure_ for mummi)
	Prefix string `json:"prefix,omitempty"`

	// Custom events  -> actions to take
	Events []WorkflowEvent `json:"events,omitempty"`
}

type WorkflowEvent struct {

	// Name of metric, indexed into model lookup (e.g., count.job_b.failed)
	Metric string `json:"metric"`

	// Conditional to check. If not set, checks if nonzero or nonempty
	When string `json:"when,omitempty"`

	// Action to take (e.g., finish-workflow)
	Action string `json:"action"`

	// Backoff and repetitions to respond to event
	Backoff     int32 `json:"backoff,omitempty"`
	Repetitions int32 `json:"repetitions,omitempty"`
	MinCompletions int32 `json:"minCompletions,omitempty"`
	MaxSize int32 `json:"maxSize,omitempty"`
	MinSize int32 `json:"minSize,omitempty"`
}

// A JobSequence is a list of JobSteps
// We serialize as an interface so we parse out each field
// separately, and then can also pass the entire thing forward as a config
// to the job (not knowing the structure in advance)
type JobSequence []JobStep

type JobStep struct {

	// Name is the name of the job (required)
	Name string `json:"name,omitempty"`

	// Configuration for the job
	// +optional
	Config JobConfig `json:"config,omitempty"`

	// Configuration for the job registry
	// +optional
	Registry RegistryConfig `json:"registry,omitempty"`

	// Architecture (arm64 or amd64)
	// +kubebuilder:default="amd64"
	// +default="amd64"
	// +optional
	Arch string `json:"arch,omitempty"`

	// Custom data config to provide to worker
	// + optional
	AppConfig string `json:"appConfig,omitempty"`

	// Properties for the tracker, etc.
	// +optional
	Properties map[string]string `json:"properties,omitempty"`

	// Namespace is inherited from StateMachine Spec
	// This is the continer image (required)
	Image string `json:"image,omitempty"`

	// Run in interactive mode for debugging
	// +optional
	Interactive bool `json:"interactive,omitempty"`

	// Working directory (and output path)
	// +optional
	Workdir string `json:"workdir,omitempty"`

	// Script for the job to run
	Script string `json:"script,omitempty"`

	// Variables are the simname (supplied by jobTracker)
	// and output / other paths that should not be customized
	// The script for the entrypoint is also generated by the operator
}

// This maps to the job config section
type JobConfig struct {

	// Number of nodes per job
	// +kubebuilder:default=1
	// +default=1
	// +optional
	Nodes int32 `json:"nodes,omitempty"`

	// Cores per task per job
	// 6 frontier / 3 summit / 5 on lassen (vsoch: this used to be 6 default)
	// +kubebuilder:default=3
	// +default=3
	// +optional
	CoresPerTask int32 `json:"coresPerTask,omitempty"`

	// GPUs per job
	// +optional
	Gpus int32 `json:"gpus,omitempty"`

	// If the job fails, try again? Defaults to false
	// because we assume the initial data is bad.
	// RetryFailure
	// +optional
	RetryFailure bool `json:"retryFailure,omitempty"`

	// Walltime (in string format) for the job
	// +optional
	Walltime string `json:"walltime,omitempty"`

	// Pull policy for the container
	// +kubebuilder:default="IfNotPresent"
	// +default="IfNotPresent"
	// +optional
	PullPolicy string `json:"pullPolicy,omitempty"`

	// A GPU label to use (in the context of ngpus >=1)
	// if not provided, defaults to nvidia.com/gpu
	//+optional
	GPULabel string `json:"gpulabel,omitempty"`

	// Command is a custom command entrypoint
	// +optional
	Command string `json:"command,omitempty"`
}

// HsaRegistry returns true if any of the host, pull, or push is not empty
func (j *JobStep) HasRegistry() bool {
	return !(j.Registry.Host == "" && j.Registry.Pull == "" && j.Registry.Push == "")
}

// The State Machine Manager manages the workflow
type Manager struct {

	// Replicas for the deployment
	// +kubebuilder:default=1
	// +default=1
	// +optional
	Replicas int32 `json:"replicas,omitempty"`

	// Subdomain to use
	// +kubebuilder:default="r"
	// +default="r"
	// +optional
	Subdomain string `json:"subdomain,omitempty"`

	// Maximum nodes to allow cluster to scale to (that jobs add up to)
	// If unset, will default to Nodes above (N=6)
	// +optional
	MaxNodes int32 `json:"maxNodes,omitempty"`

	// Cores per node (deafults to 4) maps to NCORES_PER_NODED
	// +kubebuilder:default=4
	// +default=4
	// +optional
	CoresPerNode int32 `json:"coresPerNode,omitempty"`

	// Run in interactive debug mode (sleep infinity)
	// +optional
	Interactive bool `json:"interactive,omitempty"`

	// container image for the workflow manager (must be provided)
	// +omitempty
	Image string `json:"image,omitempty"`

	// container image for the workflow manager (must be provided)
	// +omitempty
	NodeSelector string `json:"nodeSelector,omitempty"`

	// Image pull policy (e.g., Always, Never, etc.)
	// +kubebuilder:default="IfNotPresent"
	// +default="IfNotPresent"
	// +optional
	PullPolicy string `json:"pullPolicy,omitempty"`
}

// OrasConfig holds configuration values for the registry to be deployed
// TODO add support for https and credentials, along with remote option
type OrasConfig struct {

	// Note that the host is generated based on the registry name
	// # E.g., oras push <host>/<uri>:<sample> --plain-http .
	// If no external registry is used, we use the internal one here
	// e.g., host is: registry-0.mini-mummi.default.svc.cluster.local:5000
	// +optional
	Host string `json:"host,omitempty"`

	// Name for the registry (defaults to registry)
	// +kubebuilder:default="registry"
	// +default="registry"
	// +optional
	Name string `json:"name,omitempty"`

	// Port to use to interact with the registry
	// +optional
	Port int32 `json:"port,omitempty"`

	// Assume the registry doesn't use plain http
	// +optional
	NoPlainHttp bool `json:"plainHttp,omitempty"`

	// Assume we don't need to verify
	// +optional
	TLSVerify bool `json:"TLSVerify,omitempty"`

	// Replicas for the registry deployment
	// +kubebuilder:default=1
	// +default=1
	// +optional
	Replicas int32 `json:"replicas,omitempty"`

	// Container image
	// +kubebuilder:default="ghcr.io/oras-project/registry:latest"
	// +default="ghcr.io/oras-project/registry:latest"
	// +optional
	Image string `json:"image,omitempty"`

	// container image for the workflow manager (must be provided)
	// +omitempty
	NodeSelector string `json:"nodeSelector,omitempty"`

	// Image pull policy (e.g., Always, Never, etc.)
	// +kubebuilder:default="IfNotPresent"
	// +default="IfNotPresent"
	// +optional
	PullPolicy string `json:"pullPolicy,omitempty"`
}

// RegistryConfig is to orchestrate push and pull for a job
type RegistryConfig struct {

	// Tag to push to
	// +optional
	Push string `json:"push,omitempty"`

	// Tag to pull to
	// +optional
	Pull string `json:"pull,omitempty"`

	// Override registry host for this job
	// +optional
	Host string `json:"host,omitempty"`

	// Override registry plain http for this job
	// +kubebuilder:default=true
	// +default=true
	// +optional
	PlainHTTP bool `json:"plainHttp,omitempty"`
}

// PlainHttp exposes the expected positive variant of the variable
func (o *OrasConfig) PlainHttp() bool {
	return !o.NoPlainHttp
}

// StateMachineStatus defines the observed state of StateMachine
type StateMachineStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status

// StateMachine is the Schema for the StateMachines API
type StateMachine struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   StateMachineSpec   `json:"spec,omitempty"`
	Status StateMachineStatus `json:"status,omitempty"`
}

// HasInClusterRegistry determines if we have a custom registry set
func (m *StateMachine) HasInClusterRegistry() bool {
	return m.Spec.Registry.Host == ""
}

// RegistryHost returns an in- or external- registry host
func (m *StateMachine) RegistryHost() string {

	// We have an external registry defined, return it
	if !m.HasInClusterRegistry() {

		// Most production registries won't require a port
		if m.Spec.Registry.Port == 0 {
			return m.Spec.Registry.Host
		}
		return fmt.Sprintf("%s:%d", m.Spec.Registry.Host, m.Spec.Registry.Port)
	}

	// registry-0.mini-mummi.default.svc.cluster.local:5000
	return fmt.Sprintf(
		"registry-0.%s.%s.svc.cluster.local:%d",
		m.Name, m.Namespace, m.Spec.Registry.Port,
	)
}

// The selector is how different objects (e.g,. deployment are added to the headless service)
func (m *StateMachine) Selector() map[string]string {
	return map[string]string{"app": m.Name}
}

// Workflow Manager name (for config maps and deployment)
func (m *StateMachine) ManagerName() string {
	return fmt.Sprintf("%s-manager", m.Name)
}

// Cluster Role and Role names
func (m *StateMachine) ClusterRoleName() string {
	return fmt.Sprintf("%s-cluster-roles", m.Name)

}
func (m *StateMachine) RoleName() string {
	return fmt.Sprintf("%s-roles", m.Name)
}

// SetRegistryDefaults ensure we have an image, port, name, etc.
func (m *StateMachine) SetRegistryDefaults() {

	// If a custom registry is set, these variables are moot
	if !m.HasInClusterRegistry() {
		return
	}
	if m.Spec.Manager.Subdomain == "" {
		m.Spec.Manager.Subdomain = "r"
	}
	if m.Spec.Registry.Port == 0 {
		m.Spec.Registry.Port = defaultRegistryPort
	}
	fmt.Printf("🫛 StateMachine.Spec.Registry %s\n", m.RegistryHost())
	fmt.Printf("🫛 StateMachine.Spec.Manager.Subdomain %s\n", m.Spec.Manager.Subdomain)
	if m.Spec.Registry.Name == "" {
		m.Spec.Registry.Name = defaultRegistryName
	}
	if m.Spec.Registry.Replicas == 0 {
		m.Spec.Registry.Replicas = 1
	}
}

// Validate ensures we have data that is needed, and sets defaults if needed
func (m *StateMachine) Validate() bool {
	fmt.Println()

	if m.Spec.Manager.Image == "" {
		m.Spec.Manager.Image = "ghcr.io/converged-computing/state-machine-operator:manager"
	}
	if m.Spec.Registry.Image == "" {
		m.Spec.Registry.Image = "ghcr.io/oras-project/registry:latest"
	}

	// Registry, MLServer Defaults
	m.SetRegistryDefaults()

	// Validate sizes provided
	if m.Spec.Cluster.MaxSize < 1 {
		fmt.Printf("👉 StateMachine.Spec.Cluster.MaxSize must be >= 1\n")
		return false
	}
	if m.Spec.Workflow.Completed < 1 {
		fmt.Printf("👉 StateMachine.Spec.Workflow.Completed must be >= 1\n")
		return false
	}
	return true
}

// +kubebuilder:object:root=true

// StateMachineList contains a list of StateMachine
type StateMachineList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []StateMachine `json:"items"`
}

func init() {
	SchemeBuilder.Register(&StateMachine{}, &StateMachineList{})
}
