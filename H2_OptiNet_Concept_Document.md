# H2 OptiNet — AI-Driven Hydrogen Network Optimization System

## Concept Document v1.0

**Project:** H2 OptiNet
**Date:** March 2026
**Classification:** Technical Concept & Design Basis
**Author:** Process Engineering / Digital Transformation Team

---

## 1. Executive Summary

H2 OptiNet is an AI-driven optimization system that employs Mixed Integer Programming (MIP) to minimize the total operating cost of a refinery-scale hydrogen network. The system continuously optimizes hydrogen production, purification, and dispatch across multiple assets with heterogeneous cost structures, capacities, and product purities.

The pilot deployment targets a medium-scale network consisting of five production units (two steam methane reformers, one PEM electrolyser, and two by-product hydrogen sources), two purification assets (PSA and membrane), ten downstream consumer units, and two external tie-in points. The optimizer solves for the minimum-cost dispatch that satisfies all demand, purity, and pressure constraints while respecting asset operating limits.

Key business outcomes targeted by the pilot include a 5–12% reduction in hydrogen production cost through merit-order dispatch optimization, a 15–25% reduction in external hydrogen imports by maximizing use of low-cost by-product sources, improved scenario response time from hours of manual calculation to sub-minute automated dispatch recommendations, and a unified decision-support dashboard accessible to operators, engineers, and management.

---

## 2. Business Context and Objectives

### 2.1 Problem Statement

Hydrogen networks in modern refineries are operated largely by manual dispatch decisions based on operator experience. This approach leaves significant value on the table because the merit order of sources changes with feed gas prices, electricity tariffs, and unit availability. Manual balancing cannot keep pace with real-time cost fluctuations, outage events, or demand surges on downstream units.

### 2.2 Objectives

The primary objectives are to automate real-time dispatch optimization using a rigorous MIP formulation, to provide operators with scenario analysis tools for maintenance planning and demand forecasting, and to build a scalable platform that can extend from the pilot network to multi-site optimization in future phases.

### 2.3 Success Criteria

The pilot will be considered successful when it achieves a measurable cost reduction validated against a 90-day baseline period, solver execution time under 10 seconds for single-period dispatch, user adoption by at least three distinct stakeholder roles (operator, process engineer, planning engineer), and system uptime exceeding 99% over the pilot period.

---

## 3. Hydrogen Network Description

### 3.1 Network Topology

The reference network models a medium-complexity refinery hydrogen system with three pressure tiers and a total installed production capacity of 120,000 Nm³/h against a nominal demand of approximately 83,400 Nm³/h.

**Producers:**

| Unit ID  | Name                          | Type         | Capacity (Nm³/h) | Purity (mol%) | Variable Cost ($/Nm³) | CO₂ Intensity |
|----------|-------------------------------|--------------|-------------------|----------------|----------------------|---------------|
| SMR-1    | Steam Methane Reformer #1     | SMR          | 8,000 – 50,000    | 75.0           | 0.035                | 0.27 kg/Nm³   |
| SMR-2    | Steam Methane Reformer #2     | SMR          | 5,000 – 35,000    | 76.0           | 0.038                | 0.26 kg/Nm³   |
| ELEC-1   | PEM Electrolyser              | Electrolyser | 1,000 – 15,000    | 99.99          | 0.065                | 0.02 kg/Nm³   |
| BYP-CCR  | CCR By-product H₂             | By-product   | 3,000 – 12,000    | 82.0           | 0.010                | 0 (allocated) |
| BYP-ETH  | Ethylene Cracker Off-gas H₂   | By-product   | 2,000 – 8,000     | 70.0           | 0.008                | 0 (allocated) |

**Purification Assets:**

| Unit ID | Name                     | Type     | Capacity (Nm³/h) | Recovery | Product Purity |
|---------|--------------------------|----------|-------------------|----------|----------------|
| PSA-1   | Pressure Swing Adsorption| PSA      | 60,000            | 85%      | 99.9 mol%      |
| MEM-1   | Membrane Separator       | Membrane | 25,000            | 92%      | 98.0 mol%      |

**Consumers (10 process units):** The downstream consumers include hydro-desulphurisation units, a hydrocracker, hydrotreaters, an isomerisation unit, and specialty hydrogen users. Combined nominal demand is 83,400 Nm³/h with individual purity requirements ranging from 95% to 99.9% H₂.

**External Tie-ins:**

| Tie-In | Direction | Capacity    | Purity | Cost       |
|--------|-----------|-------------|--------|------------|
| IMP-1  | Import    | 20,000 Nm³/h| 99.5%  | $0.075/Nm³ |
| EXP-1  | Export    | 10,000 Nm³/h| 98.0%  | –$0.025/Nm³|

