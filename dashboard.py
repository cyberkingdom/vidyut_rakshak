
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Vidyut Rakshak Dashboard", layout="wide")
st.title("⚡ Vidyut Rakshak: Live System Monitor")

conn = sqlite3.connect("vidyut.db")

df = pd.read_sql_query("SELECT * FROM telemetry ORDER BY id DESC LIMIT 50", conn)

if not df.empty:
    latest_alert = df.iloc[0]['alert']
    col1, col2, col3 = st.columns(3)
    col1.metric("System Status", latest_alert)
    col2.metric("Total Samples Logged", len(df))
    col3.metric("Hash Chain Integrity", "PASS" if df.iloc[0]['hash_valid'] == 1 else "FAIL")

    st.subheader("Real-time Current Readings (Amps)")
    chart_data = df.pivot(index='timestamp', columns='node_id', values='current_rms')
    st.line_chart(chart_data)

    st.subheader("Cryptographic Audit Ledger (SHA-256 Hash Chain)")
    st.dataframe(df[['timestamp', 'node_id', 'current_rms', 'current_hash', 'hash_valid', 'alert']])
else:
    st.info("Waiting for telemetry data from gateway...")

