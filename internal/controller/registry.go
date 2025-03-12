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
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

// createRegistry creates a stateful set for the registry, only if warranted
// A stateful set is used and not a deployment because it can provide stateful features:
// - storage
// - network identity (e.g., registry-0)
func (r *StateMachineReconciler) createRegistry(
	ctx context.Context,
	spec *api.StateMachine,
) (ctrl.Result, error) {

	// Check for existing registry stateful set
	existing := &appsv1.StatefulSet{}
	err := r.Get(ctx, types.NamespacedName{Name: spec.Spec.Registry.Name, Namespace: spec.Namespace}, existing)
	if err != nil {
		if errors.IsNotFound(err) {
			_, err = r.createStatefulSet(ctx, spec)
		}
	}
	return ctrl.Result{}, err
}

// createStatefulSet creates the actual registry stateful set
func (r *StateMachineReconciler) createStatefulSet(
	ctx context.Context,
	spec *api.StateMachine,
) (*appsv1.StatefulSet, error) {

	mLog.Info("Creating stateful set for registry with: ", spec.Name, spec.Namespace)

	// Request the selector just once
	selector := spec.Selector()
	pullPolicy := corev1.PullPolicy(spec.Spec.Registry.PullPolicy)

	// Define the StatefulSet
	// Having a common name "registry" assumes that multiply mini-mummi in the same namespace
	// can use the same registry. I think it's unlikely we'd do this, but I think it's reasonable
	statefulSet := &appsv1.StatefulSet{
		ObjectMeta: metav1.ObjectMeta{Name: spec.Spec.Registry.Name, Namespace: spec.Namespace},
		Spec: appsv1.StatefulSetSpec{
			ServiceName: spec.Name,
			Replicas:    &spec.Spec.Registry.Replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: selector,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: selector,
				},
				Spec: corev1.PodSpec{
					Subdomain: spec.Name,
					Hostname:  spec.Spec.Registry.Name,

					// Container names can be consistent within pods
					Containers: []corev1.Container{
						{
							Name:            "registry",
							Image:           spec.Spec.Registry.Image,
							ImagePullPolicy: pullPolicy,
						},
					},
					// Note that this is on a headless service, so we don't
					// need to expose further ports to the cluster namespace
					// We might eventually want to add the registry http secret
					// ideally secret from a secret. We assume now it's just for the cluster
					// Containers -> env: name: REGISTRY_HTTP_SECRET, value: somesecret
				},
			},
		},
	}

	if spec.Spec.Registry.NodeSelector != "" {
		nodeSelector := map[string]string{"node.kubernetes.io/instance-type": spec.Spec.Manager.NodeSelector}
		statefulSet.Spec.Template.Spec.NodeSelector = nodeSelector
	}

	ctrl.SetControllerReference(spec, statefulSet, r.Scheme)
	err := r.Create(ctx, statefulSet)
	return statefulSet, err
}
