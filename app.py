"""
H₂ Network Optimization — Flask API Server
============================================
Provides a REST API for the web dashboard to interact with the
MIP optimization engine.

Endpoints:
  GET  /api/network          → network topology & asset metadata
  GET  /api/optimize         → run base-case dispatch
  POST /api/optimize         → run dispatch with custom parameters
  POST /api/scenario         → run a named scenario
  GET  /api/sensitivity      → run full sensitivity analysis
  GET  /api/merit-order      → return producer merit order
  GET  /                     → serve dashboard.html
"""

import json
import time
import os
from flask import Flask, jsonify, request, send_file
from network_config import (
    build_default_network, total_production_capacity, total_nominal_demand,
    cheapest_source_order,
)
from optimizer import (
    optimize_dispatch, run_base_case, run_sensitivity_analysis,
    run_outage_scenario, run_demand_surge, OptimizationResult,
)

app = Flask(__name__)
NETWORK = build_default_network()


# ── Helpers ─────────────────────────────────────────────────────────────────

def result_to_dict(res: OptimizationResult) -> dict:
    """Convert OptimizationResult to JSON-serialisable dict."""
    return {
        "status": res.status,
        "objective_value": round(res.objective_value, 2),
        "producer_flows": {k: round(v, 1) for k, v in res.producer_flows.items()},
        "producer_on": res.producer_on,
        "purifier_feeds": {k: round(v, 1) for k, v in res.purifier_feeds.items()},
        "consumer_supplied": {k: round(v, 1) for k, v in res.consumer_supplied.items()},
        "consumer_unmet": {k: round(v, 1) for k, v in res.consumer_unmet.items()},
        "import_flow": {k: round(v, 1) for k, v in res.import_flow.items()},
        "export_flow": {k: round(v, 1) for k, v in res.export_flow.items()},
        "cost_breakdown": {
            "total": round(res.objective_value, 2),
            "production": round(res.total_production_cost, 2),
            "import": round(res.total_import_cost, 2),
            "export_revenue": round(res.total_export_revenue, 2),
            "startup": round(res.total_startup_cost, 2),
            "unmet_penalty": round(res.total_unmet_penalty, 2),
        },
    }


def network_to_dict() -> dict:
    """Serialise the network topology for the dashboard."""
    net = NETWORK
    return {
        "producers": {
            pid: {
                "name": p.name, "type": p.type,
                "capacity_min": p.capacity_min, "capacity_max": p.capacity_max,
                "purity": p.purity, "variable_cost": p.variable_cost,
                "startup_cost": p.startup_cost, "co2_intensity": p.co2_intensity,
                "availability": p.availability,
            }
            for pid, p in net.producers.items()
        },
        "purifiers": {
            uid: {
                "name": u.name, "type": u.type,
                "capacity_max": u.capacity_max, "recovery": u.recovery,
                "product_purity": u.product_purity, "variable_cost": u.variable_cost,
            }
            for uid, u in net.purifiers.items()
        },
        "consumers": {
            cid: {
                "name": c.name,
                "demand_min": c.demand_min, "demand_max": c.demand_max,
                "demand_nominal": c.demand_nominal,
                "purity_required": c.purity_required, "priority": c.priority,
                "curtailable": c.curtailable, "penalty_unmet": c.penalty_unmet,
            }
            for cid, c in net.consumers.items()
        },
        "external": {
            eid: {
                "name": e.name, "direction": e.direction,
                "capacity_max": e.capacity_max, "purity": e.purity,
                "cost": e.cost,
            }
            for eid, e in net.external.items()
        },
        "summary": {
            "total_capacity": total_production_capacity(net),
            "total_nominal_demand": total_nominal_demand(net),
            "merit_order": cheapest_source_order(net),
        },
    }


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the single-page dashboard."""
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return send_file(dashboard_path)


@app.route("/api/network")
def get_network():
    return jsonify(network_to_dict())


@app.route("/api/optimize", methods=["GET"])
def optimize_get():
    """Base-case optimisation."""
    t0 = time.time()
    res = run_base_case(NETWORK)
    res.solver_time_sec = time.time() - t0
    return jsonify(result_to_dict(res))


@app.route("/api/optimize", methods=["POST"])
def optimize_post():
    """Custom optimisation with demand factors and forced-off units."""
    payload = request.get_json(force=True)
    demand_factors = payload.get("demand_factors", {})
    forced_off = payload.get("forced_off", [])

    t0 = time.time()
    res = optimize_dispatch(
        NETWORK,
        demand_factors=demand_factors,
        forced_off=forced_off,
    )
    res.solver_time_sec = time.time() - t0
    return jsonify(result_to_dict(res))


@app.route("/api/scenario", methods=["POST"])
def run_scenario():
    """Run a named scenario."""
    payload = request.get_json(force=True)
    scenario_name = payload.get("scenario", "base")

    t0 = time.time()

    if scenario_name == "base":
        res = run_base_case(NETWORK)
    elif scenario_name == "smr1_outage":
        res = run_outage_scenario(NETWORK, ["SMR-1"])
    elif scenario_name == "smr2_outage":
        res = run_outage_scenario(NETWORK, ["SMR-2"])
    elif scenario_name == "dual_smr_outage":
        res = run_outage_scenario(NETWORK, ["SMR-1", "SMR-2"])
    elif scenario_name == "hck_surge":
        res = run_demand_surge(NETWORK, {"C-HCK": 1.20})
    elif scenario_name == "global_surge":
        all_surge = {c: 1.10 for c in NETWORK.consumers}
        res = run_demand_surge(NETWORK, all_surge)
    else:
        return jsonify({"error": f"Unknown scenario: {scenario_name}"}), 400

    res.solver_time_sec = time.time() - t0
    d = result_to_dict(res)
    d["scenario"] = scenario_name
    return jsonify(d)


@app.route("/api/sensitivity")
def sensitivity():
    """Full sensitivity analysis — returns all scenario results."""
    t0 = time.time()
    results = run_sensitivity_analysis(NETWORK)
    output = {}
    for name, res in results.items():
        output[name] = result_to_dict(res)
    return jsonify({
        "scenarios": output,
        "wall_time_sec": round(time.time() - t0, 2),
    })


@app.route("/api/merit-order")
def merit_order():
    order = cheapest_source_order(NETWORK)
    return jsonify({
        "merit_order": [
            {
                "id": pid,
                "name": NETWORK.producers[pid].name,
                "variable_cost": NETWORK.producers[pid].variable_cost,
                "capacity_max": NETWORK.producers[pid].capacity_max,
                "type": NETWORK.producers[pid].type,
            }
            for pid in order
        ]
    })


# ── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  H₂ Network Optimization Server")
    print(f"  Dashboard: http://localhost:5000")
    print(f"  API:       http://localhost:5000/api/network")
    print("=" * 60)
    import os
    app.run(host="0.0.0.0", port=5000, debug=os.getenv('FLASK_ENV')=='development')
