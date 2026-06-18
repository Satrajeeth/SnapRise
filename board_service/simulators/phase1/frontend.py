import streamlit as st
import requests
import pandas as pd

# Simulator backend configuration
ST_BACKEND_URL = "http://localhost:8001"

st.set_page_config(page_title="Phase 1: DB & Encryption Simulator", layout="wide")

st.title("🛡️ Phase 1: Database & Encryption Simulator")
st.markdown("""
This simulator validates the core data structures and the application-level encryption layer.
It uses an isolated in-memory SQLite database to ensure no side effects on production data.
""")

# Sidebar for adding data
with st.sidebar:
    st.header("🛠️ Simulation Controls")
    st.subheader("Create New Board")
    with st.form("create_board_form"):
        name = st.text_input("Board Name", placeholder="e.g., Secret Project")
        description = st.text_area("Board Description", placeholder="Enter sensitive information here...")
        encrypt = st.checkbox("Encrypt Description", value=True, help="If checked, description will be stored as ciphertext in the DB.")
        submit = st.form_submit_button("💾 Save to DB")

    if submit:
        if name and description:
            payload = {
                "name": name,
                "description": description,
                "encrypt": encrypt
            }
            try:
                response = requests.post(f"{ST_BACKEND_URL}/simulate/boards", json=payload)
                if response.status_code == 200:
                    st.success(f"Board '{name}' created and saved successfully!")
                else:
                    st.error(f"Error from backend: {response.text}")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")
        else:
            st.warning("Please fill in both name and description.")

# Main area for displaying data
st.header("📋 Database State (Live View)")

if st.button("🔄 Refresh Table"):
    st.rerun()

try:
    response = requests.get(f"{ST_BACKEND_URL}/simulate/boards")
    if response.status_code == 200:
        data = response.json()
        if data:
            df = pd.DataFrame(data)
            # Reorder columns for optimal readability
            cols = ["name", "encryption_status", "raw_description", "decrypted_description", "id"]
            df = df[cols]
            
            # Display summary table
            st.dataframe(df, use_container_width=True)
            
            st.divider()
            st.subheader("🔍 Deep Dive: Row Comparison")
            
            # Detailed row-by-row view
            for board in data:
                with st.expander(f"Board ID: {board['id']} | Name: {board['name']}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info("**Stored in Database (Raw)**")
                        st.code(board['raw_description'], language="text")
                        st.caption(f"Status: {board['encryption_status'].upper()}")
                    with c2:
                        st.success("**Decrypted Output (Frontend)**")
                        st.write(board['decrypted_description'])
        else:
            st.info("No data in the database yet. Use the sidebar to create a board.")
    else:
        st.error(f"Failed to fetch data: {response.status_code}")
except Exception as e:
    st.error(f"Backend unreachable. Is the FastAPI server running on {ST_BACKEND_URL}?")
    st.info("Run `python run_simulator.py` to start both services.")
