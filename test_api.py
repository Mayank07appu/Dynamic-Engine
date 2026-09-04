"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["active_simulation_zones"] == 5
    assert data["surge_cap"] == 3.50


def test_get_zones():
    response = client.get("/api/v1/zones")
    assert response.status_code == 200
    zones = response.json()
    assert len(zones) == 5
    zone_ids = [z["zone_id"] for z in zones]
    assert "DOWNTOWN" in zone_ids
    assert "AIRPORT" in zone_ids


def test_get_single_zone():
    response = client.get("/api/v1/zones/DOWNTOWN")
    assert response.status_code == 200
    data = response.json()
    assert data["zone_id"] == "DOWNTOWN"
    assert "weather" in data
    assert "traffic" in data


def test_quote_endpoint():
    payload = {
        "pickup_zone": "DOWNTOWN",
        "dropoff_zone": "AIRPORT",
        "vehicle_tier": "STANDARD",
        "distance_km": 12.0,
        "duration_min": 25.0,
        "requested_at_hour": 18,
        "weather": {
            "condition": "RAIN",
            "precipitation_mm_h": 15.0,
            "visibility_km": 6.0,
            "wind_speed_kmh": 20.0,
            "temperature_c": 18.0
        },
        "traffic": {
            "congestion_index": 0.65,
            "free_flow_speed_kmh": 50.0,
            "current_speed_kmh": 25.0,
            "incidents_count": 1,
            "delay_per_km_min": 0.5,
            "is_highway": False
        },
        "custom_active_drivers": 20,
        "custom_open_requests": 35
    }
    response = client.post("/api/v1/quote", json=payload)
    assert response.status_code == 200
    quote = response.json()
    assert quote["final_fare"] > quote["subtotal_base"]
    assert quote["total_surge_multiplier"] > 1.0
    assert quote["weather_surcharge_amount"] > 0
    assert quote["traffic_surcharge_amount"] > 0
    assert quote["acceptance_probability"] > 0.0


def test_trigger_event_and_tick():
    event_payload = {
        "zone_id": "DOWNTOWN",
        "event_type": "HEAVY_RAIN",
        "severity": 0.9,
        "duration_steps": 4
    }
    response = client.post("/api/v1/zones/DOWNTOWN/event", json=event_payload)
    assert response.status_code == 200
    zone = response.json()
    assert zone["weather"]["condition"] == "HEAVY_RAIN"

    # Step simulation clock
    tick_res = client.post("/api/v1/simulation/tick")
    assert tick_res.status_code == 200
    tick_data = tick_res.json()
    assert "snapshot" in tick_data
    assert tick_data["snapshot"]["tick"] >= 1


def test_elasticity_curve_endpoint():
    response = client.get("/api/v1/elasticity/curve?base_fare=18.0&loyalty_tier=REGULAR&max_multiplier=3.5")
    assert response.status_code == 200
    data = response.json()
    assert "optimal_multiplier" in data
    assert "max_expected_gmv" in data
    assert len(data["points"]) > 10
