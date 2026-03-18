"""
H₂ Network MIP Optimizer
=========================
Mixed Integer Programming engine for optimal hydrogen dispatch.

Uses PuLP with the CBC solver (open-source, ships with PuLP) to minimise
total operating cost across the hydrogen network while respecting:
  • Production capacity and ramp-rate constraints
  • Purifier feed-rate, recovery, and purity constraints
  • Consumer demand bounds and purity requirements
  • Import/export limits
  • Mass balance at every header node
  • Binary on/off status for each producer (startup costs)

The formulation is a single-period steady-state dispatch.  For multi-period
(rolling horizon) optimization, call `optimize_dispatch` for each time-step
and pass the previous solution as warm-start.
"""

from typing import Dict, Optional, Tuple
import pulp
from network_config import (
    HydrogenNetwork, build_default_network,
    Producer, Consumer, Purifier, ExternalTieIn,
)


# ── Result container ────────────────────────────────────────────────────────

class OptimizationResult:
    """Stores the solution of a single dispatch optimization."""
    def __init__(self):
        self.status: str = "Not Solved"
        self.objective_value: float = 0.0
        self.producer_flows: Dict[str, float] = {}
        self.producer_on: Dict[str, bool] = {}
        self.purifier_feeds: Dict[str, float] = {}
        self.consumer_supplied: Dict[str, float] = {}
        self.consumer_unmet: Dict[str, float] = {}
        self.import_flow: Dict[str, float] = {}
        self.export_flow: Dict[str, float] = {}
        self.header_balance: Dict[str, float] = {}
        self.total_production_cost: float = 0.0
        self.total_import_cost: float = 0.0
        self.total_export_revenue: float = 0.0
        self.total_startup_cost: float = 0.0
        self.total_unmet_penalty: float = 0.0
        self.solver_time_sec: float = 0.0

    def summary(self) -> str:
        lines = [
            f"{'='*60}",
            f"  OPTIMIZATION RESULT  —  Status: {self.status}",
            f"{'='*60}",
            f"  Objective (total cost):  ${self.objective_value:,.2f}/h",
            f"  Production cost:         ${self.total_production_cost:,.2f}/h",
            f"  Import cost:             ${self.total_import_cost:,.2f}/h",
            f"  Export revenue:          ${self.total_export_revenue:,.2f}/h",
            f"  Startup cost (amort.):   ${self.total_startup_cost:,.2f}/h",
            f"  Unmet demand penalty:    ${self.total_unmet_penalty:,.2f}/h",
            f"  Solver wall-time:        {self.solver_time_sec:.2f} s",
            f"{'─'*60}",
            f"  PRODUCER DISPATCH:",
        ]
        for pid, flow in self.producer_flows.items():
            on = "ON " if self.producer_on.get(pid) else "OFF"
            lines.append(f"    {pid:12s}  [{on}]  {flow:>10,.0f} Nm³/h")
        lines.append(f"{'─'*60}")
        lines.append(f"  PURIFIER LOADING:")
        for uid, feed in self.purifier_feeds.items():
            lines.append(f"    {uid:12s}  {feed:>10,.0f} Nm³/h feed")
        lines.append(f"{'─'*60}")
        lines.append(f"  CONSUMER SUPPLY:")
        for cid, sup in self.consumer_supplied.items():
            unmet = self.consumer_unmet.get(cid, 0)
            tag = "  *** CURTAILED" if unmet > 0.1 else ""
            lines.append(f"    {cid:12s}  {sup:>10,.0f} Nm³/h{tag}")
        lines.append(f"{'─'*60}")
        lines.append(f"  EXTERNAL FLOWS:")
        for eid, fl in {**self.import_flow, **self.export_flow}.items():
            lines.append(f"    {eid:12s}  {fl:>10,.0f} Nm³/h")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ── Optimizer ───────────────────────────────────────────────────────────────

