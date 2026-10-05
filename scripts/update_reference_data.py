#!/usr/bin/env python3
"""
Upute za ručno ažuriranje referentnih podataka iz ISGO / HAOP izvješća.

Izvori (provjeriti najnovije verzije na https://isgo-portal.haop.hr/):

1. data/reference_municipal_hr.csv
   - Izvješće o komunalnom otpadu (godišnje)
   - Tablica: količine odvojeno sakupljenog komunalnog otpada 2010–2024
   - Tablica / poglavlje 3: nastalo, recikliranje, R1, odlaganje, ostalo (2024)
   - Stupci: godina, nastalo_t, odvojeno_t, recikliranje_t, r1_t, odlaganje_t, ostalo_t, kg_po_stanovniku

2. data/reference_waste_by_category.csv
   - ISGO: Nastanak otpada – statistike (ukupne količine po vrstama, bazna godina npr. 2022)
   - Stupci: kategorija_id, kategorija_hr, udio_2022, masa_t_2022, ukljuci_u_model, r1_eligible_default
   - Zbroj masa_t_2022 treba odgovarati ukupno nastalom otpadu za tu godinu (~7,09 Mt u 2022.)

3. data/reference_counties_municipal.csv
   - Prilog izvješća o komunalnom otpadu: po županijama nastalo i odlaganje (2024)
   - Stupci: zupanija, nastalo_t_2024, odlaganje_t_2024, regija_id
   - regija_id: zagreb | istok | jug | jadran | split (heurističke regije za prijedlog hubova)

4. data/planned_plants.yaml
   - Ručno dodati planirane/operativne energane (kapacitet_kt_a, status, ukljuci_u_izracun)

5. data/routing_defaults.yaml
   - Prilagoditi base udjele ili scenarije nakon promjene politike / recikliranja

Nakon uređivanja CSV/YAML pokrenite aplikaciju i usporedite KPI s ISGO izvješćem.
"""

from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

if __name__ == "__main__":
    print(__doc__)
    print(f"Podaci: {DATA}")
