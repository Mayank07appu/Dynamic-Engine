"""High-throughput micro-benchmark for PulseRide dynamic pricing engine."""

import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pulseride.engine.pricing import DynamicPricingEngine
from pulseride.models.schemas import (
    RideRequest,
    WeatherConditions,
    WeatherCondition,
    TrafficData,
    ZoneID,
    VehicleTier,
)


def run_benchmark(iterations: int = 10000):
    print("=" * 60)
    print(f"⚡ Benchmarking PulseRide Dynamic Pricing Engine ({iterations:,} iterations)...")
    print("=" * 60)

    engine = DynamicPricingEngine()

    req = RideRequest(
        pickup_zone=ZoneID.DOWNTOWN,
        dropoff_zone=ZoneID.AIRPORT,
        vehicle_tier=VehicleTier.STANDARD,
        distance_km=14.2,
        duration_min=28.0,
        requested_at_hour=18,
        weather=WeatherConditions(
            condition=WeatherCondition.HEAVY_RAIN,
            precipitation_mm_h=22.5,
            visibility_km=3.5,
            wind_speed_kmh=35.0,
        ),
        traffic=TrafficData(
            congestion_index=0.72,
            free_flow_speed_kmh=50.0,
            current_speed_kmh=20.0,
            incidents_count=1,
            delay_per_km_min=0.8,
        ),
        custom_active_drivers=25,
        custom_open_requests=45,
    )

    # Warmup
    for _ in range(500):
        engine.quote_ride(req)

    # Timed run
    start_time = time.perf_counter()
    for _ in range(iterations):
        engine.quote_ride(req)
    total_time = time.perf_counter() - start_time

    ops_per_sec = iterations / total_time
    avg_latency_us = (total_time / iterations) * 1_000_000

    print(f"Total Time:      {total_time:.4f} seconds")
    print(f"Throughput:      {ops_per_sec:,.0f} quotes/second")
    print(f"Avg Latency:     {avg_latency_us:.2f} microseconds per quote ({avg_latency_us / 1000:.4f} ms)")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
