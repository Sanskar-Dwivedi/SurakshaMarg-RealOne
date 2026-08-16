"""
Traffic impact model.

This is a traffic-management project, so the deterrent has to justify itself in
traffic terms, not animal-behaviour terms. The chain of reasoning is:

    livestock blocks lanes -> capacity drops -> a queue forms -> the queue takes
    longer to clear than the blockage itself lasted

That last step is the one people underestimate, and it is why clearing a cow
30 seconds sooner is worth much more than 30 vehicle-seconds. We model it with
standard deterministic queueing rather than inventing a metric.

Every rate here is a SITE PARAMETER to be measured, not a claim about India's
roads. The model ships with placeholder values clearly labelled as such; the
outputs are only as good as the counts the operator supplies.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class RoadParams:
    """
    Site parameters. All of these must be measured at the deployment site.

    `saturation_flow_veh_h_lane` of ~1800 is the classic HCM-style default for
    an ideal lane; Indian mixed traffic with two-wheelers behaves differently,
    which is exactly why this is a parameter with a stated default rather than
    a constant buried in the code.
    """

    lanes: int = 2
    saturation_flow_veh_h_lane: float = 1800.0
    demand_veh_h: float = 900.0
    mean_occupancy: float = 1.6          # persons per vehicle
    value_of_time_inr_h: float = 120.0   # placeholder; set from local data
    idle_fuel_l_per_h: float = 0.7       # per idling vehicle
    fuel_price_inr_l: float = 100.0
    co2_kg_per_l: float = 2.31

    def capacity_veh_h(self, lanes_blocked: int = 0) -> float:
        open_lanes = max(self.lanes - lanes_blocked, 0)
        return open_lanes * self.saturation_flow_veh_h_lane

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class BlockageImpact:
    blockage_s: float
    lanes_blocked: int
    demand_veh_h: float
    capacity_during_veh_h: float
    vehicles_arriving: float
    vehicles_served_during: float
    max_queue_veh: float
    queue_clear_s: float
    total_delay_veh_s: float
    total_delay_veh_h: float
    person_hours_lost: float
    fuel_litres: float
    cost_inr: float
    co2_kg: float
    note: str

    def as_dict(self) -> dict:
        return asdict(self)


def blockage_impact(
    blockage_s: float, params: RoadParams, lanes_blocked: int | None = None
) -> BlockageImpact:
    """
    Deterministic queueing model of one livestock blockage.

    Arrivals are uniform at `demand_veh_h`. During the blockage, service drops
    to the capacity of the remaining open lanes. Afterwards, full capacity
    discharges the queue. Total delay is the area of the resulting triangle.
    """
    lanes_blocked = params.lanes if lanes_blocked is None else lanes_blocked
    lanes_blocked = min(lanes_blocked, params.lanes)

    t = max(blockage_s, 0.0)
    lam = params.demand_veh_h / 3600.0                       # veh/s arriving
    mu_during = params.capacity_veh_h(lanes_blocked) / 3600.0
    mu_after = params.capacity_veh_h(0) / 3600.0

    arriving = lam * t
    served = mu_during * t
    queue = max(arriving - served, 0.0)

    # Queue discharges at (capacity - demand); if demand >= capacity it never
    # clears, which is itself the finding.
    net_discharge = mu_after - lam
    if net_discharge <= 0:
        clear_s = float("inf")
        delay_veh_s = float("inf")
    else:
        clear_s = queue / net_discharge
        # Triangle: builds over t, decays over clear_s, peak = queue.
        delay_veh_s = 0.5 * queue * (t + clear_s)

    delay_veh_h = delay_veh_s / 3600.0 if delay_veh_s != float("inf") else float("inf")
    person_h = delay_veh_h * params.mean_occupancy
    fuel = delay_veh_h * params.idle_fuel_l_per_h
    cost = person_h * params.value_of_time_inr_h + fuel * params.fuel_price_inr_l

    return BlockageImpact(
        blockage_s=t,
        lanes_blocked=lanes_blocked,
        demand_veh_h=params.demand_veh_h,
        capacity_during_veh_h=params.capacity_veh_h(lanes_blocked),
        vehicles_arriving=round(arriving, 1),
        vehicles_served_during=round(served, 1),
        max_queue_veh=round(queue, 1),
        queue_clear_s=round(clear_s, 1) if clear_s != float("inf") else -1.0,
        total_delay_veh_s=round(delay_veh_s, 1) if delay_veh_s != float("inf") else -1.0,
        total_delay_veh_h=round(delay_veh_h, 3) if delay_veh_h != float("inf") else -1.0,
        person_hours_lost=round(person_h, 3) if person_h != float("inf") else -1.0,
        fuel_litres=round(fuel, 3) if fuel != float("inf") else -1.0,
        cost_inr=round(cost, 1) if cost != float("inf") else -1.0,
        co2_kg=round(fuel * params.co2_kg_per_l, 3) if fuel != float("inf") else -1.0,
        note=(
            "Deterministic queueing with uniform arrivals. A value of -1 means "
            "demand exceeds capacity and the queue never clears within the "
            "model - report that as a finding, not as zero delay."
        ),
    )


def intervention_benefit(
    baseline_blockage_s: float,
    improved_blockage_s: float,
    params: RoadParams,
    incidents_per_day: float = 4.0,
    lanes_blocked: int | None = None,
) -> dict:
    """
    Difference between doing nothing and clearing the animal sooner.

    Deliberately expressed as a DELTA on a measured baseline, so the claim is
    'this much faster' rather than 'this system saves X', which would require
    proving the deterrent works - something the evidence does not yet support.
    """
    base = blockage_impact(baseline_blockage_s, params, lanes_blocked)
    imp = blockage_impact(improved_blockage_s, params, lanes_blocked)

    def delta(a: float, b: float) -> float:
        if a < 0 or b < 0:
            return -1.0
        return round(a - b, 3)

    return {
        "baseline": base.as_dict(),
        "improved": imp.as_dict(),
        "per_incident": {
            "delay_veh_h_saved": delta(base.total_delay_veh_h, imp.total_delay_veh_h),
            "person_hours_saved": delta(base.person_hours_lost, imp.person_hours_lost),
            "fuel_litres_saved": delta(base.fuel_litres, imp.fuel_litres),
            "cost_inr_saved": delta(base.cost_inr, imp.cost_inr),
            "co2_kg_saved": delta(base.co2_kg, imp.co2_kg),
        },
        "per_day": {
            "incidents": incidents_per_day,
            "person_hours_saved": delta(
                base.person_hours_lost * incidents_per_day,
                imp.person_hours_lost * incidents_per_day,
            ),
            "cost_inr_saved": delta(
                base.cost_inr * incidents_per_day, imp.cost_inr * incidents_per_day
            ),
            "co2_kg_saved": delta(
                base.co2_kg * incidents_per_day, imp.co2_kg * incidents_per_day
            ),
        },
        "caveat": (
            "This quantifies the value of clearing a blockage sooner. It does "
            "NOT assert that ultrasonic deterrence achieves that clearance - "
            "that is the open question the field trial must answer. Feed the "
            "measured turn-away rate in as `improved_blockage_s` to get a real "
            "figure; until then this is a sensitivity analysis, not a result."
        ),
    }


def signal_response_plan(distance_m: float, speed_limit_kmh: float, lanes_blocked: int) -> dict:
    """
    What the traffic controller should do the moment livestock is detected.

    This is the half of the system that works regardless of whether the animal
    responds to sound, which is precisely why it exists.
    """
    v = speed_limit_kmh / 3.6
    # Stopping sight distance: reaction (2.5 s, IRC/AASHTO convention) + braking
    # at a conservative 3.4 m/s^2 deceleration.
    ssd = v * 2.5 + (v * v) / (2 * 3.4)
    return {
        "detection_distance_m": round(distance_m, 1),
        "approach_speed_kmh": speed_limit_kmh,
        "stopping_sight_distance_m": round(ssd, 1),
        "advance_warning_position_m": round(max(ssd * 1.5, 100.0), 1),
        "lanes_blocked": lanes_blocked,
        "actions": [
            "Post LIVESTOCK ON ROAD on the upstream variable message sign",
            f"Place advance warning at least {max(ssd * 1.5, 100.0):.0f} m upstream",
            "Hold upstream signal red; extend clearance interval downstream",
            "Reduce advisory speed for the affected approach",
            "Raise a municipal dispatch ticket with the live camera link",
        ],
        "rationale": (
            "Warning drivers is a proven intervention with a known mechanism. "
            "Moving the animal is not. The system therefore always does the "
            "proven thing first and treats the acoustic nudge as an adjunct."
        ),
    }
