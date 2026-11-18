import time
import socket
import psutil
import requests

# URL du serveur central à contacter
URL = "http://127.0.0.1:8000/api/collect"

# Petite astuce pour choper l'adresse IP locale propre de la machine
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# Rassemble toutes les métriques système de la machine en cours
def get_metrics():
    return {
        "hostname": socket.gethostname(),
        "ip": get_ip(),
        "cpu_usage": psutil.cpu_percent(interval=1),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }

# Boucle infinie qui envoie l'état de la machine au serveur à intervalles réguliers
if __name__ == "__main__":
    print("Agent de collecte démarré...")
    while True:
        try:
            payload = get_metrics()
            res = requests.post(URL, json=payload)
            print(f"[{time.strftime('%H:%M:%S')}] Envoi réussi -> {res.json()}")
        except Exception as e:
            print(f"Oups, impossible de joindre le serveur : {e}")
            
        # Pause de 10 secondes avant la prochaine collecte
        time.sleep(10)
        
