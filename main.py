from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import sqlite3

app = FastAPI()
DB = "parc.db"

# Connexion et création de la table SQLite si elle n'existe pas encore
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hostname TEXT UNIQUE,
                ip TEXT,
                cpu REAL,
                ram REAL,
                disk REAL,
                updated_at TEXT
            )
        """)

init_db()

# Structure du JSON attendu quand l'agent envoie ses métriques
class MachineData(BaseModel):
    hostname: str
    ip: str
    cpu_usage: float
    ram_usage: float
    disk_usage: float

# Endpoint POST : Reçoit les données de l'agent et met à jour (ou crée) la machine en base
@app.post("/api/collect")
def collect_data(data: MachineData):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        
        # On vérifie si la machine est déjà enregistrée
        cursor.execute("SELECT id FROM machines WHERE hostname = ?", (data.hostname,))
        row = cursor.fetchone()
        
        if row:
            # Si elle existe déjà, on actualise ses stats et son heure de dernier contact
            cursor.execute("""
                UPDATE machines 
                SET ip = ?, cpu = ?, ram = ?, disk = ?, updated_at = ?
                WHERE hostname = ?
            """, (data.ip, data.cpu_usage, data.ram_usage, data.disk_usage, now, data.hostname))
        else:
            # Sinon, c'est une nouvelle machine, on l'ajoute
            cursor.execute("""
                INSERT INTO machines (hostname, ip, cpu, ram, disk, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (data.hostname, data.ip, data.cpu_usage, data.ram_usage, data.disk_usage, now))
            
        conn.commit()
    
    return {"status": "success"}

# Endpoint GET : Renvoie la liste de toutes les machines pour alimenter le tableau de bord
@app.get("/api/machines")
def get_machines():
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.cursor().execute("SELECT * FROM machines").fetchall()
    return [dict(r) for r in rows]

# Page d'accueil : Sert le mini dashboard HTML/JS qui s'actualise tout seul
@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Dashboard IT</title>
        <style>
            body { font-family: Arial, sans-serif; background: #f4f6f9; padding: 20px; }
            .card { max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px; border-bottom: 1px solid #ddd; text-align: left; }
            th { background: #343a40; color: white; }
            .badge { padding: 4px 8px; border-radius: 4px; color: white; font-weight: bold; }
            .ok { background: #28a745; }
            .danger { background: #dc3545; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Supervision du Parc</h2>
            <table>
                <thead>
                    <tr>
                        <th>Hostname</th>
                        <th>IP</th>
                        <th>CPU</th>
                        <th>RAM</th>
                        <th>Disque</th>
                        <th>Dernière MAJ</th>
                    </tr>
                </thead>
                <tbody id="data-table">
                    <tr><td colspan="6">Chargement...</td></tr>
                </tbody>
            </table>
        </div>

        <script>
            // Récupère les données de l'API et met à jour le tableau HTML en direct
            async function fetchData() {
                try {
                    let res = await fetch('/api/machines');
                    let rows = await res.json();
                    let tbody = document.getElementById('data-table');
                    tbody.innerHTML = '';
                    
                    if(rows.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Aucune machine enregistrée.</td></tr>';
                        return;
                    }

                    rows.forEach(m => {
                        // Petites conditions visuelles : rouge si dépassement de seuil, vert sinon
                        let cpuClass = m.cpu > 80 ? 'danger' : 'ok';
                        let ramClass = m.ram > 80 ? 'danger' : 'ok';
                        let diskClass = m.disk > 85 ? 'danger' : 'ok';

                        tbody.innerHTML += `<tr>
                            <td><b>${m.hostname}</b></td>
                            <td>${m.ip}</td>
                            <td><span class="badge ${cpuClass}">${m.cpu}%</span></td>
                            <td><span class="badge ${ramClass}">${m.ram}%</span></td>
                            <td><span class="badge ${diskClass}">${m.disk}%</span></td>
                            <td>${m.updated_at}</td>
                        </tr>`;
                    });
                } catch(err) {
                    console.error("Erreur lors de la récup des données :", err);
                }
            }

            // Premier appel direct au chargement, puis refresh toutes les 5 secondes
            fetchData();
            setInterval(fetchData, 5000);
        </script>
    </body>
    </html>
    """
