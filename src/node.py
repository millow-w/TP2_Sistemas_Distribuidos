# Qualquer elemento do Cluster Sync ao receber uma solicitação de um cliente envia uma mensagem de Pub a um tópico denominado R topic ou a uma fila denominada R Queue. Nesta mensagem de Pub é inserido apenas o ID do elemento do Cluster Sync, o pedido do cliente e a primitiva ACQUIRE. 

# Cada elemento do Cluster Sync é também um consumidor, portanto recebe todas as mensagens enviadas pelo broker e o mais interessante: NA MESMA ORDEM FIFO, por exemplo. Cabe a cada elemento do cluster ficar avaliando sua fila F (PRIVADA)  de mensagens do broker para saber se pode ou não entrar na seção crítica. 

# Após entrar na seção crítica por um tempo (Sleep de 0.2 a 1 segundo), o elemento do Cluster Sync envia uma mensagem de Pub ao mesmo tópico ou fila do broker, mas neste caso contendo seu ID, o pedido do cliente e a primitiva RELEASE. 

# Note que para entrar na seção crítica (acessar R para escrita), cada elemento do Cluster Sync deve olhar a sua ordem de ACQUIRE e também a ordem de RELEASES, assim como o pedido do cliente.

from flask import Flask, request, jsonify
import os
import logging
import threading
import time
import random
import redis
from redis.sentinel import Sentinel
# from collections import deque
import bisect

# ---------- INICIALIZAÇÃO DO FLASK -----------

app = Flask(__name__)

# ---------- CONFIGURAÇÃO DE LOGGING ----------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- VÁRIÁVEIS DE AMBIENTE ----------

NODE_ID = os.getenv('NODE_ID')
REDIS_SENTINELS = os.getenv('REDIS_SENTINELS')
REDIS_SENTINEL_MASTER = os.getenv('REDIS_SENTINEL_MASTER')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
STREAM_NAME = 'resource_r_stream'

if not all([NODE_ID, REDIS_SENTINELS, REDIS_SENTINEL_MASTER, REDIS_PASSWORD]):
    logger.error("Missing required environment variables")
    exit(1)

# ---------- CONEXÃO COM O REDIS VIA SENTINEL ----------

sentinel_list = [tuple(s.split(':')) for s in REDIS_SENTINELS.split(',')]
sentinel = Sentinel(sentinel_list, socket_timeout=5)

redis_master = sentinel.master_for(REDIS_SENTINEL_MASTER, password=REDIS_PASSWORD, socket_timeout=5)

# ---------- SINCRONIZAÇÃO DE THREADS ----------

# impede condições de corrida ao acessar/alterar a fila ou mapa de eventos.
lock = threading.Lock()

request_queue = [] # Fila FIFO de pedidos de acesso

class Request:
    def __init__(self, node_id, client_id, timestamp, access_num):
        self.node_id = node_id
        self.client_id = client_id
        self.timestamp = int(timestamp)
        self.access_num = access_num

    def __lt__(self, other):  # Define ordenação por timestamp
        return self.timestamp < other.timestamp

    def to_dict(self):
        return {
            'node_id': self.node_id,
            'client_id': self.client_id,
            'timestamp': str(self.timestamp),
            'access_num': self.access_num
        }  

# { (client_id, timestamp): threading.Event }
# mapeia pedidos que estão esperando a liberação do recurso (cada cliente espera seu .Event() ser sinalizado).
pending_requests = {}

# ----------- ENDPOINTS DE HEALTH CHECK ----------

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ready')
def ready():
    try:
        redis_master.ping()
        return "READY", 200
    except Exception as e:
        logger.erro(f"Redis not ready: {str(e)}")
        return "Not ready", 503
    
# ---------- PROCESSAMENTO DE EVENTO DO STREAM -----------

