
import json
import time
import hashlib
import datetime
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("127.0.0.1", 1883, 60)

nodes = [
    {"id": "NODE_POLE", "base_curr": 5.0, "prev_hash": "0"*64},
    {"id": "NODE_BRANCH_A", "base_curr": 2.5, "prev_hash": "0"*64},
    {"id": "NODE_BRANCH_B", "base_curr": 2.5, "prev_hash": "0"*64}
]

print("Sending simulated node telemetry... Press Ctrl+C to stop.")
try:
    while True:
        for node in nodes:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            curr = node["base_curr"]
            raw = f"{ts}{node['id']}{curr:.2f}{node['prev_hash']}"
            curr_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
            
            payload = {
                "node_id": node["id"],
                "timestamp": ts,
                "current_rms": curr,
                "case_open": 0,
                "prev_hash": node["prev_hash"],
                "current_hash": curr_hash
            }
            
            client.publish("vidyut/telemetry", json.dumps(payload))
            node["prev_hash"] = curr_hash
            time.sleep(1)
        time.sleep(2)
except KeyboardInterrupt:
    print("\nSimulation stopped.")

