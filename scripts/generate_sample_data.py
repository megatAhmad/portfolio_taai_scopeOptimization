"""
Script to generate sample maintenance data for MWCS.

Includes supporting datasets:
- Equipment Classification Master
- Work Type Categorization Reference
- Equipment Redundancy Master
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


def generate_equipment_classification_master() -> pd.DataFrame:
    """Generate Equipment Classification Master supporting dataset.

    This dataset maps equipment types to criticality classifications:
    - CRITICAL: Safety-critical, production-essential equipment
    - STANDARD: Normal operations equipment
    - LOW_PRIORITY: Non-essential, backup equipment
    """
    data = [
        # Critical Equipment
        {"Equipment Type": "Safety System", "Classification": "CRITICAL", "Priority Weight": 100, "Max Response Hours": 4, "Description": "Safety-critical systems requiring immediate attention"},
        {"Equipment Type": "Production Line", "Classification": "CRITICAL", "Priority Weight": 95, "Max Response Hours": 8, "Description": "Main production equipment"},
        {"Equipment Type": "Power Distribution", "Classification": "CRITICAL", "Priority Weight": 90, "Max Response Hours": 4, "Description": "Electrical distribution systems"},
        {"Equipment Type": "Fire Suppression", "Classification": "CRITICAL", "Priority Weight": 100, "Max Response Hours": 2, "Description": "Fire protection systems"},
        {"Equipment Type": "Emergency Generator", "Classification": "CRITICAL", "Priority Weight": 85, "Max Response Hours": 8, "Description": "Backup power systems"},

        # Standard Equipment
        {"Equipment Type": "Motor", "Classification": "STANDARD", "Priority Weight": 70, "Max Response Hours": 24, "Description": "General purpose motors"},
        {"Equipment Type": "Pump", "Classification": "STANDARD", "Priority Weight": 65, "Max Response Hours": 24, "Description": "Fluid handling pumps"},
        {"Equipment Type": "Conveyor", "Classification": "STANDARD", "Priority Weight": 60, "Max Response Hours": 48, "Description": "Material handling conveyors"},
        {"Equipment Type": "HVAC", "Classification": "STANDARD", "Priority Weight": 55, "Max Response Hours": 48, "Description": "Heating, ventilation, air conditioning"},
        {"Equipment Type": "Compressor", "Classification": "STANDARD", "Priority Weight": 60, "Max Response Hours": 24, "Description": "Air and gas compressors"},

        # Low Priority Equipment
        {"Equipment Type": "Lighting", "Classification": "LOW_PRIORITY", "Priority Weight": 30, "Max Response Hours": 168, "Description": "Non-essential lighting"},
        {"Equipment Type": "Sensor", "Classification": "LOW_PRIORITY", "Priority Weight": 40, "Max Response Hours": 72, "Description": "Monitoring sensors (non-critical)"},
        {"Equipment Type": "Office Equipment", "Classification": "LOW_PRIORITY", "Priority Weight": 20, "Max Response Hours": 168, "Description": "Office and administrative equipment"},
        {"Equipment Type": "Landscaping", "Classification": "LOW_PRIORITY", "Priority Weight": 10, "Max Response Hours": 336, "Description": "Grounds maintenance equipment"},
        {"Equipment Type": "Signage", "Classification": "LOW_PRIORITY", "Priority Weight": 15, "Max Response Hours": 168, "Description": "Signs and displays"},
    ]
    return pd.DataFrame(data)


def generate_work_type_categorization() -> pd.DataFrame:
    """Generate Work Type Categorization Reference supporting dataset.

    This dataset maps work categories to urgency classifications:
    - EMERGENCY: Immediate action required (safety/production impact)
    - PLANNED: Scheduled preventive/predictive maintenance
    - DEFERRED: Can be postponed without significant impact
    """
    data = [
        # Emergency Work Types
        {"Work Category": "Emergency Repair", "Work Type": "EMERGENCY", "Urgency Score": 100, "Max Delay Days": 0, "Budget Priority": "HIGH", "Description": "Unplanned repairs requiring immediate response"},
        {"Work Category": "Safety Issue", "Work Type": "EMERGENCY", "Urgency Score": 100, "Max Delay Days": 0, "Budget Priority": "HIGH", "Description": "Safety-related work items"},
        {"Work Category": "Production Stop", "Work Type": "EMERGENCY", "Urgency Score": 95, "Max Delay Days": 0, "Budget Priority": "HIGH", "Description": "Issues causing production stoppage"},
        {"Work Category": "Critical Failure", "Work Type": "EMERGENCY", "Urgency Score": 95, "Max Delay Days": 1, "Budget Priority": "HIGH", "Description": "Critical equipment failures"},

        # Planned Work Types
        {"Work Category": "Preventive Maintenance", "Work Type": "PLANNED", "Urgency Score": 60, "Max Delay Days": 14, "Budget Priority": "MEDIUM", "Description": "Scheduled preventive maintenance"},
        {"Work Category": "Corrective Maintenance", "Work Type": "PLANNED", "Urgency Score": 70, "Max Delay Days": 7, "Budget Priority": "MEDIUM", "Description": "Planned corrective actions"},
        {"Work Category": "Inspection", "Work Type": "PLANNED", "Urgency Score": 50, "Max Delay Days": 30, "Budget Priority": "MEDIUM", "Description": "Regular inspections"},
        {"Work Category": "Calibration", "Work Type": "PLANNED", "Urgency Score": 55, "Max Delay Days": 21, "Budget Priority": "MEDIUM", "Description": "Instrument calibration"},
        {"Work Category": "Testing", "Work Type": "PLANNED", "Urgency Score": 50, "Max Delay Days": 30, "Budget Priority": "MEDIUM", "Description": "Functional testing"},

        # Deferred Work Types
        {"Work Category": "Upgrade", "Work Type": "DEFERRED", "Urgency Score": 30, "Max Delay Days": 90, "Budget Priority": "LOW", "Description": "Equipment upgrades and improvements"},
        {"Work Category": "Cosmetic", "Work Type": "DEFERRED", "Urgency Score": 10, "Max Delay Days": 180, "Budget Priority": "LOW", "Description": "Cosmetic repairs and painting"},
        {"Work Category": "Documentation", "Work Type": "DEFERRED", "Urgency Score": 20, "Max Delay Days": 60, "Budget Priority": "LOW", "Description": "Documentation updates"},
        {"Work Category": "Training", "Work Type": "DEFERRED", "Urgency Score": 25, "Max Delay Days": 45, "Budget Priority": "LOW", "Description": "Training-related activities"},
        {"Work Category": "Minor Repair", "Work Type": "DEFERRED", "Urgency Score": 35, "Max Delay Days": 30, "Budget Priority": "LOW", "Description": "Non-urgent minor repairs"},
    ]
    return pd.DataFrame(data)


def generate_equipment_redundancy_master() -> pd.DataFrame:
    """Generate Equipment Redundancy Master supporting dataset.

    This dataset defines equipment redundancy levels:
    - NO_DEPENDENCY: Single point of failure, no backup
    - SINGLE_DEPENDENCY: One backup/alternate available
    - DUAL_DEPENDENCY: Multiple backups/alternates available
    - UNCERTAIN: Redundancy status unknown/needs assessment
    """
    random.seed(45)

    # Define equipment with redundancy levels
    equipment_redundancy = [
        # No Dependency (Single Point of Failure)
        {"Equipment ID": "EQ-001", "Equipment Name": "Main Power Transformer", "Redundancy Level": "NO_DEPENDENCY", "Backup Equipment": "", "Failover Time Hours": 0, "Risk Score": 100},
        {"Equipment ID": "EQ-002", "Equipment Name": "Central Control Server", "Redundancy Level": "NO_DEPENDENCY", "Backup Equipment": "", "Failover Time Hours": 0, "Risk Score": 95},
        {"Equipment ID": "EQ-003", "Equipment Name": "Main Production Press", "Redundancy Level": "NO_DEPENDENCY", "Backup Equipment": "", "Failover Time Hours": 0, "Risk Score": 90},

        # Single Dependency
        {"Equipment ID": "EQ-004", "Equipment Name": "Assembly Line Motor A", "Redundancy Level": "SINGLE_DEPENDENCY", "Backup Equipment": "EQ-005", "Failover Time Hours": 4, "Risk Score": 60},
        {"Equipment ID": "EQ-005", "Equipment Name": "Assembly Line Motor B", "Redundancy Level": "SINGLE_DEPENDENCY", "Backup Equipment": "EQ-004", "Failover Time Hours": 4, "Risk Score": 60},
        {"Equipment ID": "EQ-006", "Equipment Name": "Cooling Pump Primary", "Redundancy Level": "SINGLE_DEPENDENCY", "Backup Equipment": "EQ-007", "Failover Time Hours": 2, "Risk Score": 55},
        {"Equipment ID": "EQ-007", "Equipment Name": "Cooling Pump Secondary", "Redundancy Level": "SINGLE_DEPENDENCY", "Backup Equipment": "EQ-006", "Failover Time Hours": 2, "Risk Score": 55},

        # Dual Dependency
        {"Equipment ID": "EQ-008", "Equipment Name": "Network Switch A", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-009, EQ-010", "Failover Time Hours": 0.1, "Risk Score": 20},
        {"Equipment ID": "EQ-009", "Equipment Name": "Network Switch B", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-008, EQ-010", "Failover Time Hours": 0.1, "Risk Score": 20},
        {"Equipment ID": "EQ-010", "Equipment Name": "Network Switch C", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-008, EQ-009", "Failover Time Hours": 0.1, "Risk Score": 20},
        {"Equipment ID": "EQ-011", "Equipment Name": "Backup Generator 1", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-012, EQ-013", "Failover Time Hours": 0.5, "Risk Score": 25},
        {"Equipment ID": "EQ-012", "Equipment Name": "Backup Generator 2", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-011, EQ-013", "Failover Time Hours": 0.5, "Risk Score": 25},
        {"Equipment ID": "EQ-013", "Equipment Name": "Backup Generator 3", "Redundancy Level": "DUAL_DEPENDENCY", "Backup Equipment": "EQ-011, EQ-012", "Failover Time Hours": 0.5, "Risk Score": 25},

        # Uncertain (Needs Assessment)
        {"Equipment ID": "EQ-014", "Equipment Name": "Legacy Sensor Array", "Redundancy Level": "UNCERTAIN", "Backup Equipment": "TBD", "Failover Time Hours": -1, "Risk Score": 75},
        {"Equipment ID": "EQ-015", "Equipment Name": "Old Compressor Unit", "Redundancy Level": "UNCERTAIN", "Backup Equipment": "TBD", "Failover Time Hours": -1, "Risk Score": 70},
        {"Equipment ID": "EQ-016", "Equipment Name": "Custom Control Panel", "Redundancy Level": "UNCERTAIN", "Backup Equipment": "TBD", "Failover Time Hours": -1, "Risk Score": 80},
    ]

    return pd.DataFrame(equipment_redundancy)


def generate_availability_schedule() -> pd.DataFrame:
    """Generate availability schedule for resources."""
    data = []
    resource_types = ["Electrician", "Mechanic", "HVAC Tech", "Plumber", "General Labor"]

    for resource in resource_types:
        # Generate weekly availability
        base_hours = random.randint(30, 45)
        data.append({
            "Resource Type": resource,
            "Available Hours": base_hours,
            "Booked Hours": random.randint(10, base_hours - 5),
            "Hourly Rate": random.randint(50, 150),
            "Skill Level": random.choice(["Junior", "Mid", "Senior"]),
        })

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

    # Generate new supporting datasets
    equipment_class_df = generate_equipment_classification_master()
    work_type_df = generate_work_type_categorization()
    redundancy_df = generate_equipment_redundancy_master()
    availability_df = generate_availability_schedule()

    # Save to Excel with multiple sheets
    with pd.ExcelWriter(
        "sample_data/sample_maintenance_data.xlsx", engine="openpyxl"
    ) as writer:
        main_df.to_excel(writer, sheet_name="Maintenance Work", index=False)
        asset_df.to_excel(writer, sheet_name="Asset Registry", index=False)
        budget_df.to_excel(writer, sheet_name="Budget Data", index=False)
        equipment_class_df.to_excel(writer, sheet_name="Equipment Classification", index=False)
        work_type_df.to_excel(writer, sheet_name="Work Type Categorization", index=False)
        redundancy_df.to_excel(writer, sheet_name="Equipment Redundancy", index=False)
        availability_df.to_excel(writer, sheet_name="Availability", index=False)

    print("Sample data generated: sample_data/sample_maintenance_data.xlsx")
    print(f"  - Maintenance Work: {len(main_df)} rows")
    print(f"  - Asset Registry: {len(asset_df)} rows")
    print(f"  - Budget Data: {len(budget_df)} rows")
    print(f"  - Equipment Classification: {len(equipment_class_df)} rows")
    print(f"  - Work Type Categorization: {len(work_type_df)} rows")
    print(f"  - Equipment Redundancy: {len(redundancy_df)} rows")
    print(f"  - Availability: {len(availability_df)} rows")


if __name__ == "__main__":
    main()
