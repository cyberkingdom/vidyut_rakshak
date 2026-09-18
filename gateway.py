
import json
import sqlite3
import hashlib
import paho.mqtt.client as mqtt

DB_NAME = "vidyut.db"

# Initialize SQLite DB
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS telemetry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT,
        timestamp TEXT,
        current_rms REAL,
        case_open INTEGER,
        prev_hash TEXT,
        current_hash TEXT,
        hash_valid INTEGER,
        alert TEXT
    )
''')
conn.commit()

# Store latest current readings for correlation logic
node_readings = {"NODE_POLE": 0.0, "NODE_BRANCH_A": 0.0, "NODE_BRANCH_B": 0.0}

def verify_hash(data):
    raw_string = f"{data['timestamp']}{data['node_id']}{data['current_rms']:.2f}{data['prev_hash']}"
    recalculated = hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
    return recalculated == data['current_hash']

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        is_valid = verify_hash(payload)

        # Correlation Rule: Delta = Pole Current - (Branch A + Branch B)
        node_readings[payload['node_id']] = payload['current_rms']
        delta = node_readings['NODE_POLE'] - (node_readings['NODE_BRANCH_A'] + node_readings['NODE_BRANCH_B'])

        alert = "NORMAL"
        if delta > 0.5:
            alert = "ILLEGAL_TAP_DETECTED"
        elif payload.get('case_open', 0) == 1:
            alert = "CASE_TAMPER_DETECTED"

        cursor.execute('''
            INSERT INTO telemetry (node_id, timestamp, current_rms, case_open, prev_hash, current_hash, hash_valid, alert)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payload['node_id'],
            payload['timestamp'],
            payload['current_rms'],
            payload.get('case_open', 0),
            payload['prev_hash'],
            payload['current_hash'],
            1 if is_valid else 0,
            alert
        ))
        conn.commit()

        print(f"[{payload['timestamp']}] {payload['node_id']} | Current: {payload['current_rms']}A | Hash Valid: {is_valid} | Alert: {alert}")
    except Exception as e:
        print(f"Error parsing message: {e}")

client = mqtt.Client()
client.on_message = on_message
client.connect("127.0.0.1", 1883, 60)
client.subscribe("vidyut/telemetry")

print("Gateway active. Listening for local MQTT telemetry...")
client.loop_forever()
EOF
