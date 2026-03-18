# H2 OptiNet — Hydrogen Network Optimization System

AI-driven Mixed Integer Programming (MIP) system for optimal hydrogen dispatch across a refinery-scale network.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the optimization server
python app.py

# 3. Open dashboard
#    Navigate to http://localhost:5000 in your browser
```

## Standalone Usage (no server)

```bash
# Run base-case optimization directly
python optimizer.py

# Generate sample data and run 24-hour simulation
python data_generator.py --simulate

# Export scenario data to JSON
python data_generator.py --export-json --hours 168
```

## Dashboard (Demo Mode)

Open `dashboard.html` directly in a browser — it works without the server using built-in demo data. When served by Flask, it connects to the live optimization API.

## Project Structure

| File | Description |
|------|-------------|
| `network_config.py` | Hydrogen network topology, asset data, constraints |
| `optimizer.py` | MIP formulation (PuLP/CBC), solver interface, scenarios |
| `app.py` | Flask REST API server |
| `dashboard.html` | Interactive web dashboard (single-file) |
| `data_generator.py` | Time-series data generator, rolling-horizon simulator |
| `H2_OptiNet_Concept_Document.md` | Full concept & design document |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/network` | GET | Network topology & asset metadata |
| `/api/optimize` | GET | Base-case dispatch |
| `/api/optimize` | POST | Custom dispatch (demand factors, forced-off) |
| `/api/scenario` | POST | Run named scenario |
| `/api/sensitivity` | GET | All scenarios at once |
| `/api/merit-order` | GET | Producer cost ranking |

## Network Overview

- **5 producers**: 2 SMR, 1 electrolyser, 2 by-product sources
- **2 purifiers**: PSA (99.9% purity), membrane (98% purity)
- **10 consumers**: Refinery process units with varying purity needs
- **2 external tie-ins**: Import pipeline, export header
- **Total capacity**: 120,000 Nm³/h | **Nominal demand**: 83,400 Nm³/h
