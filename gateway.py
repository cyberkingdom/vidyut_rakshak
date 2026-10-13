import hashlib
import json
import sqlite3
import time
from datetime import datetime
import serial

PORT = "COM8"
BAUD = 115200
DB_NAME = "vidyut.db"

# Initialize SQLite DB matching your cryptographic ledger schema
conn = sqlite3.connect(DB_NAME, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
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
""")
conn.commit()


def get_last_hash():
  """Retrieves the previous block's hash to maintain the SHA-256 chain."""
  cursor.execute("SELECT current_hash FROM telemetry ORDER BY id DESC LIMIT 1")
  row = cursor.fetchone()
  return row[0] if row and row[0] else "0" * 64


def main():
  print(f"Connecting to ESP32 on {PORT} at {BAUD} baud...")
  try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # Allow connection to settle
  except Exception as e:
    print(f"Error opening serial port {PORT}: {e}")
    print("Make sure Arduino IDE Serial Monitor is CLOSED!")
    return

  print(
      "Gateway active. Reading USB serial telemetry & building cryptographic"
      " ledger..."
  )

  while True:
    try:
      if ser.in_waiting > 0:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line.startswith("{") and line.endswith("}"):
          data = json.loads(line)

          current_rms = float(data.get("current", 0.0))
          tamper = 1 if data.get("tamper", False) else 0
          relay = 1 if data.get("relay", False) else 0
          timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          node_id = "NODE_POLE"

          # Get previous hash for chain integrity
          prev_hash = get_last_hash()

          # Compute SHA-256 cryptographic block hash
          raw_string = f"{timestamp}{node_id}{current_rms:.2f}{prev_hash}"
          current_hash = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
          hash_valid = 1

          # Determine system alert status
          alert = "NORMAL"
          if tamper == 1 and relay == 1:
            alert = "CASE_TAMPER_AND_OVERCURRENT"
          elif tamper == 1:
            alert = "CASE_TAMPER_DETECTED"
          elif relay == 1 or current_rms > 5.0:
            alert = "OVERCURRENT_RELAY_TRIPPED"

          # Insert record into database
          cursor.execute(
              """
                INSERT INTO telemetry (node_id, timestamp, current_rms, case_open, prev_hash, current_hash, hash_valid, alert)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
              (
                  node_id,
                  timestamp,
                  current_rms,
                  tamper,
                  prev_hash,
                  current_hash,
                  hash_valid,
                  alert,
              ),
          )
          conn.commit()

          print(
              f"[{timestamp}] {node_id} | Current: {current_rms:.2f}A | Tamper:"
              f" {tamper} | Alert: {alert}"
          )
    except Exception as e:
      print(f"Runtime error: {e}")
      time.sleep(0.5)


if __name__ == "__main__":
  main()
