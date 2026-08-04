import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | Hybrid Engine", layout="wide")

LEE_COUNTY_DATA = {
    "Cape Coral": ["33904", "33909", "33914", "33990", "33991", "33993"],
    "Fort Myers": ["33901", "33905", "33907", "33908", "33912", "33913", "33916", "33919", "33966"],
    "Lehigh Acres": ["33936", "33971", "33973", "33974", "33976"],
    "Bonita Springs": ["34134", "34135"],
    "Estero": ["33928"]
}

# --- MARKETING & APP LOGIC ---
st.title("🏠 Lee County Roofing: Precision Lead Generator")
st.markdown("**Powered by the FDOR/LEEPA Hybrid Engine.** Indexing state data and verifying against live county records.")

st.sidebar.header("🎯 Targeting Parameters")
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
generate_leads = st.sidebar.button("Fetch & Verify Leads", type="primary", use_container_width=True)

# --- DYNAMIC PERMIT PORTAL LINKS ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Public Permit Verification")
st.sidebar.markdown("Verify recent roof permits before knocking.")
st.sidebar.link_button("Go to Lee County Permit Portal", "https://aca-prod.accela.com/LEECO/Default.aspx", use_container_width=True)
st.sidebar.markdown("---")

# --- HYBRID ENGINE LOGIC ---

# 1. Scraper Function (LEEPA)
def scrape_leepa_details(strap_number):
    """Hits the live LEEPA site to pull the absolute newest owner data."""
    try:
        url = f"https://www.leepa.org/Display/DisplayParcel.aspx?Strap={strap_number}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            owner_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_OwnerNameLabel')
            owner_name = owner_span.text.strip().title() if owner_span else "Public Record"
            
            sale_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_LastSaleDateLabel')
            sale_date = sale_span.text.strip() if sale_span else "Unknown"
            
            return {"owner": owner_name, "last_sale": sale_date}
    except Exception as e:
        return {"owner": "Verification Failed", "last_sale": "Unknown"}
        
    return {"owner": "Public Record", "last_sale": "Unknown"}

# 2. Index Engine (FDOR State Database)
def execute_hybrid_search(zip_code, profile):
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
    
    st.toast("Step 1: Indexing FDOR State Database schema...")
    
    # NEW FL State Database URL
    fdor_base_url = "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0"
    
    try:
        # Schema Check: Find exactly what the state named the Zip Code column this year
        schema_response = requests.get(fdor_base_url, params={"f": "json"})
        if schema_response.status_code != 200:
            st.error("Failed to read state database schema.")
            return pd.DataFrame()
            
        fields = [f.get('name', '').upper() for f in schema_response.json().get('fields', [])]
        
        zip_field = next((f for f in fields if f in ['PHY_ZIPCD', 'PHY_ZIP', 'ZIP', 'SITE_ZIP']), 'PHY_ZIPCD')
        year_field = next((f for f in fields if f in ['ACT_YR_BLT', 'YEAR_BUILT', 'YR_BLT']), 'ACT_YR_BLT')
        strap_field = next((f for f in fields if f in ['PARCELNO', 'PARCEL_ID', 'STRAP']), 'PARCELNO')
        
        st.toast(f"Step 2: Searching FDOR for {zip_code} targets...")
        
        # Build the exact query
        where_clause = f"{zip_field} LIKE '%{zip_code}%' AND {year_field} >= {target_min_year} AND {year_field} <= {target_max_year}"
        
        params = {
            "where": where_clause, 
            "outFields": "*",
            "outSR": "4326", 
            "f": "geojson",  
            "resultRecordCount": 30 # Capped at 30 so the Streamlit demo scraper doesn't timeout
        }
        
        response = requests.get(f"{fdor_base_url}/query", params=params)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                return pd.DataFrame() 
                
            st.toast(f"Step 3: FDOR Index complete. Live-verifying {len(features)} records against LEEPA...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for index, feature in enumerate(features):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                if not props or not geom:
                    continue
                
                raw_parcel = props.get(strap_field, '')
                
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    if isinstance(coords[0], list):
                        lon, lat = coords[0][0][0], coords[0][0][1] 
                    else:
                        lon, lat = coords[0], coords[1]
                        
                    status_text.text(f"Scraping LEEPA record {index + 1} of {len(features)}...")
                    live_data = scrape_leepa_details(raw_parcel)
                    
                    # Only append if we successfully get an owner from LEEPA
                    leads.append({
                        "STRAP": raw_parcel,
                        "Live Homeowner": live_data['owner'],
                        "Site Address": props.get('PHY_ADDR1', 'Unknown'),
                        "Zip": zip_code,
                        "Year Built": int(props.get(year_field, 0)),
                        "Est. Value": f"${int(props.get('JV', 0)):,}",
                        "Last Sale (LEEPA)": live_data['last_sale'],
                        "latitude": float(lat),
                        "longitude": float(lon)
                    })
                    
                    time.sleep(0.5) 
                    
                progress_bar.progress((index + 1) / len(features))
                
            status_text.text("Verification Complete.")
            
        else:
            st.error(f"Failed to connect to FDOR server. Error {response.status_code}")
            
    except Exception as e:
        st.error(f"Network error: {e}")
        
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    with st.spinner("Executing Hybrid Search Architecture..."):
        df_leads = execute_hybrid_search(selected_zip, lead_profile)
        
        if not df_leads.empty:
            st.success(f"Successfully indexed and verified {len(df_leads)} high-probability targets!")
            st.map(df_leads, zoom=13, use_container_width=True)
            
            st.markdown(f"### 🎯 Lead Profile: {lead_profile}")
            display_df = df_leads.drop(columns=["latitude", "longitude"])
            st.dataframe(display_df, use_container_width=True)
            
            # CSV Export
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lead Sheet (CSV)",
                data=csv,
                file_name=f'hybrid_roofing_leads_{selected_zip}.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.warning("No properties found matching this exact profile. Adjust filters or zip code.")
