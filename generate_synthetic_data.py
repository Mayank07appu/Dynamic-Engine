"""Synthetic dataset generation script for PulseRide dynamic pricing research.
Generates realistic ride requests with weather, traffic, and acceptance outcomes.
"""

import os
import sys
import csv
import random
from pathlib import Path

# Ensure root directory is on Python module search path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pulseride.models.schemas import (
    ZoneID,
    VehicleTier,
    WeatherCondition,
    WeatherConditions,
    TrafficData,
    RideRequest,
)
from pulseride.engine.pricing import DynamicPricingEngine


def generate_dataset(num_samples: int = 5000, output_path: str = "data/rides_synthetic_dataset.csv"):
    random.seed(42)
    engine = DynamicPricingEngine()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    zones = list(ZoneID)
    tiers = list(VehicleTier)
    weather_types = [
        WeatherCondition.CLEAR,
        WeatherCondition.DRIZZLE,
        WeatherCondition.RAIN,
        WeatherCondition.HEAVY_RAIN,
        WeatherCondition.THUNDERSTORM,
        WeatherCondition.SNOW,
        WeatherCondition.BLIZZARD,
        WeatherCondition.FOG,
    ]
    weather_weights = [0.55, 0.15, 0.12, 0.08, 0.04, 0.03, 0.01, 0.02]

    records = []

    print(f"Generating {num_samples} synthetic ride entries...")

    for i in range(num_samples):
        pickup = random.choice(zones)
        dropoff = random.choice([z for z in zones if z != pickup])
        tier = random.choice(tiers)
        dist = round(random.uniform(2.0, 28.0), 2)
        dur = round(dist * random.uniform(1.8, 3.2), 1)
        hour = random.randint(0, 23)

        weather_cond = random.choices(weather_types, weights=weather_weights, k=1)[0]
        precip = 0.0
        vis = 10.0
        if weather_cond in [WeatherCondition.RAIN, WeatherCondition.SNOW]:
            precip = round(random.uniform(3.0, 15.0), 1)
            vis = round(random.uniform(4.0, 8.0), 1)
        elif weather_cond in [WeatherCondition.HEAVY_RAIN, WeatherCondition.THUNDERSTORM, WeatherCondition.BLIZZARD]:
            precip = round(random.uniform(20.0, 60.0), 1)
            vis = round(random.uniform(0.5, 3.0), 1)

        temp = round(random.uniform(5.0, 32.0), 1)
        if weather_cond in [WeatherCondition.SNOW, WeatherCondition.BLIZZARD]:
            temp = round(random.uniform(-15.0, 0.0), 1)

        weather = WeatherConditions(
            condition=weather_cond,
            precipitation_mm_h=precip,
            visibility_km=vis,
            wind_speed_kmh=round(random.uniform(5.0, 60.0), 1),
            temperature_c=temp,
        )

        # Rush hour traffic correlated with hour
        is_rush = (7 <= hour <= 9) or (17 <= hour <= 19)
        base_cong = random.uniform(0.4, 0.85) if is_rush else random.uniform(0.05, 0.45)
        incidents = 1 if random.random() < 0.15 else (2 if random.random() < 0.03 else 0)

        traffic = TrafficData(
            congestion_index=round(base_cong, 2),
            free_flow_speed_kmh=50.0,
            current_speed_kmh=round(50.0 * max(0.2, (1.0 - base_cong * 0.7)), 1),
            incidents_count=incidents,
            delay_per_km_min=round(base_cong * 1.2, 2),
        )

        drivers = random.randint(8, 60)
        requests = random.randint(10, 80)

        loyalty = random.choices(["REGULAR", "GOLD", "PLATINUM"], weights=[0.7, 0.2, 0.1], k=1)[0]

        req = RideRequest(
            pickup_zone=pickup,
            dropoff_zone=dropoff,
            vehicle_tier=tier,
            distance_km=dist,
            duration_min=dur,
            rider_loyalty_tier=loyalty,
            requested_at_hour=hour,
            weather=weather,
            traffic=traffic,
            custom_active_drivers=drivers,
            custom_open_requests=requests,
        )

        quote = engine.quote_ride(req)

        # Simulated rider conversion based on probability
        is_accepted = 1 if random.random() < quote.acceptance_probability else 0

        records.append({
            "request_id": f"REQ-{i+1:06d}",
            "hour": hour,
            "pickup_zone": pickup.value,
            "dropoff_zone": dropoff.value,
            "vehicle_tier": tier.value,
            "distance_km": dist,
            "duration_min": dur,
            "weather_condition": weather_cond.value,
            "precipitation_mm_h": precip,
            "visibility_km": vis,
            "temperature_c": temp,
            "congestion_index": traffic.congestion_index,
            "traffic_incidents": incidents,
            "active_drivers": drivers,
            "open_requests": requests,
            "dsr_ratio": round(requests / max(1, drivers), 2),
            "rider_loyalty": loyalty,
            "subtotal_base_fare": quote.subtotal_base,
            "weather_multiplier": quote.weather_multiplier,
            "traffic_multiplier": quote.traffic_multiplier,
            "dsr_multiplier": quote.dsr_multiplier,
            "time_multiplier": quote.time_multiplier,
            "total_surge_multiplier": quote.total_surge_multiplier,
            "final_fare": quote.final_fare,
            "driver_payout": quote.driver_payout,
            "platform_commission": quote.platform_commission,
            "acceptance_probability": quote.acceptance_probability,
            "is_accepted": is_accepted,
            "is_capped": 1 if quote.is_capped else 0,
        })

    fieldnames = list(records[0].keys())
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Successfully wrote {len(records)} records to {output_file.resolve()}")


if __name__ == "__main__":
    generate_dataset()
