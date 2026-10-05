import pytest

from src.incinerator_model import size_incinerators, sum_planned_capacity


def test_sum_planned_capacity_only_included_statuses():
    plants = [
        {"kapacitet_kt_a": 100, "status": "planirano", "ukljuci_u_izracun": True},
        {"kapacitet_kt_a": 50, "status": "ideja", "ukljuci_u_izracun": True},
        {"kapacitet_kt_a": 200, "status": "planirano", "ukljuci_u_izracun": False},
    ]
    assert sum_planned_capacity(plants) == 100_000.0


def test_size_ceiling_plants():
    plants = []
    result = size_incinerators(
        q_r1_t=250_000,
        plants=plants,
        plant_capacity_kt=100,
        utilization=1.0,
    )
    assert result.n_plants == 3
    assert result.q_remaining_t == 250_000


def test_size_subtracts_planned():
    plants = [
        {"kapacitet_kt_a": 100, "status": "planirano", "ukljuci_u_izracun": True},
    ]
    result = size_incinerators(q_r1_t=150_000, plants=plants, plant_capacity_kt=100, utilization=1.0)
    assert result.q_planned_t == 100_000
    assert result.q_remaining_t == 50_000
    assert result.n_plants == 1


def test_size_no_additional_when_planned_covers():
    plants = [
        {"kapacitet_kt_a": 100, "status": "planirano", "ukljuci_u_izracun": True},
    ]
    result = size_incinerators(q_r1_t=80_000, plants=plants, plant_capacity_kt=100, utilization=1.0)
    assert result.n_plants == 0
    assert result.q_remaining_t == 0


def test_economic_threshold_flag():
    plants = []
    result = size_incinerators(
        q_r1_t=50_000,
        plants=plants,
        min_economic_kt=75,
        plant_capacity_kt=100,
        utilization=0.9,
    )
    assert result.below_economic_threshold is True
    assert result.n_plants == 1
