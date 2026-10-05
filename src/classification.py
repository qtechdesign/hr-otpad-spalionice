from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.constants import ROUTE_COMPOST, ROUTE_LANDFILL, ROUTE_OTHER, ROUTE_R1, ROUTE_RECYCLE


@dataclass
class ClassificationResult:
    by_category: pd.DataFrame
    totals_by_route: dict[str, float]
    total_mass_t: float
    q_r1_t: float


def apply_routing(
    categories: pd.DataFrame,
    routing: dict[str, dict[str, float]],
    include_hazardous_in_r1: bool = False,
) -> ClassificationResult:
    """
    Primjenjuje routing matricu na kategorije s masom u stupcu masa_t.
    Opasni otpad: R1 se poništava osim ako include_hazardous_in_r1.
    """
    rows: list[dict] = []
    totals = {
        ROUTE_RECYCLE: 0.0,
        ROUTE_COMPOST: 0.0,
        ROUTE_R1: 0.0,
        ROUTE_LANDFILL: 0.0,
        ROUTE_OTHER: 0.0,
    }

    for _, row in categories.iterrows():
        if not row.get("ukljuci_u_model", True):
            continue
        cat_id = row["kategorija_id"]
        mass = float(row["masa_t"])
        routes = routing.get(cat_id, {})
        if not routes:
            continue

        route_mass = {k: mass * float(v) for k, v in routes.items()}
        if cat_id == "opasni" and not include_hazardous_in_r1:
            shifted = route_mass.get(ROUTE_R1, 0.0)
            route_mass[ROUTE_R1] = 0.0
            route_mass[ROUTE_OTHER] = route_mass.get(ROUTE_OTHER, 0.0) + shifted

        if not row.get("r1_eligible_default", True):
            shifted = route_mass.get(ROUTE_R1, 0.0)
            route_mass[ROUTE_R1] = 0.0
            route_mass[ROUTE_LANDFILL] = route_mass.get(ROUTE_LANDFILL, 0.0) + shifted

        for route, m in route_mass.items():
            if route in totals:
                totals[route] += m

        rows.append(
            {
                "kategorija_id": cat_id,
                "kategorija_hr": row["kategorija_hr"],
                "masa_t": mass,
                **{f"masa_{route}": route_mass.get(route, 0.0) for route in totals},
            }
        )

    by_cat = pd.DataFrame(rows)
    total_mass = float(by_cat["masa_t"].sum()) if len(by_cat) else 0.0
    q_r1 = totals[ROUTE_R1]

    return ClassificationResult(
        by_category=by_cat,
        totals_by_route=totals,
        total_mass_t=total_mass,
        q_r1_t=q_r1,
    )
