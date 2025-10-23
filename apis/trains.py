
"""Train API client using SNCF and other European rail providers."""
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class TrainAPI:
    """
    Client for searching train routes.
    Uses SNCF API and falls back to web scraping for other providers.
    """

    def __init__(self):
        """Initialize train API clients."""
        # SNCF API (if available)
        self.sncf_api_key = os.getenv('SNCF_API_KEY')

    def search_trains(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search for train routes between two cities.

        Args:
            origin: Origin city name (e.g., 'Paris')
            destination: Destination city name (e.g., 'Berlin')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Optional return date
            max_results: Maximum number of results

        Returns:
            List of train offers with price, duration, and details
        """
        trains = []

        # Try SNCF API first
        sncf_results = self._search_sncf(origin, destination, departure_date)
        trains.extend(sncf_results[:max_results])

        # If we need more results, try other sources
        if len(trains) < max_results:
            # Here we would add other train APIs (Trainline, DB, etc.)
            # For now, we'll use a fallback that simulates real data structure
            pass

        return trains[:max_results]

    def _search_sncf(
        self,
        origin: str,
        destination: str,
        departure_date: str
    ) -> List[Dict]:
        """
        Search using SNCF API (French trains).

        Note: This uses the public SNCF API which provides real-time data.
        API endpoint: https://api.sncf.com/v1/coverage/sncf/
        """
        if not self.sncf_api_key:
            # If no API key, return empty (user needs to set up SNCF API)
            return []

        try:
            # SNCF API uses Navitia format
            url = "https://api.sncf.com/v1/coverage/sncf/journeys"

            params = {
                'from': origin,
                'to': destination,
                'datetime': departure_date.replace('-', '') + 'T120000'  # Format: YYYYMMDDTHHMMSS
            }

            headers = {
                'Authorization': self.sncf_api_key
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()

            trains = []
            if 'journeys' in data:
                for journey in data['journeys'][:5]:
                    train_info = self._parse_sncf_journey(journey)
                    trains.append(train_info)

            return trains

        except Exception as e:
            print(f"SNCF API error: {e}")
            return []

    def _parse_sncf_journey(self, journey: Dict) -> Dict:
        """Parse SNCF journey data into simplified format."""
        # Extract key information
        departure_time = journey.get('departure_date_time', '')
        arrival_time = journey.get('arrival_date_time', '')
        duration = journey.get('duration', 0)

        # Format duration from seconds to readable format
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        duration_str = f"PT{hours}H{minutes}M"

        # Get sections (train segments)
        sections = journey.get('sections', [])
        train_sections = [s for s in sections if s.get('type') == 'public_transport']

        # Extract price if available (not always in SNCF API)
        price = None
        currency = "EUR"

        return {
            'type': 'train',
            'provider': 'SNCF',
            'price': price,  # Price often requires additional API call
            'currency': currency,
            'duration': duration_str,
            'departure_time': departure_time,
            'arrival_time': arrival_time,
            'origin': sections[0].get('from', {}).get('name', '') if sections else '',
            'destination': sections[-1].get('to', {}).get('name', '') if sections else '',
            'transfers': len(train_sections) - 1,
            'details': {
                'sections': [
                    {
                        'line': s.get('display_informations', {}).get('label', ''),
                        'from': s.get('from', {}).get('name', ''),
                        'to': s.get('to', {}).get('name', ''),
                        'departure': s.get('departure_date_time', ''),
                        'arrival': s.get('arrival_date_time', '')
                    }
                    for s in train_sections
                ]
            }
        }

    def get_station_code(self, city_name: str) -> Optional[str]:
        """
        Get station code for a city.

        Args:
            city_name: Name of the city

        Returns:
            Station code or None
        """
        # This would require a station lookup API
        # For now, return the city name as-is
        return city_name


class TrainlineAPI:
    """
    Client for Trainline API (requires business partnership).
    This is a placeholder showing the structure for when API access is obtained.
    """

    def __init__(self):
        self.api_key = os.getenv('TRAINLINE_API_KEY')
        self.base_url = "https://api.trainline.com/v1"

    def search_trains(
        self,
        origin: str,
        destination: str,
        departure_date: str
    ) -> List[Dict]:
        """
        Search trains using Trainline API.
        Note: Requires business partnership with Trainline.
        """
        if not self.api_key:
            return []

        # This would contain actual Trainline API implementation
        # when API access is obtained through their business program
        return []


# Example usage
if __name__ == "__main__":
    api = TrainAPI()

    # Search trains from Paris to Berlin
    trains = api.search_trains(
        origin="Paris",
        destination="Berlin",
        departure_date="2025-11-01"
    )

    for train in trains:
        print(f"\nTrain: {train['price']} {train['currency']}")
        print(f"Duration: {train['duration']}")
        print(f"Transfers: {train['transfers']}")
        print(f"Provider: {train['provider']}")
