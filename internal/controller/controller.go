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

package controller

import (
	"context"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	rbacv1 "k8s.io/api/rbac/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/client-go/rest"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"

	mummi "github.com/converged-computing/state-machine-operator/api/v1alpha1"
)

var (
	mLog = ctrl.Log.WithName("state-machine")
)

// StateMachineReconciler reconciles a StateMachine object
type StateMachineReconciler struct {
	client.Client
	Scheme     *runtime.Scheme
	RESTClient rest.Interface
	RESTConfig *rest.Config
}

func NewStateMachineReconciler(
	client client.Client,
	scheme *runtime.Scheme,
	restConfig *rest.Config,
	restClient rest.Interface,
) *StateMachineReconciler {
	return &StateMachineReconciler{
		Client:     client,
		Scheme:     scheme,
		RESTClient: restClient,
		RESTConfig: restConfig,
	}
}

// +kubebuilder:rbac:groups=state-machine.converged-computing.org,resources=statemachines,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=state-machine.converged-computing.org,resources=statemachines/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=state-machine.converged-computing.org,resources=statemachines/finalizers,verbs=update

//+kubebuilder:rbac:groups=core,resources=serviceaccounts,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=secrets,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=configmaps,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=statefulsets,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=pods/log,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=pods/exec,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=persistentvolumes,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=persistentvolumeclaims,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=jobs,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources="",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources="services",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=networking.k8s.io,resources="ingresses",verbs=get;list;watch;create;update;patch;delete

//+kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=apps,resources=statefulsets,verbs=get;list;watch;create;update;patch;delete

// These are added anticipating the operator could support the controller (wfmanager)
//+kubebuilder:rbac:groups=core,resources=batch,verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=core,resources=events,verbs=create;patch
//+kubebuilder:rbac:groups=core,resources=networks,verbs=create;patch

//+kubebuilder:rbac:groups="",resources=events,verbs=create;watch;update
//+kubebuilder:rbac:groups="rbac.authorization.k8s.io",resources="rolebindings",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups="rbac.authorization.k8s.io",resources="roles",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups="",resources="rolebindings",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups="",resources="roles",verbs=get;list;watch;create;update;patch;delete
//+kubebuilder:rbac:groups=batch,resources=jobs,verbs=get;list;watch;create;update;patch;delete;exec
//+kubebuilder:rbac:groups=batch,resources=jobs/status,verbs=get;list;watch;create;update;patch;delete;exec
//+kubebuilder:rbac:groups="",resources=jobs/status,verbs=get;list;watch;create;update;patch;delete;exec
//+kubebuilder:rbac:groups=batch,resources=configmaps,verbs=get;list;watch;create;update;patch;delete;exec
//+kubebuilder:rbac:groups=batch,resources=pods,verbs=get;list;watch;create;update;patch;delete;exec

// Reconcile is part of the main kubernetes reconciliation loop which aims to
// move the current state of the cluster closer to the desired state.
// TODO(user): Modify the Reconcile function to compare the state specified by
// the StateMachine object against the actual cluster state, and then
// perform operations to make the cluster state reflect the state specified by
// the user.
//
// For more details, check Reconcile and its Result here:
// - https://pkg.go.dev/sigs.k8s.io/controller-runtime@v0.18.4/pkg/reconcile
func (r *StateMachineReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {

	// Create a new MetricSet
	var spec mummi.StateMachine

	// Keep developer informed what is going on.
	mLog.Info("🫛 Event received by StateMachine controller!")
	mLog.Info("Request: ", "req", req)

	// Does the metric exist yet (based on name and namespace)
	err := r.Get(ctx, req.NamespacedName, &spec)
	if err != nil {

		// Create it, doesn't exist yet
		if errors.IsNotFound(err) {
			mLog.Info("🔴 StateMachine not found. Ignoring since object must be deleted.")

			// This should not be necessary, but the config map isn't owned by the operator
			return ctrl.Result{}, nil
		}
		mLog.Info("🔴 Failed to get StateMachine. Re-running reconcile.")
		return ctrl.Result{Requeue: true}, err
	}

	// Show parameters provided and validate one flux runner
	if !spec.Validate() {
		mLog.Info("🔴 Your StateMachine config did not validate.")
		return ctrl.Result{}, nil
	}

	// Ensure we have the state machine (get or create!)
	result, err := r.ensureStateMachine(ctx, &spec)
	if err != nil {
		return result, err
	}

	mLog.Info("🌀 StateMachine is Ready!")
	return result, nil
}

// SetupWithManager sets up the controller with the Manager.
// TODO go through and remove things not needed
func (r *StateMachineReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&mummi.StateMachine{}).
		Owns(&corev1.Pod{}).
		Owns(&corev1.Secret{}).
		Owns(&rbacv1.Role{}).
		Owns(&corev1.Service{}).
		Owns(&corev1.ConfigMap{}).
		Owns(&appsv1.Deployment{}).
		Owns(&appsv1.StatefulSet{}).
		Owns(&rbacv1.RoleBinding{}).
		Owns(&corev1.ServiceAccount{}).
		Complete(r)
}
