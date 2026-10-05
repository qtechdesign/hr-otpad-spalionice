"""Streamlit: analiza otpada RH i dimenzioniranje spalionica."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.classification import apply_routing
from src.constants import (
    DEFAULT_LINES_PER_PLANT,
    DEFAULT_MIN_ECONOMIC_KT,
    DEFAULT_PLANT_CAPACITY_KT,
    DEFAULT_UTILIZATION,
    ROUTE_LABELS_HR,
    SCENARIO_LABELS,
    SCENARIO_STATUS_QUO,
)
from src.data_loader import (
    build_routing_matrix,
    load_counties_municipal,
    load_municipal_timeseries,
    load_planned_plants,
    load_waste_categories,
    scale_waste_masses,
)
from src.incinerator_model import size_incinerators
from src.regional import allocate_r1_by_county, suggest_regional_hubs

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

st.set_page_config(
    page_title="Otpad RH — spalionice",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_all_reference():
    return {
        "categories": load_waste_categories(),
        "municipal": load_municipal_timeseries(),
        "counties": load_counties_municipal(),
        "plants": load_planned_plants(),
    }


@st.cache_data(show_spinner=False)
def cached_routing_matrix(scenario_id: str, custom_key: str) -> dict:
    del custom_key  # samo za invalidaciju cachea kad korisnik prilagodi routing
    return build_routing_matrix(scenario_id=scenario_id)


def fmt_kt(value_t: float) -> str:
    return f"{value_t / 1000:,.1f} kt/a"


def build_export_summary(
    scenario: str,
    classification,
    sizing,
    hubs,
    params: dict,
) -> str:
    lines = [
        f"# Sažetak scenarija — {SCENARIO_LABELS.get(scenario, scenario)}",
        f"Datum: {date.today().isoformat()}",
        "",
        f"- Ukupna masa u modelu: **{fmt_kt(classification.total_mass_t)}**",
        f"- R1 pogodno (Q_R1): **{fmt_kt(classification.q_r1_t)}**",
        f"- Planirani kapacitet energana: **{fmt_kt(sizing.q_planned_t)}**",
        f"- Preostalo za nova postrojenja: **{fmt_kt(sizing.q_remaining_t)}**",
        f"- Procijenjeni broj energana: **{sizing.n_plants}** "
        f"(kapacitet {params['plant_capacity_kt']} kt/a, uravnoteženost {params['utilization']*100:.0f}%)",
        f"- Ukupno linija (×{params['lines_per_plant']}): **{sizing.lines_total}**",
        "",
        sizing.message,
        "",
        "## Regionalni prijedlog (heuristika)",
    ]
    for h in hubs:
        lines.append(
            f"- {h.regija_naziv}: {fmt_kt(h.q_r1_alloc_t)}, "
            f"~{h.n_plants_suggested} postrojenja"
        )
    lines.extend(
        [
            "",
            "_Aplikacija nije studija utjecaja na okoliš. Izvor: ISGO/HAOP referentni podaci._",
        ]
    )
    return "\n".join(lines)


def _routing_for_scenario(scenario: str) -> dict:
    if st.session_state.get("custom_routing") and st.session_state.get("routing_scenario") == scenario:
        return st.session_state["custom_routing"]
    custom_key = st.session_state.get("routing_custom_key", "")
    return cached_routing_matrix(scenario, custom_key)


def main():
    try:
        _render_app()
    except Exception as exc:
        st.error("Greška pri učitavanju aplikacije. Detalji ispod.")
        st.exception(exc)


def _render_app():
    st.title("Analiza otpada u Republici Hrvatskoj")
    st.caption(
        "Scenarijsko planiranje: vrste i količine otpada, routing gospodarenja, "
        "procjena broja energana (R1). Podaci: ISGO / HAOP (referentni CSV u repou)."
    )

    ref = load_all_reference()

    with st.sidebar:
        st.header("Scenarij i parametri")
        scenario = st.selectbox(
            "Scenarij",
            options=list(SCENARIO_LABELS.keys()),
            format_func=lambda k: SCENARIO_LABELS[k],
            index=list(SCENARIO_LABELS.keys()).index(SCENARIO_STATUS_QUO),
        )
        growth = st.slider("Projekcija rasta otpada (%/god)", 0.0, 5.0, 1.0, 0.1)
        target_year = st.number_input("Ciljna godina projekcije", 2022, 2040, 2024)
        include_hazardous = st.checkbox("Uključi opasni otpad u R1 (what-if)", value=False)

        st.divider()
        plant_capacity_kt = st.number_input(
            "Kapacitet postrojenja (kt/a)",
            min_value=20.0,
            max_value=500.0,
            value=float(DEFAULT_PLANT_CAPACITY_KT),
            step=5.0,
        )
        min_economic_kt = st.number_input(
            "Min. ekonomski prag (kt/a)",
            min_value=20.0,
            max_value=200.0,
            value=float(DEFAULT_MIN_ECONOMIC_KT),
            step=5.0,
        )
        utilization = st.slider(
            "Uravnoteženost kapaciteta (max opterećenje)",
            0.5,
            1.0,
            float(DEFAULT_UTILIZATION),
            0.05,
        )
        lines_per_plant = st.number_input(
            "Linija po postrojenju",
            min_value=1,
            max_value=4,
            value=int(DEFAULT_LINES_PER_PLANT),
        )

        st.divider()
        page = st.radio(
            "Prikaz",
            [
                "Pregled",
                "Vrste otpada",
                "Komunalni otpad",
                "Spalionice",
                "Regije",
                "Metodologija",
            ],
            index=0,
        )

    if st.session_state.get("routing_scenario") != scenario:
        st.session_state.pop("custom_routing", None)
        st.session_state["routing_scenario"] = scenario

    routing = _routing_for_scenario(scenario)
    categories = scale_waste_masses(
        ref["categories"],
        base_year=2022,
        growth_pct_per_year=growth,
        target_year=int(target_year),
    )
    classification = apply_routing(
        categories,
        routing,
        include_hazardous_in_r1=include_hazardous,
    )
    sizing = size_incinerators(
        q_r1_t=classification.q_r1_t,
        plants=ref["plants"],
        plant_capacity_kt=plant_capacity_kt,
        min_economic_kt=min_economic_kt,
        utilization=utilization,
        lines_per_plant=int(lines_per_plant),
    )
    q_for_regions = sizing.q_remaining_t if sizing.q_remaining_t > 0 else classification.q_r1_t
    hubs = suggest_regional_hubs(
        ref["counties"],
        q_for_regions,
        plant_capacity_kt=plant_capacity_kt,
        utilization=utilization,
    )

    params = {
        "plant_capacity_kt": plant_capacity_kt,
        "utilization": utilization,
        "lines_per_plant": int(lines_per_plant),
    }

    if page == "Pregled":
        _page_overview(classification, sizing, scenario, target_year, hubs, params)
    elif page == "Vrste otpada":
        _page_types(categories, classification, routing, scenario)
    elif page == "Komunalni otpad":
        _page_municipal(ref, categories, target_year)
    elif page == "Spalionice":
        _page_plants(ref, sizing, plant_capacity_kt, utilization)
    elif page == "Regije":
        _page_regions(ref, q_for_regions, hubs)
    else:
        _page_methodology()


def _page_overview(classification, sizing, scenario, target_year, hubs, params):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ukupno u modelu", fmt_kt(classification.total_mass_t))
    c2.metric("Q_R1 (gorivo energana)", fmt_kt(classification.q_r1_t))
    c3.metric("Planirano energana", fmt_kt(sizing.q_planned_t))
    c4.metric("Broj dodatnih energana", sizing.n_plants)

    if sizing.below_economic_threshold:
        st.warning(sizing.message)
    else:
        st.info(sizing.message)

    route_df = pd.DataFrame(
        [
            {"Ruta": ROUTE_LABELS_HR.get(k, k), "Masa (t/a)": v}
            for k, v in classification.totals_by_route.items()
        ]
    )
    fig_routes = px.pie(
        route_df,
        names="Ruta",
        values="Masa (t/a)",
        title="Raspodjela po rutama gospodarenja",
    )
    st.plotly_chart(fig_routes, use_container_width=True, config=PLOTLY_CONFIG)

    st.subheader("Izvoz rezultata")
    export_csv = classification.by_category.to_csv(index=False).encode("utf-8")
    summary_md = build_export_summary(scenario, classification, sizing, hubs, params)
    col_a, col_b = st.columns(2)
    col_a.download_button(
        "Preuzmi tablicu kategorija (CSV)",
        export_csv,
        file_name=f"otpad_rh_{scenario}_{target_year}.csv",
        mime="text/csv",
    )
    col_b.download_button(
        "Preuzmi sažetak (Markdown)",
        summary_md.encode("utf-8"),
        file_name=f"otpad_rh_sažetak_{scenario}.md",
        mime="text/markdown",
    )


def _page_types(categories, classification, routing, scenario):
    st.subheader("Kategorije otpada (ISGO agregat, bazna struktura 2022 + projekcija)")
    bar_df = categories[["kategorija_hr", "masa_t"]].copy()
    fig_bar = px.bar(
        bar_df,
        x="kategorija_hr",
        y="masa_t",
        labels={"masa_t": "Masa (t/a)", "kategorija_hr": "Kategorija"},
        title="Nastali otpad po kategorijama",
    )
    fig_bar.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)

    st.dataframe(classification.by_category, use_container_width=True, hide_index=True)

    with st.expander("Prilagodi routing za odabranu kategoriju (napredno)"):
        cat_ids = list(routing.keys())
        sel = st.selectbox("Kategorija", cat_ids, format_func=lambda i: i, key="route_cat_sel")
        routes = routing[sel]
        cols = st.columns(len(routes))
        new_routes = {}
        for col, (route, val) in zip(cols, routes.items()):
            new_routes[route] = col.number_input(
                ROUTE_LABELS_HR.get(route, route),
                0.0,
                1.0,
                float(val),
                0.01,
                key=f"route_{sel}_{route}",
            )
        if st.button("Primijeni prilagodbu routinga"):
            st.session_state["custom_routing"] = build_routing_matrix(scenario, {sel: new_routes})
            st.session_state["routing_scenario"] = scenario
            st.session_state["routing_custom_key"] = f"{scenario}_{sel}_{hash(frozenset(new_routes.items()))}"
            st.rerun()


def _page_municipal(ref, categories, target_year):
    st.subheader("Komunalni otpad — referentna vremenska serija (ISGO)")
    muni = ref["municipal"].dropna(subset=["nastalo_t"])
    if len(muni):
        fig_m = px.line(
            muni,
            x="godina",
            y="nastalo_t",
            markers=True,
            labels={"nastalo_t": "Nastalo (t/a)", "godina": "Godina"},
            title="Nastali komunalni otpad u RH",
        )
        st.plotly_chart(fig_m, use_container_width=True, config=PLOTLY_CONFIG)

    m2024 = ref["municipal"].query("godina == 2024")
    if len(m2024):
        row = m2024.iloc[0]
        st.markdown(
            f"**2024 (službeno):** nastalo **{row['nastalo_t']:,.0f} t/a** "
            f"({row.get('kg_po_stanovniku', 486)} kg/st), recikliranje "
            f"**{row.get('recikliranje_t', 0):,.0f} t**, R1 **{row.get('r1_t', 0):,.0f} t**, "
            f"odlaganje **{row.get('odlaganje_t', 0):,.0f} t**."
        )

    kucanstva_row = categories[categories["kategorija_id"] == "kucanstva"]
    if len(kucanstva_row):
        st.markdown(
            f"Modelirana kategorija *kućanstva/sličan* u {target_year}: "
            f"**{kucanstva_row.iloc[0]['masa_t']:,.0f} t/a** "
            f"(ukupni otpad u RH uključuje i industrijske tokove)."
        )


def _page_plants(ref, sizing, plant_capacity_kt, utilization):
    st.subheader("Dimenzioniranje energana (spalionica s R1)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Q_R1", fmt_kt(sizing.q_r1_t))
    m2.metric("Oduzeto (planirano)", fmt_kt(sizing.q_planned_t))
    m3.metric("Preostalo Q", fmt_kt(sizing.q_remaining_t))

    st.markdown(
        f"Efektivni kapacitet po postrojenju: **{fmt_kt(sizing.effective_capacity_t)}** "
        f"(= {plant_capacity_kt} kt × {utilization*100:.0f}%)."
    )
    st.markdown(
        f"**Procjena: {sizing.n_plants}** dodatnih energana, **{sizing.lines_total}** linija ukupno."
    )

    st.markdown("#### Planirana / referentna postrojenja")
    st.dataframe(pd.DataFrame(ref["plants"]), use_container_width=True, hide_index=True)

    load_df = pd.DataFrame(
        {
            "Stavka": ["Q_R1", "Planirano", "Preostalo za nova postrojenja"],
            "t/a": [sizing.q_r1_t, sizing.q_planned_t, sizing.q_remaining_t],
        }
    )
    fig_load = px.bar(load_df, x="Stavka", y="t/a", title="Opterećenje vs planirani kapacitet")
    st.plotly_chart(fig_load, use_container_width=True, config=PLOTLY_CONFIG)


def _page_regions(ref, q_for_regions, hubs):
    st.subheader("Regionalni prijedlog (proporcionalno komunalnom otpadu po županiji)")
    counties_alloc = allocate_r1_by_county(q_for_regions, ref["counties"])
    st.dataframe(
        counties_alloc.sort_values("q_r1_alloc_t", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    hub_rows = [
        {
            "Regija": h.regija_naziv,
            "Q_R1 (t/a)": round(h.q_r1_alloc_t),
            "Predloženo postrojenja": h.n_plants_suggested,
            "Županije": ", ".join(h.zupanije),
        }
        for h in hubs
    ]
    st.markdown("#### Regionalni čvorovi (heuristika)")
    st.dataframe(pd.DataFrame(hub_rows), use_container_width=True, hide_index=True)

    fig_reg = px.bar(
        pd.DataFrame(hub_rows),
        x="Regija",
        y="Q_R1 (t/a)",
        title="Alokacija R1 po regijama",
    )
    fig_reg.update_layout(xaxis_tickangle=-25)
    st.plotly_chart(fig_reg, use_container_width=True, config=PLOTLY_CONFIG)


def _page_methodology():
    st.markdown(
        """
