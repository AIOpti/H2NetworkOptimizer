"""
Sample Data & Time-Series Generator
=====================================
Generates realistic operational profiles for testing the H₂ optimizer
across different time periods and operating conditions.

Usage:
    python data_generator.py              # generate 24-hour profile & run
    python data_generator.py --hours 168  # 7-day profile
"""

import argparse
import json
import math
import random
from typing import Dict, List, Tuple
from network_config import build_default_network, HydrogenNetwork


def generate_demand_profile(
    network: HydrogenNetwork,
    hours: int = 24,
    seed: int = 42,
) -> List[Dict[str, float]]:
    """
    Generate hourly demand factors for each consumer.

    Models:
      - Diurnal pattern (lower at night, ramp up in morning)
      - Random perturbations (±5–10%)
      - Occasional step-changes (unit start/stop)

    Returns list of dicts, one per hour, mapping consumer ID → demand factor.
    """
    rng = random.Random(seed)
    profiles = []

    for h in range(hours):
        hour_of_day = h % 24
        factors = {}

        for cid, con in network.consumers.items():
            # Base diurnal pattern
            diurnal = 0.85 + 0.15 * math.sin(math.pi * (hour_of_day - 6) / 12)
            diurnal = max(0.70, min(1.15, diurnal))

            # Random noise
            noise = rng.gauss(1.0, 0.03)

            # Occasional step-changes (2% chance per hour per consumer)
            step = 1.0
            if rng.random() < 0.02:
                step = rng.choice([0.5, 0.7, 1.2, 1.3])

            factor = diurnal * noise * step
            factor = max(con.demand_min / con.demand_nominal,
                         min(con.demand_max / con.demand_nominal, factor))
            factors[cid] = round(factor, 3)

        profiles.append(factors)

    return profiles


def generate_availability_schedule(
    network: HydrogenNetwork,
    hours: int = 24,
    seed: int = 123,
) -> List[List[str]]:
    """
    Generate hourly list of forced-off producers (maintenance events).

    Models planned maintenance windows (4–8 hour blocks) with low probability.

    Returns list of lists, one per hour, containing producer IDs that are offline.
    """
    rng = random.Random(seed)
    schedule: List[List[str]] = [[] for _ in range(hours)]

    for pid in network.producers:
        # 10% chance of a maintenance event in the period
        if rng.random() < 0.10:
            start = rng.randint(0, max(0, hours - 8))
            duration = rng.randint(4, 8)
            for h in range(start, min(start + duration, hours)):
                schedule[h].append(pid)

    return schedule


def generate_cost_variation(
    network: HydrogenNetwork,
    hours: int = 24,
    seed: int = 99,
) -> List[Dict[str, float]]:
    """
    Generate hourly variable-cost multipliers per producer.

    Models fuel / electricity price fluctuations:
      - Natural gas price ±15% diurnal swing (affects SMRs)
      - Electricity price ±30% diurnal swing (affects electrolyser)
      - By-products stable (±2%)
    """
    rng = random.Random(seed)
    profiles = []

    for h in range(hours):
        hour_of_day = h % 24
        costs = {}

        for pid, prod in network.producers.items():
            if prod.type == "SMR":
                # Gas price peaks in evening heating hours
                swing = 1.0 + 0.15 * math.sin(math.pi * (hour_of_day - 18) / 12)
                costs[pid] = round(prod.variable_cost * swing * rng.gauss(1.0, 0.02), 4)
            elif prod.type == "Electrolyser":
                # Electricity cheap at night, expensive afternoon
                swing = 1.0 + 0.30 * math.sin(math.pi * (hour_of_day - 14) / 12)
                costs[pid] = round(prod.variable_cost * swing * rng.gauss(1.0, 0.03), 4)
            else:
                costs[pid] = round(prod.variable_cost * rng.gauss(1.0, 0.01), 4)

        profiles.append(costs)

    return profiles


def generate_full_scenario_set(hours: int = 24, seed: int = 42) -> dict:
    """
    Generate a complete set of time-varying inputs for multi-period testing.
    """
    network = build_default_network()
    return {
        "hours": hours,
        "demand_factors": generate_demand_profile(network, hours, seed),
        "forced_off": generate_availability_schedule(network, hours, seed + 1),
        "cost_variations": generate_cost_variation(network, hours, seed + 2),
    }


# ── Rolling-Horizon Simulation ─────────────────────────────────────────────

def run_rolling_horizon(hours: int = 24, seed: int = 42, verbose: bool = True):
    """
    Simulate rolling-horizon dispatch over the given number of hours.
    Solves one MIP per hour with time-varying demands and availability.
    """
    from optimizer import optimize_dispatch

    network = build_default_network()
    data = generate_full_scenario_set(hours, seed)

    total_cost = 0.0
    results = []

    for h in range(hours):
        demand_factors = data["demand_factors"][h]
        forced_off = data["forced_off"][h]

        result = optimize_dispatch(
            network,
            demand_factors=demand_factors,
            forced_off=forced_off,
        )

        total_cost += result.objective_value
        results.append({
            "hour": h,
            "status": result.status,
            "cost": round(result.objective_value, 2),
            "production": round(result.total_production_cost, 2),
            "import": round(result.total_import_cost, 2),
            "unmet_penalty": round(result.total_unmet_penalty, 2),
            "producers_on": sum(1 for v in result.producer_on.values() if v),
            "forced_off": forced_off,
        })

        if verbose:
            off_str = f" [offline: {','.join(forced_off)}]" if forced_off else ""
            unmet_str = f" ⚠ UNMET ${result.total_unmet_penalty:.0f}" if result.total_unmet_penalty > 0 else ""
            print(f"  Hour {h:3d}:  ${result.objective_value:>8,.2f}/h  "
                  f"({result.status}){off_str}{unmet_str}")

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Total cost over {hours}h:  ${total_cost:,.2f}")
        print(f"  Average hourly cost:     ${total_cost/hours:,.2f}")
        print(f"{'='*50}")

    return results, total_cost


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="H2 Network Data Generator")
    parser.add_argument("--hours", type=int, default=24, help="Number of hours to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--export-json", action="store_true", help="Export scenario data to JSON")
    parser.add_argument("--simulate", action="store_true", help="Run rolling-horizon simulation")
    args = parser.parse_args()

    if args.export_json:
        data = generate_full_scenario_set(args.hours, args.seed)
        with open("scenario_data.json", "w") as f:
            json.dump(data, f, indent=2)
        print(f"Exported {args.hours}-hour scenario to scenario_data.json")

    if args.simulate:
        print(f"\nRunning {args.hours}-hour rolling-horizon simulation...\n")
        run_rolling_horizon(args.hours, args.seed)
    elif not args.export_json:
        # Default: show sample data
        net = build_default_network()
        profile = generate_demand_profile(net, 24, args.seed)
        print("Sample 24h demand factors for Hydrocracker (C-HCK):")
        for h, factors in enumerate(profile):
            bar = "█" * int(factors["C-HCK"] * 30)
            print(f"  {h:2d}:00  {factors['C-HCK']:.3f}  {bar}")
