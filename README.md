# Goalkeeper Analysis Dashboard

A web-based goalkeeper analysis tool built on [StatsBomb open data](https://github.com/statsbomb/open-data) that combines data pipeline engineering with competitive goalkeeping domain knowledge.

> **Status:** In development. Pipeline foundation (Milestone 1) underway.

## What This Does

Takes raw match event data from professional soccer competitions and transforms it into interactive goalkeeper performance analysis across three dimensions:

- **Shot stopping** — where shots came from, where they ended up on the goal frame, how the keeper responded, and what the expected goals model says about their performance
- **Distribution** — how the keeper plays the ball out, completion rates by pass type and length, directional tendencies
- **Sweeping & claiming** — how far the keeper operates from goal, how often they come for crosses, success rates on aerial challenges

Each view includes tactical annotations that interpret the data from a goalkeeper's perspective — not just what the numbers are, but what they mean for a coaching staff evaluating performance.

## Architecture

```
StatsBomb open data (JSON)
        │
   Python pipeline
   (ingest → extract → compute → serialize)
        │
   Pre-computed JSON
        │
   Next.js frontend
   (interactive dashboard)
```

The pipeline processes raw event data into pre-computed JSON files that the frontend reads statically. No database, no API server — the data is small enough that pre-computation keeps the architecture simple and the deployment free.

## Tech Stack

**Pipeline:** Python, pandas, mplsoccer, pytest
**Frontend:** Next.js, React, Tailwind, Recharts
**CI/CD:** GitHub Actions
**Hosting:** Vercel

## Running Locally

### Pipeline

```bash
cd data-pipeline
pip install -r requirements.txt
python 01_ingest.py
python 02_extract_gk_events.py
python 03_compute_metrics.py
python 04_generate_viz_data.py

# Run tests
pytest tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Data Attribution

This project uses [StatsBomb open data](https://github.com/statsbomb/open-data), provided free for non-commercial use under the [StatsBomb Public Data License](https://github.com/statsbomb/open-data/blob/master/LICENSE.pdf).

Built by [Hagen Carriere](https://hagen-carriere.github.io).
