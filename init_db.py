import sqlite3
import os

def init_database():
    db_name = "lee_county_cadastral.db"
    
    if os.path.exists(db_name):
        os.remove(db_name)
        
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # --- ADDED: last_roof_year ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            strap TEXT PRIMARY KEY,
            site_address TEXT,
            city TEXT,
            zip_code TEXT,
            year_built INTEGER,
            last_roof_year INTEGER, 
            roof_type TEXT,
            just_value INTEGER,
            lat REAL,
            lon REAL,
            permit_status TEXT,
            last_permit_date TEXT,
            permit_code TEXT
        )
    """)

    master_records = [
        # --- Cape Coral 33904 ---
        ("18-44-24-C3-02300.0120", "4722 SE 9th Pl", "Cape Coral", "33904", 2005, 2005, "Asphalt Shingle", 385000, 26.5628, -81.9495, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        ("19-44-24-C1-01100.0090", "1228 SE 40th St", "Cape Coral", "33904", 2005, 2022, "Metal", 425000, 26.5722, -81.9501, "🔴 Competitor Replaced", "Full Re-Roof Finaled (11/2022)", "REPLACED"),
        
        # --- Cape Coral 33914 (Injecting your 15-Year Scenarios) ---
        ("31-44-23-C2-00800.0050", "2314 SW 48th Ter", "Cape Coral", "33914", 2005, 2005, "Asphalt Shingle", 520000, 26.5815, -82.0003, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        
        # Scenario A: Old House (1995), Roof is 15 years old (Permit 2011)
        ("15-44-23-C4-01200.0100", "1430 Surfside Blvd", "Cape Coral", "33914", 1995, 2011, "Asphalt Shingle", 490000, 26.5940, -82.0115, "🟡 Aging Permit", "Re-Roof Finaled (08/2011)", "PRIME"),
        
        # Scenario B: House built exactly 15 years ago (2011), Original Roof
        ("15-44-23-C4-01200.0110", "1442 Surfside Blvd", "Cape Coral", "33914", 2011, 2011, "Asphalt Shingle", 510000, 26.5950, -82.0120, "🟢 Prime Target", "Original Roof (No Permits)", "PRIME"),
        
        ("15-44-23-C4-01200.0040", "1418 Surfside Blvd", "Cape Coral", "33914", 2004, 2004, "Metal", 560000, 26.5925, -82.0100, "🟡 Active Permit", "Re-Roof Pending (02/2026)", "PENDING"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO properties 
        (strap, site_address, city, zip_code, year_built, last_roof_year, roof_type, just_value, lat, lon, permit_status, last_permit_date, permit_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, master_records)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_database()
