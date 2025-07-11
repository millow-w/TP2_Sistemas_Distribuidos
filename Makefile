.PHONY: help start-cluster stop-cluster build-app deploy-redis test-redis undeploy-redis clean

APP_NAME = tp2-cluster-sync-redis
APP_VERSION = latest
DOCKER_REGISTRY = camilaapa
REDIS_CONFIG_DIR = kubernets-config/redis-config

help:
	@echo "Comandos disponíveis:"
	@echo "  start-cluster - Inicia o cluster Minikube"
	@echo "  stop-cluster  - Para o cluster Minikube"
	@echo "  build-app     - Constrói a imagem Docker da aplicação"
	@echo "  deploy-redis  - Implanta o Redis no Kubernetes"
	@echo "  test-redis    - Testa a conexão com o Redis"
	@echo "  undeploy-redis- Remove o Redis do Kubernetes"
	@echo "  clean         - Limpa recursos locais"

start-cluster:
	@echo "Iniciando cluster Minikube..."
	minikube start
	minikube docker-env
	@echo "\nConfigure o ambiente Docker com:"
	@echo "eval \$$(minikube docker-env)"

stop-cluster:
	@echo "Parando cluster Minikube..."
	minikube stop

build-app:
	docker build -t $(DOCKER_REGISTRY)/$(APP_NAME):$(APP_VERSION) .

deploy-redis:
	@echo "Deploying Redis Master..."
	kubectl apply -f $(REDIS_CONFIG_DIR)/redis-secret.yaml
	kubectl apply -f $(REDIS_CONFIG_DIR)/redis-master.yaml
	@echo "Deploying Redis Sentinel..."
	kubectl apply -f $(REDIS_CONFIG_DIR)/redis-sentinel.yaml
	@echo "Deploying Redis Slaves..."
	kubectl apply -f $(REDIS_CONFIG_DIR)/redis-slave.yaml

test-redis:
	@echo "Testando conexão com Redis..."
	@echo "Executando teste de ping do Master..."
	kubectl run redis-tester --image=redis:6.0 -it --rm --restart=Never -- \
		redis-cli -h redis-master -a $$(kubectl get secret redis-secret -o jsonpath='{.data.password}' | base64 -d) ping
	@echo "\nTestando Sentinel..."
	kubectl run sentinel-tester --image=redis:6.0 -it --rm --restart=Never -- \
		redis-cli -h redis-sentinel -p 26379 sentinel get-master-addr-by-name mymaster
	@echo "\nTestando Slaves..."
	kubectl run slave-tester --image=redis:6.0 -it --rm --restart=Never -- \
		sh -c "redis-cli -h redis-slave info replication | grep 'role:slave'"

undeploy-redis:
	@echo "Removendo Redis..."
	kubectl delete -f $(REDIS_CONFIG_DIR)/redis-master.yaml
	kubectl delete -f $(REDIS_CONFIG_DIR)/redis-secret.yaml
	kubectl delete -f $(REDIS_CONFIG_DIR)/redis-sentinel.yaml
	kubectl delete -f $(REDIS_CONFIG_DIR)/redis-slave.yaml

clean:
	@echo "Limpando recursos locais..."
	docker rmi $(DOCKER_REGISTRY)/$(APP_NAME):$(APP_VERSION) 2>/dev/null || true
	minikube delete