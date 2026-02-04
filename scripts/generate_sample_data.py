"""
Script to generate sample maintenance data for MWCS.
"""

import random
from datetime import datetime, timedelta

import pandas as pd


def generate_sample_data(num_rows: int = 100) -> pd.DataFrame:
    """Generate sample maintenance work items."""
    random.seed(42)

    categories = [
        "Preventive Maintenance",
        "Corrective Maintenance",
        "Emergency Repair",
        "Inspection",
        "Calibration",
        "Upgrade",
    ]

    priorities = ["High", "Medium", "Low"]
    risk_levels = ["Critical", "High", "Medium", "Low"]
    locations = [
        "Building A - Floor 1",
        "Building A - Floor 2",
        "Building B - Basement",
        "Building B - Floor 1",
        "Warehouse",
        "Outdoor Facility",
    ]

    descriptions = [
        "Replace worn bearings on conveyor system",
        "Inspect and clean HVAC filters",
        "Calibrate pressure sensors",
        "Repair hydraulic leak on press machine",
        "Upgrade control panel firmware",
        "Lubricate all moving parts on assembly line",
        "Replace damaged electrical wiring",
        "Test emergency stop systems",
        "Clean and inspect cooling tower",
        "Replace worn drive belts",
        "Repair water pump motor",
        "Inspect fire suppression system",
        "Replace faulty temperature sensors",
        "Service forklift hydraulic system",
        "Repair compressor unit",
        "Install new safety guards",
        "Replace lighting fixtures",
        "Service elevator mechanisms",
        "Repair roof drainage system",
        "Inspect structural supports",
    ]

    data = []

    for i in range(1, num_rows + 1):
        # Generate random dates within the past 2 years
        days_ago = random.randint(30, 730)
        last_service = datetime.now() - timedelta(days=days_ago)

        # Generate cost based on category and priority
        base_cost = random.randint(500, 5000)
        priority = random.choice(priorities)
        if priority == "High":
            base_cost *= 1.5
        elif priority == "Low":
            base_cost *= 0.7

        row = {
            "Work ID": f"WO-{i:05d}",
            "Description": random.choice(descriptions),
            "Priority": priority,
            "Category": random.choice(categories),
            "Estimated Hours": random.randint(1, 40),
            "Last Service Date": last_service.strftime("%Y-%m-%d"),
            "Asset ID": f"AST-{random.randint(1000, 9999)}",
            "Location": random.choice(locations),
            "Cost Estimate": round(base_cost, 2),
            "Risk Level": random.choice(risk_levels),
            "Dependencies": (
                f"WO-{random.randint(1, i):05d}" if random.random() > 0.7 else ""
            ),
        }
        data.append(row)

    return pd.DataFrame(data)


def generate_asset_registry(num_assets: int = 50) -> pd.DataFrame:
    """Generate a sample asset registry."""
    random.seed(43)

    asset_types = ["Motor", "Pump", "Conveyor", "HVAC", "Compressor", "Sensor"]
    criticalities = ["Critical", "High", "Medium", "Low"]

    data = []
    for i in range(1, num_assets + 1):
        data.append(
            {
                "Asset ID": f"AST-{1000 + i}",
                "Asset Name": f"{random.choice(asset_types)} Unit {i}",
                "Asset Type": random.choice(asset_types),
                "Criticality": random.choice(criticalities),
                "Install Date": (
                    datetime.now() - timedelta(days=random.randint(365, 3650))
                ).strftime("%Y-%m-%d"),
                "Expected Life (Years)": random.randint(5, 20),
            }
        )

    return pd.DataFrame(data)


def generate_budget_data() -> pd.DataFrame:
    """Generate sample budget data."""
    data = [
        {
            "Category": "Preventive Maintenance",
            "Annual Budget": 100000,
            "Spent YTD": 45000,
            "Remaining": 55000,
        },
        {
            "Category": "Corrective Maintenance",
            "Annual Budget": 75000,
            "Spent YTD": 30000,
            "Remaining": 45000,
        },
        {
            "Category": "Emergency Repair",
            "Annual Budget": 50000,
            "Spent YTD": 35000,
            "Remaining": 15000,
        },
        {
            "Category": "Inspection",
            "Annual Budget": 25000,
            "Spent YTD": 10000,
            "Remaining": 15000,
        },
        {
            "Category": "Calibration",
            "Annual Budget": 15000,
            "Spent YTD": 8000,
            "Remaining": 7000,
        },
        {
            "Category": "Upgrade",
            "Annual Budget": 60000,
            "Spent YTD": 20000,
            "Remaining": 40000,
        },
    ]
    return pd.DataFrame(data)


def main():
    """Generate and save sample data."""
    import os

    # Ensure sample_data directory exists
    os.makedirs("sample_data", exist_ok=True)

    # Generate data
    main_df = generate_sample_data(100)
    asset_df = generate_asset_registry(50)
    budget_df = generate_budget_data()

    # Save to Excel with multiple sheets
    with pd.ExcelWriter(
        "sample_data/sample_maintenance_data.xlsx", engine="openpyxl"
    ) as writer:
        main_df.to_excel(writer, sheet_name="Maintenance Work", index=False)
        asset_df.to_excel(writer, sheet_name="Asset Registry", index=False)
        budget_df.to_excel(writer, sheet_name="Budget Data", index=False)

    print("Sample data generated: sample_data/sample_maintenance_data.xlsx")
    print(f"  - Maintenance Work: {len(main_df)} rows")
    print(f"  - Asset Registry: {len(asset_df)} rows")
    print(f"  - Budget Data: {len(budget_df)} rows")


if __name__ == "__main__":
    main()
