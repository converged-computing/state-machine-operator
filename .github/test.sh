#!/bin/bash

set -eEu -o pipefail

# Show logs for the manager (need to do this while it exists)
sleep 10
manager=$(kubectl get pods  -l component=state-machine-manager -o json | jq -r .items[0].metadata.name)
echo "Manager pod is $manager"
kubectl logs $manager

# For each job, we want to wait until complete
while true
  do
  sleep 20
  echo "Checking jobs..."
  kubectl get pods
  # We need 12 completed (successful) jobs
  counter=0
  for job in $(kubectl get jobs -o json | jq -r .items[].metadata.name)  
    do
      failed_status=$(kubectl get job $job -o jsonpath={.status.failed})
      success_status=$(kubectl get job $job -o jsonpath={.status.succeeded})
      if [[ "${success_status}" == "1" ]]; then
         echo "Job $job was successful"
         counter=$(expr $counter + 1)
      fi
      if [[ "${failed_status}" == "1" ]]; then
         echo "Job ${job} has failed"
         exit 1;
      fi
  done
  if [[ "$counter" == "12" ]]; then
     echo "Workflow completed successfully"
     break
  fi 
done

kubectl logs $manager

