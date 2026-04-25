# NYC Tenant Insights

A Zillow plugin prototype that surfaces real housing complaint and violation data so renters know what they're signing up for — before they sign the lease.

Built for the CUNY AI Innovation Challenge 2026 (AI Data Science track, Housing & Urban Communities theme).

---

## The Problem

Apartment listings show you the price, the photos, and the floor plan. They don't show you the 451 housing complaints filed by tenants last year, the 15 open HPD violations, or the fact that the heat goes out every winter. That data exists — NYC publishes it — but renters never see it.

## Our Solution

NYC Tenant Insights merges three public datasets into a single tool that grades every Manhattan building A through F based on housing quality. Pick any address and instantly see:

- Building Grade (A–F) based on complaint volume, severity-weighted violations, and unresolved issues
- Visual comparisons vs. ZIP code and Manhattan averages
- Violation severity breakdown (Class A / B / C, with NYC HPD definitions)
- AI-generated risk summary powered by Anthropic Claude
- Recency signals — last complaint, last violation, open issues

## Data Sources

- NYC 311 Housing Complaints (HPD agency, 2025) — data.cityofnewyork.us
- NYC HPD Housing Maintenance Code Violations (2024–2025) — data.cityofnewyork.us
- Zillow Observed Rent Index (ZORI) — ZIP-level rent data, monthly

## Tech Stack

- Python 3.14, pandas for data processing
- Streamlit for the interactive web app
- Anthropic Claude (claude-sonnet-4-5) for grounded AI analysis
- NYC Open Data SoQL API for filtered data ingestion

## How to Run

1. Clone the repo:
   \`\`\`
   git clone https://github.com/jb0289/nyc-tenant-insights.git
   cd nyc-tenant-insights
   \`\`\`

2. Install dependencies:
   \`\`\`
   pip install streamlit pandas anthropic
   \`\`\`

3. Set your Anthropic API key:
   \`\`\`
   export ANTHROPIC_API_KEY="your_key_here"
   \`\`\`

4. Run the data prep (one-time):
   \`\`\`
   python3 prep_data.py
   \`\`\`

5. Launch the app:
   \`\`\`
   streamlit run app.py
   \`\`\`

## Project Structure

\`\`\`
nyc-tenant-insights/
├── app.py            Streamlit web app
├── prep_data.py      Data cleaning + grading pipeline
├── data/             Raw and processed CSVs (gitignored)
└── README.md
\`\`\`

## Team

- John Berich
- Joe Britton
- Summer Morrison
- Yangmei Lu

## Links

- Live App: https://nyc-tenant-insights-5gh64ejvqu9mauzgikwshs.streamlit.app/
- Zillow Plugin Mockup: https://grand-sprinkles-48b9ea.netlify.app/
- Pitch Video: https://www.youtube.com/watch?v=4FoYHdaBBC8
- Slide Deck: [Google Slides link]

## License & Attribution

Built with public data from NYC Open Data and Zillow Research. Educational / hackathon use only.
