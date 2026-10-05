# Analiza otpada u RH i dimenzioniranje spalionica

Streamlit aplikacija za scenarijsko planiranje gospodarenja otpadom u Republici Hrvatskoj: količine i vrste otpada, routing (recikliranje, kompost, R1, odlaganje) te procjena broja energana (spalionica s oporabom energije).

**Izvori podataka:** [ISGO / HAOP](https://isgo-portal.haop.hr/) — komunalni otpad 2024, statistike nastanka otpada (2022).

> Ova aplikacija nije zamjena za studiju utjecaja na okoliš. Služi za transparentne scenarije i edukaciju.

## Pokretanje

```bash
cd "560 Otpad"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Testovi

```bash
pip install pytest
pytest tests/
```

## Struktura

- `app.py` — Streamlit sučelje
- `src/` — model klasifikacije, dimenzioniranje, regionalna raspodjela
- `data/` — referentni CSV/YAML (ISGO)
- `scripts/update_reference_data.py` — upute za ažuriranje podataka

## Metodologija (sažetak)

1. Kategorije otpada iz ISGO 2022 skaliraju se projekcijom rasta.
2. Po kategoriji primjenjuje se routing matrica (% recikliranje, kompost/MBO, R1, odlaganje, ostalo).
3. `Q_R1` = suma masa usmjerenih u R1; oduzima se kapacitet planiranih energana.
4. Broj postrojenja = `ceil(Q_ostalo / (kapacitet × uravnoteženost))`, uz ekonomski prag.
