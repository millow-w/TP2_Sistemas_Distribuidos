# Qualquer elemento do Cluster Sync ao receber uma solicitação de um cliente envia uma mensagem de Pub a um tópico denominado R topic ou a uma fila denominada R Queue. Nesta mensagem de Pub é inserido apenas o ID do elemento do Cluster Sync, o pedido do cliente e a primitiva ACQUIRE. 

# Cada elemento do Cluster Sync é também um consumidor, portanto recebe todas as mensagens enviadas pelo broker e o mais interessante: NA MESMA ORDEM FIFO, por exemplo. Cabe a cada elemento do cluster ficar avaliando sua fila F (PRIVADA)  de mensagens do broker para saber se pode ou não entrar na seção crítica. 

# Após entrar na seção crítica por um tempo (Sleep de 0.2 a 1 segundo), o elemento do Cluster Sync envia uma mensagem de Pub ao mesmo tópico ou fila do broker, mas neste caso contendo seu ID, o pedido do cliente e a primitiva RELEASE. 

# Note que para entrar na seção crítica (acessar R para escrita), cada elemento do Cluster Sync deve olhar a sua ordem de ACQUIRE e também a ordem de RELEASES, assim como o pedido do cliente.

# src/node.py
from flask import Flask
import os
import logging

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health')
def health():
    logger.info("Health check called")
    return "OK", 200

@app.route('/ready')
def ready():
    logger.info("Ready check called")
    
    # Verifica se as variáveis essenciais estão presentes
    required_envs = ['REDIS_SENTINELS', 'REDIS_SENTINEL_MASTER', 'REDIS_PASSWORD', 'NODE_ID']
    for var in required_envs:
        if not os.getenv(var):
            logger.error(f"Missing environment variable: {var}")
            return f"Missing environment variable: {var}", 503
    
    return "READY", 200

if __name__ == '__main__':
    # Log das variáveis de ambiente no startup (cuidado com senhas em produção)
    logger.info("Starting node with environment:")
    logger.info(f"NODE_ID: {os.getenv('NODE_ID')}")
    logger.info(f"REDIS_SENTINELS: {os.getenv('REDIS_SENTINELS')}")
    logger.info(f"REDIS_SENTINEL_MASTER: {os.getenv('REDIS_SENTINEL_MASTER')}")
    logger.info("REDIS_PASSWORD is set: " + ("yes" if os.getenv("REDIS_PASSWORD") else "no"))
    
    app.run(host='0.0.0.0', port=5000)