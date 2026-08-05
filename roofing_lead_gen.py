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
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }

    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-left: 6px solid #77BA43; 
        border-radius: 5px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.08); 
    }
    
    h1, h2, h3, h4 {
        color: #464646 !important;
        font-weight: 800 !important;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; font-size: 16px; color: #464646; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CAMPAIGN BUILDER ---
if os.path.exists("cwc_logo.png"):
    st.sidebar.image("cwc_logo.png", use_container_width=True)
else:
    st.sidebar.markdown("## CWC Roofing")
    
st.sidebar.caption("Proprietary Lead Routing Engine")
st.sidebar.markdown("---")

st.sidebar.title("⚙️ Campaign Builder")

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
        
    return df

# --- MAIN DASHBOARD ---
st.title("Residential Roofing Intelligence Engine")
st.markdown("**CWC Multi-State Pipeline PoC** — Currently indexing: *SWFL Sandbox (Lee County)*")

if execute_query:
    if not selected_materials:
        st.error("Please select at least one roof material to query.")
    else:
        df_leads = build_and_run_query(selected_zip, house_year_range, roof_age_range, selected_materials)
        
        if not df_leads.empty:
            st.markdown("### Campaign Overview")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matching Properties", len(df_leads))
            c2.metric("Pipeline Equity", f"${df_leads['just_value'].sum():,.0f}")
            c3.metric("Avg Roof Age", f"{df_leads['current_roof_age'].mean():.1f} Yrs")
            c4.metric("Materials targeted", str(len(selected_materials)))
            
            st.markdown("---")
            
            # --- TABBED EXECUTIVE VIEW ---
            tab1, tab2, tab3 = st.tabs(["🗺️ Territory Map", "📋 Lead Roster", "⚙️ Action Workflows"])
            
            with tab1:
                st.markdown("#### Optimized Canvassing Clusters")
                st.map(df_leads, zoom=13, use_container_width=True)
                
            with tab2:
                st.markdown("#### Qualified Target List")
                display_df = df_leads[['site_address', 'roof_type', 'year_built', 'current_roof_age', 'permit_status', 'last_permit_date']]
                display_df.columns = ["Address", "Material", "House Built", "Roof Age (Yrs)", "Status", "Permit Detail"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
            with tab3:
                st.markdown("#### Campaign Execution & Export")
                st.info("In the Phase 2 production rollout, these workflows will connect directly to your marketing tech stack.")
                
                col_a, col_b, col_c = st.columns(3)
                col_a.button("☁️ Push to CRM (Salesforce / GHL)", use_container_width=True)
                col_b.button("📬 Trigger Direct Mail Postcards", use_container_width=True)
                
                csv = df_leads.to_csv(index=False).encode('utf-8')
                col_c.download_button(
                    label="📥 Download CSV Target List", 
                    data=csv, 
                    file_name=f"cwc_campaign_{selected_zip}.csv", 
                    use_container_width=True
                )
                
        else:
            st.warning("No properties matched your exact query parameters. Try widening the scope.")
else:
    st.info("👈 Use the Campaign Builder to define your exact canvassing targets.")
