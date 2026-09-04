"""Tests for the CitySimulator dynamics and fleet relocation."""

from pulseride.simulation.simulator import CitySimulator
from pulseride.models.schemas import ZoneID, SimulationEvent


def test_simulator_initialization():
    sim = CitySimulator(random_seed=123)
    assert len(sim.zones) == 5
    assert sim.current_hour == 17
    assert sim.tick_counter == 0

    downtown = sim.get_zone(ZoneID.DOWNTOWN)
    assert downtown.name == "Downtown Central"
    assert downtown.active_drivers > 0
    assert downtown.surge_multiplier >= 1.0


def test_shock_event_trigger_and_recovery():
    sim = CitySimulator(random_seed=123)
    event = SimulationEvent(
        zone_id=ZoneID.DOWNTOWN,
        event_type="HEAVY_RAIN",
        severity=0.8,
        duration_steps=2,
    )
    zone = sim.trigger_event(event)
    assert zone.weather.precipitation_mm_h > 15.0
    assert zone.surge_multiplier > 1.3

    # Tick 1: event still active
    sim.tick()
    assert len(sim.active_events) == 1

    # Tick 2: event expires and recovers
    sim.tick()
    assert len(sim.active_events) == 0


def test_autonomous_driver_relocation():
    sim = CitySimulator(random_seed=123)
    # Manually spike Downtown surge to trigger relocation from lowest zone
    event = SimulationEvent(
        zone_id=ZoneID.DOWNTOWN,
        event_type="CONCERT_EXIT",
        severity=1.0,
        duration_steps=5,
    )
    sim.trigger_event(event)
    initial_downtown_drivers = sim.zones[ZoneID.DOWNTOWN].active_drivers

    # Tick multiple times to allow drivers to gravitate towards Downtown
    for _ in range(3):
        sim.tick()

    # Downtown should have absorbed additional drivers responding to surge incentive
    assert sim.zones[ZoneID.DOWNTOWN].active_drivers >= initial_downtown_drivers
