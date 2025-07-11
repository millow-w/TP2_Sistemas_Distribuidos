# Qualquer elemento do Cluster Sync ao receber uma solicitação de um cliente envia uma mensagem de Pub a um tópico denominado R topic ou a uma fila denominada R Queue. Nesta mensagem de Pub é inserido apenas o ID do elemento do Cluster Sync, o pedido do cliente e a primitiva ACQUIRE. 

# Cada elemento do Cluster Sync é também um consumidor, portanto recebe todas as mensagens enviadas pelo broker e o mais interessante: NA MESMA ORDEM FIFO, por exemplo. Cabe a cada elemento do cluster ficar avaliando sua fila F (PRIVADA)  de mensagens do broker para saber se pode ou não entrar na seção crítica. 

# Após entrar na seção crítica por um tempo (Sleep de 0.2 a 1 segundo), o elemento do Cluster Sync envia uma mensagem de Pub ao mesmo tópico ou fila do broker, mas neste caso contendo seu ID, o pedido do cliente e a primitiva RELEASE. 

# Note que para entrar na seção crítica (acessar R para escrita), cada elemento do Cluster Sync deve olhar a sua ordem de ACQUIRE e também a ordem de RELEASES, assim como o pedido do cliente.