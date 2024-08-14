#!/bin/bash

# Check if minikube is running if not, start it
minikube_status=$(minikube status -o json)

if [[ "$minikube_status" = *"Stopped"* ]]; then
    echo $'\nMinikube is installed and configured\n'
    minikube start
elif [[ "$minikube_status" = *"Running"* ]]; then
    echo $'\nMinikube is already running\n'
else
    echo $'\nMinikube has to be initialized\n'
    read -p "State how much memory you want to allocate to minikube - in GB - e.g., '4' = 4GB: " minikube_memory
    read -p "State how much CPU you want to allocate to minikube - in cores - e.g., '4' = 4 cores: " minikube_cpu

    minikube start --cpus $minikube_cpu --memory $(($minikube_memory * 1000))
    echo $'\nMinikube initialized\n'
fi

# Check if Minikube has the necessary addons

minikube_addons=$(minikube addons list -o json)

if [[ "$minikube_addons" != *"ingress"* ]]; then
    echo $'\Enablijng  Minikube ingress addon\n'
    minikube addons enable ingress
fi

if [[ "$minikube_addons" != *"ingress-dns"* ]]; then
    echo $'\nEnabling Minikube ingress-dns addon\n'
    minikube addons enable ingress-dns
fi

# Build all container images
echo $'Building Container images, this can take several minutes dependening on internet speed\n'
sudo -u $USER make build_all
echo $'\nContainer images builded\n'

# Initialize MongoDB
echo $'\nDownloading and initializing MongoDB Container, this can take several minutes dependening on internet speed\n'
kubectl apply -f deployment/kubernetes-mongodb
echo $'\nMongoDB Container initialized\n'

# Apply all kubernetes configurations
echo $'\nApplying Kubernetes configurations\n'
kubectl apply -f deployment/kubernetes-mongodb/
echo $'\nKubernetes configurations applied\n'

# Inserting first games into landing area
echo $'\nInserting first games into landing area\n'
kubectl create job --from=cronjob/update-new-games first-run-landing-area
echo $'\nWaiting for first-run-landing-area job to be ready\n'
kubectl wait --for=condition=ready pod -l app=update-new-games
kubectl attach -it jobs/first-run-landing-area
echo $'\nFinished updating landing area\n'

# Update silver table
echo $'\nUpdating silver table\n'
kubectl create job --from=cronjob/update-silver-games first-run-update-silver-games
echo $'\nWaiting for update-silver-games job to be ready\n'
kubectl wait --for=condition=ready pod -l app=update-silver-games
kubectl attach -it jobs/update-silver-games
echo $'\nFinished updating silver table\n'

echo $'\nFinished setup'
echo $'The data can now be accesed in the Mongo DB'
echo 'You can access the Database in the following URL' 
minikube service mongo-nodeport-svc --url
echo $´Please check the README.md for more information\n'