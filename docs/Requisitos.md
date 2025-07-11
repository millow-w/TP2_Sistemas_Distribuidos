# Requisitos do Sistema

## Requisitos de Cliente

- Cada cliente conhece apenas um elemento do cluster denominado **Cluster Sync** (Cluster de Sincronização de Acesso ao Recurso R).
- Cada cliente possui um ID único e, a cada pedido de acesso ao recurso R, envia um timestamp para garantir pedidos únicos.
- O **Cluster Sync** deve ser composto por no mínimo 5 processos, encapsulados em containers, VMs ou máquinas reais.
- O cliente recebe apenas a mensagem **COMMITTED** de um elemento do Cluster Sync após o acesso a R ser concluído.
- Após receber uma mensagem **COMMITTED**, o cliente entra em estado de espera (sleep de 1 a 5 segundos, calculado aleatoriamente) e volta a pedir acesso de escrita ao recurso R.
- Cada cliente deve pedir entre 10 e 50 acessos de escrita ao recurso R, forçando a concorrência e a validação do protocolo de exclusão mútua.

---

## Requisitos do Node do Cluster Sync

- Qualquer elemento do Cluster Sync, ao receber uma solicitação de um cliente, envia uma mensagem de publicação (Pub) a um tópico denominado **R topic** ou a uma fila denominada **R Queue**.
  - Nesta mensagem, insere-se apenas o ID do elemento do Cluster Sync, o pedido do cliente e a primitiva **ACQUIRE**.
- Cada elemento do Cluster Sync é também consumidor, recebendo todas as mensagens enviadas pelo broker **na mesma ordem FIFO**.
  - Cabe a cada elemento do cluster avaliar sua fila **F (privada)** de mensagens do broker para saber se pode ou não entrar na seção crítica.
- Após entrar na seção crítica por um tempo (sleep de 0.2 a 1 segundo), o elemento do Cluster Sync envia uma mensagem de publicação ao mesmo tópico ou fila do broker, contendo seu ID, o pedido do cliente e a primitiva **RELEASE**.
- Para entrar na seção crítica (acessar R para escrita), cada elemento do Cluster Sync deve verificar a ordem das mensagens **ACQUIRE** e **RELEASE**, assim como o pedido do cliente.

---