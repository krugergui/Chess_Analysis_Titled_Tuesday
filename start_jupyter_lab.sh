#!/bin/bash

# check if minikube is running, if not, run it
minikube status 
if [ $? -ne 0 ]
then
	minikube start
fi

# check if mongo database is running, if not, run it
kubectl get deployments/mongo | grep mongo
if [ $? -ne 0 ]
then
	kubectl apply -f deployment/kubernetes-mongodb/
	# wait until the mongo pod is running
	kubectl wait --for=condition=ready deployment/mongo
fi

kubectl get pods | grep jupyter-pod
if [ $? -ne 0 ]
then
	kubectl applt -f deployment/kubernetes-spark-jupyter/create_rbac.yaml
	kubectl apply -f deployment/kubernetes-spark-jupyter/run_k8s_jupyter.yaml
	# wait until the jupyter pod is running
	kubectl wait --for=condition=ready pod jupyter-pod
fi

while [ -z "$TOKEN" ]
do 
    echo "Waiting for jupyter pod to be ready..."
    sleep 2s
	TOKEN=$(kubectl logs jupyter-pod | sed -nr "s/.*token=(.*)/\1/p" | head -1 | tr -d "\r\n")
done 
URL=$(minikube service --url jupyter-pod-svc)
JUPYTER_LAB_URL=${URL}/lab?token=${TOKEN}

printf "To access the jupyter lab, go to:\n"
printf "${JUPYTER_LAB_URL}\n"
xdg-open ${JUPYTER_LAB_URL}
