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

st.set_page_config(page_title="CWC Roofing | Intelligence Engine", layout="wide", initial_sidebar_state="expanded")

# --- CWC BRANDED CSS & FONT INJECTION ---
st.markdown("""
    <style>
    /* Import Montserrat Font to match CWC Branding */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');

    /* Force font across all Streamlit elements */
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* Metric Card Styling */
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-left: 6px solid #77BA43; /* CWC Green Accent */
        border-radius: 5px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.08); 
    }
    
    /* Query Box Styling - Matching their dark header */
    .query-box { 
        background-color: #464646; /* CWC Charcoal */
        color: #77BA43; /* CWC Green */
        padding: 15px; 
        border-radius: 5px; 
        font-family: 'Courier New', monospace; 
        border: 1px solid #333333;
    }
    
    /* Main Header Styling */
    h1, h2, h3 {
        color: #464646 !important;
        font-weight: 800 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CAMPAIGN BUILDER ---
st.sidebar.markdown("## 🏢 CWC Roofing")
st.sidebar.caption("Proprietary Lead Routing Engine")
st.sidebar.markdown("---")

st.sidebar.title("⚙️ Advanced Query Builder")

LEE_COUNTY_DATA = {"Cape Coral": ["33904", "33914"]}
selected_city = st.sidebar.selectbox("1. Target Market", list(LEE_COUNTY_DATA.keys()))
selected_zip = st.sidebar.selectbox("2. Territory (Zip Code)", LEE_COUNTY_DATA[selected_city])

st.sidebar.markdown("---")
st.sidebar.subheader("Structural Filters")
house_year_range = st.sidebar.slider("House Year Built Range", min_value=1950, max_value=2026, value=(1950, 2026))

st.sidebar.markdown("---")
st.sidebar.subheader("Roof Age & Condition")
roof_age_range = st.sidebar.slider("Effective Roof Age (Years)", min_value=0, max_value=50, value=(14, 25))

selected_materials = st.sidebar.multiselect(
    "Target Roof Materials", 
    ["Asphalt Shingle", "Concrete Tile", "Metal", "Flat/Built-Up"],
    default=["Asphalt Shingle", "Concrete Tile", "Metal"]
)

execute_query = st.sidebar.button("Run Custom Query ⚡", type="primary", use_container_width=True)

# --- ENGINE LOGIC ---
def build_and_run_query(zip_code, house_years, roof_ages, materials):
    current_year = 2026
    
    max_roof_year = current_year - roof_ages[0]
    min_roof_year = current_year - roof_ages[1]
    
    conn = sqlite3.connect(DB_FILE)
    
    base_query = f"""
        SELECT site_address, roof_type, year_built, last_roof_year, just_value, permit_status, last_permit_date, lat, lon 
        FROM properties 
        WHERE zip_code = '{zip_code}' 
        AND year_built >= {house_years[0]} AND year_built <= {house_years[1]}
        AND last_roof_year >= {min_roof_year} AND last_roof_year <= {max_roof_year}
    """
    
    if materials:
        mat_string = "', '".join(materials)
        base_query += f" AND roof_type IN ('{mat_string}')"
        
    df = pd.read_sql_query(base_query, conn)
    conn.close()
    
    if not df.empty:
        df['current_roof_age'] = current_year - df['last_roof_year']
        
    return df, base_query

# --- MAIN DASHBOARD ---
st.title("Residential Roofing Intelligence Engine")
st.markdown("**CWC Multi-State Pipeline PoC** — Currently indexing: *SWFL Sandbox (Lee County)*")

if execute_query:
    if not selected_materials:
        st.error("Please select at least one roof material to query.")
    else:
        df_leads, raw_sql = build_and_run_query(selected_zip, house_year_range, roof_age_range, selected_materials)
        
        with st.expander("🔍 View Raw Database Query", expanded=False):
            st.markdown(f"<div class='query-box'>{raw_sql}</div>", unsafe_allow_html=True)
            st.caption("Notice how we query 'last_roof_year' separately from 'year_built' to ensure no replacement permutations are missed.")
        
        if not df_leads.empty:
            st.markdown("### Query Results")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matching Properties", len(df_leads))
            c2.metric("Pipeline Equity", f"${df_leads['just_value'].sum():,.0f}")
            c3.metric("Avg Roof Age", f"{df_leads['current_roof_age'].mean():.1f} Yrs")
            c4.metric("Materials", ", ".join(selected_materials))
            
            st.markdown("#### Qualified Lead Roster")
            
            display_df = df_leads[['site_address', 'roof_type', 'year_built', 'current_roof_age', 'permit_status', 'last_permit_date']]
            display_df.columns = ["Address", "Material", "House Built", "Roof Age (Yrs)", "Status", "Permit Detail"]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
                
        else:
            st.warning("No properties matched your exact query parameters.")
else:
    st.info("👈 Use the Query Builder to define your exact canvassing targets.")
