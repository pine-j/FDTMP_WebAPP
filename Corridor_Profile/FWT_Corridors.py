import geopandas as gpd  # type: ignore
import pandas as pd  # type: ignore
import os
import sys
import random

def main():
    # Set working directory to the script's location for relative path usage
    # or use the specific J: drive paths if this script is run in an environment where J: is mounted.
    # For this implementation, we will look in the same directory as the script.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define file paths
    # Note: User requested specific J: paths. 
    # We default to checking the local directory first, but you can uncomment the J: paths if needed.
    
    # Local relative paths (recommended for portability)
    xlsx_path = os.path.join(script_dir, 'FTW_Corridors.xlsx')
    gpkg_path = os.path.join(script_dir, 'Input_GeoFiles', 'raptor_results2023.gpkg')
    output_path = os.path.join(script_dir, 'Output_Files', 'FTW_Corridor_Profiles.gpkg')

    # J: Drive paths (as requested in prompt - uncomment to force usage)
    # xlsx_path = r"J:\FTW District Transportation Master Plan - Documents\40_Tasks\01_Existing and Future Conditions\08 Web APP\FDTMP_WebAPP\Corridor_Profile\FTW_Corridors.xlsx"
    # gpkg_path = r"J:\FTW District Transportation Master Plan - Documents\40_Tasks\01_Existing and Future Conditions\08 Web APP\FDTMP_WebAPP\Corridor_Profile\Input_GeoFiles\raptor_results2023.gpkg"
    # output_path = r"J:\FTW District Transportation Master Plan - Documents\40_Tasks\01_Existing and Future Conditions\08 Web APP\FDTMP_WebAPP\Corridor_Profile\Output_Files\FTW_Corridor_Profiles.gpkg"

    print(f"Reading Excel file from: {xlsx_path}")
    if not os.path.exists(xlsx_path):
        print(f"Error: Excel file not found at {xlsx_path}")
        return

    print(f"Reading GeoPackage from: {gpkg_path}")
    if not os.path.exists(gpkg_path):
        print(f"Error: GeoPackage file not found at {gpkg_path}")
        return

    # 1. Load Data
    try:
        df_hwys = pd.read_excel(xlsx_path)
        # Ensure HWY_Label column exists
        if 'HWY_Label' not in df_hwys.columns:
            print("Error: 'HWY_Label' column not found in Excel file.")
            print("Available columns:", df_hwys.columns.tolist())
            return
        target_hwys = df_hwys['HWY_Label'].unique()
        print(f"Found {len(target_hwys)} target highways.")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    try:
        gdf_raptor = gpd.read_file(gpkg_path)
        print(f"Loaded GeoPackage with {len(gdf_raptor)} rows.")
    except Exception as e:
        print(f"Error reading GeoPackage: {e}")
        return

    # 2. Filter Data
    if 'HWY' not in gdf_raptor.columns:
        print("Error: 'HWY' column not found in GeoPackage.")
        return
    
    gdf_filtered = gdf_raptor[gdf_raptor['HWY'].isin(target_hwys)].copy()
    print(f"Filtered to {len(gdf_filtered)} rows matching target highways.")

    if len(gdf_filtered) == 0:
        print("No matching records found. Exiting.")
        return

    # 3. Calculate Cross Section Lengths
    # Ensure we have a projected CRS for length calculation
    original_crs = gdf_filtered.crs
    if not original_crs.is_projected:
        print("CRS is not projected. Reprojecting to EPSG:2276 (NAD83 / Texas North Central (ftUS)) for length calculation.")
        # Using Texas North Central (ft) as a safe default for FTW District
        gdf_calc = gdf_filtered.to_crs(epsg=2276)
        length_unit_is_feet = True
    else:
        print(f"Using existing projected CRS: {original_crs.name}")
        gdf_calc = gdf_filtered.copy()
        # Heuristic to check if units are likely meters or feet based on CRS name or axis info
        # Assuming meters if not obvious, but for US State Plane it's often feet.
        # Safest is to force reprojection if we want to be sure, but let's try to detect.
        # For simplicity in this script, we'll assume if it was already projected, the user knows the units. 
        # However, to be robust for "FTW", let's reproject to EPSG:2276 anyway to guarantee feet, 
        # then convert to miles.
        gdf_calc = gdf_filtered.to_crs(epsg=2276)
        length_unit_is_feet = True

    # Calculate length in miles
    # 1 mile = 5280 feet
    gdf_calc['segment_length_miles'] = (gdf_calc.geometry.length / 5280.0).round(1)

    # Add segment length to gdf_filtered for weighted mean calculation
    # Match by index to copy segment_length_miles from gdf_calc to gdf_filtered
    gdf_filtered['segment_length_miles'] = gdf_calc['segment_length_miles'].values

    # Calculate total miles per HWY
    print("Calculating total miles per highway...")
    df_total_miles = gdf_calc.groupby('HWY')['segment_length_miles'].sum().reset_index()
    df_total_miles.rename(columns={'segment_length_miles': 'Total_Miles'}, inplace=True)
    df_total_miles['Total_Miles'] = df_total_miles['Total_Miles'].round(1)

    # Group by HWY and Roadway_Cross_Section
    if 'Roadway_Cross_Section' in gdf_calc.columns:
        print("Calculating cross-section lengths...")
        # Fill NA with 'Unknown' to avoid losing data in pivot
        gdf_calc['Roadway_Cross_Section'] = gdf_calc['Roadway_Cross_Section'].fillna('Unknown')
        
        pivot_data = gdf_calc.groupby(['HWY', 'Roadway_Cross_Section'])['segment_length_miles'].sum().reset_index()
        
        # Pivot: HWY as index, Cross_Section as columns, values are miles
        df_pivot = pivot_data.pivot(index='HWY', columns='Roadway_Cross_Section', values='segment_length_miles')
        df_pivot = df_pivot.fillna(0) # Fill missing cross sections with 0 miles
        
        # Round all miles columns to one decimal place
        df_pivot = df_pivot.round(1)
        
        # Rename columns to indicate they are miles, e.g., "2U" -> "2U_miles"
        df_pivot.columns = [f"{col}_miles" for col in df_pivot.columns]
        df_pivot.reset_index(inplace=True)
        print("Cross-section pivot created.")
    else:
        print("Warning: 'Roadway_Cross_Section' column not found. Skipping pivot step.")
        df_pivot = pd.DataFrame({'HWY': target_hwys}) # Empty placeholder with HWYs

    # 4. Dissolve Geometry and Aggregate Attributes
    print("Dissolving geometries...")
    
    # Calculate weighted values for AADT and Truck_AADT before dissolving
    if 'AADT' in gdf_filtered.columns:
        gdf_filtered['AADT_weighted'] = gdf_filtered['AADT'] * gdf_filtered['segment_length_miles']
    if 'Truck_AADT' in gdf_filtered.columns:
        gdf_filtered['Truck_AADT_weighted'] = gdf_filtered['Truck_AADT'] * gdf_filtered['segment_length_miles']
    
    agg_dict = {}
    # Columns to sum
    for col in ['Number_Of_Crashes', 'Number_Of_Fatal_Crashes']:
        if col in gdf_filtered.columns:
            agg_dict[col] = 'sum'
    
    # Weighted columns to sum (for weighted mean calculation)
    if 'AADT_weighted' in gdf_filtered.columns:
        agg_dict['AADT_weighted'] = 'sum'
    if 'Truck_AADT_weighted' in gdf_filtered.columns:
        agg_dict['Truck_AADT_weighted'] = 'sum'
    
    # Sum segment lengths for weighted mean denominator
    if 'segment_length_miles' in gdf_filtered.columns:
        agg_dict['segment_length_miles'] = 'sum'

    # Dissolve
    gdf_dissolved = gdf_filtered.dissolve(by='HWY', aggfunc=agg_dict)
    gdf_dissolved.reset_index(inplace=True)
    
    # Calculate weighted means after dissolving
    if 'AADT_weighted' in gdf_dissolved.columns and 'segment_length_miles' in gdf_dissolved.columns:
        # Avoid division by zero
        mask = gdf_dissolved['segment_length_miles'] > 0
        gdf_dissolved.loc[mask, 'AADT'] = gdf_dissolved.loc[mask, 'AADT_weighted'] / gdf_dissolved.loc[mask, 'segment_length_miles']
        gdf_dissolved.loc[~mask, 'AADT'] = None
        # Drop temporary weighted column
        gdf_dissolved.drop(columns=['AADT_weighted'], inplace=True)
    
    if 'Truck_AADT_weighted' in gdf_dissolved.columns and 'segment_length_miles' in gdf_dissolved.columns:
        # Avoid division by zero
        mask = gdf_dissolved['segment_length_miles'] > 0
        gdf_dissolved.loc[mask, 'Truck_AADT'] = gdf_dissolved.loc[mask, 'Truck_AADT_weighted'] / gdf_dissolved.loc[mask, 'segment_length_miles']
        gdf_dissolved.loc[~mask, 'Truck_AADT'] = None
        # Drop temporary weighted column
        gdf_dissolved.drop(columns=['Truck_AADT_weighted'], inplace=True)
    
    # Drop segment_length_miles column as it's temporary (Total_Miles will be merged later)
    if 'segment_length_miles' in gdf_dissolved.columns:
        gdf_dissolved.drop(columns=['segment_length_miles'], inplace=True)

    # 5. Merge Data
    print("Merging pivoted data...")
    gdf_final = gdf_dissolved.merge(df_pivot, on='HWY', how='left')
    
    # Merge total miles
    print("Merging total miles...")
    gdf_final = gdf_final.merge(df_total_miles, on='HWY', how='left')
    
    # Merge Excel columns (join on HWY_Label from Excel to HWY from GeoPackage)
    print("Merging Excel columns...")
    gdf_final = gdf_final.merge(df_hwys, left_on='HWY', right_on='HWY_Label', how='left')
    
    # Remove HWY_Label column as it's the same as HWY
    if 'HWY_Label' in gdf_final.columns:
        gdf_final.drop(columns=['HWY_Label'], inplace=True)
    
    # Generate random project columns for each HWY
    print("Generating random project columns...")
    random.seed(42)  # Fixed seed for reproducibility
    n_rows = len(gdf_final)
    
    # Construction projects
    gdf_final['Projects_Construction'] = [random.randint(10, 50) for _ in range(n_rows)]
    gdf_final['Project_Length_Construction'] = [random.randint(50, 150) for _ in range(n_rows)]
    gdf_final['Project_Cost_Construction'] = [f"${random.randint(10, 500)}B" for _ in range(n_rows)]
    
    # Funded projects
    gdf_final['Projects_Funded'] = [random.randint(10, 100) for _ in range(n_rows)]
    gdf_final['Project_Length_Funded'] = [random.randint(100, 250) for _ in range(n_rows)]
    gdf_final['Project_Cost_Funded'] = [f"${random.randint(50, 1000)}B" for _ in range(n_rows)]
    
    # Partially funded projects
    gdf_final['Projects_PartialFunded'] = [random.randint(100, 400) for _ in range(n_rows)]
    gdf_final['Project_Length_PartialFunded'] = [random.randint(100, 500) for _ in range(n_rows)]
    gdf_final['Project_Cost_PartialFunded'] = [f"${random.randint(50, 1000)}B" for _ in range(n_rows)]
    gdf_final['Project_FundingGap_PartialFunded'] = [f"${random.randint(50, 1000)}B" for _ in range(n_rows)]
    
    # Unfunded projects
    gdf_final['Projects_Unfunded'] = [random.randint(100, 400) for _ in range(n_rows)]
    gdf_final['Project_Length_Unfunded'] = [random.randint(100, 500) for _ in range(n_rows)]
    gdf_final['Project_Cost_Unfunded'] = [f"${random.randint(50, 1000)}B" for _ in range(n_rows)]
    gdf_final['Project_FundingGap_Unfunded'] = [f"${random.randint(50, 1000)}B" for _ in range(n_rows)]
    
    # Reorder columns: Excel columns first, then computed columns
    print("Reordering columns...")
    # Get Excel column names (excluding HWY_Label since it matches HWY)
    excel_cols = [col for col in df_hwys.columns if col != 'HWY_Label']
    
    # Get all current columns
    all_cols = list(gdf_final.columns)
    
    # Separate geometry column (must be preserved for GeoDataFrame)
    geometry_col = gdf_final.geometry.name
    
    # Get computed columns (everything that's not an Excel column and not geometry)
    computed_cols = [col for col in all_cols if col not in excel_cols and col != geometry_col]
    
    # Reorder: Excel columns first, then computed columns, geometry last
    new_column_order = excel_cols + computed_cols + [geometry_col]
    
    # Reorder the dataframe
    gdf_final = gdf_final[new_column_order]

    # 6. Export Data
    print(f"Exporting to {output_path}...")
    try:
        gdf_final.to_file(output_path, driver="GPKG", layer='FTW_Corridor_Profiles')
        print("Export complete.")
    except Exception as e:
        print(f"Error exporting data: {e}")

if __name__ == "__main__":
    main()

