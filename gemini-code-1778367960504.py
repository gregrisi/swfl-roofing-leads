import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator | LIVE", layout="wide")

# Geographic Data for SWFL
COUNTY_CITY_MAP = {
    "Lee": ["Alva", "Bokeelia", "Bonita Springs", "Cape Coral", "Estero", "Fort Myers", "Lehigh Acres", "Sanibel"],
    "Collier": ["Ave Maria", "Everglades City", "Golden Gate", "Immokalee", "Marco Island", "Naples"],
    "Charlotte": ["Babcock Ranch", "Englewood", "Port Charlotte", "Punta Gorda", "Rotonda West"]
}

# --- MARKETING & APP LOGIC ---
st.title("🏠 SWFL Roofing: Live Public Records Lead Generator")
st.markdown("**Powered by Live ATTOM API Data.** Pulling real-time property tax and sales records.")

st.sidebar.header("🎯 Targeting Parameters")

# 1. Geography Inputs
selected_county = st.sidebar.selectbox("Select County", list(COUNTY_CITY_MAP.keys()))
cities_in_county = sorted(COUNTY_CITY_MAP[selected_county])
selected_cities = st.sidebar.multiselect("Select Target Cities/Areas", cities_in_county, default=cities_in_county[:3])

# 2. Market Filters
st.sidebar.subheader("Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)

# The old manual API input boxes have been completely removed from here!

generate_leads = st.sidebar.button("Fetch Live Records")

# --- LIVE ATTOM API ENGINE ---
def fetch_attom_records(county, cities, min_age):
    # Retrieve the hidden API key from Streamlit Secrets securely
    try:
        api_key = st.secrets["ATTOM_API_KEY"]
    except KeyError:
        st.error("API Key not found in Streamlit Secrets. Please check your app settings.")
        return pd.DataFrame()

    current_year = datetime.now().year
    max_year_built = current_year - min_age
    
    # ATTOM's Snapshot endpoint
    api_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/snapshot"
    
    headers = {
        "accept": "application/json",
        "apikey": api_key
    }
    
    leads = []
    
    for city in cities:
        params = {
            "cityname": city,
            "minYearBuilt": 1900,
            "maxYearBuilt": max_year_built,
            "pagesize": 50 # Limits return to keep app fast and protect free limits
        }
        
        try:
            response = requests.get(api_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse ATTOM's specific JSON structure
                for property in data.get('property', []):
                    address = property.get('address', {})
                    summary = property.get('summary', {})
                    sale = property.get('sale', {})
                    
                    leads.append({
                        "Site Address": address.get('line1', 'Unknown'),
                        "City": address.get('locality', city),
                        "Zip": address.get('postal1', 'Unknown'),
                        "Year Built": summary.get('yearBuilt', 'Unknown'),
                        "Last Sale Date": sale.get('saleSearchDate', 'Unknown'),
                        "Absentee Owner": "Yes" if summary.get('absenteeInd') == "Y" else "No"
                    })
            else:
                st.error(f"ATTOM API Error {response.status_code}. You may have hit your rate limit or the key is invalid.")
                break
                
        except Exception as e:
            st.error(f"Network error connecting to ATTOM: {e}")
            break
            
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    if not selected_cities:
        st.error("Please select at least one city.")
    else:
        with st.spinner("Connecting to ATTOM servers and compiling county records..."):
            df_leads = fetch_attom_records(selected_county, selected_cities, min_home_age)
            
            if not df_leads.empty:
                st.success(f"Successfully retrieved {len(df_leads)} live property records.")
                
                # Display to the user
                st.dataframe(df_leads, use_container_width=True)
                
                # Export functionality
                csv = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Live Data CSV",
                    data=csv,
                    file_name=f'live_roofing_data_{selected_county.lower()}.csv',
                    mime='text/csv',
                )
