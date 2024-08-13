install:
		./install.sh

start_minikube:
		@if ! minikube status > /dev/null 2>&1; then \
			minikube start; \
		fi

build_update_silver_etl:
		make start_minikube
		eval $$(minikube -p minikube docker-env) ;\
		docker build -t update_silver_etl -f deployment/Dockerfiles/Dockerfile_update_silver . ;\
		docker image prune -f

build_update_new_games:
		make start_minikube
		eval $$(minikube -p minikube docker-env) ;\
		docker build -t update_new_games -f deployment/Dockerfiles/Dockerfile_update_new_games . ;\
		docker image prune -f

build_spark_base:
		make start_minikube
		eval $$(minikube -p minikube docker-env) ;\
		docker build -t spark-k8s-base -f deployment/Dockerfiles/Dockerfile-spark-k8s-base . ;\
		docker image prune -f

build_spark_driver:
		make start_minikube
		eval $$(minikube -p minikube docker-env) && \
		docker build -t spark-k8s-driver -f deployment/Dockerfiles/Dockerfile-spark-k8s-driver . ;\
		docker image prune -f

build_spark_jupyter:
		make start_minikube
		eval $$(minikube -p minikube docker-env) && \
		docker build -t spark-k8s-jupyter -f deployment/Dockerfiles/Dockerfile-spark-k8s-jupyter . ;\
		docker image prune -f

build_all:
		@make build_update_silver_etl
		@make build_update_new_games
		@make build_spark_base
		@make build_spark_driver
		@make build_spark_jupyter

setup_kubernetes_cluster:
		minikube start
		kubectl apply -f deployment/kubernetes-mongodb