### 3.2 Header System

Hydrogen flows through three principal headers: an HP Header (45 barg) collecting output from all producers except the electrolyser, a UHP Header carrying ultra-high purity product from the PSA, the electrolyser, and external imports, and an HPC Header distributing membrane-purified hydrogen to moderate-purity consumers and the export connection.

### 3.3 Merit Order

Under nominal conditions, the economic merit order (cheapest first) is: BYP-ETH ($0.008) → BYP-CCR ($0.010) → SMR-1 ($0.035) → SMR-2 ($0.038) → ELEC-1 ($0.065). External import at $0.075/Nm³ is the marginal source.

---

## 4. System Architecture

### 4.1 Architecture Overview

The system follows a three-tier architecture: a Data Layer that ingests real-time process data, an Optimization Layer that formulates and solves the MIP dispatch problem, and a Presentation Layer that serves results to users via a web dashboard and API.

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│   Web Dashboard (HTML/JS)  ←→  REST API (Flask)             │
│   Scenario Manager  |  KPI Panels  |  Network Visualisation │
└──────────────────────────┬──────────────────────────────────┘
                           │ JSON/REST
┌──────────────────────────┴──────────────────────────────────┐
│                   OPTIMIZATION LAYER                         │
│   MIP Formulation (PuLP)  →  CBC Solver                     │
│   Scenario Engine  |  Sensitivity Analyzer                   │
│   Network Config   |  Constraint Builder                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ Data Models
┌──────────────────────────┴──────────────────────────────────┐
│                      DATA LAYER                              │
│   network_config.py (asset metadata & topology)              │
│   Real-time OPC-UA / Historian interface (future phase)      │
│   Demand forecasting module (future phase)                   │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Technology Stack

| Component           | Technology                                  | Rationale                                                    |
|---------------------|---------------------------------------------|--------------------------------------------------------------|
| Optimization Engine | Python 3.10+ / PuLP with CBC solver         | Open-source, production-grade MIP solver, easy Gurobi swap   |
| API Server          | Flask (Python)                              | Lightweight, well-documented, easy to deploy                 |
| Dashboard           | Single-file HTML + vanilla JS               | Zero build step, runs in any browser, easy to embed          |
| Data Configuration  | Python dataclasses (`network_config.py`)    | Type-safe, self-documenting, version-controllable            |
| Deployment          | Docker container or direct Python venv      | Portable across Windows/Linux control room machines          |

### 4.3 Module Structure

```
h2-optinet/
├── network_config.py    # Network topology, asset data, constraints
├── optimizer.py         # MIP formulation, solver interface, scenarios
├── app.py               # Flask API server
├── dashboard.html       # Web dashboard (single-file, self-contained)
├── data_generator.py    # Sample data & time-series generator
├── requirements.txt     # Python dependencies
└── README.md            # Setup & usage instructions
```

---

## 5. Optimization Model

### 5.1 Problem Formulation

The dispatch problem is formulated as a Mixed Integer Program minimizing total hourly operating cost subject to physical and operational constraints.

**Decision Variables:**

- x_prod[p] ∈ ℝ⁺ — hydrogen production rate at producer p (Nm³/h)
- y_on[p] ∈ {0, 1} — binary on/off status for producer p
- x_pur[u] ∈ ℝ⁺ — feed rate to purifier u (Nm³/h)
- x_con[c] ∈ ℝ⁺ — hydrogen supplied to consumer c (Nm³/h)
- x_unmet[c] ∈ ℝ⁺ — unmet demand slack at consumer c (Nm³/h)
- x_imp[e], x_exp[e] ∈ ℝ⁺ — import/export flows (Nm³/h)

**Objective Function:**

```
Minimize Z = Σ_p (cost_p × x_prod[p])          # production cost
           + Σ_e (cost_e × x_imp[e])            # import cost
           + Σ_e (cost_e × x_exp[e])            # export revenue (negative cost)
           + Σ_p (startup_p / T × y_on[p])      # amortised startup
           + Σ_c (penalty_c × x_unmet[c])       # unmet demand penalty
```

where T is the startup amortisation horizon (default 8 hours).

**Constraints:**

1. Producer capacity linking: `capacity_min[p] × y_on[p] ≤ x_prod[p] ≤ capacity_max[p] × y_on[p]`
2. Purifier capacity: `x_pur[u] ≤ capacity_max[u]`
3. Import/export limits: `x_imp[e] ≤ cap_imp[e]`, `x_exp[e] ≤ cap_exp[e]`
4. Demand satisfaction: `x_con[c] + x_unmet[c] = demand_nominal[c] × factor[c]`
5. Non-curtailability: `x_unmet[c] = 0` for priority-1 consumers
6. Mass balance at HP Header: `Σ(production from SMRs + by-products) = Σ(purifier feeds)`
7. Mass balance at UHP Header: `PSA recovery × PSA feed + electrolyser + imports = Σ(UHP consumers)`
8. Mass balance at HPC Header: `Membrane recovery × membrane feed = Σ(HPC consumers) + exports`