### Metodologija

1. **Ulaz:** agregirane kategorije nastanka otpada (ISGO, ~7,09 Mt u 2022.) skalirane projekcijom rasta do ciljne godine.
2. **Routing:** za svaku kategoriju udjeli recikliranja, komposta/MBO, R1, odlaganja i ostalog (zbroj = 1). Scenarij prepisuje zadane udjele (`data/routing_defaults.yaml`).
3. **Q_R1:** suma masa usmjerenih u R1; kategorije označene kao ne-R1 (npr. mineralni, metali) preusmjeravaju R1 u odlaganje.
4. **Dimenzioniranje:**
   - `Q_ostalo = max(0, Q_R1 − kapacitet_planiranih energana)`
   - `N = ceil(Q_ostalo / (kapacitet_postrojenja × uravnoteženost))`
   - Ako je `Q_ostalo` ispod ekonomskog praga → preporuka regionalnog spajanja tokova (više CGO → jedna energana).
5. **Regije:** alokacija `Q_ostalo` proporcionalno nastalom komunalnom otpadu po županiji; broj postrojenja po regiji iz istog kapaciteta.

### Izvori

- [ISGO — komunalni otpad 2024](https://isgo-portal.haop.hr/)
- [ISGO — nastanak otpada, statistike](https://isgo-portal.haop.hr/hr/pokazatelji/nastanak-otpada-statistike)

### Ograničenja

- Nije zamjena za NUS / IPPC projektiranje stvarne energane.
- Industrijski tokovi nisu u punoj EWC granularnosti; moguće proširenje uploadom CSV.
- Županijski podaci u repou su sažetak za regionalni prikaz (normalizirano na ukupno 1,878,802 t u 2024.).

### Deploy

- Streamlit Cloud: **Main file** `streamlit_app.py` (preporučeno) ili `app.py`.
        """
    )


if __name__ == "__main__":
    main()
