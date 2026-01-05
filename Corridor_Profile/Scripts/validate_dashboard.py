"""
Dashboard Validation Script for FTW Corridor Profiles

This script reads the FTW_Corridor_Profiles.gpkg file and generates an Excel spreadsheet
with all corridor profile metrics matching the ArcGIS Experience Builder dashboard display.

The output includes:
- One row per corridor with all metrics
- A final "TOTAL (All Corridors)" summary row with aggregated values
- Formatted numbers matching the dashboard display

Usage:
    python validate_dashboard.py

Output:
    Dashboard_Validation.xlsx in the Output_Files directory
"""

import geopandas as gpd
import pandas as pd
import os
import sys


def format_compact_currency(value):
    """
    Format a number as compact currency matching the Arcade formatCompact function.
    Examples: 1500 -> $1.5K, 1500000 -> $1.5M, 1500000000 -> $1.5B
    """
    if pd.isna(value) or value == 0:
        return "$0"
    
    abs_val = abs(value)
    
    if abs_val >= 1_000_000_000:
        return f"${round(value / 1_000_000_000, 1)}B"
    elif abs_val >= 1_000_000:
        return f"${round(value / 1_000_000, 1)}M"
    elif abs_val >= 1_000:
        return f"${round(value / 1_000, 1)}K"
    else:
        return f"${round(value, 1)}"


def format_compact_number(value):
    """
    Format a number as compact (without currency symbol) matching the Arcade FormatCompact function.
    Used for Tons display on the dashboard.
    Examples: 1500 -> 1.5K, 1500000 -> 1.5M, 1500000000 -> 1.5B, 500 -> 500
    """
    if pd.isna(value) or value == 0:
        return "0"
    
    abs_val = abs(value)
    
    if abs_val >= 1_000_000_000:
        result = round(value / 1_000_000_000, 1)
        # Remove trailing .0 if present
        return f"{result:g}B"
    elif abs_val >= 1_000_000:
        result = round(value / 1_000_000, 1)
        return f"{result:g}M"
    elif abs_val >= 1_000:
        result = round(value / 1_000, 1)
        return f"{result:g}K"
    else:
        result = round(value, 1)
        return f"{result:g}"


