# NYC Tenant Insights

A Streamlit app that helps renters evaluate Manhattan buildings before signing a lease, using real NYC 311 complaint data and Zillow rent trends.

## Features

- Search any Manhattan address in the dataset
- See building complaint count and risk percentile
- AI-powered tenant summary (powered by Claude claude-sonnet-4-5)
- Rent trend chart for the building's ZIP code (last 2 years)

## Setup

1. Install dependencies:
   ```bash
   pip install streamlit pandas anthropic
   ```

2. Set your Anthropic API key:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```

3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Data Sources

- NYC 311 building complaints
- Zillow Observed Rent Index (ZORI)
- Manhattan ZIP code rent and complaint aggregates
