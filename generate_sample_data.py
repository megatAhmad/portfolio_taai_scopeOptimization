import pandas as pd
import os

def generate_datasets():
    # Create sample_data directory
    os.makedirs("sample_data", exist_ok=True)

    # 1. Original Equipment List (Canonical)
    equipment = [
        {"Equipment_ID": "P-101A", "Description": "Main Feed Pump A", "System": "Feedwater"},
        {"Equipment_ID": "P-101B", "Description": "Main Feed Pump B", "System": "Feedwater"},
        {"Equipment_ID": "HX-205", "Description": "Heat Exchanger Subcooler", "System": "Cooling"},
        {"Equipment_ID": "V-301", "Description": "Surge Vessel", "System": "Storage"},
        {"Equipment_ID": "C-400A", "Description": "Primary Compressor A", "System": "Compression"},
        {"Equipment_ID": "C-400B", "Description": "Primary Compressor B", "System": "Compression"},
        {"Equipment_ID": "FT-505", "Description": "Flow Transmitter", "System": "Instrumentation"},
        {"Equipment_ID": "PSV-901", "Description": "Pressure Safety Valve Main", "System": "Safety"},
        {"Equipment_ID": "M-600", "Description": "Agitator Motor", "System": "Mixing"},
    ]
    df_orig = pd.DataFrame(equipment)
    df_orig.to_csv("sample_data/original_equipment_list.csv", index=False)

    # 2. Criticality Master (Contains slight variations in IDs)
    criticality = [
        {"Eq_Tag": "P101-A", "Criticality_Rating": "A1", "Notes": "High priority"}, # Dirty ID (missing hyphen in prefix, added to suffix)
        {"Eq_Tag": "P-101B", "Criticality_Rating": "B2", "Notes": "Standard"},
        {"Eq_Tag": "HX205", "Criticality_Rating": "A2", "Notes": "Fouling risk"},  # Dirty ID (missing hyphen)
        {"Eq_Tag": "V-301", "Criticality_Rating": "C3", "Notes": "Low priority"},
        {"Eq_Tag": "C 400A", "Criticality_Rating": "A1", "Notes": "Vibration issues"}, # Dirty ID (space instead of hyphen)
        {"Eq_Tag": "C-400B", "Criticality_Rating": "B1", "Notes": "Backup unit"},
    ]
    df_crit = pd.DataFrame(criticality)
    df_crit.to_csv("sample_data/criticality_master.csv", index=False)

    # 3. Regulatory Compliance (Different column naming for IDs)
    regulatory = [
        {"TagNo": "PSV-901", "Reg_Category": "MANDATORY", "Inspection_Freq": "12mo"}, 
        {"TagNo": "P-101A", "Reg_Category": "COMPLIANCE", "Inspection_Freq": "24mo"},
        {"TagNo": "FT-505", "Reg_Category": "MANDATORY", "Inspection_Freq": "6mo"},
        {"TagNo": "HX-205", "Reg_Category": "OPTIONAL", "Inspection_Freq": "60mo"},
    ]
    df_reg = pd.DataFrame(regulatory)
    df_reg.to_csv("sample_data/regulatory_compliance.csv", index=False)

    # 4. Historical Scope (Contains very dirty/semantic variations)
    historical = [
        {"Asset_ID": "P-101A", "Previous_Scope": "RECOMMENDED", "Last_Maintained": "2023"},
        {"Asset_ID": "Pump 101B", "Previous_Scope": "DEFERRED", "Last_Maintained": "2021"}, # Very dirty ID (semantic abbreviation)
        {"Asset_ID": "C-400A", "Previous_Scope": "RECOMMENDED", "Last_Maintained": "2022"},
        {"Asset_ID": "C-400B", "Previous_Scope": "RECOMMENDED", "Last_Maintained": "2024"},
        {"Asset_ID": "M-600", "Previous_Scope": "DEFERRED", "Last_Maintained": "2019"},
    ]
    df_hist = pd.DataFrame(historical)
    df_hist.to_csv("sample_data/historical_scope.csv", index=False)

    print("Successfully generated 4 sample datasets in the 'sample_data/' directory:")
    print(" - original_equipment_list.csv (Clean Master Data)")
    print(" - criticality_master.csv (Contains slight ID formatting noise and 'A1', 'B2' ratings)")
    print(" - regulatory_compliance.csv (Contains 'MANDATORY' / 'COMPLIANCE' categorizations)")
    print(" - historical_scope.csv (Contains highly varied semantic IDs like 'Pump 101B')")

if __name__ == "__main__":
    generate_datasets()
