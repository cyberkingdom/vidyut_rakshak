
import sqlite3
import pandas as pd
import streamlit as st
import time

# --- Command Center Page Config ---
st.set_page_config(
    page_title="Vidyut Rakshak | Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Electrical Grid Styling
st.markdown("""
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
""", unsafe_allow_html=True)

st.markdown("<h1 class='grid-title'>⚡ VIDYUT RAKSHAK: GRID COMMAND CENTER</h1>", unsafe_allow_html=True)
st.caption("Real-Time Line Telemetry, Power Loss Balance & Cryptographic Audit Ledger")

# Database Query Function
def load_telemetry():
    conn = sqlite3.connect("vidyut.db")
    query = "SELECT * FROM telemetry ORDER BY id DESC LIMIT 150"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

df = load_telemetry()

# Sidebar Controls
st.sidebar.header("⚙️ Control Room Setup")
auto_refresh = st.sidebar.checkbox("Enable Live Refresh", value=True)
refresh_rate = st.sidebar.slider("Refresh Interval (Sec)", 1, 10, 2)
st.sidebar.markdown("---")
st.sidebar.write(f"**Database Target:** `vidyut.db`")
st.sidebar.write(f"**Loaded Samples:** {len(df)}")

if not df.empty:
    latest_row = df.iloc[0]
    latest_alert = latest_row['alert']
    hash_valid = latest_row['hash_valid'] == 1

    # Node-wise Current Aggregation
    latest_by_node = df.groupby('node_id').first()
    pole_curr = float(latest_by_node.loc['NODE_POLE', 'current_rms']) if 'NODE_POLE' in latest_by_node.index else 0.0
    branch_a = float(latest_by_node.loc['NODE_BRANCH_A', 'current_rms']) if 'NODE_BRANCH_A' in latest_by_node.index else 0.0
    branch_b = float(latest_by_node.loc['NODE_BRANCH_B', 'current_rms']) if 'NODE_BRANCH_B' in latest_by_node.index else 0.0

    total_metered = branch_a + branch_b
    unaccounted_loss = round(max(0.0, pole_curr - total_metered), 2)

    # --- Top Command KPI Row ---
    col1, col2, col3, col4 = st.columns([1.3, 1, 1, 1])

    with col1:
        if latest_alert == "NORMAL":
            st.markdown("<div class='status-card-normal'>🟢 STATE: NORMAL</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='status-card-alert'> {latest_alert}</div>", unsafe_allow_html=True)

    with col2:
        st.metric(
            label="Main Pole Supply (CT1)",
            value=f"{pole_curr:.2f} A"
        )

    with col3:
        st.metric(
            label="Unaccounted Loss Delta",
            value=f"{unaccounted_loss:.2f} A",
            delta="Line Tap / Theft" if unaccounted_loss > 0.5 else "Grid Balanced",
            delta_color="inverse" if unaccounted_loss > 0.5 else "normal"
        )

    with col4:
        st.metric(
            label="Hash Chain Status",
            value="PASS 🛡️" if hash_valid else "FAIL ⚠️",
            delta="Verified SHA-256" if hash_valid else "Data Tampered",
            delta_color="normal" if hash_valid else "inverse"
        )

    st.markdown("---")

    # --- Primary Viewports ---
    tab_live, tab_balance, tab_audit = st.tabs([
        " Live Telemetry Waves", 
        "⚡ Phase Load Breakdown", 
        " Cryptographic Audit Ledger"
    ])

    with tab_live:
        st.subheader("Real-time Phase Current Telemetry (Amperes)")
        chart_data = df.pivot(index='timestamp', columns='node_id', values='current_rms')
        st.line_chart(chart_data)

    with tab_balance:
        st.subheader("Line Current Balance Summary")
        b1, b2, b3 = st.columns(3)
        b1.metric("Pole CT Input", f"{pole_curr:.2f} A")
        b2.metric("Branch A Meter", f"{branch_a:.2f} A")
        b3.metric("Branch B Meter", f"{branch_b:.2f} A")

        st.markdown("**Current Distribution Breakdown:**")
        balance_df = pd.DataFrame({
            "Measurement Node": ["Pole Supply (CT1)", "Sum of Load Meters (CT2 + CT3)", "Unmetered Line Loss"],
            "Current Reading": [f"{pole_curr:.2f} A", f"{total_metered:.2f} A", f"{unaccounted_loss:.2f} A"],
            "Evaluation": [
                "Total Grid Input",
                "Legitimate Demand",
                "ILLEGAL HOOK TAP DETECTED" if unaccounted_loss > 0.5 else "Line Balanced"
            ]
        })
        st.table(balance_df)

    with tab_audit:
        st.subheader("Cryptographic SHA-256 Integrity Ledger")
        st.dataframe(
            df[['id', 'timestamp', 'node_id', 'current_rms', 'current_hash', 'hash_valid', 'alert']],
            column_config={
                "id": "ID",
                "timestamp": "Timestamp",
                "node_id": "Node ID",
                "current_rms": st.column_config.NumberColumn("Current (A)", format="%.2f A"),
                "current_hash": "SHA-256 Hash Signature",
                "hash_valid": st.column_config.CheckboxColumn("Valid Chain"),
                "alert": "System Status"
            },
            use_container_width=True,
            hide_index=True
        )

    # Real-time Auto Refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()

else:
    st.info("Waiting for telemetry data from gateway...")


