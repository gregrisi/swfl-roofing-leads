import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LEEPA LIVE", layout="wide")

# Focus exclusively on Lee County for Phase 1
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
    
    # Determine age brackets based on the selected marketing profile
    if "Insurance Panic" in profile:
        min_age, max_age = 14, 16
    elif "Code Trap" in profile:
        min_age, max_age = 18, 100 # Built before 2009 (assuming current year 2026)
    elif "Underlayment" in profile:
        min_age, max_age = 20, 25
    else:
        min_age, max_age = 15, 100

    target_max_year = current_year - min_age
    target_min_year = current_year - max_age

    leads = []
    
    st.toast(f"Querying live LEEPA database for Zip: {zip_code}...")
    
    # ArcGIS REST API Endpoint provided by Lee County
    arcgis_url = "https://services2.arcgis.com/LvWGAAhHwbCJ2GMP/arcgis/rest/services/Lee_County_Parcels/FeatureServer/0/query"
    
    # We construct a spatial/SQL query. 
    # Note: ArcGIS field names vary. We use 1=1 and filter in Python to ensure stability against schema changes, 
    # pulling a sample size of 500 records to process.
    params = {
        "where": "1=1", 
        "outFields": "*",
        "outSR": "4326", # Forces the map coordinates into standard Latitude/Longitude
        "f": "geojson",  # Returns clean JSON with geometry
        "resultRecordCount": 500 
    }
    
    try:
        response = requests.get(arcgis_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            progress_bar = st.progress(0)
            
            for index, feature in enumerate(features):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                if not props or not geom:
                    continue
                    
                # Standardizing the variable names (LEEPA might use slightly different tags like SITE_ZIP or ZIP)
                record_zip = str(props.get('SITE_ZIP') or props.get('ZIP') or props.get('SITUS_ZIP', ''))
                year_built = props.get('ACT_YR_BLT') or props.get('YEAR_BUILT') or props.get('YR_BLT')
                
                # Check if it matches our Zip Code and our Target Age Bracket
                if zip_code in record_zip and isinstance(year_built, (int, float)):
                    if target_min_year <= year_built <= target_max_year:
                        
                        # Handle point coordinates from GeoJSON
                        coords = geom.get('coordinates', [])
                        if len(coords) >= 2:
                            # GeoJSON is [Longitude, Latitude] for points, or nested arrays for polygons.
                            # We extract the first available coordinate pair for the map pin.
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
                                "Year Built": int(year_built),
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
            st.warning("No properties found matching this exact profile in the sample set. The county API may require specific field mapping for this Zip.")
