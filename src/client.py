# REQUISITOS DE CLIENTE

# Cada cliente conhece apenas um elemento do cluster denominado CLUSTER DE SINCRONIZAÇÃO DE ACESSO AO RECURSO R (abreviação Cluster Sync).

# Cada cliente possui um ID único e a cada pedido de acesso ao recurso R, o mesmo envia o timestamp para garantir pedidos únicos. 

# O Cluster Sync deve ser composto por, no mínimo, 5 processos encapsulados em containers ou VMs ou máquinas reais. 

# O cliente recebe apenas a mensagem COMMITTED de um elemento do Cluster Sync após o acesso a R ser concluído. 

# Após receber uma mensagem COMMITTED, o cliente entra em estado de espera (Sleep de 1 a 5 segundos calculado aleatoriamente) e volta a pedir acesso de escrita ao recurso R. 

# Cada cliente deve pedir entre 10 e 50 acessos de escrita ao recurso R, forçando, desta forma, a concorrência e, consequentemente, a validação do protocolo de exclusão mútua. 