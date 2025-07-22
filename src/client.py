# REQUISITOS DE CLIENTE

# Cada cliente conhece apenas um elemento do cluster denominado CLUSTER DE SINCRONIZAÇÃO DE ACESSO AO RECURSO R (abreviação Cluster Sync).

# Cada cliente possui um ID único e a cada pedido de acesso ao recurso R, o mesmo envia o timestamp para garantir pedidos únicos. 

# O Cluster Sync deve ser composto por, no mínimo, 5 processos encapsulados em containers ou VMs ou máquinas reais. 

# O cliente recebe apenas a mensagem COMMITTED de um elemento do Cluster Sync após o acesso a R ser concluído. 

# Após receber uma mensagem COMMITTED, o cliente entra em estado de espera (Sleep de 1 a 5 segundos calculado aleatoriamente) e volta a pedir acesso de escrita ao recurso R. 

# Cada cliente deve pedir entre 10 e 50 acessos de escrita ao recurso R, forçando, desta forma, a concorrência e, consequentemente, a validação do protocolo de exclusão mútua. 

import os
import time
import random
import requests
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    client_id = os.getenv('CLIENT_ID')
    node_url = os.getenv('NODE_URL')
    
    logger.info(f"Client {client_id} starting. Connected to node: {node_url}")
    
    while True:
        try:
            # Incrementa o contador no nó
            response = requests.post(f"{node_url}/increment")
            if response.status_code == 200:
                counter = response.json().get('counter')
                logger.info(f"{client_id} incremented counter to {counter}")
            else:
                logger.error(f"Failed to increment: {response.text}")
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
        
        # Intervalo aleatório entre 1-3 segundos
        time.sleep(random.uniform(1, 3))

if __name__ == '__main__':
    main()