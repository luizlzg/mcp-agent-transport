# Setup Guide

Complete guide to set up and run the European Transportation AI Agent.

## Prerequisites

- **Python 3.10 or higher** (required by LangChain 1.0 - Python 3.9 support dropped)
- Node.js and npm (for MCP servers - optional)
- API keys for transportation services

## Step 1: Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Get API Keys

### Required: LLM Provider (choose one)

**Option A: OpenAI**
1. Go to https://platform.openai.com/
2. Create an account or sign in
3. Navigate to API keys section
4. Create a new API key
5. Copy the key

**Option B: Anthropic Claude**
1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Navigate to API keys
4. Create a new API key
5. Copy the key

### Optional: Transportation APIs

**Amadeus (Flights) - RECOMMENDED**
1. Go to https://developers.amadeus.com/
2. Sign up for free self-service account
3. Create an app to get API key and secret
4. Free tier: 200-10,000 requests/month

**SNCF (French Trains)**
1. Go to https://www.digital.sncf.com/startup/api
2. Sign up for API access
3. Get your API key
4. Provides real-time French train data

**RapidAPI (FlixBus)**
1. Go to https://rapidapi.com/
2. Create an account
3. Subscribe to FlixBus API (free tier available)
4. Copy your RapidAPI key

## Step 3: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your API keys
# On Windows, you can use: notepad .env
# On macOS/Linux: nano .env or vim .env
```

Edit `.env` and add your keys:

```env
# Required: Choose one
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# Optional but recommended
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret

# Optional
SNCF_API_KEY=your_sncf_key
RAPIDAPI_KEY=your_rapidapi_key
```

## Step 4: Install MCP Servers (Optional)

MCP servers provide filesystem access for saving itineraries.

```bash
# The servers will be auto-installed when first used via npx
# Or you can pre-install them globally:
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-fetch
```

## Step 5: Run the Agent

```bash
python main.py
```

You should see the welcome screen and API configuration status.

## Example Conversation

```
You: I need to go from Paris to Berlin next week

Agent: I'd be happy to help you find the best route from Paris to Berlin!
       To give you the most relevant options, could you tell me:
       - What specific date would you like to travel?
       - Do you prioritize cost or speed?

You: November 15th, 2025. I prefer the cheapest option.

Agent: Let me search for the cheapest options for you...
       [Agent searches flights, trains, and buses]

       Here are your options from Paris to Berlin on November 15th, 2025:

       1. FlixBus: €45.90 - 13 hours 30 minutes (cheapest!)
       2. Train via SNCF: €89.00 - 8 hours 15 minutes
       3. Flight via Ryanair: €129.00 - 2 hours

       The bus is the cheapest option at €45.90. Would you like me to save
       this itinerary for you?

You: Yes, save it please

Agent: I've saved your itinerary as "paris_berlin_2025-11-15.json"
```

## Troubleshooting

### "No LLM API key configured"
- Make sure you've set either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`
- Check that the `.env` file is in the project root directory
- Verify the API key is valid and active

### "No flights/trains/buses found"
- Check that the corresponding API key is set in `.env`
- Verify the API key is active and has available quota
- Some APIs may have geographic or route limitations

### "ModuleNotFoundError"
- Make sure you've activated your virtual environment
- Run `pip install -r requirements.txt` again
- Check that you're using Python 3.10 or higher

### MCP Server Issues
- Ensure Node.js and npm are installed
- Try running `npm install -g @modelcontextprotocol/server-filesystem` manually
- Check that the `saved_itineraries` directory exists

## API Rate Limits

- **Amadeus Free Tier**: 200-10,000 requests/month (varies by endpoint)
- **OpenAI GPT-4**: Pay per use
- **Anthropic Claude**: Pay per use
- **RapidAPI FlixBus**: Check your subscription tier

## Next Steps

1. Try different travel queries
2. Experiment with date ranges
3. Save and load itineraries
4. Compare prices across different dates

## Getting Help

- Check the README.md for project overview
- Review the code in `agent/` and `apis/` directories
- Open an issue on GitHub (if applicable)

## Production Deployment

For production use:
1. Use environment-specific `.env` files
2. Implement proper error handling and logging
3. Add rate limiting to prevent API quota exhaustion
4. Consider caching API responses
5. Add authentication for multi-user scenarios
6. Monitor API usage and costs
