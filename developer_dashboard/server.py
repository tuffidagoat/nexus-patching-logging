import os
import sqlite3
import zlib
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DATA_FOLDER_NAME = "2d-extras_Data" 
GAME_FILE_PATH = os.path.join(BASE_DIR, GAME_DATA_FOLDER_NAME, "StreamingAssets", "game_config.json")

app = FastAPI(title="NEXUS Live-Ops Pipeline Engine")

def init_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            player_id TEXT,
            event_type TEXT,
            severity TEXT,
            message TEXT
        )
    """)
    conn.commit()
    return conn

db_conn = init_db()
CURRENT_PATCH = {"patch_id": 0, "payload": ""}

class LogModel(BaseModel):
    player_id: str
    event_type: str
    severity: str
    message: str

@app.post("/api/telemetry-logs")
async def receive_logs(log: LogModel):
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry_logs (player_id, event_type, severity, message) VALUES (?, ?, ?, ?)",
        (log.player_id, log.event_type, log.severity, log.message)
    )
    db_conn.commit()
    print(f"📡 [NETWORK ACTION] Log written to SQLite RAM matrix: {log.event_type}")
    return {"status": "success", "message": "Telemetry indexed"}

@app.get("/api/get-logs")
async def get_logs():
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, timestamp, player_id, event_type, severity, message FROM telemetry_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    
    logs = []
    for r in rows:
        # Extract individual tuple indices from database results cleanly
        logs.append({
            "id": r[0],
            "timestamp": r[1],
            "player_id": r[2],
            "event_type": r[3],
            "severity": r[4],
            "message": r[5]
        })
    return JSONResponse(content=logs)

@app.post("/api/deploy-patch")
async def deploy_patch(request: Request):
    global CURRENT_PATCH
    data = await request.json()
    new_config = data.get("new_config")
    
    try:
        os.makedirs(os.path.dirname(GAME_FILE_PATH), exist_ok=True)
        with open(GAME_FILE_PATH, "w") as f:
            f.write(new_config)
    except Exception as e:
        print(f"[WARNING] Local game file output bypassed: {e}")

    patch_bytes = zlib.compress(new_config.encode('utf-8'))
    hex_payload = patch_bytes.hex()
    
    CURRENT_PATCH["patch_id"] += 1
    CURRENT_PATCH["payload"] = hex_payload
    
    cursor = db_conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry_logs (player_id, event_type, severity, message) VALUES (?, ?, ?, ?)",
        ("NEXUS_SERVER", "PATCH_DEPLOYED", "SUCCESS", f"Version {CURRENT_PATCH['patch_id']} compiled into {len(patch_bytes)} bytes.")
    )
    db_conn.commit()

    return {"status": "deployed", "patch_id": CURRENT_PATCH["patch_id"], "size_bytes": len(patch_bytes)}

@app.get("/api/latest-patch")
async def get_latest_patch():
    return JSONResponse(content=CURRENT_PATCH)

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html_path = os.path.join(BASE_DIR, "dashboard.html")
    if not os.path.exists(html_path):
        return HTMLResponse(content="Dashboard HTML missing", status_code=404)
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
