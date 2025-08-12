O código implementa a lógica de um cliente de comunicação baseado em localização que utiliza duas tecnologias complementares:

RMI (Remote Method Invocation) com Pyro4 para troca de mensagens síncronas entre usuários próximos e online.

RabbitMQ como Message-Oriented Middleware (MOM) para envio e recebimento de mensagens assíncronas quando o destinatário está offline ou fora do raio de alcance.

Ele se conecta a um serviço de localização remoto, que mantém registro das posições, status e raios de comunicação dos usuários, e gerencia o envio de mensagens diretas ou via filas de mensagens.

Instruções de uso
1. Iniciar o RabbitMQ
Certifique-se de que o RabbitMQ está rodando na máquina local (porta padrão 5672):

bash
sudo systemctl start rabbitmq-server
2. Iniciar o Servidor de Nomes do Pyro4
Abra um terminal e execute:

bash
python -m Pyro4.naming
Isso iniciará o serviço de nomes na porta padrão 9090.

3. Iniciar o Serviço de Localização
(O serviço location.service deve estar implementado e registrado no Pyro4 antes de iniciar clientes).

4. Iniciar o Cliente de Usuário
Em outro terminal, execute:

bash
python user_client.py
Informe:

Nome do usuário

Latitude e Longitude atuais

Raio de comunicação (em km)

Se o nome não estiver em uso, o usuário será registrado no serviço de localização e terá sua fila dedicada criada no RabbitMQ.