### 5.2 Solver Configuration

The default solver is COIN-OR CBC (open-source), configured with a 0.5% MIP gap tolerance and a 60-second time limit. The architecture supports a seamless upgrade path to Gurobi or CPLEX by changing a single solver parameter.

### 5.3 Scenario Engine

The system supports pre-defined and custom scenarios: base-case nominal dispatch, individual and combined producer outages, demand surge scenarios on specific consumers or globally, and import/export unavailability.

---

## 6. Data Architecture

### 6.1 Current Phase (Pilot)

During the pilot, all asset data is defined in `network_config.py` using Python dataclasses. This provides a single source of truth for the network topology that is version-controllable, type-safe, and easily auditable.

### 6.2 Future Phase (OT Integration)

The production system will integrate with the site's OPC-UA infrastructure and process historian to receive real-time flow rates, temperatures, pressures, and unit statuses. A data adapter module will map historian tags to the network model parameters, enabling closed-loop optimization.

### 6.3 API Specification

| Endpoint            | Method | Description                              |
|---------------------|--------|------------------------------------------|
| /api/network        | GET    | Network topology and asset metadata      |
| /api/optimize       | GET    | Base-case dispatch optimization          |
| /api/optimize       | POST   | Custom dispatch with demand factors      |
| /api/scenario       | POST   | Run a named scenario                     |
| /api/sensitivity    | GET    | Full sensitivity analysis                |
| /api/merit-order    | GET    | Producer merit order                     |

---

## 7. Dashboard Design

The web dashboard is a single-file HTML application with no build step required. It provides KPI summary cards showing total cost, production cost, import cost, export revenue, and unmet demand penalty. The cost breakdown bar visualizes the relative contribution of each cost component. Producer and consumer tables show dispatch status, flow rates, and loading percentages. Purifier and external flow panels provide real-time utilisation data. A CO₂ summary panel calculates emissions based on producer dispatch and intensity factors. The sidebar offers one-click scenario selection with instant re-optimization.

The dashboard operates in two modes: connected mode (served by Flask, calling the API for live optimization) and demo mode (opened directly as a file, using built-in sample data for demonstration).

---

## 8. Deployment Strategy

### 8.1 Pilot Deployment

The pilot runs as a standalone Python application on a designated control room workstation or engineering server. Dependencies are managed via pip and a requirements.txt file. The Flask server hosts both the API and the dashboard on port 5000.

### 8.2 Production Deployment

For production, the system will be containerised using Docker with an Nginx reverse proxy, connected to the site's OPC-UA infrastructure, monitored via standard IT health-check endpoints, and backed by a PostgreSQL database for historical dispatch records and audit trails.

---

## 9. Roadmap

| Phase | Scope | Timeline |
|-------|-------|----------|
| Phase 1 (Pilot) | Static network model, manual data, web dashboard, scenario analysis | Current |
| Phase 2 | OPC-UA integration, real-time data, historian connection | +3 months |
| Phase 3 | Rolling-horizon multi-period optimization, demand forecasting | +6 months |
| Phase 4 | Maintenance scheduling integration, production planning | +9 months |
| Phase 5 | Multi-site optimization, energy market integration | +12 months |

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Solver performance degrades with network growth | Medium | High | Pre-validate with larger test networks; Gurobi upgrade path |
| Real-time data quality issues | High | Medium | Data validation layer with fallback to last-known-good values |
| Operator trust / adoption resistance | Medium | High | Operator-in-the-loop design; recommendations not automation |
| Model constraints don't capture all real physics | Medium | Medium | Iterative refinement with process engineers; audit cycle |

---

## Appendix A — Glossary

| Term | Definition |
|------|-----------|
| MIP | Mixed Integer Program — optimization with continuous and binary variables |
| PSA | Pressure Swing Adsorption — high-purity hydrogen separation technology |
| SMR | Steam Methane Reformer — primary hydrogen production unit |
| CCR | Continuous Catalytic Reformer — naphtha reforming unit producing by-product H₂ |
| Nm³/h | Normal cubic metres per hour (standard flow rate at 0°C, 1 atm) |
| Merit order | Ranking of sources from cheapest to most expensive variable cost |
| UHP | Ultra-High Purity (>99.9 mol% H₂) |
| HPC | High Purity Clean (>97 mol% H₂, membrane-grade) |
