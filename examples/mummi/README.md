# Mummi Demo

The code and containers for this demo are entirely private. Follow the same instructions to create the kind cluster and install the operator. Then:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 633731392008.dkr.ecr.us-east-1.amazonaws.com
kind load docker-image 633731392008.dkr.ecr.us-east-1.amazonaws.com/mini-mummi:mlrunner
kind load docker-image 633731392008.dkr.ecr.us-east-1.amazonaws.com/mini-mummi:createsims
kind load docker-image 633731392008.dkr.ecr.us-east-1.amazonaws.com/mini-mummi:cganalysis
```

And apply:

```bash
kubectl apply -f mummi.yaml
```
