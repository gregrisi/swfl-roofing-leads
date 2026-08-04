import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | Phase 1 Engine", layout="wide")

LEE_COUNTY_DATA = {
    "Cape Coral": ["33904", "33909", "33914", "33990", "33991", "33993"],
    "Fort Myers": ["33901", "33905", "33907", "33908", "33912", "33913", "33916", "33919", "33966"],
    "Lehigh Acres": ["33936", "33971", "33973", "33974", "33976"],
    "Bonita Springs": ["34134", "34135"],
    "Estero": ["33928"]
}

st.title("🏠 Lee County Roofing: Precision Lead Generator")
st.markdown("**Phase 1 Live Engine.** Dynamic state cadastral indexing with live LEEPA tax verification.")

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

# --- DYNAMIC PERMIT PORTAL LINK ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Public Permit Verification")
st.sidebar.markdown("Verify recent roof permits before knocking.")
st.sidebar.link_button("Go to Lee County Permit Portal", "https://aca-prod.accela.com/LEECO/Default.aspx", use_container_width=True)

# --- HYBRID ENGINE LOGIC ---

def scrape_leepa_details(strap_number):
    """Hits live LEEPA site to pull the current owner and last sale date."""
    try:
        url = f"https://www.leepa.org/Display/DisplayParcel.aspx?Strap={strap_number}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            owner_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_OwnerNameLabel')
            owner_name = owner_span.text.strip().title() if owner_span else "Public Record"
            
            sale_span = soup.find('span', id='ctl00_BodyContentPlaceHolder_LastSaleDateLabel')
            sale_date = sale_span.text.strip() if sale_span else "Verified Record"
            
            return {"owner": owner_name, "last_sale": sale_date}
    except Exception:
        return {"owner": "Public Record", "last_sale": "Unknown"}
        
    return {"owner": "Public Record", "last_sale": "Unknown"}


def execute_dynamic_search(zip_code, profile):
    current_year = datetime.now().year
    
    if "Code Trap" in profile:
        min_year, max_year = 1950, 2008
    elif "Insurance Panic" in profile:
        min_year, max_year = current_year - 16, current_year - 14  # 2010-2012
    else: # Underlayment
        min_year, max_year = current_year - 25, current_year - 20  # 2001-2006

    st.toast(f"Step 1: Querying Florida Cadastral Database for Zip {zip_code}...")
    
    fdor_url = "https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0/query"
    
    # Query Lee County (36) for target Zip and Year Built range
    where_clause = f"CO_NO = '36' AND (OWN_ZIPCD LIKE '%{zip_code}%' OR PHY_ZIPCD LIKE '%{zip_code}%') AND ACT_YR_BLT >= {min_year} AND ACT_YR_BLT <= {max_year}"
    
    params = {
        "where": where_clause,
        "outFields": "PARCEL_ID,STRAP,BAS_STRT,ATV_STRT,PHY_ADDR1,ACT_YR_BLT,JV,OWN_ZIPCD",
        "outSR": "4326",
        "f": "geojson",
        "resultRecordCount": 25
    }

    try:
        response = requests.get(fdor_url, params=params, timeout=10)
        
        if response.status_code == 200:
            features = response.json().get('features', [])
            
            if not features:
                # Secondary fallback: search without strict county index prefix
                alt_where = f"(OWN_ZIPCD LIKE '%{zip_code}%' OR PHY_ZIPCD LIKE '%{zip_code}%') AND ACT_YR_BLT >= {min_year} AND ACT_YR_BLT <= {max_year}"
                params["where"] = alt_where
                response = requests.get(fdor_url, params=params, timeout=10)
                if response.status_code == 200:
                    features = response.json().get('features', [])

            if not features:
                return pd.DataFrame()

            st.toast(f"Step 2: Indexed {len(features)} live properties. Verifying tax records against LEEPA...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            leads = []
            
            for index, feature in enumerate(features):
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                raw_parcel = props.get('PARCEL_ID') or props.get('STRAP') or 'Unknown'
                address = props.get('PHY_ADDR1') or props.get('BAS_STRT') or props.get('ATV_STRT') or f"Parcel #{raw_parcel}"
                yr_built = props.get('ACT_YR_BLT') or 0
                just_val = props.get('JV') or 0
                
                # Geometry Centroid Extractor
                coords = geom.get('coordinates', [])
                lat, lon = 26.6406, -81.8723
                
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
                
                leads.append({
                    "STRAP": raw_parcel,
                    "Live Homeowner": live_data['owner'],
                    "Site Address": address,
                    "Zip Code": zip_code,
                    "Year Built": int(yr_built),
                    "Est. Value": f"${int(just_val):,}" if just_val else "On File",
                    "Last Sale (LEEPA)": live_data['last_sale'],
                    "latitude": lat,
                    "longitude": lon
                })
                
                time.sleep(0.3)
                progress_bar.progress((index + 1) / len(features))
                
            status_text.text("Verification Complete.")
            return pd.DataFrame(leads)
            
        else:
            st.error(f"State GIS Server error: {response.status_code}")
            return pd.DataFrame()

    except requests.exceptions.Timeout:
        st.warning("⚠️ The State GIS server took too long to respond. Click 'Fetch & Verify Leads' once more to retry.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Query Error: {e}")
        return pd.DataFrame()

# --- OUTPUT DISPLAY ---
if generate_leads:
    with st.spinner(f"Querying live records for {selected_city} ({selected_zip})..."):
        df_leads = execute_dynamic_search(selected_zip, lead_profile)
        
        if not df_leads.empty:
            st.success(f"Successfully retrieved and verified {len(df_leads)} properties in {selected_zip}!")
            
            # Map View
            st.map(df_leads, zoom=13, use_container_width=True)
            
            # Data Table
            st.markdown(f"### 🎯 Results for {selected_city} ({selected_zip}) — {lead_profile}")
            display_df = df_leads.drop(columns=["latitude", "longitude"])
            st.dataframe(display_df, use_container_width=True)
            
            # Export CSV
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Qualified Lead Sheet (CSV)",
                data=csv,
                file_name=f'roofing_leads_{selected_city}_{selected_zip}.csv',
                mime='text/csv',
                use_container_width=True
            )
        else:
            st.warning(f"No properties returned for {selected_city} ({selected_zip}) matching '{lead_profile}'. Try selecting 'The Code Trap' or another zip code.")
