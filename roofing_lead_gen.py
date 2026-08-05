import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import os
from init_db import init_database

# Ensure DB exists
DB_FILE = "lee_county_cadastral.db"
if not os.path.exists(DB_FILE):
    init_database()

st.set_page_config(page_title="ApexRoof | Query Engine", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 8px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1); }
    .query-box { background-color: #1e1e1e; color: #00ff00; padding: 10px; border-radius: 5px; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

# --- ADVANCED QUERY BUILDER (SIDEBAR) ---
st.sidebar.title("⚙️ Advanced Query Builder")
st.sidebar.markdown("Define your exact territory and lead parameters.")

LEE_COUNTY_DATA = {"Cape Coral": ["33904", "33914"]}
selected_city = st.sidebar.selectbox("1. Target Market", list(LEE_COUNTY_DATA.keys()))
selected_zip = st.sidebar.selectbox("2. Territory (Zip Code)", LEE_COUNTY_DATA[selected_city])

st.sidebar.markdown("---")
st.sidebar.subheader("Property Filters")
# Dynamic Sliders instead of rigid buttons
year_range = st.sidebar.slider("Year Built Range", min_value=1980, max_value=2024, value=(1995, 2008))
min_value = st.sidebar.number_input("Minimum Home Value ($)", min_value=100000, value=300000, step=25000)

st.sidebar.markdown("---")
st.sidebar.subheader("Intelligence Filters")
# Multi-select for materials (allows selecting Asphalt AND Metal)
selected_materials = st.sidebar.multiselect(
    "Target Roof Materials", 
    ["Asphalt Shingle", "Concrete Tile", "Metal", "Flat/Built-Up"],
    default=["Asphalt Shingle"]
)

# Permit Exclusivity
permit_filter = st.sidebar.radio(
    "Permit Verification", 
    ["Must have NO recent roof permits", "Show all (including recently replaced)"]
)

execute_query = st.sidebar.button("Run Custom Query ⚡", type="primary", use_container_width=True)

# --- ENGINE LOGIC & SQL GENERATION ---
def build_and_run_query(zip_code, years, min_val, materials, permits):
    conn = sqlite3.connect(DB_FILE)
    
    # Constructing the dynamic SQL Query
    base_query = f"SELECT site_address, roof_type, year_built, just_value, permit_status, last_permit_date, lat, lon FROM properties WHERE zip_code = '{zip_code}' AND year_built >= {years[0]} AND year_built <= {years[1]} AND just_value >= {min_val}"
    
    if materials:
        mat_string = "', '".join(materials)
        base_query += f" AND roof_type IN ('{mat_string}')"
        
    if "NO recent roof" in permits:
        base_query += " AND permit_code = 'PRIME'"
        
    df = pd.read_sql_query(base_query, conn)
    conn.close()
    return df, base_query

# --- MAIN DASHBOARD ---
st.title("Roofing Intelligence Engine")

if execute_query:
    if not selected_materials:
        st.error("Please select at least one roof material to query.")
    else:
        df_leads, raw_sql = build_and_run_query(selected_zip, year_range, min_value, selected_materials, permit_filter)
        
        # --- QUERY TRANSPARENCY BOX ---
        with st.expander("🔍 View Raw Database Query (Transparency Inspector)", expanded=False):
            st.markdown(f"<div class='query-box'>{raw_sql}</div>", unsafe_allow_html=True)
            st.caption("This is the exact logic executed against the county tax and permit records.")
        
        if not df_leads.empty:
            st.markdown("### Query Results")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matching Properties", len(df_leads))
            c2.metric("Pipeline Equity", f"${df_leads['just_value'].sum():,.0f}")
            c3.metric("Oldest Target", df_leads['year_built'].min())
            c4.metric("Materials", ", ".join(selected_materials))
            
            tab1, tab2 = st.tabs(["📋 Interactive Data Table", "🗺️ Territory Map"])
            
            with tab1:
                st.markdown("**Pro Tip:** Click any column header (like *Year Built* or *Permit History*) to sort the data.")
                
                # Format Dataframe for display
                display_df = df_leads[['site_address', 'roof_type', 'year_built', 'just_value', 'permit_status', 'last_permit_date']]
                display_df.columns = ["Address", "Material", "Year Built", "Est. Value", "Permit Status", "Permit History / Date"]
                
                # Render highly interactive table
                st.dataframe(
                    display_df, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "Est. Value": st.column_config.NumberColumn("Est. Value", format="$%d")
                    }
                )
                
            with tab2:
                st.map(df_leads, zoom=13, use_container_width=True)
                
        else:
            st.warning("No properties matched your exact query parameters. Try widening the Year Built range or adding more Roof Materials.")
else:
    st.info("👈 Use the Advanced Query Builder to define your exact canvassing targets.")
