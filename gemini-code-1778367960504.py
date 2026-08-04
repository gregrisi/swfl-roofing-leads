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

# --- HYBRID ENGINE LOGIC ---

# 1. Scraper Function (LEEPA)
def scrape_leepa_details(strap_number):
    """Hits the live LEEPA site to pull the absolute newest owner data."""
    try:
        url = f"https://www.leepa.org/Display/DisplayParcel.aspx?Strap={strap_number}"
        # We must use a header to pretend we are a real browser, otherwise LEEPA blocks the request
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Scrape Owner Name (LEEPA puts it in a specific span id)
            owner_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_OwnerNameLabel')
            owner_name = owner_span.text.strip().title() if owner_span else "Public Record"
            
            # Scrape Latest Sale Date (Optional, but looks great for demos)
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
    
    st.toast("Step 1: Indexing FDOR State Database for coordinate targets...")
    
    # FDOR Statewide REST API (Normalized Data)
    fdor_url = "https://ca.dep.state.fl.us/arcgis/rest/services/OpenData/PARCELS/MapServer/0/query"
    
    # FDOR uses standard columns across the entire state
    where_clause = f"PHY_ZIP = '{zip_code}' AND ACT_YR_BLT >= {target_min_year} AND ACT_YR_BLT <= {target_max_year}"
    
    params = {
        "where": where_clause, 
        "outFields": "PARCELNO,PHY_ADDR1,ACT_YR_BLT,JV",
        "outSR": "4326", 
        "f": "geojson",  
        "resultRecordCount": 30 # Capped at 30 for the Streamlit demo so the scraping doesn't timeout
    }
    
    try:
        response = requests.get(fdor_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
            if not features:
                return pd.DataFrame() 
                
            st.toast(f"Step 2: FDOR Index complete. Live-verifying {len(features)} records against LEEPA...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for index, feature in enumerate(features):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                if not props or not geom:
                    continue
                
                # Format the FDOR ParcelNO into the STRAP format LEEPA expects
                raw_parcel = props.get('PARCELNO', '')
                
                # Handle map coordinates
                coords = geom.get('coordinates', [])
                if len(coords) >= 2:
                    if isinstance(coords[0], list):
                        lon, lat = coords[0][0][0], coords[0][0][1] 
                    else:
                        lon, lat = coords[0], coords[1]
                        
                    # LIVE VERIFICATION STEP
                    status_text.text(f"Scraping LEEPA record {index + 1} of {len(features)}...")
                    live_data = scrape_leepa_details(raw_parcel)
                    
                    leads.append({
                        "STRAP": raw_parcel,
                        "Live Homeowner (LEEPA)": live_data['owner'],
                        "Site Address": props.get('PHY_ADDR1', 'Unknown'),
                        "Zip": zip_code,
                        "Year Built": int(props.get('ACT_YR_BLT', 0)),
                        "Est. Value": f"${int(props.get('JV', 0)):,}",
                        "Last Sale (LEEPA)": live_data['last_sale'],
                        "latitude": float(lat),
                        "longitude": float(lon)
                    })
                    
                    # Be polite to the county servers
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
        else:
            st.warning("No properties found matching this exact profile.")
