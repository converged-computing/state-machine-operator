/*
Copyright 2025 Lawrence Livermore National Security, LLC
 (c.f. AUTHORS, NOTICE.LLNS, COPYING)

This is part of the Flux resource manager framework.
For details, see https://github.com/flux-framework.

SPDX-License-Identifier: Apache-2.0
*/

package controller

import (
	"context"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
	manager "github.com/converged-computing/state-machine-operator/internal/controller/manager"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

// ensure the wfmaanger deployment is created
func (r *StateMachineReconciler) ensureManager(
	ctx context.Context,
	spec *api.StateMachine,
) (ctrl.Result, error) {

	// Create the config map entrypoint first
	cm := &corev1.ConfigMap{}
	err := r.Get(ctx, types.NamespacedName{Name: spec.ManagerName(), Namespace: spec.Namespace}, cm)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createManagerEntrypoint(ctx, spec)
		}
		return ctrl.Result{}, err
	}

	// Create the MLServer deployment
	existing := &appsv1.Deployment{}
	err = r.Get(ctx, types.NamespacedName{Name: spec.ManagerName(), Namespace: spec.Namespace}, existing)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createManager(ctx, spec)
		}
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, err
}

// createMLServer creates the MLserver
func (r *StateMachineReconciler) createManager(
	ctx context.Context,
	spec *api.StateMachine,
) (*appsv1.Deployment, error) {

	deployment := manager.NewWorkflowManagerDeployment(spec)
	ctrl.SetControllerReference(spec, deployment, r.Scheme)
	err := r.Create(ctx, deployment)
	return deployment, err
}

// createMLServerEntrypoint creates the entrypoint configmap
func (r *StateMachineReconciler) createManagerEntrypoint(
	ctx context.Context,
	spec *api.StateMachine,
) (*corev1.ConfigMap, error) {

	// Return data for the workflow manager entrypoint, along with all of the job specs
	// entrypoint.sh
	// kubernetes_start.sh
	// wfmanager.yaml
	// jobs_cg.yaml
	// jobs_createsim.yaml

	data, err := manager.NewEntrypoint(spec)
	if err != nil {
		return nil, err
	}
	cm := &corev1.ConfigMap{
		ObjectMeta: metav1.ObjectMeta{
			Name:      spec.ManagerName(),
			Namespace: spec.Namespace,
		},
		Data: data,
	}

	ctrl.SetControllerReference(spec, cm, r.Scheme)
	err = r.Create(ctx, cm)
	return cm, err
}
