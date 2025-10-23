"""Bus API client using FlixBus via RapidAPI."""
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class FlixBusAPI:
    """Client for searching FlixBus routes via RapidAPI."""

    def __init__(self):
        """Initialize FlixBus API client."""
        self.rapidapi_key = os.getenv('RAPIDAPI_KEY')
        self.rapidapi_host = "flixbus2.p.rapidapi.com"
        self.base_url = f"https://{self.rapidapi_host}"

    def search_buses(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search for bus routes between two cities.

        Args:
            origin: Origin city name (e.g., 'Paris')
            destination: Destination city name (e.g., 'Berlin')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date
            adults: Number of passengers
            max_results: Maximum number of results

        Returns:
            List of bus offers with price, duration, and details
        """
        if not self.rapidapi_key:
            print("Warning: RAPIDAPI_KEY not set. Please set it to use FlixBus API.")
            return []

        try:
            # First, get station IDs for origin and destination
            origin_id = self._search_station(origin)
            destination_id = self._search_station(destination)

            if not origin_id or not destination_id:
                print(f"Could not find stations for {origin} or {destination}")
                return []

            # Search for trips
            trips = self._search_trips(
                origin_id,
                destination_id,
                departure_date,
                adults
            )

            return trips[:max_results]

        except Exception as e:
            print(f"FlixBus API error: {e}")
            return []

    def _search_station(self, city_name: str) -> Optional[str]:
        """
        Search for FlixBus station ID by city name.

        Args:
            city_name: Name of the city

        Returns:
            Station ID or None
        """
        try:
            url = f"{self.base_url}/search/stations"

            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": self.rapidapi_host
            }

            params = {
                "query": city_name
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Return the first matching station ID
            if data and len(data) > 0:
                return str(data[0].get('id'))

            return None

        except Exception as e:
            print(f"Error searching station: {e}")
            return None

    def _search_trips(
        self,
        origin_id: str,
        destination_id: str,
        departure_date: str,
        adults: int = 1
    ) -> List[Dict]:
        """
        Search for trips between two stations.

        Args:
            origin_id: Origin station ID
            destination_id: Destination station ID
            departure_date: Departure date in YYYY-MM-DD format
            adults: Number of passengers

        Returns:
            List of trip offers
        """
        try:
            url = f"{self.base_url}/search/trips"

            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": self.rapidapi_host
            }

            params = {
                "from_id": origin_id,
                "to_id": destination_id,
                "date": departure_date,
                "adult": adults
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            buses = []
            trips = data.get('trips', []) if isinstance(data, dict) else data

            for trip in trips:
                bus_info = self._parse_trip(trip)
                buses.append(bus_info)

            return buses

        except Exception as e:
            print(f"Error searching trips: {e}")
            return []

    def _parse_trip(self, trip: Dict) -> Dict:
        """Parse FlixBus trip data into simplified format."""
        # Extract price
        price_info = trip.get('price', {})
        price = price_info.get('total', 0) if isinstance(price_info, dict) else 0
        currency = price_info.get('currency', 'EUR') if isinstance(price_info, dict) else 'EUR'

        # Extract departure and arrival
        departure = trip.get('departure', {})
        arrival = trip.get('arrival', {})

        departure_time = departure.get('date', '') if isinstance(departure, dict) else ''
        arrival_time = arrival.get('date', '') if isinstance(arrival, dict) else ''

        # Calculate duration
        duration = trip.get('duration', {})
        if isinstance(duration, dict):
            hours = duration.get('hours', 0)
            minutes = duration.get('minutes', 0)
            duration_str = f"PT{hours}H{minutes}M"
        else:
            duration_str = "PT0H0M"

        # Get origin and destination
        origin = departure.get('station', {}).get('name', '') if isinstance(departure, dict) else ''
        destination = arrival.get('station', {}).get('name', '') if isinstance(arrival, dict) else ''

        # Get transfers
        transfers = len(trip.get('transfers', [])) if 'transfers' in trip else 0

        return {
            'type': 'bus',
            'provider': 'FlixBus',
            'price': price,
            'currency': currency,
            'duration': duration_str,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'origin': origin,
            'destination': destination,
            'transfers': transfers,
            'details': {
                'trip_uid': trip.get('uid', ''),
                'available_seats': trip.get('available', {}).get('seats', 0)
            }
        }


# Example usage
if __name__ == "__main__":
    api = FlixBusAPI()

    # Search buses from Paris to Berlin
    buses = api.search_buses(
        origin="Paris",
        destination="Berlin",
        departure_date="2025-11-01"
    )

    for bus in buses:
        print(f"\nBus: {bus['price']} {bus['currency']}")
        print(f"Duration: {bus['duration']}")
        print(f"Transfers: {bus['transfers']}")
        print(f"Departure: {bus['departure_time']}")
        print(f"Arrival: {bus['arrival_time']}")
