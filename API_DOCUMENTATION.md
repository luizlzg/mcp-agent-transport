# API Documentation

This document explains the APIs used in the European Transportation Agent and how to obtain access to them.

## Overview

The agent integrates with three types of transportation APIs:
- **Flights**: Amadeus API
- **Trains**: SNCF API (and potentially others)
- **Buses**: FlixBus via RapidAPI

## 1. Amadeus API (Flights)

### Description
Amadeus provides a comprehensive flight search API with access to global airline inventory, real-time pricing, and booking capabilities.

### Signup Process
1. Visit https://developers.amadeus.com/
2. Click "Register" in the top right
3. Fill out the form (email, name, company)
4. Verify your email
5. Log in to the dashboard
6. Click "Create New App"
7. Name your app (e.g., "European Transport Agent")
8. Copy your **API Key** and **API Secret**

### Pricing
- **Test Environment**: Free, with monthly quota (200-10,000 requests depending on endpoint)
- **Production**: Pay-as-you-go starting at €0.0008-0.025 per API call
- Free quota continues in production

### Key Endpoints Used
- `GET /v2/shopping/flight-offers` - Search flights
- `GET /v1/reference-data/locations` - Get IATA codes for cities

### Rate Limits
- Test: Varies by endpoint (typically 200-10,000 free requests/month)
- Production: Unlimited with pay-per-use

### Environment Variables
```env
AMADEUS_API_KEY=your_api_key_here
AMADEUS_API_SECRET=your_api_secret_here
```

### Documentation
- Main docs: https://developers.amadeus.com/self-service
- Flight Search: https://developers.amadeus.com/self-service/category/flights

---

## 2. SNCF API (French Trains)

### Description
SNCF (French National Railway Company) provides real-time data for trains in France and connections to neighboring countries. Uses the Navitia open-source engine.

### Signup Process
1. Visit https://www.digital.sncf.com/startup/api
2. Create an account
3. Request API access
4. Wait for approval (usually 1-2 business days)
5. Receive your API key via email

### Pricing
- **Free tier**: Available for non-commercial use
- **Commercial**: Contact SNCF for pricing

### Key Features
- Real-time train schedules
- Delay information
- Route planning
- Station information

### Key Endpoints Used
- `GET /v1/coverage/sncf/journeys` - Search train journeys

### Environment Variables
```env
SNCF_API_KEY=your_sncf_api_key
```

### Documentation
- API Portal: https://www.digital.sncf.com/startup/api
- Navitia Docs: https://doc.navitia.io/

### Notes
- Primarily covers France and some international routes
- Real-time data includes delays and cancellations
- May not include pricing for all routes

---

## 3. RapidAPI - FlixBus (Buses)

### Description
FlixBus API via RapidAPI provides access to Europe's largest intercity bus network with real-time schedules, pricing, and availability.

### Signup Process
1. Visit https://rapidapi.com/
2. Create a free account
3. Search for "FlixBus" in the API marketplace
4. Choose a FlixBus API provider (e.g., "3b-data/flixbus2")
5. Subscribe to a plan (free tier usually available)
6. Copy your **RapidAPI Key** from the dashboard

### Pricing
Varies by provider, typical options:
- **Free tier**: 100-500 requests/month
- **Basic**: $10-20/month for 5,000-10,000 requests
- **Pro**: $50-100/month for 50,000+ requests

### Key Features
- Station search and autocomplete
- Trip search with pricing
- Timetables
- Seat availability

### Key Endpoints Used
- `GET /search/stations` - Find FlixBus stations
- `GET /search/trips` - Search bus trips

### Environment Variables
```env
RAPIDAPI_KEY=your_rapidapi_key
```

### Documentation
- RapidAPI FlixBus: https://rapidapi.com/3b-data-3b-data-default/api/flixbus2
- Alternative: https://blog.allthingsdev.co/flixbus-api

---

