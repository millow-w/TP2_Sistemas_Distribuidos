.PHONY: help start-cluster stop-cluster build-app deploy-redis test-redis undeploy-redis \
        deploy-cluster-sync undeploy-cluster-sync test-cluster-sync \
        deploy-clients undeploy-clients test-clients \
        deploy-all undeploy-all test-system \
        clean

APP_NAME = tp2-cluster-sync-redis
APP_VERSION = latest
DOCKER_REGISTRY = camilaapa
REDIS_CONFIG_DIR = kubernets-config/redis-config
CLUSTER_SYNC_CONFIG_DIR = kubernets-config/cluster-sync-config
CLIENT_CONFIG_DIR = kubernets-config/client-config

help:
	@echo "Comandos disponíveis:"
	@echo "  start-cluster          - Inicia o cluster Minikube"
	@echo "  stop-cluster           - Para o cluster Minikube"
	@echo "  build-app              - Constrói a imagem Docker da aplicação"
	@echo "  deploy-redis           - Implanta o Redis no Kubernetes"
	@echo "  test-redis             - Testa a conexão com o Redis"
	@echo "  undeploy-redis         - Remove o Redis do Kubernetes"
	@echo "  deploy-cluster-sync    - Implanta os nós do cluster de sincronização"
	@echo "  undeploy-cluster-sync  - Remove os nós do cluster de sincronização"
	@echo "  test-cluster-sync      - Testa a saúde dos nós do cluster"
	@echo "  deploy-clients         - Implanta os clientes"
	@echo "  undeploy-clients       - Remove os clientes"
	@echo "  test-clients           - Verifica os logs iniciais dos clientes"
	@echo "  deploy-all             - Implanta todo o sistema (Redis, nós e clientes)"
	@echo "  undeploy-all           - Remove todo o sistema"
	@echo "  test-system            - Testa o sistema de exclusão mútua distribuída"
	@echo "  clean                  - Limpa recursos locais"

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

deploy-cluster-sync:
	@echo "Implantando nós do cluster..."
	kubectl apply -f $(CLUSTER_SYNC_CONFIG_DIR)/cluster-sync-headless-service.yaml
	kubectl apply -f $(CLUSTER_SYNC_CONFIG_DIR)/cluster-sync-statefulset.yaml

undeploy-cluster-sync:
	@echo "Removendo nós do cluster..."
	kubectl delete -f $(CLUSTER_SYNC_CONFIG_DIR)/cluster-sync-statefulset.yaml
	kubectl delete -f $(CLUSTER_SYNC_CONFIG_DIR)/cluster-sync-headless-service.yaml

test-cluster-sync:
	@echo "Testando nós..."
	kubectl run tester --image=curlimages/curl --rm -it --restart=Never -- \
		sh -c "curl -s node-0.node:5000/health && echo"

deploy-clients:
	@echo "Implantando clientes..."
	kubectl apply -f $(CLIENT_CONFIG_DIR)/

undeploy-clients:
	@echo "Removendo clientes..."
	kubectl delete -f $(CLIENT_CONFIG_DIR)/

test-clients:
	@echo "Verificando logs dos clientes:"
	@for i in 0 1 2 3 4; do \
		echo -n "client-$$i: "; \
		kubectl logs job/client-$$i | grep "starting"; \
	done

deploy-all: build-app deploy-redis deploy-cluster-sync deploy-clients
	@echo "Sistema completo implantado!"

undeploy-all: undeploy-clients undeploy-cluster-sync undeploy-redis
	@echo "Todos os componentes removidos!"

test-cs: 
	@echo "Vendo quem está em cs: "
	@kubectl run cs-watcher --rm -it --restart=Never --image=redis:6.0 \
		-- redis-cli -h redis-master -a redisStrongPass123 SUBSCRIBE cs_monitor


test-system: test-redis test-cluster-sync
	@echo "Testando sistema de exclusão mútua distribuída..."
	@echo "Aguardando execução dos clientes..."

	# Aguarda até todos os pods de clientes saírem do estado Running
	@while kubectl get pods | grep client | grep -q Running; do sleep 1; done
	@sleep 2

	@echo "\nVerificando conclusão dos clientes:"
	@for i in 0 1 2 3 4; do \
		echo "======== Client $$i ========"; \
		kubectl logs job/client-$$i | grep -e "completed all accesses" -e "ERROR" | tail -1; \
		echo; \
	done

	@echo "\nVerificando erros nos nós do cluster:"
	@for i in 0 1 2 3 4; do \
		echo "======== Node $$i ========"; \
		kubectl logs node-$$i | grep "ERROR" | tail -5; \
		echo; \
	done

	@echo "\nTeste do sistema completo!"

clean:
	@echo "Limpando recursos locais..."
	docker rmi $(DOCKER_REGISTRY)/$(APP_NAME):$(APP_VERSION) 2>/dev/null || true
	minikube delete