def optimize_dispatch(
    network: HydrogenNetwork,
    demand_factors: Optional[Dict[str, float]] = None,
    forced_off: Optional[list] = None,
    max_solve_time: int = 60,
    mip_gap: float = 0.005,
) -> OptimizationResult:
    """
    Solve the single-period hydrogen dispatch MIP.

    Parameters
    ----------
    network : HydrogenNetwork
        Fully configured network from network_config.
    demand_factors : dict, optional
        Multipliers on nominal demand per consumer, e.g. {"C-HCK": 1.15}.
        Defaults to 1.0 for all consumers.
    forced_off : list, optional
        Producer IDs forced offline (maintenance / outage scenario).
    max_solve_time : int
        CBC solver time limit in seconds.
    mip_gap : float
        Acceptable MIP optimality gap (0.005 = 0.5%).

    Returns
    -------
    OptimizationResult
    """
    result = OptimizationResult()
    demand_factors = demand_factors or {}
    forced_off = forced_off or []

    # Amortise startup cost over 8-hour horizon
    STARTUP_AMORT_HOURS = 8.0

    # ── Sets ────────────────────────────────────────────────────────────
    P = list(network.producers.keys())
    U = list(network.purifiers.keys())
    C = list(network.consumers.keys())
    IMP = [e for e in network.external if network.external[e].direction == "Import"]
    EXP = [e for e in network.external if network.external[e].direction == "Export"]

    # ── Problem ─────────────────────────────────────────────────────────
    prob = pulp.LpProblem("H2_Network_Dispatch", pulp.LpMinimize)

    # ── Decision Variables ──────────────────────────────────────────────
    # Producer flow (continuous) and on/off (binary)
    x_prod = {p: pulp.LpVariable(f"x_prod_{p}", lowBound=0) for p in P}
    y_on   = {p: pulp.LpVariable(f"y_on_{p}", cat="Binary") for p in P}

    # Purifier feed flow
    x_pur = {u: pulp.LpVariable(f"x_pur_{u}", lowBound=0) for u in U}

    # Consumer supplied flow and unmet (slack)
    x_con   = {c: pulp.LpVariable(f"x_con_{c}", lowBound=0) for c in C}
    x_unmet = {c: pulp.LpVariable(f"x_unmet_{c}", lowBound=0) for c in C}

    # Import / Export flows
    x_imp = {e: pulp.LpVariable(f"x_imp_{e}", lowBound=0) for e in IMP}
    x_exp = {e: pulp.LpVariable(f"x_exp_{e}", lowBound=0) for e in EXP}

    # ── Objective Function ──────────────────────────────────────────────
    # Minimise:  production cost + import cost - export revenue
    #          + amortised startup cost + unmet demand penalty
    prod_cost = pulp.lpSum(
        network.producers[p].variable_cost * x_prod[p] for p in P
    )
    import_cost = pulp.lpSum(
        network.external[e].cost * x_imp[e] for e in IMP
    )
    export_revenue = pulp.lpSum(
        network.external[e].cost * x_exp[e] for e in EXP  # cost is negative
    )
    startup_cost = pulp.lpSum(
        (network.producers[p].startup_cost / STARTUP_AMORT_HOURS) * y_on[p]
        for p in P
    )
    unmet_penalty = pulp.lpSum(
        network.consumers[c].penalty_unmet * x_unmet[c] for c in C
    )

    prob += prod_cost + import_cost + export_revenue + startup_cost + unmet_penalty

    # ── Constraints ─────────────────────────────────────────────────────

    # 1. Producer capacity (big-M linking)
    for p in P:
        pr = network.producers[p]
        prob += x_prod[p] <= pr.capacity_max * y_on[p] * pr.availability, f"ProdMax_{p}"
        prob += x_prod[p] >= pr.capacity_min * y_on[p], f"ProdMin_{p}"

    # 2. Forced outages
    for p in forced_off:
        if p in y_on:
            prob += y_on[p] == 0, f"ForcedOff_{p}"

    # 3. Purifier capacity
    for u in U:
        pu = network.purifiers[u]
        prob += x_pur[u] <= pu.capacity_max, f"PurMax_{u}"

    # 4. Import / Export caps
    for e in IMP:
        ext = network.external[e]
        if ext.available:
            prob += x_imp[e] <= ext.capacity_max, f"ImpMax_{e}"
        else:
            prob += x_imp[e] == 0, f"ImpOff_{e}"

    for e in EXP:
        ext = network.external[e]
        if ext.available:
            prob += x_exp[e] <= ext.capacity_max, f"ExpMax_{e}"
        else:
            prob += x_exp[e] == 0, f"ExpOff_{e}"

    # 5. Consumer demand satisfaction
    for c in C:
        con = network.consumers[c]
        factor = demand_factors.get(c, 1.0)
        target = con.demand_nominal * factor
        prob += x_con[c] + x_unmet[c] >= target, f"DemandMet_{c}"
        prob += x_con[c] <= con.demand_max * factor, f"DemandMax_{c}"

        # Non-curtailable consumers cannot have unmet demand
        if not con.curtailable:
            prob += x_unmet[c] == 0, f"NoCurtail_{c}"

    # 6. Mass balance — HP Header
    #    In:  SMR-1, SMR-2, BYP-CCR, BYP-ETH
    #    Out: PSA-1 feed, MEM-1 feed
    hp_in = [p for p in P if p != "ELEC-1"]
    prob += (
        pulp.lpSum(x_prod[p] for p in hp_in)
        == pulp.lpSum(x_pur[u] for u in U),
        "MB_HP_Header"
    )

    # 7. Mass balance — UHP Header (ultra-high purity)
    #    In:  PSA-1 product, Electrolyser, Imports
    #    Out: UHP consumers
    uhp_consumers = ["C-HDS1", "C-HDS2", "C-HCK", "C-DHT", "C-ISO", "C-LUB"]
    prob += (
        network.purifiers["PSA-1"].recovery * x_pur["PSA-1"]
        + x_prod["ELEC-1"]
        + pulp.lpSum(x_imp[e] for e in IMP)
        == pulp.lpSum(x_con[c] for c in uhp_consumers if c in x_con),
        "MB_UHP_Header"
    )

    # 8. Mass balance — HPC Header (high-purity clean)
    #    In:  MEM-1 product
    #    Out: HPC consumers + Export
    hpc_consumers = ["C-HTR", "C-NHT", "C-WAX", "C-H2S"]
    prob += (
        network.purifiers["MEM-1"].recovery * x_pur["MEM-1"]
        == pulp.lpSum(x_con[c] for c in hpc_consumers if c in x_con)
           + pulp.lpSum(x_exp[e] for e in EXP),
        "MB_HPC_Header"
    )

    # ── Solve ───────────────────────────────────────────────────────────
    solver = pulp.PULP_CBC_CMD(
        msg=0,
        timeLimit=max_solve_time,
        gapRel=mip_gap,
    )
    prob.solve(solver)

    # ── Extract Results ─────────────────────────────────────────────────
    result.status = pulp.LpStatus[prob.status]

    if prob.status == pulp.constants.LpStatusOptimal:
        result.objective_value = pulp.value(prob.objective)

        for p in P:
            result.producer_flows[p] = pulp.value(x_prod[p]) or 0
            result.producer_on[p] = bool(round(pulp.value(y_on[p]) or 0))

        for u in U:
            result.purifier_feeds[u] = pulp.value(x_pur[u]) or 0

        for c in C:
            result.consumer_supplied[c] = pulp.value(x_con[c]) or 0
            result.consumer_unmet[c] = pulp.value(x_unmet[c]) or 0

        for e in IMP:
            result.import_flow[e] = pulp.value(x_imp[e]) or 0
        for e in EXP:
            result.export_flow[e] = pulp.value(x_exp[e]) or 0

        # Cost breakdown
        result.total_production_cost = sum(
            network.producers[p].variable_cost * result.producer_flows[p]
            for p in P
        )
        result.total_import_cost = sum(
            network.external[e].cost * result.import_flow[e] for e in IMP
        )
        result.total_export_revenue = sum(
            abs(network.external[e].cost) * result.export_flow[e] for e in EXP
        )
        result.total_startup_cost = sum(
            (network.producers[p].startup_cost / STARTUP_AMORT_HOURS)
            * (1 if result.producer_on[p] else 0)
            for p in P
        )
        result.total_unmet_penalty = sum(
            network.consumers[c].penalty_unmet * result.consumer_unmet[c]
            for c in C
        )

    return result


