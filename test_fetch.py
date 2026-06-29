import logging
logging.basicConfig(level=logging.WARNING)
from google_sheets_writer import read_historical_data

print("Testing historical data fetch...")
hubs = ["oskemen.hub", "astana.hub"]

for hub in hubs:
    print(f"\n--- Fetching for {hub} ---")
    try:
        history = read_historical_data(account_name=hub)
        if history:
            print(f"Found {len(history)} records for {hub}:")
            print(history)
        else:
            print(f"No records returned for {hub}")
    except Exception as e:
        print(f"Exception during fetch for {hub}: {e}")
