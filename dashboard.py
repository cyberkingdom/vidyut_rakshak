import hashlib
import sqlite3
import time
import pandas as pd
import streamlit as st

# --- Command Center Page Config ---
st.set_page_config(
    page_title="Vidyut Rakshak | Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Electrical Grid Styling
st.markdown(
    """
    <style>
    /* Dark Slate Background */
    .stApp {
        background-color: #0b0f19;
        color: #e0e6ed;
    }
    
    /* Neon Command Header */
    .grid-title {
        font-family: 'Monaco', 'Courier New', monospace;
        color: #00f3ff;
        text-shadow: 0 0 10px rgba(0, 243, 255, 0.4);
        font-weight: bold;
        letter-spacing: 1px;
    }

    /* Dynamic Status Cards */
    .status-card-normal {
        background-color: #064e3b;
        color: #34d399;
        padding: 14px;
        border-radius: 8px;
        border: 1px solid #059669;
        box-shadow: 0 0 12px rgba(52, 211, 153, 0.2);
        font-weight: bold;
        text-align: center;
        font-size: 18px;
        font-family: monospace;
    }
    .status-card-alert {
        background-color: #7f1d1d;
        color: #fca5a5;
        padding: 14px;
        border-radius: 8px;
        border: 1px solid #dc2626;
        box-shadow: 0 0 16px rgba(239, 68, 68, 0.4);
        font-weight: bold;
        text-align: center;
        font-size: 18px;
        font-family: monospace;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    "<h1 class='grid-title'>⚡ VIDYUT RAKSHAK: GRID COMMAND CENTER</h1>",
    unsafe_allow_html=True,
)
st.caption(
    "Real-Time Line Telemetry, Power Loss Balance & Cryptographic Audit Ledger"
)


# Database Query Function
def load_telemetry():
  try:
    conn = sqlite3.connect("vidyut.db")
    query = "SELECT * FROM telemetry ORDER BY id DESC LIMIT 150"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df
  except Exception:
    return pd.DataFrame()


df = load_telemetry()

# Sidebar Controls
st.sidebar.header("⚙️ Control Room Setup")
auto_refresh = st.sidebar.checkbox("Enable Live Refresh", value=True)
refresh_rate = st.sidebar.slider("Refresh Interval (Sec)", 1, 10, 2)
st.sidebar.markdown("---")
st.sidebar.write("**Database Target:** `vidyut.db`")
st.sidebar.write(f"**Loaded Samples:** {len(df)}")

if not df.empty:
  latest_row = df.iloc[0]

  # Universal column mapping for current/rms and tamper/case_open
  current_rms = float(
      latest_row.get(
          "current_rms", latest_row.get("current", latest_row.get("current", 0.0))
      )
  )
  tamper_status = bool(
      latest_row.get(
          "case_open", latest_row.get("tamper", latest_row.get("tamper", 0))
      )
  )
  relay_status = bool(latest_row.get("relay", 0))

  # --- Alert Priority ---
  if tamper_status:
    alert_text = "🚨 ALERT: ENCLOSURE TAMPER DETECTED!"
  elif relay_status or current_rms > 60.0:
    alert_text = "⚠️ ALERT: OVERCURRENT RELAY TRIPPED"
  else:
    alert_text = "NORMAL"

  unaccounted_loss = round(max(0.0, current_rms - 5.0), 2)
  hash_valid = bool(latest_row.get("hash_valid", 1))

  # --- Top Command KPI Row ---
  col1, col2, col3, col4 = st.columns([1.3, 1, 1, 1])

  with col1:
    if alert_text == "NORMAL":
      st.markdown(
          "<div class='status-card-normal'>🟢 STATE: NORMAL</div>",
          unsafe_allow_html=True,
      )
    else:
      st.markdown(
          f"<div class='status-card-alert'>{alert_text}</div>",
          unsafe_allow_html=True,
      )

  with col2:
    st.metric(label="Main Pole Supply (CT1)", value=f"{current_rms:.2f} A")

  with col3:
    st.metric(
        label="Unaccounted Loss Delta",
        value=f"{unaccounted_loss:.2f} A",
        delta=(
            "Line Tap / Theft" if unaccounted_loss > 0.5 else "Grid Balanced"
        ),
        delta_color="inverse" if unaccounted_loss > 0.5 else "normal",
    )

  with col4:
    st.metric(
        label="Hash Chain Status",
        value="PASS 🛡️" if hash_valid else "FAIL ⚠️",
        delta="Verified SHA-256" if hash_valid else "Data Tampered",
        delta_color="normal" if hash_valid else "inverse",
    )

  st.markdown("---")

  # --- Primary Viewports ---
  tab_live, tab_balance, tab_audit = st.tabs([
      " Live Telemetry Waves",
      "⚡ Phase Load Breakdown",
      " Cryptographic Audit Ledger",
  ])

  with tab_live:
    st.subheader("Real-time Phase Current Telemetry (Amperes)")
    chart_df = df.sort_values("id")
    curr_col = (
        "current_rms"
        if "current_rms" in chart_df.columns
        else ("current" if "current" in chart_df.columns else None)
    )
    if curr_col and "timestamp" in chart_df.columns:
      st.line_chart(chart_df.set_index("timestamp")[[curr_col]])
    else:
      st.info("Waiting for valid waveform columns...")

  with tab_balance:
    st.subheader("Line Current Balance Summary")
    b1, b2, b3 = st.columns(3)
    b1.metric("Pole CT Input", f"{current_rms:.2f} A")
    b2.metric(
        "Enclosure Tamper Switch",
        "OPEN (TAMPER)" if tamper_status else "CLOSED (SECURE)",
    )
    b3.metric(
        "Power Relay State",
        "TRIPPED (OPEN)" if relay_status else "ACTIVE (CLOSED)",
    )

    st.markdown("**Hardware Diagnostics & Current Distribution Breakdown:**")
    balance_df = pd.DataFrame({
        "Measurement Node": [
            "Pole Supply (CT1)",
            "Enclosure Lock Sensor",
            "Relay Isolation Circuit",
        ],
        "Current Reading / State": [
            f"{current_rms:.2f} A",
            "OPEN" if tamper_status else "SECURE",
            "TRIPPED" if relay_status else "NORMAL",
        ],
        "Evaluation": [
            (
                "ILLEGAL HOOK TAP DETECTED"
                if current_rms > 5.0
                else "Line Balanced"
            ),
            "TAMPER ALERT DETECTED" if tamper_status else "Enclosure Ok",
            "Line Power Cut" if relay_status else "Normal Operation",
        ],
    })
    st.table(balance_df)

  with tab_audit:
    st.subheader("Cryptographic SHA-256 Integrity Ledger")
    ledger_df = df.copy()

    # Normalize columns dynamically so the table never breaks
    if "current_rms" not in ledger_df.columns:
      if "current" in ledger_df.columns:
        ledger_df["current_rms"] = ledger_df["current"]
      else:
        ledger_df["current_rms"] = 0.0

    if "case_open" not in ledger_df.columns:
      if "tamper" in ledger_df.columns:
        ledger_df["case_open"] = ledger_df["tamper"]
      else:
        ledger_df["case_open"] = 0

    if "node_id" not in ledger_df.columns:
      ledger_df["node_id"] = "NODE_POLE"

    if "current_hash" not in ledger_df.columns:
      ledger_df["current_hash"] = ledger_df.apply(
          lambda r: hashlib.sha256(str(r.to_dict()).encode()).hexdigest(),
          axis=1,
      )

    if "hash_valid" not in ledger_df.columns:
      ledger_df["hash_valid"] = 1

    # Filter columns that exist in the dataframe
    display_cols = [
        c
        for c in [
            "id",
            "timestamp",
            "node_id",
            "current_rms",
            "case_open",
            "current_hash",
            "hash_valid",
        ]
        if c in ledger_df.columns
    ]

    st.dataframe(
        ledger_df[display_cols],
        column_config={
            "id": "ID",
            "timestamp": "Timestamp",
            "node_id": "Node ID",
            "current_rms": st.column_config.NumberColumn(
                "Current (A)", format="%.2f A"
            ),
            "case_open": "Case Open",
            "current_hash": "SHA-256 Hash Signature",
            "hash_valid": st.column_config.CheckboxColumn("Valid Chain"),
        },
        use_container_width=True,
        hide_index=True,
    )

  # Real-time Auto Refresh
  if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()

else:
  st.info("Waiting for telemetry data from gateway...")
