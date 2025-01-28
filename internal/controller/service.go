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

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

// exposeService will expose services - one for the port 5000 forward, and the other for job networking (headless)
func (r *StateMachineReconciler) exposeServices(
	ctx context.Context,
	spec *api.StateMachine,
) (ctrl.Result, error) {

	// Create either the headless service or broker service
	existing := &corev1.Service{}
	err := r.Get(ctx, types.NamespacedName{Name: spec.Name, Namespace: spec.Namespace}, existing)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createHeadlessService(ctx, spec)
		}
		return ctrl.Result{}, err
	}
	return ctrl.Result{}, err
}

// createHeadlessService creates the service for the MiniCluster
func (r *StateMachineReconciler) createHeadlessService(
	ctx context.Context,
	spec *api.StateMachine,
) (*corev1.Service, error) {

	mLog.Info("Creating headless service with: ", spec.Name, spec.Namespace)
	service := &corev1.Service{
		ObjectMeta: metav1.ObjectMeta{Name: spec.Name, Namespace: spec.Namespace},
		Spec: corev1.ServiceSpec{
			ClusterIP: "None",
			Selector:  spec.Selector(),
		},
	}
	ctrl.SetControllerReference(spec, service, r.Scheme)
	err := r.Create(ctx, service)
	return service, err
}
