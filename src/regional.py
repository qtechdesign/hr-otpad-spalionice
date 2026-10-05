from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

REGION_LABELS = {
    "zagreb": "Sjeverozapad (Zagreb i okolica)",
    "istok": "Slavonija i istok",
    "jug": "Kontinentalna jug (Karlovac, Lika, Gorski kotar)",
    "jadran": "Sjeverna Dalmacija",
    "split": "Splitsko-dalmatinska i jug",
}


@dataclass
class RegionalHub:
    regija_id: str
    regija_naziv: str
    q_r1_alloc_t: float
    zupanije: list[str]
    n_plants_suggested: int


def allocate_r1_by_county(q_r1_total_t: float, counties: pd.DataFrame) -> pd.DataFrame:
    df = counties.copy()
    total = df["nastalo_t_2024"].sum()
    if total <= 0:
        df["q_r1_alloc_t"] = 0.0
        return df
    df["q_r1_alloc_t"] = q_r1_total_t * (df["nastalo_t_2024"] / total)
    return df


def suggest_regional_hubs(
    counties: pd.DataFrame,
    q_r1_total_t: float,
    plant_capacity_kt: float = 100.0,
    utilization: float = 0.90,
) -> list[RegionalHub]:
    df = allocate_r1_by_county(q_r1_total_t, counties)
    effective = plant_capacity_kt * 1000.0 * utilization
    hubs: list[RegionalHub] = []

    # Splitsko-dalmatinska u zaseban hub "split" ako postoji regija_id split — map jadran+split
    region_groups = df.groupby("regija_id", as_index=False).agg(
        q_r1_alloc_t=("q_r1_alloc_t", "sum"),
        zupanije=("zupanija", lambda s: list(s)),
    )

    for _, row in region_groups.iterrows():
        reg_id = row["regija_id"]
        q = float(row["q_r1_alloc_t"])
        if effective <= 0:
            n = 0
        elif q <= 0:
            n = 0
        else:
            n = int(math.ceil(q / effective))
        hubs.append(
            RegionalHub(
                regija_id=reg_id,
                regija_naziv=REGION_LABELS.get(reg_id, reg_id),
                q_r1_alloc_t=q,
                zupanije=row["zupanije"],
                n_plants_suggested=n,
            )
        )

    hubs.sort(key=lambda h: h.q_r1_alloc_t, reverse=True)
    return hubs
