import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LEEPA LIVE", layout="wide")

LEE_COUNTY_DATA = {
    "Cape Coral": ["33904", "33909", "33914", "33990", "33991", "33993"],
    "Fort Myers": ["33901", "33905", "33907", "33908", "33912", "33913", "33916", "33919", "33966"],
    "Lehigh Acres": ["33936", "33971", "33973", "33974", "33976"],
    "Bonita Springs": ["34134", "34135"],
    "Estero": ["33928"]
}

# --- MARKETING & APP LOGIC ---
st.title("🏠 Lee County Roofing: Precision Lead Generator")
st.markdown("**Powered by Live LEEPA ArcGIS Public Records.** Target properties based on Florida insurance cliffs and building code triggers.")

st.sidebar.header("🎯 Targeting Parameters")

st.sidebar.subheader("📍 Geographic Targeting")
selected_city = st.sidebar.selectbox("1. Select City", list(LEE_COUNTY_DATA.keys()))
selected_zip = st.sidebar.selectbox("2. Select Zip Code", LEE_COUNTY_DATA[selected_city])

st.sidebar.subheader("🔥 Lead Qualification Profiles")
lead_profile = st.sidebar.radio(
    "Select Target Strategy:",
    [
        "The Insurance Panic (14-16 Years Old)",
        "The Code Trap (Pre-2009 - 25% Rule)",
        "The Underlayment Timebomb (20-25 Years Old)"
    ]
)

st.sidebar.markdown("---")
generate_leads = st.sidebar.button("Fetch LEEPA Records & Map", type="primary", use_container_width=True)

# --- DYNAMIC PERMIT PORTAL LINKS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Public Permit Verification")
st.sidebar.markdown("Verify recent roof permits before knocking.")
st.sidebar.link_button("Go to Lee County Permit Portal", "https://aca-prod.accela.com/LEECO/Default.aspx", use_container_width=True)
st.sidebar.markdown("---")

# --- LIVE LEEPA ARCGIS ENGINE ---
def fetch_leepa_arcgis_records(zip_code, profile):
    current_year = datetime.now().year
    
    if "Insurance Panic" in profile:
        min_age, max_age = 14, 16
    elif "Code Trap" in profile:
        min_age, max_age = 18, 100 
    elif "Underlayment" in profile:
        min_age, max_age = 20, 25
    else:
        min_age, max_age = 15, 100

    target_max_year = current_year - min_age
    target_min_year = current_year - max_age

    leads = []
    
    # 1. DYNAMIC SCHEMA MAPPING
    st.toast("Step 1: Analyzing Lee County Database Schema...")
    base_url = "https://services2.arcgis.com/LvWGAAhHwbCJ2GMP/arcgis/rest/services/Lee_County_Parcels/FeatureServer/0"
    
    try:
        schema_response = requests.get(base_url, params={"f": "json"})
        if schema_response.status_code != 200:
            st.error("Failed to read county database schema.")
            return pd.DataFrame()
            
        fields = [f.get('name', '').upper() for f in schema_response.json().get('fields', [])]
        
        # Hunt for the exact column names Lee County is currently using
        zip_field = next((f for f in fields if f in ['SITE_ZIP', 'ZIP', 'SITUS_ZIP', 'ZIP_CODE']), 'SITE_ZIP')
        year_field = next((f for f in fields if f in ['ACT_YR_BLT', 'YEAR_BUILT', 'YR_BLT']), 'ACT_YR_BLT')
        
        st.toast(f"Step 2: Querying live data for {zip_code} targets...")
        
        # 2. SERVER-SIDE FILTERING 
        # We force the ArcGIS server to do the filtering, not our Python app, so we don't get 500 random records.
        where_clause = f"{zip_field} LIKE '%{zip_code}%' AND {year_field} >= {target_min_year} AND {year_field} <= {target_max_year}"
        
        params = {
            "where": where_clause, 
            "outFields": "*",
            "outSR": "4326", 
            "f": "geojson",  
            "resultRecordCount": 1000 # Increased payload size for dense zip codes
        }
        
        response = requests.get(f"{base_url}/query", params=params)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                return pd.DataFrame() # Returns empty if literally zero houses match
                
            progress_bar = st.progress(0)
            
            for index, feature in enumerate(features):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                if not props or not geom:
                    continue
                    
                # Handle point coordinates from GeoJSON
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    if isinstance(coords[0], list):
                        lon, lat = coords[0][0][0], coords[0][0][1] 
                    else:
                        lon, lat = coords[0], coords[1]
                        
                    leads.append({
                        "STRAP": props.get('STRAP', 'Unknown'),
                        "Homeowner": str(props.get('OWNER') or props.get('OWNER_NAME', 'Public Record')).title(),
                        "Site Address": props.get('SITE_ADDR') or props.get('SITUS_ADDR', 'Unknown'),
                        "City": selected_city,
                        "Zip": zip_code,
                        "Year Built": int(props.get(year_field, 0)),
                        "Est. Value": f"${int(props.get('JUST_VALUE') or props.get('ASSESSED_VAL', 0)):,}",
                        "latitude": float(lat),
                        "longitude": float(lon)
                    })
                    
                progress_bar.progress((index + 1) / len(features))
                
        else:
            st.error(f"Failed to connect to LEEPA server. Error {response.status_code}")
            
    except Exception as e:
        st.error(f"Network error: {e}")
        
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    with st.spinner("Mining LEEPA Database and generating target map..."):
        df_leads = fetch_leepa_arcgis_records(selected_zip, lead_profile)
        
        if not df_leads.empty:
            st.success(f"Successfully identified {len(df_leads)} high-probability targets in {selected_zip}!")
            
            # Interactive Map
            st.map(df_leads, zoom=13, use_container_width=True)
            
            # Data Table
            st.markdown(f"### 🎯 Lead Profile: {lead_profile}")
            display_df = df_leads.drop(columns=["latitude", "longitude"])
            st.dataframe(display_df, use_container_width=True)
            
            # CSV Export
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lead Sheet (CSV)",
                data=csv,
                file_name=f'leepa_roofing_leads_{selected_zip}.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.warning("No properties found matching this exact profile. Adjust your filters and try again.")
