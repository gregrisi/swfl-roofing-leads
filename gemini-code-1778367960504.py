import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | Diagnostic Mode", layout="wide")

LEE_COUNTY_DATA = {
    "Cape Coral": ["33904", "33909", "33914", "33990", "33991", "33993"],
    "Fort Myers": ["33901", "33905", "33907", "33908", "33912", "33913", "33916", "33919", "33966"],
    "Lehigh Acres": ["33936", "33971", "33973", "33974", "33976"]
}

st.title("🏠 Lee County Roofing: Precision Lead Generator")
st.markdown("**Diagnostic Mode Active:** X-Raying State Database Schema.")

st.sidebar.header("🎯 Targeting Parameters")
selected_city = st.sidebar.selectbox("1. Select City", list(LEE_COUNTY_DATA.keys()))
selected_zip = st.sidebar.selectbox("2. Select Zip Code", LEE_COUNTY_DATA[selected_city])

lead_profile = st.sidebar.radio(
    "Select Target Strategy:",
    ["The Code Trap (Pre-2009 - 25% Rule)"]
)

generate_leads = st.sidebar.button("Fetch & Verify Leads", type="primary", use_container_width=True)

def execute_diagnostic_search(zip_code):
    st.toast("Connecting to FL State Database...")
    fdor_base_url = "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0"
    
    try:
        # 1. READ THE SCHEMA
        schema_response = requests.get(fdor_base_url, params={"f": "json"})
        if schema_response.status_code != 200:
            st.error("Could not reach state server to read schema.")
            return
            
        fields = [f.get('name', '').upper() for f in schema_response.json().get('fields', [])]
        
        # DISPLAY THE BLUEPRINT TO THE USER
        st.info(f"**DIAGNOSTIC 1 - State Database Columns:** {', '.join(fields[:30])}...")
        
        # Safely find the best columns based on what actually exists
        zip_field = next((f for f in fields if f in ['PHY_ZIPCD', 'PHY_ZIP', 'ZIP', 'OWN_ZIPCD', 'OWN_ZIP']), 'UNKNOWN_ZIP')
        year_field = next((f for f in fields if f in ['ACT_YR_BLT', 'YEAR_BUILT', 'YR_BLT']), 'UNKNOWN_YEAR')
        
        # 2. RUN A SAFER QUERY (Using '=' instead of 'LIKE' in case zip is a number)
        where_clause = f"{zip_field} = '{zip_code}' AND {year_field} <= 2008 AND {year_field} >= 1950"
        
        st.info(f"**DIAGNOSTIC 2 - Executing Query:** {where_clause}")
        
        params = {
            "where": where_clause, 
            "outFields": "*",
            "outSR": "4326", 
            "f": "geojson",  
            "resultRecordCount": 10 
        }
        
        response = requests.get(f"{fdor_base_url}/query", params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Catch silent ArcGIS errors
            if 'error' in data:
                st.error(f"**SERVER REJECTED QUERY:** {data['error'].get('message')} - {data['error'].get('details')}")
                return
                
            features = data.get('features', [])
            st.success(f"**DIAGNOSTIC 3 - Result:** The server returned {len(features)} matching houses.")
            
        else:
            st.error(f"Server responded with error code: {response.status_code}")
            
    except Exception as e:
        st.error(f"Network error: {e}")

if generate_leads:
    with st.spinner("Running Diagnostic X-Ray..."):
        execute_diagnostic_search(selected_zip)
