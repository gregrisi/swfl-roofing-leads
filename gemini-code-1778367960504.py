import streamlit as st
import pandas as pd
import random
from datetime import datetime

# --- CONFIGURATION & SETUP ---
st.set_page_config(page_title="SWFL Roofing Lead Generator", layout="wide")

# Geographic Data for SWFL
COUNTY_CITY_MAP = {
    "Lee": ["Fort Myers", "Cape Coral", "Bonita Springs", "Estero", "Lehigh Acres"],
    "Collier": ["Naples", "Marco Island", "Golden Gate", "Immokalee"],
    "Charlotte": ["Punta Gorda", "Port Charlotte", "Englewood", "Rotonda West"]
}

# --- MARKETING & APP LOGIC ---
st.title("🏠 SWFL Roofing: Precision Lead Generator")
st.markdown("""
**Designed for Canvassing & Cold Calling.** Filter by highly targeted zones to find homeowners facing insurance renewals or aging roofs.
""")

st.sidebar.header("🎯 Targeting Parameters")

# 1. Simple Input: Select County
selected_county = st.sidebar.selectbox("Select County", list(COUNTY_CITY_MAP.keys()))

# 2. Simple Input: Select Cities within County
cities_in_county = COUNTY_CITY_MAP[selected_county]
selected_cities = st.sidebar.multiselect("Select Target Cities", cities_in_county, default=cities_in_county)

# 3. Market Consideration: Age of Roof / Insurance Risk
st.sidebar.subheader("Property Filters")
min_home_age = st.sidebar.slider("Minimum Home Age (Years)", 0, 50, 15)
exclude_recent_roofs = st.sidebar.checkbox("Exclude Homes with Roofs < 10 Yrs Old", value=True)

# Generate Application Action
generate_leads = st.sidebar.button("Generate Lead Sheet")

# --- MOCK DATA GENERATOR (Simulating API Pull) ---
def fetch_targeted_leads(county, cities, min_age, exclude_new_roofs):
    leads = []
    current_year = datetime.now().year
    
    # Generate 20-50 targeted leads for the sales team
    num_leads = random.randint(20, 50) 
    
    street_names = ["Palm", "Cypress", "Mangrove", "Gulf", "Tamiami", "Coconut", "Banyan"]
    street_types = ["Blvd", "Ave", "St", "Dr", "Way"]
    
    for _ in range(num_leads):
        city = random.choice(cities)
        year_built = random.randint(current_year - 50, current_year - min_age)
        
        # Determine roof age based on filters
        if exclude_new_roofs:
            roof_age = random.randint(11, current_year - year_built)
        else:
            roof_age = random.randint(1, current_year - year_built)
            
        leads.append({
            "Homeowner": f"Resident {random.randint(1000, 9999)}",
            "Address": f"{random.randint(100, 9999)} {random.choice(street_names)} {random.choice(street_types)}",
            "City": city,
            "Zip": f"339{random.randint(10, 99)}",
            "Year Built": year_built,
            "Est. Roof Age": roof_age,
            "Insurance Risk": "High" if roof_age > 15 else "Moderate",
            "Phone Number": f"(239) 555-{random.randint(1000, 9999)}"
        })
        
    return pd.DataFrame(leads)

# --- OUTPUT FOR SALES TEAM ---
if generate_leads:
    if not selected_cities:
        st.error("Please select at least one city.")
    else:
        with st.spinner("Querying property records and permit history..."):
            df_leads = fetch_targeted_leads(selected_county, selected_cities, min_home_age, exclude_recent_roofs)
            
            # Sort by highest need (Oldest Roof) to prioritize canvassing
            df_leads = df_leads.sort_values(by="Est. Roof Age", ascending=False).reset_index(drop=True)
            
            st.success(f"Successfully generated {len(df_leads)} high-probability leads in {selected_county} County.")
            
            # Simple, readable format for sales
            st.dataframe(
                df_leads, 
                use_container_width=True,
                column_config={
                    "Est. Roof Age": st.column_config.NumberColumn(
                        "Est. Roof Age",
                        help="Calculated from last recorded roofing permit.",
                        format="%d yrs"
                    ),
                    "Insurance Risk": st.column_config.TextColumn(
                        "Insurance Risk",
                        help="Homes with roofs >15 years face policy cancellation in FL."
                    )
                }
            )
            
            # Export functionality for canvassers
            csv = df_leads.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Lead Sheet for Canvassing (CSV)",
                data=csv,
                file_name=f'roofing_leads_{selected_county.lower()}.csv',
                mime='text/csv',
            )
else:
    st.info("Adjust your targeting parameters on the left and click 'Generate Lead Sheet'.")