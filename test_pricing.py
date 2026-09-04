"""Unit tests for the PulseRide dynamic pricing engine and scoring components."""

import pytest
from pulseride.models.schemas import (
    VehicleTier,
    WeatherConditions,
    WeatherCondition,
    TrafficData,
    RideRequest,
    ZoneID,
)
from pulseride.engine.weather import WeatherScorer
from pulseride.engine.traffic import TrafficScorer
from pulseride.engine.elasticity import ElasticityModel
from pulseride.engine.pricing import DynamicPricingEngine


class TestWeatherScorer:
    def test_clear_weather_zero_delta(self):
        clear = WeatherConditions(condition=WeatherCondition.CLEAR, precipitation_mm_h=0.0)
        delta, score, explanations = WeatherScorer.calculate_surge(clear)
        assert delta == 0.0
        assert score == 0.0

    def test_heavy_rain_escalation(self):
        rain = WeatherConditions(condition=WeatherCondition.HEAVY_RAIN, precipitation_mm_h=30.0)
        delta, score, explanations = WeatherScorer.calculate_surge(rain)
        assert delta > 0.40
        assert score > 0.30
        assert len(explanations) > 0

    def test_thunderstorm_and_visibility(self):
        storm = WeatherConditions(
            condition=WeatherCondition.THUNDERSTORM,
            precipitation_mm_h=50.0,
            visibility_km=1.0,
            wind_speed_kmh=75.0,
        )
        delta, score, explanations = WeatherScorer.calculate_surge(storm)
        assert delta >= 0.80
        assert any("visibility" in e.lower() for e in explanations)
        assert any("winds" in e.lower() for e in explanations)

    def test_subzero_freezing_hazard(self):
        freezing = WeatherConditions(
            condition=WeatherCondition.SNOW,
            temperature_c=-10.0,
            precipitation_mm_h=10.0,
        )
        delta, score, explanations = WeatherScorer.calculate_surge(freezing)
        assert delta > 0.4
        assert any("freezing" in e.lower() for e in explanations)


class TestTrafficScorer:
    def test_free_flow_traffic(self):
        light_traffic = TrafficData(congestion_index=0.10, current_speed_kmh=50.0, free_flow_speed_kmh=50.0)
        delta, score, explanations = TrafficScorer.calculate_surge(light_traffic)
        assert delta < 0.05

    def test_heavy_congestion_and_speed_deficit(self):
        heavy = TrafficData(
            congestion_index=0.85,
            current_speed_kmh=12.0,
            free_flow_speed_kmh=50.0,
            incidents_count=2,
        )
        delta, score, explanations = TrafficScorer.calculate_surge(heavy)
        assert delta > 0.60
        assert any("bottlenecks" in e.lower() for e in explanations)
        assert any("incident" in e.lower() for e in explanations)


class TestElasticityModel:
    def test_high_acceptance_at_1x(self):
        prob = ElasticityModel.calculate_acceptance_probability(1.0)
        assert prob > 0.85

    def test_drop_in_acceptance_at_high_surge(self):
        prob = ElasticityModel.calculate_acceptance_probability(3.2)
        assert prob < 0.15

    def test_optimal_multiplier_discovery(self):
        opt_m, max_gmv, opt_prob = ElasticityModel.find_optimal_multiplier(base_fare=20.0)
        assert 1.4 <= opt_m <= 2.2
        assert max_gmv > 20.0
        assert 0.3 <= opt_prob <= 0.8


class TestDynamicPricingEngine:
    @pytest.fixture
    def engine(self):
        return DynamicPricingEngine(surge_cap=3.50)

    def test_baseline_standard_quote(self, engine):
        req = RideRequest(
            pickup_zone=ZoneID.DOWNTOWN,
            dropoff_zone=ZoneID.AIRPORT,
            vehicle_tier=VehicleTier.STANDARD,
            distance_km=10.0,
            duration_min=20.0,
            requested_at_hour=14,  # Non-rush
            weather=WeatherConditions(condition=WeatherCondition.CLEAR),
            traffic=TrafficData(congestion_index=0.15),
            custom_active_drivers=40,
            custom_open_requests=30,
        )
        quote = engine.quote_ride(req)
        # Base pickup: $3.00 + 10 * 1.25 + 20 * 0.35 = 3 + 12.5 + 7 = 22.50
        assert quote.subtotal_base == 22.50
        assert quote.total_surge_multiplier == 1.00
        assert quote.final_fare == 22.50
        assert quote.driver_payout > 0
        assert quote.platform_commission > 0
        assert quote.is_capped is False

    def test_surge_clamping_at_ceiling(self, engine):
        req = RideRequest(
            pickup_zone=ZoneID.DOWNTOWN,
            dropoff_zone=ZoneID.AIRPORT,
            vehicle_tier=VehicleTier.STANDARD,
            distance_km=10.0,
            duration_min=20.0,
            requested_at_hour=18,  # Peak evening rush (+0.25x)
            weather=WeatherConditions(
                condition=WeatherCondition.BLIZZARD,
                precipitation_mm_h=70.0,
                visibility_km=0.5,
                wind_speed_kmh=80.0,
                temperature_c=-15.0,
            ),
            traffic=TrafficData(
                congestion_index=0.98,
                current_speed_kmh=5.0,
                free_flow_speed_kmh=50.0,
                incidents_count=4,
            ),
            custom_active_drivers=5,
            custom_open_requests=100,  # DSR 20.0
        )
        quote = engine.quote_ride(req)
        assert quote.total_surge_multiplier == 3.50
        assert quote.is_capped is True
        assert quote.final_fare == round(quote.subtotal_base * 3.50, 2)
        assert any("statutory" in e.lower() or "fair limit" in e.lower() for e in quote.explanations)

    def test_driver_hardship_incentive(self, engine):
        req_normal = RideRequest(
            distance_km=10.0, duration_min=20.0, requested_at_hour=12,
            weather=WeatherConditions(condition=WeatherCondition.CLEAR),
            traffic=TrafficData(congestion_index=0.1),
            custom_active_drivers=50, custom_open_requests=20
        )
        req_storm = RideRequest(
            distance_km=10.0, duration_min=20.0, requested_at_hour=12,
            weather=WeatherConditions(condition=WeatherCondition.THUNDERSTORM, precipitation_mm_h=35.0),
            traffic=TrafficData(congestion_index=0.7),
            custom_active_drivers=15, custom_open_requests=40
        )
        quote_normal = engine.quote_ride(req_normal)
        quote_storm = engine.quote_ride(req_storm)

        # Storm driver payout must be significantly higher
        assert quote_storm.driver_payout > quote_normal.driver_payout
        # Driver gets >= 80% of surge increment
        surge_diff = quote_storm.final_fare - quote_normal.final_fare
        payout_diff = quote_storm.driver_payout - quote_normal.driver_payout
        assert payout_diff >= (surge_diff * 0.75)
