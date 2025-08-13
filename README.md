# First Responder Wellness Grant Finder

Simple, static site that lists grants for first-responder **wellness programs**, **psychological evaluations (pre-employment)**, **critical incident stress debriefing**, and **fitness for duty**.

- **Auto-updates daily** via GitHub Actions (no API keys).
- **Sources (initial):**
  - DHS Science & Technology FRG Grants: https://www.dhs.gov/science-and-technology/frg-grants
  - Ohio Fire Chiefs Association news (historical + future): http://www.ohiofirechiefs.com/
  - Ohio First Responder Recruitment, Retention, and Resilience program pages (state site)

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python fetch.py
# opens data/grants.json; then open docs/index.html in a browser (or run a simple http server)
