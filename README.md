# Handlebar Event Listing Reporter

## Overview
The Handlebar Event Listing Reporter is a Streamlit application designed to monitor and report on event ticket availability and pricing. It allows users to fetch event data from a specified URL, check ticket availability, and view detailed reports on events.

## Features
- Fetch event links from a specified events page.
- Check ticket availability and pricing for selected events.
- Display event data in a user-friendly interface.
- Export event reports in PDF format.

## Project Structure
```
handlebar-event-listing-reporter/
├── src/
│   ├── app.py          # Main entry point of the Streamlit application
│   └── utils.py        # Utility functions for fetching and managing event data
├── requirements.txt     # List of dependencies
└── README.md            # Project documentation
```

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd handlebar-event-listing-reporter
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the Streamlit application:
   ```
   streamlit run src/app.py
   ```

## Usage
- Open your web browser and navigate to the URL provided by Streamlit (usually `http://localhost:8501`).
- Enter the URL of the events page you want to monitor.
- Click on "Fetch Events" to retrieve the list of events.
- Select the events you want to check and click "Check Selected" to see ticket availability and pricing.
- Use the "Export PDF Report" button to generate a report of the event data.

## Dependencies
- Streamlit
- BeautifulSoup
- cloudscraper
- pandas
- reportlab
- Other libraries as needed

## License
This project is licensed under the MIT License. See the LICENSE file for details.# handlebar-event-monitor
