from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class IncineratorSizingResult:
    q_r1_t: float
    q_planned_t: float
    q_remaining_t: float
    n_plants: int
    effective_capacity_t: float
    below_economic_threshold: bool
    min_economic_kt: float
    lines_total: int
    planned_plants: list[dict[str, Any]]
    message: str


def sum_planned_capacity(
    plants: list[dict[str, Any]],
    statuses: tuple[str, ...] = ("planirano", "operativno", "u_izgradnji"),
) -> float:
    total_kt = 0.0
    for p in plants:
        if not p.get("ukljuci_u_izracun", True):
            continue
        if p.get("status") not in statuses:
            continue
        total_kt += float(p.get("kapacitet_kt_a", 0))
    return total_kt * 1000.0


def size_incinerators(
    q_r1_t: float,
    plants: list[dict[str, Any]],
    plant_capacity_kt: float = 100.0,
    min_economic_kt: float = 75.0,
    utilization: float = 0.90,
    lines_per_plant: int = 1,
) -> IncineratorSizingResult:
    q_planned = sum_planned_capacity(plants)
    q_remaining = max(0.0, q_r1_t - q_planned)
    effective_cap = plant_capacity_kt * 1000.0 * utilization

    if effective_cap <= 0:
        n_plants = 0
    elif q_remaining <= 0:
        n_plants = 0
    else:
        n_plants = int(math.ceil(q_remaining / effective_cap))

    below_threshold = 0 < q_remaining < min_economic_kt * 1000.0
    lines_total = n_plants * max(1, lines_per_plant)

    if q_remaining <= 0:
        msg = (
            "Planirani kapacitet energana pokriva procijenjeni R1 tok "
            "(nema dodatnih postrojenja)."
        )
    elif below_threshold:
        msg = (
            f"Preostali R1 tok ({q_remaining/1000:.1f} kt/a) ispod ekonomskog praga "
            f"{min_economic_kt} kt/a — preporuka regionalnog spajanja CGO tokova."
        )
    else:
        msg = (
            f"Potrebno oko {n_plants} postrojenja od {plant_capacity_kt} kt/a "
            f"(uravnoteženost {utilization*100:.0f}%)."
        )

    return IncineratorSizingResult(
        q_r1_t=q_r1_t,
        q_planned_t=q_planned,
        q_remaining_t=q_remaining,
        n_plants=n_plants,
        effective_capacity_t=effective_cap,
        below_economic_threshold=below_threshold,
        min_economic_kt=min_economic_kt,
        lines_total=lines_total,
        planned_plants=[p for p in plants if p.get("ukljuci_u_izracun", True)],
        message=msg,
    )