# ── Scenario Helpers ────────────────────────────────────────────────────────

def run_base_case(network: HydrogenNetwork) -> OptimizationResult:
    """Run the base-case dispatch with nominal demands."""
    return optimize_dispatch(network)


def run_outage_scenario(
    network: HydrogenNetwork, offline_units: list
) -> OptimizationResult:
    """Simulate one or more producers going offline."""
    return optimize_dispatch(network, forced_off=offline_units)


def run_demand_surge(
    network: HydrogenNetwork, surge_consumers: Dict[str, float]
) -> OptimizationResult:
    """Simulate demand increase on selected consumers."""
    return optimize_dispatch(network, demand_factors=surge_consumers)


def run_sensitivity_analysis(
    network: HydrogenNetwork,
) -> Dict[str, OptimizationResult]:
    """
    Run a battery of scenarios and return results keyed by scenario name.
    """
    results = {}

    # Base case
    results["Base Case"] = run_base_case(network)

    # SMR-1 outage
    results["SMR-1 Outage"] = run_outage_scenario(network, ["SMR-1"])

    # SMR-2 outage
    results["SMR-2 Outage"] = run_outage_scenario(network, ["SMR-2"])

    # Both SMRs down (extreme)
    results["Dual SMR Outage"] = run_outage_scenario(network, ["SMR-1", "SMR-2"])

    # 20% demand surge on hydrocracker
    results["HCK Surge +20%"] = run_demand_surge(network, {"C-HCK": 1.20})

    # Global 10% demand increase
    all_surge = {c: 1.10 for c in network.consumers}
    results["Global +10%"] = run_demand_surge(network, all_surge)

    return results


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    net = build_default_network()

    print("\n▸ Running base-case optimization...\n")
    base = run_base_case(net)
    print(base.summary())

    print("\n▸ Running sensitivity analysis...\n")
    scenarios = run_sensitivity_analysis(net)
    for name, res in scenarios.items():
        print(f"\n{'━'*60}")
        print(f"  Scenario: {name}")
        print(f"  Status: {res.status}  |  Cost: ${res.objective_value:,.2f}/h")
        if res.total_unmet_penalty > 0:
            print(f"  ⚠  Unmet demand penalty: ${res.total_unmet_penalty:,.2f}/h")
