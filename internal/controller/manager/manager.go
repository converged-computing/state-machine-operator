package wfmanager

import (
	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"

	api "github.com/converged-computing/state-machine-operator/api/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	ctrl "sigs.k8s.io/controller-runtime"
)

var (
	mLog = ctrl.Log.WithName("mlserver")
)

// NewWorkflowManagerDeployment returns a new MLServer deployment based on the spec
func NewWorkflowManagerDeployment(spec *api.StateMachine) *appsv1.Deployment {

	mLog.Info("Creating state machine manager deployment for: ", spec.ManagerName(), spec.Namespace)

	// Prepare pull policy and selector. Use "Never" for pre-loaded image
	// Note that interactive mode is added in entrypoint after staging
	pullPolicy := corev1.PullPolicy(spec.Spec.Manager.PullPolicy)
	command := []string{"/bin/bash", "/state_machine_operator/entrypoint.sh"}
	selector := spec.Selector()

	// MLServer container
	container := corev1.Container{
		Name:            "manager",
		Image:           spec.Spec.Manager.Image,
		ImagePullPolicy: pullPolicy,
		Command:         command,

		// Entrypoint with entrypoint.sh and kubernetes_start.sh
		VolumeMounts: []corev1.VolumeMount{
			{
				Name:      "manager-entrypoint",
				MountPath: "/state_machine_operator/",
			},
		},
	}

	// This configmap has entrypoint.sh and kubernetes_start.sh
	// It should be created before the ML Server deployment
	volumes := []corev1.Volume{
		{
			Name: "manager-entrypoint",
			VolumeSource: corev1.VolumeSource{
				ConfigMap: &corev1.ConfigMapVolumeSource{
					LocalObjectReference: corev1.LocalObjectReference{
						Name: spec.ManagerName(),
					},
				},
			},
		},
	}

	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      spec.ManagerName(),
			Namespace: spec.Namespace,
			Labels:    selector,
		},
		Spec: appsv1.DeploymentSpec{
			// Note that if we increase replicas, need to check if entrypoint needs to change
			Replicas: &spec.Spec.Manager.Replicas,

			// Match labels say which deployment a set of pods apply to
			Selector: &metav1.LabelSelector{
				MatchLabels: selector,
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: selector,
				},
				Spec: corev1.PodSpec{
					// The service account allows the pod to interact with the API
					ServiceAccountName: spec.Name,
					Subdomain:          spec.Name,
					Hostname:           "manager",
					Containers:         []corev1.Container{container},
					Volumes:            volumes,
				},
			},
		},
	}
}
