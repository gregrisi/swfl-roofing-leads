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
st.markdown("**Powered by Live API Data.** Pulling real-time property tax, sales, and permit records.")

st.sidebar.header("🎯 Targeting Parameters")

# 1. Geography Inputs
selected_county = st.sidebar.selectbox("Select County", list(COUNTY_CITY_MAP.keys()))
cities_in_county = sorted(COUNTY_CITY_MAP[selected_county])
selected_cities = st.sidebar.multiselect("Select Target Cities/Areas", cities_in_county, default=cities_in_county[:3])

# 2. Market Filters
st.sidebar.subheader("Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)
recent_sale = st.sidebar.checkbox("Prioritize Recent Home Sales (Last 12 Months)", value=False, help="Great for targeting insurance-mandated roof replacements.")

# 3. LIVE DATA CREDENTIALS
st.sidebar.subheader("API Integration")
api_provider = st.sidebar.selectbox("Select Data Provider", ["ATTOM Data", "PropertyRadar", "Estated"])
api_key = st.sidebar.text_input(f"{api_provider} API Key", type="password")

generate_leads = st.sidebar.button("Fetch Live Records")

# --- LIVE API ENGINE ---
def fetch_live_records(county, cities, min_age, recent_sale_flag, provider, key):
    """
    Production function to call a Real Estate API.
    Note: The exact URL and JSON mapping will depend on your specific provider's documentation.
    """
    
    current_year = datetime.now().year
    max_year_built = current_year - min_age
    
    # Example: Structuring the API Request for a standard provider like ATTOM
    api_url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/expandedprofile"
    
    headers = {
        "accept": "application/json",
        "apikey": key
    }
    
    leads = []
    
    # We iterate through the selected cities to pull data
    for city in cities:
        # These parameters map to the API's required formatting
        params = {
            "address1": city,
            "state": "FL",
            "county": county,
            "minYearBuilt": 1900,
            "maxYearBuilt": max_year_built
        }
        
        try:
            # Execute the live network request
            response = requests.get(api_url, headers=headers, params=params)
            
            # Check if the API accepted our key and parameters
            if response.status_code == 200:
                data = response.json()
                
                # Parse the complex JSON response into a simple format for sales
                # (This parsing logic is a template and must be aligned with the provider's exact JSON structure)
                for property in data.get('property', []):
                    last_sale_date = property.get('sale', {}).get('saleSearchDate', 'Unknown')
                    
                    leads.append({
                        "Homeowner(s)": property.get('owner', {}).get('owner1FullName', 'Public Record'),
                        "Site Address": property.get('address', {}).get('line1', 'Unknown'),
                        "City": city,
                        "Zip": property.get('address', {}).get('postal1', 'Unknown'),
                        "Year Built": property.get('summary', {}).get('yearBuilt', 'Unknown'),
                        "Last Sale Date": last_sale_date,
                        "Absentee Owner": "Yes" if property.get('summary', {}).get('absenteeInd') == "Y" else "No"
                    })
            else:
                st.error(f"API Error {response.status_code}: Please check your API Key and subscription limits.")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Network error connecting to API: {e}")
            return pd.DataFrame()
            
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    if not selected_cities:
        st.error("Please select at least one city.")
    elif not api_key:
        st.error(f"A valid {api_provider} API Key is required to pull live public records.")
    else:
        with st.spinner(f"Connecting to {api_provider} servers and compiling county records..."):
            df_leads = fetch_live_records(selected_county, selected_cities, min_home_age, recent_sale, api_provider, api_key)
            
            if not df_leads.empty:
                st.success(f"Successfully retrieved {len(df_leads)} live property records.")
                
                # Highlight absentee owners (great for direct mail, harder for door-knocking)
                st.dataframe(df_leads, use_container_width=True)
                
                csv = df_leads.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Live Data CSV",
                    data=csv,
                    file_name=f'live_roofing_data_{selected_county.lower()}.csv',
                    mime='text/csv',
                )
