"""Amadeus API client for flight searches."""
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from amadeus import Client, ResponseError
from dotenv import load_dotenv

load_dotenv()


class AmadeusFlightAPI:
    """Client for searching flights using Amadeus API."""

    # Class-level cache for IATA codes to prevent repeated lookups
    _iata_cache: Dict[str, Optional[str]] = {}
    _last_request_time = 0
    _min_request_interval = 0.5  # 500ms between requests to avoid rate limits

    def __init__(self):
        """Initialize Amadeus client with credentials from environment."""
        api_key = os.getenv('AMADEUS_API_KEY')
        api_secret = os.getenv('AMADEUS_API_SECRET')

        if not api_key or not api_secret:
            print("[WARN] Amadeus API credentials not found in environment!")
            print("[WARN] Set AMADEUS_API_KEY and AMADEUS_API_SECRET in .env file")

        self.client = Client(
            client_id=api_key,
            client_secret=api_secret
        )

    def _rate_limit(self):
        """Ensure minimum time between API requests."""
        current_time = time.time()
        time_since_last = current_time - AmadeusFlightAPI._last_request_time

        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            print(f"[DEBUG] Rate limiting: waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)

        AmadeusFlightAPI._last_request_time = time.time()

    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search for flights between two cities.

        Args:
            origin: IATA code of departure city (e.g., 'PAR' for Paris)
            destination: IATA code of arrival city (e.g., 'BER' for Berlin)
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date in YYYY-MM-DD format
            adults: Number of adult passengers
            max_results: Maximum number of results to return

        Returns:
            List of flight offers with price, duration, and details
        """
        try:
            print(f"[DEBUG] Amadeus search: {origin} -> {destination} on {departure_date}")
            print(f"[DEBUG] Request params: originLocationCode={origin}, destinationLocationCode={destination}, departureDate={departure_date}, adults={adults}, max={max_results}")

            # Apply rate limiting
            self._rate_limit()

            # Build parameters - only include returnDate if it's not None
            params = {
                'originLocationCode': origin,
                'destinationLocationCode': destination,
                'departureDate': departure_date,
                'adults': adults,
                'max': max_results
            }

            # Only add returnDate if it's provided (Amadeus API rejects returnDate=None)
            if return_date:
                params['returnDate'] = return_date

            response = self.client.shopping.flight_offers_search.get(**params)

            flights = []
            for offer in response.data:
                flight_info = self._parse_flight_offer(offer)
                flights.append(flight_info)

            print(f"[DEBUG] Found {len(flights)} flights")
            return flights

        except ResponseError as error:
            print(f"[ERROR] Amadeus API error: {error}")
            print(f"[ERROR] Request was: {origin} -> {destination} on {departure_date}")

            # Extract detailed error information
            if hasattr(error, 'response'):
                response = error.response
                print(f"[ERROR] Status Code: {response.status_code if hasattr(response, 'status_code') else 'unknown'}")

                # Try to get the error body
                if hasattr(response, 'body'):
                    import json
                    try:
                        error_body = json.loads(response.body) if isinstance(response.body, str) else response.body
                        print(f"[ERROR] Error Details: {json.dumps(error_body, indent=2)}")

                        # Extract specific error messages
                        if 'errors' in error_body:
                            for err in error_body['errors']:
                                print(f"[ERROR]   - {err.get('title', 'Error')}: {err.get('detail', 'No details')}")
                                if 'source' in err:
                                    print(f"[ERROR]     Source: {err['source']}")
                    except:
                        print(f"[ERROR] Response body: {response.body}")

                # Try to get result/data
                if hasattr(response, 'result'):
                    print(f"[ERROR] Result: {response.result}")
                if hasattr(response, 'data'):
                    print(f"[ERROR] Data: {response.data}")

            return []

    def _parse_flight_offer(self, offer) -> Dict:
        """Parse Amadeus flight offer into simplified format."""
        itinerary = offer['itineraries'][0]
        segments = itinerary['segments']

        # Calculate total duration
        total_duration = itinerary['duration']

        # Get price
        price = float(offer['price']['total'])
        currency = offer['price']['currency']

        # Get departure and arrival info
        first_segment = segments[0]
        last_segment = segments[-1]

        departure_time = first_segment['departure']['at']
        arrival_time = last_segment['arrival']['at']

        # Count stops
        num_stops = len(segments) - 1

        return {
            'type': 'flight',
            'provider': 'Amadeus',
            'price': price,
            'currency': currency,
            'duration': total_duration,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'origin': first_segment['departure']['iataCode'],
            'destination': last_segment['arrival']['iataCode'],
            'stops': num_stops,
            'carriers': list(set([seg['carrierCode'] for seg in segments])),
            'details': {
                'segments': [
                    {
                        'carrier': seg['carrierCode'],
                        'flight_number': seg['number'],
                        'from': seg['departure']['iataCode'],
                        'to': seg['arrival']['iataCode'],
                        'departure': seg['departure']['at'],
                        'arrival': seg['arrival']['at']
                    }
                    for seg in segments
                ]
            }
        }

    def get_city_iata_code(self, city_name: str) -> Optional[str]:
        """
        Get IATA code for a city name with caching.

        Args:
            city_name: Name of the city

        Returns:
            IATA code or None if not found
        """
        # Check cache first
        cache_key = city_name.upper()
        if cache_key in AmadeusFlightAPI._iata_cache:
            cached_code = AmadeusFlightAPI._iata_cache[cache_key]
            print(f"[DEBUG] Using cached IATA code for {city_name}: {cached_code}")
            return cached_code

        print(f"[DEBUG] Looking up IATA code for: {city_name}")

        # Apply rate limiting before API call
        self._rate_limit()

        try:
            # Try with CITY or AIRPORT subtypes - note: pass as comma-separated string
            response = self.client.reference_data.locations.get(
                keyword=city_name,
                subType='CITY,AIRPORT'  # Amadeus expects comma-separated string, not list
            )

            if response.data:
                print(f"[DEBUG] Found {len(response.data)} locations for {city_name}")
                # Prefer CITY type, but fallback to AIRPORT
                for location in response.data:
                    print(f"[DEBUG]   - {location.get('name')} ({location.get('iataCode')}) [{location.get('subType')}]")
                    if location.get('subType') == 'CITY':
                        code = location['iataCode']
                        print(f"[DEBUG] Using CITY code: {code}")
                        # Cache the result
                        AmadeusFlightAPI._iata_cache[cache_key] = code
                        return code
                # If no CITY found, return first result (usually AIRPORT)
                code = response.data[0]['iataCode']
                print(f"[DEBUG] Using first code: {code}")
                # Cache the result
                AmadeusFlightAPI._iata_cache[cache_key] = code
                return code

            print(f"[WARN] No locations found for {city_name}")
            # Cache the failure to avoid repeated lookups
            AmadeusFlightAPI._iata_cache[cache_key] = None
            return None

        except ResponseError as error:
            print(f"[ERROR] Error getting IATA code for '{city_name}': {error}")

            # If we got rate limited (429), don't try fallback - return None
            if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
                if error.response.status_code == 429:
                    print(f"[ERROR] Rate limited - please wait before retrying")
                    # Don't cache rate limit failures
                    return None

            # For other errors, try common IATA codes as fallback
            common_codes = {
                'PARIS': 'PAR', 'LONDON': 'LON', 'BERLIN': 'BER',
                'MADRID': 'MAD', 'ROME': 'ROM', 'DUBLIN': 'DUB',
                'AMSTERDAM': 'AMS', 'BARCELONA': 'BCN', 'MUNICH': 'MUC',
                'VIENNA': 'VIE', 'PRAGUE': 'PRG', 'BUDAPEST': 'BUD',
                'LISBON': 'LIS', 'BRUSSELS': 'BRU', 'COPENHAGEN': 'CPH',
                'STOCKHOLM': 'STO', 'OSLO': 'OSL', 'ATHENS': 'ATH'
            }

            if cache_key in common_codes:
                code = common_codes[cache_key]
                print(f"[DEBUG] Using common IATA code: {code}")
                AmadeusFlightAPI._iata_cache[cache_key] = code
                return code

            # Cache the failure
            AmadeusFlightAPI._iata_cache[cache_key] = None
            return None


# Example usage
if __name__ == "__main__":
    api = AmadeusFlightAPI()

    # Search flights from Paris to Berlin
    flights = api.search_flights(
        origin="PAR",
        destination="BER",
        departure_date="2025-11-01"
    )

    for flight in flights:
        print(f"\nFlight: {flight['price']} {flight['currency']}")
        print(f"Duration: {flight['duration']}")
        print(f"Stops: {flight['stops']}")
        print(f"Carriers: {', '.join(flight['carriers'])}")
