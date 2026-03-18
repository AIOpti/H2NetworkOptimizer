"""
Hydrogen Network Configuration
==============================
Defines the hypothetical medium-scale hydrogen network topology for the
AI-driven H2 optimization system.  This module is the single source of truth
for every asset, connection, and operating constraint in the network.

Network comprises:
  * 5 Production units (2 SMR, 1 Electrolyser, 2 By-product sources)
  * 2 Purification assets (1 PSA, 1 Membrane)
  * 10 Consumer nodes (refinery process units)
  * 2 External tie-ins (import pipeline, export header)

All flow rates in Nm³/h, costs in $/Nm³, pressures in barg.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class Producer:
    """Hydrogen production unit."""
    id: str
    name: str
    type: str                        # SMR | Electrolyser | ByProduct
    capacity_min: float              # Nm³/h  – minimum stable output
    capacity_max: float              # Nm³/h  – nameplate capacity
    purity: float                    # mol-% H₂ at battery limit
    variable_cost: float             # $/Nm³  – fuel / power / feed cost
    startup_cost: float              # $      – cold-start penalty
    ramp_rate: float                 # Nm³/h per minute
    pressure_out: float              # barg   – delivery pressure
    availability: float = 1.0        # 0-1    – planned availability factor
    co2_intensity: float = 0.0       # kg CO₂ / Nm³ H₂


@dataclass
class Purifier:
    """Hydrogen purification asset (PSA / Membrane)."""
    id: str
    name: str
    type: str                        # PSA | Membrane
    capacity_max: float              # Nm³/h  – max feed rate
    recovery: float                  # 0-1    – H₂ recovery fraction
    product_purity: float            # mol-%  – guaranteed outlet purity
    feed_purity_min: float           # mol-%  – minimum acceptable feed
    variable_cost: float             # $/Nm³ feed
    pressure_drop: float             # bar    – across the unit


@dataclass
class Consumer:
    """Hydrogen consuming process unit."""
    id: str
    name: str
    demand_min: float                # Nm³/h  – contractual minimum
    demand_max: float                # Nm³/h  – peak demand
    demand_nominal: float            # Nm³/h  – normal operating demand
    purity_required: float           # mol-%  – minimum acceptable purity
    pressure_required: float         # barg   – minimum supply pressure
    priority: int = 1                # 1 (highest) … 5 (lowest)
    curtailable: bool = False        # can demand be curtailed?
    penalty_unmet: float = 0.0       # $/Nm³  – cost of unmet demand


@dataclass
class ExternalTieIn:
    """Import pipeline or export header."""
    id: str
    name: str
    direction: str                   # Import | Export
    capacity_max: float              # Nm³/h
    purity: float                    # mol-%
    cost: float                      # $/Nm³  (positive = cost, negative = revenue)
    pressure: float                  # barg
    available: bool = True


@dataclass
class PipeSegment:
    """A directed pipe connection between two nodes."""
    id: str
    from_node: str
    to_node: str
    capacity_max: float              # Nm³/h
    pressure_drop: float             # bar
    length_m: float = 0.0            # metres (for loss calc)


@dataclass
class HydrogenNetwork:
    """Complete network topology."""
    producers: Dict[str, Producer] = field(default_factory=dict)
    purifiers: Dict[str, Purifier] = field(default_factory=dict)
    consumers: Dict[str, Consumer] = field(default_factory=dict)
    external: Dict[str, ExternalTieIn] = field(default_factory=dict)
    pipes: List[PipeSegment] = field(default_factory=list)


# ── Network Builder ─────────────────────────────────────────────────────────

def build_default_network() -> HydrogenNetwork:
    """
    Construct the reference medium-scale hydrogen network.

    Topology sketch (simplified):

        SMR-1 ──────┐
        SMR-2 ──────┤
        ELEC-1 ─────┤──► HP Header (45 barg) ──► PSA-1 ──► UHP Header
        BYP-CCR ────┤                         └──► MEM-1 ──► HP Clean
        BYP-ETH ────┘
                     │
        IMP-1 ──────►│ LP Header (25 barg) ──► Consumers C1–C10
                     │
                     └──► EXP-1 (excess sales)
    """
    net = HydrogenNetwork()

    # ── Producers ───────────────────────────────────────────────────────
    net.producers = {
        "SMR-1": Producer(
            id="SMR-1", name="Steam Methane Reformer #1", type="SMR",
            capacity_min=8_000, capacity_max=50_000,
            purity=75.0, variable_cost=0.035, startup_cost=15_000,
            ramp_rate=200, pressure_out=45.0,
            co2_intensity=0.27,
        ),
        "SMR-2": Producer(
            id="SMR-2", name="Steam Methane Reformer #2", type="SMR",
            capacity_min=5_000, capacity_max=35_000,
            purity=76.0, variable_cost=0.038, startup_cost=12_000,
            ramp_rate=180, pressure_out=45.0,
            co2_intensity=0.26,
        ),
        "ELEC-1": Producer(
            id="ELEC-1", name="PEM Electrolyser", type="Electrolyser",
            capacity_min=1_000, capacity_max=15_000,
            purity=99.99, variable_cost=0.065, startup_cost=500,
            ramp_rate=500, pressure_out=30.0,
            co2_intensity=0.02,
        ),
        "BYP-CCR": Producer(
            id="BYP-CCR", name="CCR By-product H₂", type="ByProduct",
            capacity_min=3_000, capacity_max=12_000,
            purity=82.0, variable_cost=0.010, startup_cost=0,
            ramp_rate=50, pressure_out=20.0,
            co2_intensity=0.0,   # allocated to main product
        ),
        "BYP-ETH": Producer(
            id="BYP-ETH", name="Ethylene Cracker Off-gas H₂", type="ByProduct",
            capacity_min=2_000, capacity_max=8_000,
            purity=70.0, variable_cost=0.008, startup_cost=0,
            ramp_rate=30, pressure_out=18.0,
            co2_intensity=0.0,
        ),
    }

    # ── Purifiers ───────────────────────────────────────────────────────
    net.purifiers = {
        "PSA-1": Purifier(
            id="PSA-1", name="Pressure Swing Adsorption #1", type="PSA",
            capacity_max=60_000, recovery=0.85,
            product_purity=99.9, feed_purity_min=65.0,
            variable_cost=0.004, pressure_drop=2.0,
        ),
        "MEM-1": Purifier(
            id="MEM-1", name="Membrane Separator #1", type="Membrane",
            capacity_max=25_000, recovery=0.92,
            product_purity=98.0, feed_purity_min=60.0,
            variable_cost=0.003, pressure_drop=5.0,
        ),
    }

    # ── Consumers ───────────────────────────────────────────────────────
    consumers_data = [
        ("C-HDS1", "Hydro-desulphurisation Unit 1",  8_000, 18_000, 14_000, 99.9, 40.0, 1, False, 0.20),
        ("C-HDS2", "Hydro-desulphurisation Unit 2",  5_000, 12_000,  9_000, 99.9, 40.0, 1, False, 0.20),
        ("C-HCK",  "Hydrocracker",                  15_000, 35_000, 28_000, 99.9, 42.0, 1, False, 0.25),
        ("C-HTR",  "Hydrotreater",                   4_000, 10_000,  7_500, 98.0, 35.0, 2, False, 0.15),
        ("C-ISO",  "Isomerisation Unit",              1_500,  4_000,  3_000, 99.0, 30.0, 2, True,  0.10),
        ("C-DHT",  "Diesel Hydrotreater",             6_000, 15_000, 11_000, 99.5, 38.0, 1, False, 0.18),
        ("C-NHT",  "Naphtha Hydrotreater",            3_000,  8_000,  5_500, 97.0, 28.0, 3, True,  0.08),
        ("C-LUB",  "Lube Oil Hydrotreater",           1_000,  3_500,  2_200, 99.0, 35.0, 3, True,  0.12),
        ("C-WAX",  "Wax Hydrofinisher",                 500,  2_000,  1_200, 98.0, 25.0, 4, True,  0.06),
        ("C-H2S",  "Amine / Claus Feed H₂",          1_000,  3_000,  2_000, 95.0, 20.0, 5, True,  0.04),
    ]
    for cid, name, dmin, dmax, dnom, pur, pres, pri, curt, pen in consumers_data:
        net.consumers[cid] = Consumer(
            id=cid, name=name,
            demand_min=dmin, demand_max=dmax, demand_nominal=dnom,
            purity_required=pur, pressure_required=pres,
            priority=pri, curtailable=curt, penalty_unmet=pen,
        )

    # ── External Tie-ins ────────────────────────────────────────────────
    net.external = {
        "IMP-1": ExternalTieIn(
            id="IMP-1", name="External Pipeline Import",
            direction="Import", capacity_max=20_000,
            purity=99.5, cost=0.075, pressure=45.0,
        ),
        "EXP-1": ExternalTieIn(
            id="EXP-1", name="Export to Neighbour Site",
            direction="Export", capacity_max=10_000,
            purity=98.0, cost=-0.025, pressure=25.0,
        ),
    }

    # ── Pipe Segments (adjacency / connectivity) ────────────────────────
    # Producer → HP Header
    for pid in ["SMR-1", "SMR-2", "BYP-CCR", "BYP-ETH"]:
        net.pipes.append(PipeSegment(
            id=f"P-{pid}-HPH", from_node=pid, to_node="HP-HEADER",
            capacity_max=net.producers[pid].capacity_max, pressure_drop=0.5,
        ))
    # Electrolyser → UHP header (already high purity)
    net.pipes.append(PipeSegment(
        id="P-ELEC1-UHP", from_node="ELEC-1", to_node="UHP-HEADER",
        capacity_max=15_000, pressure_drop=0.5,
    ))
    # HP Header → Purifiers
    net.pipes.append(PipeSegment(
        id="P-HPH-PSA1", from_node="HP-HEADER", to_node="PSA-1",
        capacity_max=60_000, pressure_drop=0.2,
    ))
    net.pipes.append(PipeSegment(
        id="P-HPH-MEM1", from_node="HP-HEADER", to_node="MEM-1",
        capacity_max=25_000, pressure_drop=0.2,
    ))
    # Purifiers → UHP / HP-Clean headers
    net.pipes.append(PipeSegment(
        id="P-PSA1-UHP", from_node="PSA-1", to_node="UHP-HEADER",
        capacity_max=51_000, pressure_drop=0.3,
    ))
    net.pipes.append(PipeSegment(
        id="P-MEM1-HPC", from_node="MEM-1", to_node="HPC-HEADER",
        capacity_max=23_000, pressure_drop=0.3,
    ))
    # Import → UHP Header
    net.pipes.append(PipeSegment(
        id="P-IMP1-UHP", from_node="IMP-1", to_node="UHP-HEADER",
        capacity_max=20_000, pressure_drop=0.3,
    ))
    # Headers → Consumers (simplified: all high-purity consumers from UHP)
    uhp_consumers = ["C-HDS1", "C-HDS2", "C-HCK", "C-DHT", "C-ISO", "C-LUB"]
    for cid in uhp_consumers:
        net.pipes.append(PipeSegment(
            id=f"P-UHP-{cid}", from_node="UHP-HEADER", to_node=cid,
            capacity_max=net.consumers[cid].demand_max * 1.1,
            pressure_drop=1.0,
        ))
    hpc_consumers = ["C-HTR", "C-NHT", "C-WAX", "C-H2S"]
    for cid in hpc_consumers:
        net.pipes.append(PipeSegment(
            id=f"P-HPC-{cid}", from_node="HPC-HEADER", to_node=cid,
            capacity_max=net.consumers[cid].demand_max * 1.1,
            pressure_drop=1.0,
        ))
    # Export connection from HPC header
    net.pipes.append(PipeSegment(
        id="P-HPC-EXP1", from_node="HPC-HEADER", to_node="EXP-1",
        capacity_max=10_000, pressure_drop=0.5,
    ))

    return net


# ── Convenience helpers ─────────────────────────────────────────────────────

def total_production_capacity(net: HydrogenNetwork) -> float:
    return sum(p.capacity_max for p in net.producers.values())

def total_nominal_demand(net: HydrogenNetwork) -> float:
    return sum(c.demand_nominal for c in net.consumers.values())

def cheapest_source_order(net: HydrogenNetwork) -> List[str]:
    """Return producer IDs sorted by ascending variable cost (merit order)."""
    return sorted(net.producers, key=lambda pid: net.producers[pid].variable_cost)


if __name__ == "__main__":
    network = build_default_network()
    print(f"Producers:  {len(network.producers)}")
    print(f"Purifiers:  {len(network.purifiers)}")
    print(f"Consumers:  {len(network.consumers)}")
    print(f"External:   {len(network.external)}")
    print(f"Pipes:      {len(network.pipes)}")
    print(f"Total capacity:  {total_production_capacity(network):,.0f} Nm³/h")
    print(f"Nominal demand:  {total_nominal_demand(network):,.0f} Nm³/h")
    print(f"Merit order:     {cheapest_source_order(network)}")