def process_event(event_data):
    with lock:
        # Extrai dados do evento publicado
        event_type = event_data['type']
        node_id = event_data['node_id']
        client_id = event_data['client_id']
        timestamp = event_data['timestamp']
        access_num = event_data['access_num']

        # Chave única para identificar o pedido
        key = (client_id, timestamp)

        if event_type == 'ACQUIRE': 
            # request_queue.append({
            #     'node_id': node_id,
            #     'client_id': client_id,
            #     'timestamp': timestamp,
            #     'access_num': access_num
            # })
            new_req = Request(node_id, client_id, timestamp, access_num)
            bisect.insort(request_queue, new_req)
            logger.info(f"ACQUIRE added to queue - Client: {client_id}, TS: {timestamp}")
        elif event_type == 'RELEASE':
            # if request_queue and request_queue[0]['client_id'] == client_id and request_queue[0]['timestamp'] == timestamp:
            if request_queue and request_queue[0].client_id == client_id and str(request_queue[0].timestamp) == timestamp:
                # request_queue.popleft()
                request_queue.pop(0)
                logger.info(f"RELEASE processed - Client: {client_id}, TS: {timestamp}")

        # Verifica se o primeiro da fila é deste nó e sinaliza
        # if request_queue and request_queue[0]['node_id'] == NODE_ID:
        #     next_req = request_queue[0]
        #     next_key = (next_req['client_id'], next_req['timestamp'])

        #     if next_key in pending_requests:
        #         pending_requests[next_key].set()
        #         logger.info(f"Resource granted for Client: {next_req['client_id']}, Access#: {next_req['access_num']}")

        if request_queue and request_queue[0].node_id == NODE_ID:
            next_req = request_queue[0]
            next_key = (next_req.client_id, str(next_req.timestamp))
            if next_key in pending_requests:
                pending_requests[next_key].set()
                logger.info(f"Resource granted for Client: {next_req.client_id}, Access#: {next_req.access_num}")

# ---------- CONSUMIDOR DE EVENTOS (STREAM READER) -----------
def consume_events():
    last_id = '0'
    while True: # Verificar isso depois ##############&&&&&&&&&&########
        try:
            events = redis_master.xread({STREAM_NAME: last_id}, count=1, block=5000)
            if events:
                stream, messages = events[0]
                for message_id, message_data in messages:
                    last_id = message_id
                    process_event({k.decode(): v.decode() for k, v in message_data.items()})
        except redis.exceptions.TimeoutError:
            logger.debug("No new event in stream, waiting again...")
            time.sleep(1)

# ---------- ENDPOINT PARA SOLICITAÇÃO DE ACESSO -----------
@app.route('/request_access', methods=['POST'])
def handle_request():
    data = request.json
    client_id = data['client_id']
    timestamp = data['timestamp']
    access_num = data['access_num']

    logger.info(f"Request received - Client: {client_id}, Access#: {access_num}, TS: {timestamp}")
    
    # Publicar evento ACQUIRE
    try:
        event_data = {
            'type': 'ACQUIRE',
            'node_id': NODE_ID,
            'client_id': client_id,
            'timestamp': str(timestamp),
            'access_num': str(access_num)
        }
        redis_master.xadd(STREAM_NAME, event_data)
        logger.info(f"ACQUIRE published - Client: {client_id}, TS: {timestamp}")
    except Exception as e:
        logger.error(f"Failed to publish ACQUIRE: {str(e)}")
        return jsonify({"status": "ERROR"}), 500

    # Cria evento de sincronização
    event = threading.Event()
    key = (client_id, str(timestamp))

    with lock:
        pending_requests[key] = event

    # Aguardar liberação do recurso (timeout: 30s)
    if not event.wait(30):
        with lock:
            if key in pending_requests:
                del pending_requests[key]
        return jsonify({"status": "TIMEOUT"}), 408
    
    # Simular tempo na seçao crítica
    time.sleep(random.uniform(0.2, 1.0))

    # Publicar evento RELEASE
    try:
        event_data = {
            'type': 'RELEASE', 
            'node_id': NODE_ID,
            'client_id': client_id, 
            'timestamp': str(timestamp),
            'access_num': str(access_num)
        }
        redis_master.xadd(STREAM_NAME, event_data)
        logger.info(f"RELEASE published - Client: {client_id}, TS: {timestamp}")
    except Exception as e:
        logger.error(f"Failed to publish RELEASE: {str(e)}")

    with lock:
        if key in pending_requests:
            del pending_requests[key]

    return jsonify({"status": "COMMITTED"}), 200

if __name__ == '__main__':
    logger.info(f"Starting node {NODE_ID}")
    logger.info(f"Redis Master: {REDIS_SENTINEL_MASTER}")
    logger.info(f"Redis Sentinels: {REDIS_SENTINELS}")

    # Inicia thread de consumo
    consumer_thread = threading.Thread(target=consume_events, daemon=True)
    consumer_thread.start()

    app.run(host='0.0.0.0', port=5000)