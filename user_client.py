import Pyro4
import Pyro4.naming
import time
import threading
from broker_manager import BrokerManager
from message_utils import get_rabbitmq_connection, close_rabbitmq_connection
import json

@Pyro4.expose
class MessageReceiver:
    def __init__(self, username):
        self.username = username
        self.buffer = []  # Armazena mensagens síncronas recebidas

    def receive_message(self, sender, message):
        entry = f"[SYNC MSG] {sender} -> {self.username}: {message}"
        self.buffer.append(entry)

class UserClient:
    def __init__(self, username, latitude, longitude, status, radius):
        self.username = username
        self.latitude = latitude
        self.longitude = longitude
        self.status = status  # 'online' ou 'offline'
        self.radius = radius

        self.location_service = Pyro4.Proxy("PYRONAME:location.service")
        self.broker = BrokerManager()

        registered = self.location_service.register_user(username, latitude, longitude, status, radius)
        if not registered:
            print("[ERRO] Nome de usuário já registrado.")
            exit(1)

        self.broker.create_user(username)

        # Iniciar o receptor RMI para mensagens síncronas
        self.receptor = MessageReceiver(username)
        self.daemon = Pyro4.Daemon()
        uri = self.daemon.register(self.receptor)
        ns = Pyro4.locateNS()
        ns.register(f"client.{username}", uri)

        threading.Thread(target=self.daemon.requestLoop, daemon=True).start()

        print(f"[OK] Usuário '{username}' registrado com sucesso e pronto para comunicação síncrona.")

    def update_status(self, status):
        self.status = status
        self.location_service.update_user(self.username, status=status)
        print(f"[INFO] Status atualizado para: {status}")

    def update_location(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.location_service.update_user(self.username, latitude=latitude, longitude=longitude)
        print("[INFO] Localização atualizada.")

    def update_radius(self, radius):
        self.radius = radius
        self.location_service.update_user(self.username, radius=radius)
        print("[INFO] Raio de alcance atualizado.")

    def get_contacts(self):
        contacts = self.location_service.get_nearby_contacts(self.username)
        print("[CONTATOS PROXIMOS]")
        for c in contacts:
            print(f"  - {c['username']} | Status: {c['status']} | Distância: {c['distance']}km")
        return contacts

    def send_message(self, recipient, message):
        contact_info = self.location_service.get_user_info(recipient)
        if not contact_info:
            print("[ERRO] Usuário não encontrado.")
            return

        contacts = self.location_service.get_nearby_contacts(self.username)
        online_close = any(c['username'] == recipient and c['status'] == 'online' for c in contacts)

        if online_close:
            print(f"[SYNC] Enviando mensagem síncrona para {recipient}: {message}")
            try:
                proxy = Pyro4.Proxy(f"PYRONAME:client.{recipient}")
                proxy.receive_message(self.username, message)
            except Exception as e:
                print(f"[ERRO] Falha na comunicação síncrona com {recipient}: {e}")
        else:
            print(f"[ASYNC] Usuário offline/distante. Enviando via MOM.")
            payload = json.dumps({
                'from': self.username,
                'message': message,
                'timestamp': time.time()
            })
            self.broker.add_queue(f"user_{recipient}")
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.basic_publish(
                exchange='',
                routing_key=f"user_{recipient}",
                body=payload,
                properties=None
            )
            close_rabbitmq_connection(connection)

    def check_async_messages(self):
        print("[INFO] Verificando mensagens assíncronas...")
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.queue_declare(queue=f"user_{self.username}", durable=True)
        while True:
            method, props, body = channel.basic_get(queue=f"user_{self.username}", auto_ack=True)
            if method:
                msg = json.loads(body.decode())
                print(f"[MSG] {msg['from']}: {msg['message']}")
            else:
                break
        close_rabbitmq_connection(connection)

    def check_sync_messages(self):
        if not self.receptor.buffer:
            print("[INFO] Nenhuma mensagem síncrona nova.")
        else:
            print("[INFO] Mensagens síncronas recebidas:")
            for entry in self.receptor.buffer:
                print(f"  {entry}")
            self.receptor.buffer.clear()

if __name__ == '__main__':
    nome = input("Nome: ")
    lat = float(input("Latitude: "))
    lon = float(input("Longitude: "))
    raio = float(input("Raio de comunicação (km): "))

    cli = UserClient(nome, lat, lon, 'online', raio)

    while True:
        print("\n1. Ver contatos próximos\n2. Enviar mensagem\n3. Verificar mensagens assíncronas\n4. Verificar mensagens síncronas\n5. Mudar status\n6. Atualizar localização\n7. Atualizar raio\n0. Sair")
        op = input("Opção: ").strip()
        if op == '1':
            cli.get_contacts()
        elif op == '2':
            dest = input("Para quem: ")
            msg = input("Mensagem: ")
            cli.send_message(dest, msg)
        elif op == '3':
            cli.check_async_messages()
        elif op == '4':
            cli.check_sync_messages()
        elif op == '5':
            novo = input("Novo status (online/offline): ")
            cli.update_status(novo)
        elif op == '6':
            lat = float(input("Nova latitude: "))
            lon = float(input("Nova longitude: "))
            cli.update_location(lat, lon)
        elif op == '7':
            r = float(input("Novo raio (km): "))
            cli.update_radius(r)
        elif op == '0':
            cli.update_status('offline')
            print("Encerrando...")
            break
        else:
            print("Opção inválida")
