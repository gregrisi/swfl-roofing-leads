import streamlit as st
import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os
from init_db import init_database

DB_FILE = "lee_county_cadastral.db"
if not os.path.exists(DB_FILE):
    init_database()

st.set_page_config(page_title="ApexRoof | Enterprise Lead Engine", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 8px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CAMPAIGN BUILDER ---
st.sidebar.title("Campaign Builder")
st.sidebar.markdown("Build targeted canvassing & mailer campaigns.")

LEE_COUNTY_DATA = {
    "Cape Coral": ["33904", "33914"],
}
selected_city = st.sidebar.selectbox("1. Target Market", list(LEE_COUNTY_DATA.keys()))
selected_zip = st.sidebar.selectbox("2. Territory (Zip Code)", LEE_COUNTY_DATA[selected_city])

st.sidebar.markdown("---")
lead_profile = st.sidebar.radio("3. Code & Age Profile", ["The Code Trap (Pre-2009)", "The Underlayment Timebomb (20-25 Yrs)"])
roof_material = st.sidebar.selectbox("4. Roof Material Targeting", ["All Roof Types", "Asphalt Shingle", "Concrete Tile", "Metal"])
permit_filter = st.sidebar.selectbox("5. Permit Intelligence", ["🟢 Prime Targets (No Recent Permits)", "Show All Properties"])

generate_leads = st.sidebar.button("Execute Pipeline Sync ⚡", type="primary", use_container_width=True)

# --- ENGINE LOGIC ---
def query_cadastral_db(city, zip_code, profile, material, permit_choice):
    current_year = datetime.now().year
    min_year, max_year = (1950, 2008) if "Code Trap" in profile else (current_year - 25, current_year - 20)

    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM properties WHERE zip_code = ? AND year_built >= ? AND year_built <= ?"
    params = [zip_code, min_year, max_year]
    
    if material != "All Roof Types":
        query += " AND roof_type = ?"
        params.append(material)
        
    if "Prime Targets" in permit_choice:
        query += " AND permit_code = 'PRIME'"
        
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# --- MAIN DASHBOARD ---
st.title("Roofing Intelligence Engine")
st.markdown("Multi-State Pipeline PoC — Currently indexing: **SWFL Sandbox (Lee County)**")

if generate_leads:
    with st.spinner("Executing ETL pull & verifying tax rolls..."):
        time.sleep(0.5) 
        df_leads = query_cadastral_db(selected_city, selected_zip, lead_profile, roof_material, permit_filter)
        
        if not df_leads.empty:
            total_leads = len(df_leads)
            total_value = df_leads['just_value'].sum()
            avg_age = datetime.now().year - df_leads['year_built'].mean()
            
            st.markdown("### Campaign Overview")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Verified Targets", total_leads)
            col2.metric("Total Home Equity (Est)", f"${total_value:,.0f}")
            col3.metric("Avg Roof Age", f"{avg_age:.0f} Years")
            col4.metric("Material Target", roof_material)
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["🗺️ Territory Map", "📋 Rep Walking List", "⚙️ Integrations & Export"])
            
            with tab1:
                st.markdown("#### Optimized Canvassing Clusters")
                st.map(df_leads, zoom=13, use_container_width=True)
                
            with tab2:
                st.markdown("#### Qualified Door List (Material & Permit Verified)")
                # Formatting the dataframe to show off the exact data they want
                display_df = df_leads[['site_address', 'roof_type', 'year_built', 'permit_status', 'last_permit_date']]
                display_df.columns = ["Site Address", "Roof Material", "Year Built", "Permit Status", "Permit History / Dates"]
                st.dataframe(display_df, use_container_width=True)
                
            with tab3:
                st.markdown("#### Automated Workflows (Phase 2 Previews)")
                c1, c2, c3 = st.columns(3)
                c1.button("☁️ Push to Salesforce / GoHighLevel", use_container_width=True)
                c2.button("📬 Trigger Direct Mail Postcards", use_container_width=True)
                csv = df_leads.to_csv(index=False).encode('utf-8')
                c3.download_button("📥 Manual CSV Export", data=csv, file_name=f'campaign_{selected_zip}.csv', use_container_width=True)
                
        else:
            st.warning("No targets found matching these exact material and permit filters.")
else:
    st.info("👈 Configure your campaign parameters in the sidebar and execute the pipeline.")