## 4. Alternative APIs

### Trainline API (Trains)
- **Access**: Business partnership required
- **Coverage**: 270+ rail operators across 40 countries
- **Website**: https://www.thetrainline.com/solutions/api
- **Note**: Not for public access; requires B2B agreement

### Kiwi.com Tequila API (Flights)
- **Access**: Previously open, now restricted to partners
- **Coverage**: Global flights with unique multi-carrier combinations
- **Website**: https://tequila.kiwi.com/
- **Status**: Partner access only as of 2025

### Omio API (Multi-modal)
- **Access**: Affiliate program or B2B partnership
- **Coverage**: Trains, buses, flights across Europe
- **Website**: https://www.omio.com/
- **Note**: Primarily for travel platforms

---

## LLM Providers

### OpenAI (GPT-4)

**Signup**:
1. Visit https://platform.openai.com/
2. Create account
3. Go to API keys section
4. Create new secret key

**Pricing**:
- GPT-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- GPT-4 Turbo: Lower cost variant

**Environment Variable**:
```env
OPENAI_API_KEY=sk-...
```

### Anthropic (Claude)

**Signup**:
1. Visit https://console.anthropic.com/
2. Create account
3. Add payment method
4. Go to API keys
5. Create new key

**Pricing**:
- Claude 3.5 Sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- Claude 3 Opus: Higher cost, best performance

**Environment Variable**:
```env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Model Context Protocol (MCP)

### Filesystem Server
- **Installation**: `npm install -g @modelcontextprotocol/server-filesystem`
- **Purpose**: Save and load itineraries
- **No API key required**

### Fetch Server
- **Installation**: `npm install -g @modelcontextprotocol/server-fetch`
- **Purpose**: Web content fetching
- **No API key required**

---

## API Usage Best Practices

### 1. Rate Limiting
```python
import time
from functools import wraps

def rate_limit(calls_per_second):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator
```

### 2. Caching
```python
from functools import lru_cache
import hashlib
import json

@lru_cache(maxsize=100)
def cached_search(origin, destination, date):
    # Your API call here
    pass
```

### 3. Error Handling
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def api_call_with_retry():
    # Your API call here
    pass
```

### 4. Cost Monitoring
- Track API calls per session
- Set up billing alerts
- Implement usage quotas per user
- Cache frequent queries

---

## Testing APIs

### Test Amadeus
```bash
curl -X GET \
  "https://test.api.amadeus.com/v2/shopping/flight-offers?originLocationCode=PAR&destinationLocationCode=BER&departureDate=2025-11-15&adults=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Test SNCF
```bash
curl -X GET \
  "https://api.sncf.com/v1/coverage/sncf/journeys?from=Paris&to=Berlin&datetime=20251115T120000" \
  -H "Authorization: YOUR_API_KEY"
```

### Test FlixBus (via RapidAPI)
```bash
curl -X GET \
  "https://flixbus2.p.rapidapi.com/search/stations?query=Paris" \
  -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
  -H "X-RapidAPI-Host: flixbus2.p.rapidapi.com"
```

---

## Troubleshooting

### "401 Unauthorized"
- Check that your API key is correct
- Ensure you're using the right authentication method
- Verify the key is active and not expired

### "429 Too Many Requests"
- You've exceeded the rate limit
- Wait before making more requests
- Implement rate limiting in your code

### "403 Forbidden"
- API key may not have permission for this endpoint
- Check your subscription tier
- Verify you're using the correct API version

### "No Results Found"
- Check date format (YYYY-MM-DD)
- Verify city names or codes are correct
- Some routes may not be available
- Try different dates or cities

---

## Additional Resources

- **Amadeus Blog**: https://developers.amadeus.com/blog
- **SNCF Developer Portal**: https://www.digital.sncf.com/startup
- **RapidAPI Guides**: https://docs.rapidapi.com/
- **LangChain Docs**: https://python.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
