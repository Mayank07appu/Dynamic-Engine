"""Exploratory analysis and econometric modeling of dynamic pricing.
Runs statistical sensitivity analysis on synthetic ride logs.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np


def run_analysis(dataset_path: str = "data/rides_synthetic_dataset.csv"):
    csv_file = Path(dataset_path)
    if not csv_file.exists():
        print(f"Dataset not found at {csv_file}. Run scripts/generate_synthetic_data.py first.")
        return

    df = pd.read_csv(csv_file)
    print("=" * 65)
    print("📊 PULSERIDE PRICING MODEL EXPLORATION & SENSITIVITY ANALYSIS")
    print("=" * 65)
    print(f"Total Evaluated Rides: {len(df):,}")
    print(f"Average Base Fare:     ${df['subtotal_base_fare'].mean():.2f}")
    print(f"Average Final Fare:    ${df['final_fare'].mean():.2f}")
    print(f"Average Surge Multiplier: {df['total_surge_multiplier'].mean():.2f}x (Max: {df['total_surge_multiplier'].max():.2f}x)")
    print(f"Average Acceptance Rate:  {df['acceptance_probability'].mean() * 100:.1f}%")
    print(f"Capped Rides Ratio:       {(df['is_capped'].sum() / len(df)) * 100:.2f}%")

    print("\n📈 SURGE IMPACT BREAKDOWN BY WEATHER CONDITION:")
    weather_grp = df.groupby("weather_condition")[["weather_multiplier", "total_surge_multiplier", "final_fare", "is_accepted"]].mean()
    print(weather_grp.round(2).to_string())

    print("\n🚦 SURGE CORRELATION MATRIX:")
    corr_cols = ["precipitation_mm_h", "congestion_index", "dsr_ratio", "total_surge_multiplier", "final_fare", "is_accepted"]
    corr = df[corr_cols].corr()
    print(corr.round(3).to_string())

    # Flat pricing vs Dynamic pricing GMV comparison
    # Flat pricing assumes multiplier = 1.0x with ~95% acceptance
    flat_gmv = (df["subtotal_base_fare"] * 0.95).sum()
    dynamic_gmv = (df["final_fare"] * df["is_accepted"]).sum()
    uplift_pct = ((dynamic_gmv - flat_gmv) / flat_gmv) * 100

    print("\n💰 REVENUE & GMV COMPARISON (DYNAMIC VS FLAT PRICING):")
    print(f"Simulated Flat Pricing GMV:    ${flat_gmv:,.2f}")
    print(f"Dynamic Pricing Realized GMV:  ${dynamic_gmv:,.2f}")
    print(f"Net Revenue Uplift:            +{uplift_pct:.2f}%")
    print("=" * 65)


if __name__ == "__main__":
    run_analysis()
