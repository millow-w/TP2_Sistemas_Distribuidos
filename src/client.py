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
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    client_id = os.getenv('CLIENT_ID')
    node_url = os.getenv('NODE_URL')

    logger.info(f"Client {client_id} starting. Connected to node: {node_url}")

    # total_access = 2

    total_access = random.randint(10, 50)

    logger.info(f"Client {client_id} will perform {total_access} accesses to resource R")
    
    for access_num in range(1, total_access + 1):
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        logger.info(f"Client {client_id} requesting access #{access_num} to R. Timestamp: {timestamp}")

        try:
            response = requests.post(
                f"{node_url}/request_access",
                json={
                    "client_id": client_id,
                    "timestamp": timestamp,
                    "access_num": access_num
                },
                timeout=5
            )

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "COMMITTED":
                    logger.info(f"Access #{access_num} COMMITTED for client {client_id}")
                    sleep_time = random.uniform(1, 5)
                    logger.info(f"Client {client_id} sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Unexpected response: {response_data}")
            else:
                logger.error(f"Request failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")

    logger.info(f"Client {client_id} completed all accesses with {total_access} accessess in total.")
    sys.exit(0)

if __name__  == '__main__':
    main()
            