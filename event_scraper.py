#!/usr/bin/env python3
"""
NYC Free Summer Concerts Event Scraper
Scrapes event data from Secret NYC and uses Claude API to parse into structured data
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import re
from datetime import datetime, date
import os
from typing import List, Dict, Any
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')  # Set your API key as environment variable
TARGET_URL = 'https://secretnyc.co/free-summer-concerts-2025-full-list/'
OUTPUT_FILE = 'nyc_events.csv'

class EventScraper:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def scrape_webpage(self, url: str) -> str:
        """Scrape the target webpage and extract text content"""
        print(f"Scraping webpage: {url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML and extract text
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            print(f"Successfully scraped {len(text)} characters")
            return text
            
        except Exception as e:
            print(f"Error scraping webpage: {e}")
            raise

    def parse_events_with_claude(self, text_content: str) -> List[Dict[str, Any]]:
        """Use Claude API to parse event data from text content"""
        print("Parsing events with Claude API...")
        
        # Split text into chunks to process entire content
        chunk_size = 7000  # Conservative chunk size to avoid token limits
        text_chunks = []
        
        # Try to split by concert series sections first
        series_patterns = [
            r'Bryant Park Picnic Performances',
            r'SummerStage',
            r'Backyard at Hudson Yards',
            r'Battery Park.*?River & Blues Festival',
            r'Lincoln Center.*?Summer for the City',
            r'TSQ Live',
            r'Hudson River Park',
            r'Carnegie Hall Citywide',
            r'DUMBO.*?Live at the Archway',
            r'BRIC Celebrate Brooklyn',
            r'Sounds at Sunset'
        ]
        
        # First, try to split by concert series
        remaining_text = text_content
        for pattern in series_patterns:
            match = re.search(pattern, remaining_text, re.IGNORECASE)
            if match:
                before = remaining_text[:match.start()]
                section = remaining_text[match.start():match.start() + chunk_size]
                if before.strip():
                    text_chunks.append(before.strip())
                if section.strip():
                    text_chunks.append(section.strip())
                remaining_text = remaining_text[match.start() + len(section):]
        
        # If we have remaining text, add it
        if remaining_text.strip():
            text_chunks.append(remaining_text.strip())
        
        # If chunking failed, fall back to simple character-based chunking
        if len(text_chunks) <= 1:
            text_chunks = []
            for i in range(0, len(text_content), chunk_size):
                chunk = text_content[i:i + chunk_size]
                if chunk.strip():
                    text_chunks.append(chunk.strip())
        
        print(f"Processing {len(text_chunks)} text chunks...")
        
        all_events = []
        
        for i, chunk in enumerate(text_chunks):
            print(f"Processing chunk {i+1}/{len(text_chunks)}...")
            
            prompt = f"""
            Please analyze the following text about NYC free summer concerts and extract structured event data. 
            
            Look for patterns like:
            - "June 5:" or "July 10:" followed by event names
            - Artists/band names
            - Venue information
            
            For each event, extract:
            - date (in YYYY-MM-DD format, assume year 2025)
            - event_name (the name/title of the event or artist)
            - time (if specified, otherwise use "Time TBA")
            - location (venue/address if specified, otherwise use venue series location)
            - venue_series (the concert series name like "Bryant Park", "SummerStage", "Hudson Yards", etc.)
            
            IMPORTANT: Return ONLY a valid JSON array, nothing else. Skip any text before or after the JSON.
            Only include events with specific dates. Skip recurring descriptions and TBA events.
            
            Example format:
            [
                {{
                    "date": "2025-06-05",
                    "event_name": "Contemporary Dance",
                    "time": "Time TBA",
                    "location": "Bryant Park",
                    "venue_series": "Bryant Park"
                }},
                {{
                    "date": "2025-06-25",
                    "event_name": "Marc Scibilia",
                    "time": "18:00",
                    "location": "Public Square & Gardens, Hudson Yards",
                    "venue_series": "Hudson Yards"
                }}
            ]
            
            Text to analyze:
            {chunk}
            """
            
            try:
                message = self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=4000,
                    temperature=0,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
                
                # Extract JSON from response
                response_text = message.content[0].text
                
                # Find JSON in the response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    chunk_events = json.loads(json_str)
                    all_events.extend(chunk_events)
                    print(f"Chunk {i+1} parsed {len(chunk_events)} events")
                else:
                    print(f"No JSON found in chunk {i+1} response")
                    
            except Exception as e:
                print(f"Error parsing chunk {i+1}: {e}")
                continue
        
        # Remove duplicates based on date and event_name
        seen_events = set()
        unique_events = []
        
        for event in all_events:
            event_key = (event.get('date', ''), event.get('event_name', ''))
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
        
        print(f"Total events parsed: {len(all_events)}, unique events: {len(unique_events)}")
        
        if not unique_events:
            print("No events found with Claude API, falling back to manual parsing")
            return self.fallback_parse(text_content)
        
        return unique_events
    
    def fallback_parse(self, text_content: str) -> List[Dict[str, Any]]:
        """Fallback manual parsing if Claude API fails"""
        print("Using fallback parsing method...")
        events = []
        
        # Simple regex-based parsing as fallback
        date_pattern = r'(June|July|August|September)\s+(\d{1,2}):\s*(.+)'
        month_map = {'June': 6, 'July': 7, 'August': 8, 'September': 9}
        
        lines = text_content.split('\n')
        current_venue = "Unknown"
        
        for line in lines:
            line = line.strip()
            if 'Bryant Park' in line:
                current_venue = "Bryant Park"
            elif 'SummerStage' in line:
                current_venue = "SummerStage"
            elif 'Hudson Yards' in line:
                current_venue = "Hudson Yards"
            
            match = re.search(date_pattern, line)
            if match:
                month_name, day, event_name = match.groups()
                if month_name in month_map:
                    date_str = f"2025-{month_map[month_name]:02d}-{int(day):02d}"
                    events.append({
                        'date': date_str,
                        'event_name': event_name.strip(),
                        'time': None,
                        'location': None,
                        'venue_series': current_venue
                    })
        
        print(f"Fallback parsing found {len(events)} events")
        return events
    
    def create_dataframe(self, events: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert events list to pandas DataFrame"""
        if not events:
            print("No events to create DataFrame from")
            return pd.DataFrame()
        
        df = pd.DataFrame(events)
        
        # Clean and standardize data
        df['date'] = pd.to_datetime(df['date'])
        df['event_name'] = df['event_name'].astype(str)
        df['time'] = df['time'].fillna('Time TBA')
        df['location'] = df['location'].fillna('Location TBA')
        df['venue_series'] = df['venue_series'].fillna('Unknown Venue')
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"Created DataFrame with {len(df)} events")
        return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Save DataFrame to CSV file"""
        df.to_csv(filename, index=False)
        print(f"Saved events to {filename}")
    
    def run(self):
        """Main execution method"""
        try:
            # Step 1: Scrape webpage
            text_content = self.scrape_webpage(TARGET_URL)
            
            # Step 2: Parse with Claude
            events = self.parse_events_with_claude(text_content)
            
            # Step 3: Create DataFrame
            df = self.create_dataframe(events)
            
            if df.empty:
                print("No events found - exiting")
                return
            
            # Step 4: Save to CSV
            self.save_to_csv(df, OUTPUT_FILE)
            
            # Step 5: Display summary
            print(f"\n=== SUMMARY ===")
            print(f"Total events parsed: {len(df)}")
            print(f"Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
            print(f"Venue series: {', '.join(df['venue_series'].unique())}")
            print(f"Data saved to: {OUTPUT_FILE}")
            
            # Show sample events
            print(f"\n=== SAMPLE EVENTS ===")
            print(df.head().to_string(index=False))
            
        except Exception as e:
            print(f"Error in main execution: {e}")
            raise

def main():
    """Main function"""
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: Please set ANTHROPIC_API_KEY environment variable")
        print("Export it like: export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # Run scraper
    scraper = EventScraper(api_key)
    scraper.run()

if __name__ == "__main__":
    main()
