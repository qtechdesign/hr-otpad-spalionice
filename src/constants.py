from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

SCENARIO_STATUS_QUO = "status_quo_2024"
SCENARIO_EU = "eu_smer"
SCENARIO_AGGRESSIVE_R1 = "agresivno_r1"

SCENARIO_LABELS = {
    SCENARIO_STATUS_QUO: "Status quo 2024",
    SCENARIO_EU: "EU smjer (više recikliranja, manje odlaganja)",
    SCENARIO_AGGRESSIVE_R1: "Agresivno R1 (what-if)",
}

DEFAULT_PLANT_CAPACITY_KT = 100.0
DEFAULT_MIN_ECONOMIC_KT = 75.0
DEFAULT_UTILIZATION = 0.90
DEFAULT_LINES_PER_PLANT = 1

ROUTE_RECYCLE = "recikliranje"
ROUTE_COMPOST = "kompost_mbo"
ROUTE_R1 = "r1"
ROUTE_LANDFILL = "odlaganje"
ROUTE_OTHER = "ostalo"

ROUTE_LABELS_HR = {
    ROUTE_RECYCLE: "Recikliranje",
    ROUTE_COMPOST: "Kompost / MBO",
    ROUTE_R1: "R1 (energetska oporaba)",
    ROUTE_LANDFILL: "Odlaganje",
    ROUTE_OTHER: "Ostalo",
}
