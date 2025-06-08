# NYC Free Summer Concerts Event Tracker

An app that scrapes NYC free summer concert data and displays today's events.

## Components

1. **Python Backend** (`event_scraper.py`) - Scrapes web data and uses Claude API to parse events into a CSV
2. **UI** (`index.html`) - Displays today's events from the parsed CSV data

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Anthropic API Key

You'll need an Anthropic API key to use Claude for parsing the event data.

Create a `.env` file with
```
ANTHROPIC_API_KEY='your-api-key-here'
```

### 3. Run the Python Scraper

```bash
python event_scraper.py
```

This will:
- Scrape the [Secret NYC events page](https://secretnyc.co/free-summer-concerts-2025-full-list/)
- Use Claude API to parse and structure the event data
- Save results to `nyc_events.csv`
- Display a summary of parsed events

### 4. Start the Local Server and Open the Frontend

Start a local server to serve the frontend:

```bash
python -m http.server 8000
```

Then open your web browser and navigate to `http://localhost:8000` to:
- Upload the generated `nyc_events.csv` file
- View today's events automatically filtered from the dataset

## File Structure

```
├── event_scraper.py
├── index.html
├── requirements.txt
├── README.md
└── nyc_events.csv      # Generated events data (after running scraper)
```

## Features

### Python Backend
- Web scraping with requests and BeautifulSoup
- Intelligent event parsing using Claude API
- Fallback parsing if API fails
- Data validation and cleaning
- Pandas DataFrame export to CSV

### UI
- Clean, modern black and white design
- CSV file upload and parsing
- Automatic filtering for today's events
- Responsive design for mobile/desktop
- Error handling and loading states

## Data Structure

The CSV contains the following columns:
- `date` - Event date (YYYY-MM-DD format)
- `event_name` - Name/title of the event
- `time` - Event time (if available)
- `location` - Venue location/address
- `venue_series` - Concert series name (Bryant Park, SummerStage, etc.)
