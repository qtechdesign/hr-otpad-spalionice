from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.constants import DATA_DIR, SCENARIO_STATUS_QUO


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    return pd.read_csv(path)


def _as_bool(series: pd.Series) -> pd.Series:
    """CSV 'false' nije Python False ako se koristi astype(bool) na tekstu."""
    return series.astype(str).str.strip().str.lower().isin(["true", "1", "yes", "da"])


def load_waste_categories() -> pd.DataFrame:
    df = _read_csv("reference_waste_by_category.csv")
    df["ukljuci_u_model"] = _as_bool(df["ukljuci_u_model"])
    df["r1_eligible_default"] = _as_bool(df["r1_eligible_default"])
    return df


def load_municipal_timeseries() -> pd.DataFrame:
    df = _read_csv("reference_municipal_hr.csv")
    return df


def load_counties_municipal() -> pd.DataFrame:
    df = _read_csv("reference_counties_municipal.csv")
    total = df["nastalo_t_2024"].sum()
    target = 1_878_802
    if total > 0 and abs(total - target) > 1:
        factor = target / total
        df = df.copy()
        df["nastalo_t_2024"] = (df["nastalo_t_2024"] * factor).round(0).astype(int)
        df["odlaganje_t_2024"] = (df["odlaganje_t_2024"] * factor).round(0).astype(int)
    return df


def load_routing_yaml() -> dict[str, Any]:
    path = DATA_DIR / "routing_defaults.yaml"
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_planned_plants() -> list[dict[str, Any]]:
    path = DATA_DIR / "planned_plants.yaml"
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return list(data.get("plants", []))


def build_routing_matrix(
    scenario_id: str = SCENARIO_STATUS_QUO,
    custom_overrides: dict[str, dict[str, float]] | None = None,
) -> dict[str, dict[str, float]]:
    """Vraća routing udio po kategoriji_id."""
    raw = load_routing_yaml()
    base = deepcopy(raw.get("base", {}))
    scenarios = raw.get("scenarios", {})
    if scenario_id in scenarios:
        for cat_id, routes in scenarios[scenario_id].items():
            if cat_id not in base:
                base[cat_id] = {}
            base[cat_id].update(routes)
    if custom_overrides:
        for cat_id, routes in custom_overrides.items():
            if cat_id not in base:
                base[cat_id] = {}
            base[cat_id].update(routes)
    _normalize_routing(base)
    return base


def _normalize_routing(matrix: dict[str, dict[str, float]]) -> None:
    for cat_id, routes in matrix.items():
        total = sum(float(v) for v in routes.values())
        if total <= 0:
            continue
        if abs(total - 1.0) > 0.001:
            for key in routes:
                routes[key] = float(routes[key]) / total


def scale_waste_masses(
    categories: pd.DataFrame,
    base_year: int = 2022,
    growth_pct_per_year: float = 0.0,
    target_year: int = 2024,
) -> pd.DataFrame:
    """Skalira mase kategorija prema projekciji rasta."""
    df = categories.copy()
    years = max(0, target_year - base_year)
    factor = (1.0 + growth_pct_per_year / 100.0) ** years
    df["masa_t"] = df["masa_t_2022"] * factor
    return df
