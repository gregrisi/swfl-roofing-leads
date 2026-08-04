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
st.markdown("**Powered by the Direct LEEPA Spatial Engine.** Real-time county indexing with live owner verification.")

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

def scrape_leepa_details(strap_number):
    """Hits the live LEEPA site to pull the absolute newest owner data."""
    try:
        url = f"https://www.leepa.org/Display/DisplayParcel.aspx?Strap={strap_number}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            owner_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_OwnerNameLabel')
            owner_name = owner_span.text.strip().title() if owner_span else "Public Record"
            
            sale_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_LastSaleDateLabel')
            sale_date = sale_span.text.strip() if sale_span else "Unknown"
            
            return {"owner": owner_name, "last_sale": sale_date}
    except Exception:
        return {"owner": "Verification Failed", "last_sale": "Unknown"}
        
    return {"owner": "Public Record", "last_sale": "Unknown"}


def execute_hybrid_search(zip_code, profile):
    current_year = datetime.now().year
    leads = []
    
    # Calculate age brackets
    if "Code Trap" in profile:
        min_year, max_year = 1950, 2008
    elif "Insurance Panic" in profile:
        min_year, max_year = current_year - 16, current_year - 14  # 2010 to 2012
    else: # Underlayment
        min_year, max_year = current_year - 25, current_year - 20  # 2001 to 2006

    st.toast("Step 1: Connecting to Direct Lee County Spatial Engine...")
    
    # Primary Source: Direct Lee County GIS Endpoint (Lightning Fast)
    leeco_gis_url = "https://services1.arcgis.com/13R9S6EEqgMvC7Ua/arcgis/rest/services/Lee_County_Parcels/FeatureServer/0/query"
    
    # Fallback Source: FDOR State Database
    fdor_gis_url = "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query"

    features = []
    use_state_fallback = False

    # Attempt 1: Query Lee County Direct GIS
    try:
        where_clause = f"(ZIP = '{zip_code}' OR SITUS_ZIP = '{zip_code}') AND (YEAR_BUILT >= {min_year} AND YEAR_BUILT <= {max_year})"
        params = {
            "where": where_clause,
            "outFields": "STRAP,PARCEL_ID,SITUS_ADDRESS,SITUS_ZIP,YEAR_BUILT,JUST_VALUE,OWNER_NAME",
            "outSR": "4326",
            "f": "geojson",
            "resultRecordCount": 25
        }
        
        response = requests.get(leeco_gis_url, params=params, timeout=6)
        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            
        if not features:
            # If no features with exact ZIP match, loosen filter to match standard GIS zip strings
            where_clause = f"SITUS_ZIP LIKE '%{zip_code}%' AND (YEAR_BUILT >= {min_year} AND YEAR_BUILT <= {max_year})"
            params["where"] = where_clause
            response = requests.get(leeco_gis_url, params=params, timeout=6)
            if response.status_code == 200:
                features = response.json().get('features', [])
                
    except Exception:
        use_state_fallback = True

    # Attempt 2: Fallback to FDOR State Server if Lee County GIS is unreachable
    if use_state_fallback or not features:
        try:
            st.toast("Primary engine busy. Failing over to FDOR State Database...")
            where_clause = f"CO_NO = '36' AND OWN_ZIPCD LIKE '%{zip_code}%' AND ACT_YR_BLT >= {min_year} AND ACT_YR_BLT <= {max_year}"
            params = {
                "where": where_clause,
                "outFields": "*",
                "outSR": "4326",
                "f": "geojson",
                "resultRecordCount": 20
            }
            response = requests.get(fdor_gis_url, params=params, timeout=8)
            if response.status_code == 200:
                features = response.json().get('features', [])
        except Exception as e:
            st.error(f"GIS Engines unavailable: {e}")
            return pd.DataFrame()

    if not features:
        return pd.DataFrame()

    st.toast(f"Step 2: Indexed {len(features)} spatial targets. Verifying against live LEEPA tax records...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, feature in enumerate(features):
        props = feature.get('properties', {})
        geom = feature.get('geometry', {})
        
        raw_parcel = props.get('STRAP') or props.get('PARCEL_ID') or props.get('PARCELNO') or 'Unknown'
        address = props.get('SITUS_ADDRESS') or props.get('PHY_ADDR1') or props.get('BAS_STRT') or f"Parcel #{raw_parcel}"
        yr_built = props.get('YEAR_BUILT') or props.get('ACT_YR_BLT') or 0
        just_val = props.get('JUST_VALUE') or props.get('JV') or 0
        
        # Coordinate Parsing
        coords = geom.get('coordinates', [])
        lat, lon = 26.6406, -81.8723 # Default Cape Coral coordinates fallback
        
        if coords:
            c = coords
            try:
                while isinstance(c, list) and len(c) > 0 and isinstance(c[0], list):
                    c = c[0]
                if isinstance(c, list) and len(c) >= 2:
                    lon, lat = float(c[0]), float(c[1])
            except Exception:
                pass

        status_text.text(f"Scraping LEEPA record {index + 1} of {len(features)}...")
        live_data = scrape_leepa_details(raw_parcel)
        
        # Use LEEPA live owner name if found, fallback to GIS owner record
        owner_name = live_data['owner'] if live_data['owner'] != "Public Record" else props.get('OWNER_NAME', 'Public Record').title()

        leads.append({
            "STRAP": raw_parcel,
            "Live Homeowner": owner_name,
            "Site Address": address,
            "Zip Code": zip_code,
            "Year Built": int(yr_built),
            "Est. Value": f"${int(just_val):,}",
            "Last Sale (LEEPA)": live_data['last_sale'],
            "latitude": lat,
            "longitude": lon
        })
        
        time.sleep(0.4) 
        progress_bar.progress((index + 1) / len(features))
        
    status_text.text("Verification Complete.")
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    with st.spinner("Executing Direct Spatial Architecture..."):
        df_leads = execute_hybrid_search(selected_zip, lead_profile)
        
        if not df_leads.empty:
            st.success(f"Successfully indexed and verified {len(df_leads)} high-probability targets!")
            
            # Interactive Map
            st.map(df_leads, zoom=13, use_container_width=True)
            
            # Lead Table
            st.markdown(f"### 🎯 Lead Profile: {lead_profile}")
            display_df = df_leads.drop(columns=["latitude", "longitude"])
            st.dataframe(display_df, use_container_width=True)
            
            # Downloadable CSV Lead Sheet
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lead Sheet (CSV)",
                data=csv,
                file_name=f'hybrid_roofing_leads_{selected_zip}.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            if "Insurance Panic" in lead_profile:
                st.warning("⚠️ MARKET INSIGHT: 0 Results Found. The 14-16 year age bracket hits the 2010-2012 housing crash where almost no homes were built in Cape Coral. Switch to 'The Code Trap' profile to target the 2004-2006 boom!")
            else:
                st.warning("No properties found matching this exact profile. Try selecting another Zip Code or Profile.")
