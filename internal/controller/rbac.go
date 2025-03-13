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
	rbacv1 "k8s.io/api/rbac/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

// createRBAC to create roles and role bindings for workflow manager.
// This is not the ideal design - we should instead have the wfmanager interact with a grpc api
// Or have the operator do the orchestration / monitoring completely.
// It's too big a change to do off the bat, but should be done.
func (r *StateMachineReconciler) createRBAC(
	ctx context.Context,
	spec *api.StateMachine,
) (ctrl.Result, error) {

	// Role (permissions for the namespace)
	existing := &corev1.ServiceAccount{}
	err := r.Get(ctx, types.NamespacedName{Name: spec.Name, Namespace: spec.Namespace}, existing)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createServiceAccount(ctx, spec)
		}
		return ctrl.Result{}, err
	}

	// Cluster Role (permissions to watch nodes)
	clusterRole := &rbacv1.ClusterRole{}
	err = r.Get(ctx, types.NamespacedName{Name: spec.ClusterRoleName(), Namespace: spec.Namespace}, clusterRole)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createClusterRole(ctx, spec)

		}
		return ctrl.Result{}, err
	}

	// Role Bindings for the role
	clusterBinding := &rbacv1.ClusterRoleBinding{}
	err = r.Get(ctx, types.NamespacedName{Name: spec.ClusterRoleName(), Namespace: spec.Namespace}, clusterBinding)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createClusterRoleBinding(ctx, spec)
		}
		return ctrl.Result{}, err
	}

	// Role (permissions for the namespace)
	role := &rbacv1.Role{}
	err = r.Get(ctx, types.NamespacedName{Name: spec.RoleName(), Namespace: spec.Namespace}, role)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createRole(ctx, spec)

		}
		return ctrl.Result{}, err
	}

	// Role Bindings for the role
	binding := &rbacv1.RoleBinding{}
	err = r.Get(ctx, types.NamespacedName{Name: spec.RoleName(), Namespace: spec.Namespace}, binding)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createRoleBinding(ctx, spec)
			return ctrl.Result{}, err
		}
	}
	return ctrl.Result{}, err
}

// createServiceAccount creates the service account needed for the role bindings
func (r *StateMachineReconciler) createServiceAccount(
	ctx context.Context,
	spec *api.StateMachine,
) (*corev1.ServiceAccount, error) {
	mLog.Info("Creating service account for: ", spec.Name, spec.Namespace)
	sa := &corev1.ServiceAccount{
		ObjectMeta: metav1.ObjectMeta{Name: spec.Name, Namespace: spec.Namespace},
	}
	ctrl.SetControllerReference(spec, sa, r.Scheme)
	err := r.Create(ctx, sa)
	return sa, err
}

// createRole creates permissions for the wfmanager scoped to the namespace
func (r *StateMachineReconciler) createRole(
	ctx context.Context,
	spec *api.StateMachine,
) (*rbacv1.Role, error) {

	mLog.Info("Creating role for: ", spec.Name, spec.Namespace)
	role := &rbacv1.Role{
		ObjectMeta: metav1.ObjectMeta{Name: spec.RoleName(), Namespace: spec.Namespace},
		Rules: []rbacv1.PolicyRule{
			{
				APIGroups: []string{"", "batch"},
				Resources: []string{"pods", "jobs", "configmaps", "jobs/status"},
				Verbs:     []string{"list", "get", "patch", "create", "delete", "watch"},
			},
		},
	}
	ctrl.SetControllerReference(spec, role, r.Scheme)
	err := r.Create(ctx, role)
	return role, err
}

// createRole creates permissions for the wfmanager scoped to the namespace
func (r *StateMachineReconciler) createClusterRole(
	ctx context.Context,
	spec *api.StateMachine,
) (*rbacv1.ClusterRole, error) {

	mLog.Info("Creating cluster role for: ", spec.Name, spec.Namespace)
	role := &rbacv1.ClusterRole{
		ObjectMeta: metav1.ObjectMeta{Name: spec.ClusterRoleName(), Namespace: spec.Namespace},
		Rules: []rbacv1.PolicyRule{
			{
				APIGroups: []string{""},
				Resources: []string{"nodes"},
				Verbs:     []string{"list", "get", "watch"},
			},
		},
	}
	ctrl.SetControllerReference(spec, role, r.Scheme)
	err := r.Create(ctx, role)
	return role, err
}

// createRoleBinding creates the role binding to allow wfmanager to create jobs
func (r *StateMachineReconciler) createRoleBinding(
	ctx context.Context,
	spec *api.StateMachine,
) (*rbacv1.RoleBinding, error) {
	mLog.Info("Creating role binding for: ", spec.Name, spec.Namespace)
	binding := &rbacv1.RoleBinding{
		ObjectMeta: metav1.ObjectMeta{Name: spec.RoleName(), Namespace: spec.Namespace},
		Subjects: []rbacv1.Subject{
			{
				Kind:      "ServiceAccount",
				Name:      spec.Name,
				Namespace: spec.Namespace,
			},
		},
		RoleRef: rbacv1.RoleRef{
			Kind:     "Role",
			Name:     spec.RoleName(),
			APIGroup: "rbac.authorization.k8s.io",
		},
	}
	ctrl.SetControllerReference(spec, binding, r.Scheme)
	err := r.Create(ctx, binding)
	return binding, err
}

func (r *StateMachineReconciler) createClusterRoleBinding(
	ctx context.Context,
	spec *api.StateMachine,
) (*rbacv1.ClusterRoleBinding, error) {
	mLog.Info("Creating role binding for cluster role: ", spec.Name, spec.Namespace)
	binding := &rbacv1.ClusterRoleBinding{
		ObjectMeta: metav1.ObjectMeta{Name: spec.ClusterRoleName(), Namespace: spec.Namespace},
		Subjects: []rbacv1.Subject{
			{
				Kind:      "ServiceAccount",
				Name:      spec.Name,
				Namespace: spec.Namespace,
			},
		},
		RoleRef: rbacv1.RoleRef{
			Kind:     "ClusterRole",
			Name:     spec.ClusterRoleName(),
			APIGroup: "rbac.authorization.k8s.io",
		},
	}
	ctrl.SetControllerReference(spec, binding, r.Scheme)
	err := r.Create(ctx, binding)
	return binding, err
}
