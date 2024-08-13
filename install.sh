#!/bin/bash
# Checks if the user is using Ubuntu 24.04 LTS
if [[ "$(lsb_release -rs)" != "24.04" ]]; then
    echo '\nThis project requires Ubuntu 24.04 LTS'
    echo 'Exiting...'
    exit 0
fi

# Checks if the user has root privileges
if [[ "$EUID" -ne 0 ]]; then
    echo '\nThis project requires root privileges'
    echo 'Exiting...'
    exit 0
fi

reboot_required=false

# Check if Docker is installed
if [[ -x "$(command -v docker)" ]]; then
    echo $'\nDocker is already installed'
else
    # Install Docker CE
    echo $'\nInstalling Docker CE -  more info: https://docs.docker.com/engine/install/ubuntu/\n'
    
    # Add Docker's official GPG key:
    sudo apt-get install ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add the repository to Apt sources:
    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update

    # Install Docker Engine
    sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Check if Docker CE is installed correctly
    docker_message=$(sudo docker run hello-world)

    if [[ "$docker_message" = *"Hello from Docker!"* ]]; then
        echo '\nDocker CE was installed correctly\n'
    else
        echo '\nDocker CE installation failed'
        echo 'Please contact the project owner'
        exit 0
    fi

    # Add user to Docker group
    echo $'\nAdding user to Docker group\n'
    sudo groupadd docker
    sudo usermod -aG docker $USER
    newgrp docker
    echo $'User added to Docker group\n'

    reboot_required=true
fi

# Install minikube
if [[ -x "$(command -v minikube)" ]]; then
    echo $'\nMinikube is already installed'
else
    echo $'\nInstalling Minikube - more info: https://minikube.sigs.k8s.io/docs/start/\n'
    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube_latest_amd64.deb
    sudo dpkg -i minikube_latest_amd64.deb
    
    # Check if minikube is installed correctly
    if [[ -x "$(command -v minikube)" ]]; then
        echo $'\nMinikube was installed correctly\n'
    else
        echo $'\nMinikube installation failed'
        echo 'Please contact the project owner'
        exit 0
    fi
fi

# Install kubectl

if [[ -x "$(command -v kubectl)" ]]; then
    echo $'\nKubectl is already installed'
else
    echo $'\nInstalling kubectl - more info: https://kubernetes.io/docs/tasks/tools/\n'
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

    # Check if kubectl is installed correctly
    if [[ -x "$(command -v kubectl)" ]]; then
        echo $'\nKubectl was installed correctly\n'
    else
        echo $'\nKubectl installation failed'
        echo 'Please contact the project owner'
        exit 0
    fi
fi

if [[ "$reboot_required" = true ]]; then
    echo $'\nReboot required, please restart your system to complete the installation\n'
    echo $'This is required for Docker to start without root\n'
    echo $'After reboot, run this script again'
    exit 0
fi

docker_message=$(docker run hello-world)

if [[ "$docker_message" != *"Hello from Docker!"* ]]; then
    echo $'\nDocker is not running without root, have you rebooted?'
    echo 'If yes, please contact the project owner'
    exit 0
fi

echo $'\nPrerequisites Fullfiled'

exit 0