import Pyro4
import threading
import json

@Pyro4.expose
class LocationService:
    def __init__(self):
        self.users = {}  # username -> user info
        self.lock = threading.Lock()

    def register_user(self, username, latitude, longitude, status, radius):
        with self.lock:
            if username in self.users:
                return False
            self.users[username] = {
                'latitude': latitude,
                'longitude': longitude,
                'status': status,  # 'online' ou 'offline'
                'radius': radius,
                'contacts': set()
            }
            return True

    def update_user(self, username, latitude=None, longitude=None, status=None, radius=None):
        with self.lock:
            if username not in self.users:
                return False
            if latitude is not None:
                self.users[username]['latitude'] = latitude
            if longitude is not None:
                self.users[username]['longitude'] = longitude
            if status is not None:
                self.users[username]['status'] = status
            if radius is not None:
                self.users[username]['radius'] = radius
            return True

    def get_nearby_contacts(self, username):
        from math import radians, cos, sin, sqrt, atan2

        def distance(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c

        with self.lock:
            if username not in self.users:
                return []
            u = self.users[username]
            lat1, lon1, rad = u['latitude'], u['longitude'], u['radius']
            nearby = []
            for other, data in self.users.items():
                if other == username:
                    continue
                dist = distance(lat1, lon1, data['latitude'], data['longitude'])
                if dist <= rad:
                    nearby.append({
                        'username': other,
                        'status': data['status'],
                        'distance': round(dist, 2)
                    })
            return nearby

    def get_user_info(self, username):
        with self.lock:
            return self.users.get(username, None)

if __name__ == '__main__':
    daemon = Pyro4.Daemon()
    ns = Pyro4.locateNS()
    uri = daemon.register(LocationService())
    ns.register("location.service", uri)
    print("[Location Service] Servidor de localização iniciado e aguardando requisições...")
    daemon.requestLoop()