def main():
    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)  # Go up to Corridor_Profile directory
    
    gpkg_path = os.path.join(parent_dir, 'Output_Files', 'FTW_Corridor_Profiles.gpkg')
    output_path = os.path.join(parent_dir, 'Output_Files', 'Dashboard_Validation.xlsx')
    
    print(f"Reading GeoPackage from: {gpkg_path}")
    
    if not os.path.exists(gpkg_path):
        print(f"Error: GeoPackage file not found at {gpkg_path}")
        print("Please run FWT_Corridors.py first to generate the GeoPackage file.")
        sys.exit(1)
    
    # Read the GeoPackage
    try:
        gdf = gpd.read_file(gpkg_path)
        print(f"Loaded {len(gdf)} corridors from GeoPackage.")
    except Exception as e:
        print(f"Error reading GeoPackage: {e}")
        sys.exit(1)
    
    # Print available columns for debugging
    print(f"\nAvailable columns in GeoPackage:")
    for col in sorted(gdf.columns):
        print(f"  - {col}")
    print()
    
    # Define the columns we need and their display names
    # Map from GeoPackage column name to display name
    column_mapping = {
        # Corridor identification
        'HWY': 'Corridor',
        'Corridor': 'Corridor_Name',
        
        # Roadway metrics
        'Total_Miles': 'Total_Corridor_Length_mi',
        'two_L_miles': '2_Lanes_mi',
        'four_U_plus_miles': '4_Lanes_Undivided_mi',
        'four_D_plus_miles': '4+_Lanes_Divided_mi',
        
        # Traffic metrics
        'AADT': 'AADT',
        'Truck_AADT': 'Truck_AADT',
        'Truck_percentage': 'Truck_Percentage',
        'Tons': 'Tons',
        
        # Safety metrics
        'Number_Of_Crashes': 'Number_of_Crashes',
        'Number_Of_Fatal_Crashes': 'Number_of_Fatal_Crashes',
        
        # TxDOT Roadway Projects - Under Construction
        'Projects_Construction': 'Construction_Num_Projects',
        'Project_Cost_Construction': 'Construction_Est_Cost',
        
        # TxDOT Roadway Projects - Fully Funded
        'Projects_Funded': 'Funded_Num_Projects',
        'Project_Cost_Funded': 'Funded_Est_Cost',
        
        # TxDOT Roadway Projects - Partially Funded
        'Projects_PartialFunded': 'PartialFunded_Num_Projects',
        'Project_Cost_PartialFunded': 'PartialFunded_Est_Cost',
        'Project_FundingGap_PartialFunded': 'PartialFunded_Funding_Gap',
        
        # TxDOT Roadway Projects - Unfunded
        'Projects_Unfunded': 'Unfunded_Num_Projects',
        'Project_Cost_Unfunded': 'Unfunded_Est_Cost',
    }
    
    # Build the output dataframe with only available columns
    output_data = {}
    missing_columns = []
    
    for gpkg_col, display_name in column_mapping.items():
        if gpkg_col in gdf.columns:
            output_data[display_name] = gdf[gpkg_col].values
        else:
            missing_columns.append(gpkg_col)
    
    if missing_columns:
        print(f"Warning: The following columns were not found in the GeoPackage:")
        for col in missing_columns:
            print(f"  - {col}")
        print()
    
    df_output = pd.DataFrame(output_data)
    
    # Sort by corridor name if available
    if 'Corridor' in df_output.columns:
        # Try to sort by Order column if it exists
        if 'Order' in gdf.columns:
            df_output['_sort_order'] = gdf['Order'].values
            df_output = df_output.sort_values('_sort_order')
            df_output = df_output.drop(columns=['_sort_order'])
        else:
            df_output = df_output.sort_values('Corridor')
    
    # Reset index after sorting
    df_output = df_output.reset_index(drop=True)
    
    # Calculate the "All Corridors" summary row
    print("Calculating summary row for all corridors...")
    
    summary_row = {}
    
    # Corridor identification
    if 'Corridor' in df_output.columns:
        summary_row['Corridor'] = 'TOTAL (All Corridors)'
    if 'Corridor_Name' in df_output.columns:
        summary_row['Corridor_Name'] = 'All Corridors Summary'
    
    # Mileage columns - SUM
    mileage_cols = ['Total_Corridor_Length_mi', '2_Lanes_mi', '4_Lanes_Undivided_mi', '4+_Lanes_Divided_mi']
    for col in mileage_cols:
        if col in df_output.columns:
            summary_row[col] = round(df_output[col].sum(), 1)
    
    # Traffic metrics - Weighted Average
    # AADT: Weighted average = SUM(AADT * Total_Miles) / SUM(Total_Miles)
    if 'AADT' in df_output.columns and 'Total_Corridor_Length_mi' in df_output.columns:
        total_miles = df_output['Total_Corridor_Length_mi'].sum()
        if total_miles > 0:
            # Filter out rows where AADT is 0 or null for weighted average
            valid_mask = (df_output['AADT'].notna()) & (df_output['AADT'] > 0) & (df_output['Total_Corridor_Length_mi'] > 0)
            if valid_mask.any():
                weighted_sum = (df_output.loc[valid_mask, 'AADT'] * df_output.loc[valid_mask, 'Total_Corridor_Length_mi']).sum()
                valid_miles = df_output.loc[valid_mask, 'Total_Corridor_Length_mi'].sum()
                summary_row['AADT'] = round(weighted_sum / valid_miles, 0) if valid_miles > 0 else 0
            else:
                summary_row['AADT'] = 0
        else:
            summary_row['AADT'] = 0
    
    # Truck_AADT: Weighted average
    if 'Truck_AADT' in df_output.columns and 'Total_Corridor_Length_mi' in df_output.columns:
        total_miles = df_output['Total_Corridor_Length_mi'].sum()
        if total_miles > 0:
            valid_mask = (df_output['Truck_AADT'].notna()) & (df_output['Truck_AADT'] > 0) & (df_output['Total_Corridor_Length_mi'] > 0)
            if valid_mask.any():
                weighted_sum = (df_output.loc[valid_mask, 'Truck_AADT'] * df_output.loc[valid_mask, 'Total_Corridor_Length_mi']).sum()
                valid_miles = df_output.loc[valid_mask, 'Total_Corridor_Length_mi'].sum()
                summary_row['Truck_AADT'] = round(weighted_sum / valid_miles, 0) if valid_miles > 0 else 0
            else:
                summary_row['Truck_AADT'] = 0
        else:
            summary_row['Truck_AADT'] = 0
    
    # Truck_Percentage: Calculate from weighted averages
    if 'AADT' in summary_row and 'Truck_AADT' in summary_row:
        if summary_row['AADT'] > 0:
            summary_row['Truck_Percentage'] = round((summary_row['Truck_AADT'] / summary_row['AADT']) * 100, 1)
        else:
            summary_row['Truck_Percentage'] = 0
    
    # Tons: Weighted average (matching ArcadeScript logic - filter by Truck_AADT > 0)
    # The ArcadeScript in Truck_AADT.js uses: if (n_t_aadt > 0 && n_miles > 0)
    if 'Tons' in df_output.columns and 'Total_Corridor_Length_mi' in df_output.columns:
        if 'Truck_AADT' in df_output.columns:
            # Match ArcadeScript: filter by Truck_AADT > 0 (not Tons > 0)
            valid_mask = (df_output['Truck_AADT'].notna()) & (df_output['Truck_AADT'] > 0) & (df_output['Total_Corridor_Length_mi'] > 0)
            if valid_mask.any():
                weighted_sum = (df_output.loc[valid_mask, 'Tons'].fillna(0) * df_output.loc[valid_mask, 'Total_Corridor_Length_mi']).sum()
                valid_miles = df_output.loc[valid_mask, 'Total_Corridor_Length_mi'].sum()
                summary_row['Tons'] = round(weighted_sum / valid_miles, 1) if valid_miles > 0 else 0
            else:
                summary_row['Tons'] = 0
        else:
            summary_row['Tons'] = 0
    
    # Safety metrics - SUM
    safety_cols = ['Number_of_Crashes', 'Number_of_Fatal_Crashes']
    for col in safety_cols:
        if col in df_output.columns:
            summary_row[col] = int(df_output[col].sum())
    
    # Project counts - SUM
    project_count_cols = ['Construction_Num_Projects', 'Funded_Num_Projects', 
                          'PartialFunded_Num_Projects', 'Unfunded_Num_Projects']
    for col in project_count_cols:
        if col in df_output.columns:
            summary_row[col] = int(df_output[col].sum())
    
    # Project costs - SUM
    project_cost_cols = ['Construction_Est_Cost', 'Funded_Est_Cost', 
                         'PartialFunded_Est_Cost', 'PartialFunded_Funding_Gap', 
                         'Unfunded_Est_Cost']
    for col in project_cost_cols:
        if col in df_output.columns:
            summary_row[col] = round(df_output[col].sum(), 1)
    
    # Append summary row
    df_summary = pd.DataFrame([summary_row])
    df_final = pd.concat([df_output, df_summary], ignore_index=True)
    
    # Create a formatted version for display
    print("\nCreating formatted output...")
    
    # Export to Excel with two sheets:
    # 1. Raw data (for calculations/comparisons)
    # 2. Formatted data (matching dashboard display)
    
    print(f"\nExporting to: {output_path}")
    
    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Raw Data
            df_final.to_excel(writer, sheet_name='Raw_Data', index=False)
            
            # Sheet 2: Formatted Data (with compact currency formatting for costs)
            df_formatted = df_final.copy()
            
            # Format cost columns as compact currency
            cost_columns = ['Construction_Est_Cost', 'Funded_Est_Cost', 
                           'PartialFunded_Est_Cost', 'PartialFunded_Funding_Gap', 
                           'Unfunded_Est_Cost']
            for col in cost_columns:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(format_compact_currency)
            
            # Format percentage column
            if 'Truck_Percentage' in df_formatted.columns:
                df_formatted['Truck_Percentage'] = df_formatted['Truck_Percentage'].apply(
                    lambda x: f"{x:.1f}%" if pd.notna(x) else "0%"
                )
            
            # Format mileage columns
            mileage_cols = ['Total_Corridor_Length_mi', '2_Lanes_mi', '4_Lanes_Undivided_mi', '4+_Lanes_Divided_mi']
            for col in mileage_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(
                        lambda x: f"{x:.1f} mi" if pd.notna(x) else "0.0 mi"
                    )
            
            # Format AADT columns with commas
            aadt_cols = ['AADT', 'Truck_AADT']
            for col in aadt_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(
                        lambda x: f"{int(x):,}" if pd.notna(x) and x > 0 else "0"
                    )
            
            # Format Tons using compact format (matching dashboard: 0, 1.5K, 2M, etc.)
            if 'Tons' in df_formatted.columns:
                df_formatted['Tons'] = df_formatted['Tons'].apply(format_compact_number)
            
            # Format crash counts with commas
            crash_cols = ['Number_of_Crashes', 'Number_of_Fatal_Crashes']
            for col in crash_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(
                        lambda x: f"{int(x):,}" if pd.notna(x) else "0"
                    )
            
            # Format project counts
            project_count_cols = ['Construction_Num_Projects', 'Funded_Num_Projects', 
                                  'PartialFunded_Num_Projects', 'Unfunded_Num_Projects']
            for col in project_count_cols:
                if col in df_formatted.columns:
                    df_formatted[col] = df_formatted[col].apply(
                        lambda x: f"{int(x):,}" if pd.notna(x) else "0"
                    )
            
            df_formatted.to_excel(writer, sheet_name='Formatted_Display', index=False)
        
        print("Export complete!")
        print(f"\nOutput file: {output_path}")
        print(f"  - Sheet 'Raw_Data': Contains raw numeric values for calculations")
        print(f"  - Sheet 'Formatted_Display': Contains formatted values matching dashboard display")
        
    except Exception as e:
        print(f"Error exporting to Excel: {e}")
        sys.exit(1)
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS (All Corridors)")
    print("="*80)
    
    summary = df_final.iloc[-1]  # Last row is the summary
    
    print(f"\nTotal Corridors: {len(df_final) - 1}")
    
    if 'Total_Corridor_Length_mi' in summary:
        print(f"Total Corridor Length: {summary['Total_Corridor_Length_mi']:.1f} mi")
    
    if '2_Lanes_mi' in summary:
        print(f"  - 2 Lanes: {summary['2_Lanes_mi']:.1f} mi")
    if '4_Lanes_Undivided_mi' in summary:
        print(f"  - 4 Lanes Undivided: {summary['4_Lanes_Undivided_mi']:.1f} mi")
    if '4+_Lanes_Divided_mi' in summary:
        print(f"  - 4+ Lanes Divided: {summary['4+_Lanes_Divided_mi']:.1f} mi")
    
    if 'AADT' in summary:
        print(f"\nAADT (weighted avg): {summary['AADT']:,.0f}")
    if 'Truck_AADT' in summary:
        print(f"Truck AADT (weighted avg): {summary['Truck_AADT']:,.0f}")
    if 'Truck_Percentage' in summary:
        print(f"Truck Percentage: {summary['Truck_Percentage']:.1f}%")
    if 'Tons' in summary:
        print(f"Tons (weighted avg): {format_compact_number(summary['Tons'])}")
    
    if 'Number_of_Crashes' in summary:
        print(f"\nNumber of Crashes: {int(summary['Number_of_Crashes']):,}")
    if 'Number_of_Fatal_Crashes' in summary:
        print(f"Number of Fatal Crashes: {int(summary['Number_of_Fatal_Crashes']):,}")
    
    print("\nTxDOT Roadway Projects:")
    if 'Construction_Num_Projects' in summary:
        print(f"  Under Construction: {int(summary['Construction_Num_Projects']):,} projects, {format_compact_currency(summary['Construction_Est_Cost'])}")
    if 'Funded_Num_Projects' in summary:
        print(f"  Fully Funded: {int(summary['Funded_Num_Projects']):,} projects, {format_compact_currency(summary['Funded_Est_Cost'])}")
    if 'PartialFunded_Num_Projects' in summary:
        print(f"  Partially Funded: {int(summary['PartialFunded_Num_Projects']):,} projects, {format_compact_currency(summary['PartialFunded_Est_Cost'])}, Gap: {format_compact_currency(summary['PartialFunded_Funding_Gap'])}")
    if 'Unfunded_Num_Projects' in summary:
        print(f"  Unfunded: {int(summary['Unfunded_Num_Projects']):,} projects, {format_compact_currency(summary['Unfunded_Est_Cost'])}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
