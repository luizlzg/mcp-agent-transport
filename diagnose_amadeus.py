"""Diagnostic script to test Amadeus API connection and identify issues."""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("AMADEUS API DIAGNOSTICS")
print("=" * 80)

# Test 1: Check credentials
print("\n1. Checking API Credentials")
print("-" * 80)
api_key = os.getenv('AMADEUS_API_KEY')
api_secret = os.getenv('AMADEUS_API_SECRET')

if not api_key:
    print("[FAIL] AMADEUS_API_KEY not found in environment")
    print("       Add to .env file: AMADEUS_API_KEY=your_key")
    exit(1)
else:
    print(f"[OK] AMADEUS_API_KEY found: {api_key[:10]}...")

if not api_secret:
    print("[FAIL] AMADEUS_API_SECRET not found in environment")
    print("       Add to .env file: AMADEUS_API_SECRET=your_secret")
    exit(1)
else:
    print(f"[OK] AMADEUS_API_SECRET found: {api_secret[:10]}...")

# Test 2: Initialize client
print("\n2. Initializing Amadeus Client")
print("-" * 80)
try:
    from amadeus import Client
    client = Client(
        client_id=api_key,
        client_secret=api_secret
    )
    print("[OK] Client initialized successfully")
except Exception as e:
    print(f"[FAIL] Failed to initialize client: {e}")
    exit(1)

# Test 3: Test authentication
print("\n3. Testing Authentication (token request)")
print("-" * 80)
try:
    # This should trigger an authentication call
    response = client.reference_data.locations.get(
        keyword="Paris",
        subType="CITY"
    )
    print("[OK] Authentication successful")
    print(f"[OK] Token acquired, API is accessible")
except Exception as e:
    print(f"[FAIL] Authentication failed: {e}")
    print("\nPossible issues:")
    print("  - Invalid API credentials")
    print("  - Network connectivity problem")
    print("  - API endpoint changed")
    print("  - Account suspended/expired")
    exit(1)

# Test 4: Test location lookup
print("\n4. Testing Location Lookup")
print("-" * 80)
test_cities = ["Paris", "London", "Berlin"]

for city in test_cities:
    try:
        print(f"\nLooking up: {city}")
        response = client.reference_data.locations.get(
            keyword=city,
            subType="CITY,AIRPORT"
        )

        if response.data:
            print(f"  [OK] Found {len(response.data)} locations")
            for i, loc in enumerate(response.data[:3]):  # Show first 3
                print(f"       {i+1}. {loc.get('name')} ({loc.get('iataCode')}) - {loc.get('subType')}")
        else:
            print(f"  [WARN] No results for {city}")

    except Exception as e:
        print(f"  [FAIL] Error: {e}")

# Test 5: Test flight search
print("\n5. Testing Flight Search")
print("-" * 80)
try:
    from datetime import datetime, timedelta

    # Search for a flight 30 days from now
    future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"Searching: PAR -> LON on {future_date}")
    response = client.shopping.flight_offers_search.get(
        originLocationCode="PAR",
        destinationLocationCode="LON",
        departureDate=future_date,
        adults=1,
        max=2
    )

    if response.data:
        print(f"[OK] Found {len(response.data)} flight offers")
        for i, offer in enumerate(response.data):
            price = offer['price']['total']
            currency = offer['price']['currency']
            print(f"     {i+1}. {price} {currency}")
    else:
        print("[WARN] No flight offers found")

except Exception as e:
    print(f"[FAIL] Flight search error: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
print("\nIf all tests passed, the Amadeus API is working correctly.")
print("If you're still seeing 400 errors, check:")
print("  1. Date format (must be YYYY-MM-DD)")
print("  2. IATA codes are valid (3-letter codes)")
print("  3. Departure date is in the future")
print("  4. Origin and destination are different")
print("=" * 80)
