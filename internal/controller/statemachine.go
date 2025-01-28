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

	ctrl "sigs.k8s.io/controller-runtime"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
)

// ensureStateMachine creates a new StateMachine
func (r *StateMachineReconciler) ensureStateMachine(
	ctx context.Context,
	spec *api.StateMachine,
) (ctrl.Result, error) {

	// Create headless service for the State Machine jobs / registry
	result, err := r.exposeServices(ctx, spec)
	if err != nil {
		return result, err
	}

	// Create RBAC that will give the state machine manager permission to create jobs
	// This means Role and RoleBinding that provide permission on the level of a namespace
	result, err = r.createRBAC(ctx, spec)
	if err != nil {
		return result, err
	}

	// Create the registry, only if we need to!
	// The selector is needed to add it to the headless service
	if spec.HasInClusterRegistry() {
		result, err := r.createRegistry(ctx, spec)
		if err != nil {
			return result, err
		}
	}

	// Create the wfmanager deployment
	result, err = r.ensureManager(ctx, spec)
	if err != nil {
		return result, err
	}

	// TODO: look into labels for autoscaler for jobs that wfmanager creates
	return ctrl.Result{}, nil
}
