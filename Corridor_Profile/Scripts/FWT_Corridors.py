import geopandas as gpd  # type: ignore
import pandas as pd  # type: ignore
import os
import sys
import random
import shutil
import tempfile
import time

def read_excel_safe(path, sheet_name, **kwargs):
    """
    Attempts to read an Excel file. If permission is denied (e.g., file open),
    tries to copy it to a temporary location and read from there.
    """
    try:
        return pd.read_excel(path, sheet_name=sheet_name, **kwargs)
    except PermissionError:
        print(f"Permission denied for {path}. File might be open. Attempting to read from temporary copy...")
        
        # Create a temp file with same extension
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_copy_{int(time.time())}_{os.path.basename(path)}")
        
        try:
            shutil.copy2(path, temp_path)
            print(f"Copied to temporary file: {temp_path}")
            df = pd.read_excel(temp_path, sheet_name=sheet_name, **kwargs)
            
            # Try to clean up (might fail if still held, but usually ok)
            try:
                os.remove(temp_path)
            except Exception:
                pass
                
            return df
        except Exception as e:
            print(f"Failed to read from temporary copy: {e}")
            raise e

def main():
    # Set working directory to the script's location for relative path usage
    # or use the specific J: drive paths if this script is run in an environment where J: is mounted.
    # For this implementation, we will look in the parent directory (Corridor_Profile).
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)  # Go up to Corridor_Profile directory
    
    # Define file paths
    # Note: User requested specific J: paths. 
    # We default to checking the local directory first, but you can uncomment the J: paths if needed.
    
    # Local relative paths (recommended for portability)
    xlsx_path = os.path.join(parent_dir, 'Input_Files', 'FTW_Corridors.xlsx')
    gpkg_path = os.path.join(parent_dir, 'Input_Files', 'raptor_results_FTW.gpkg')
    output_path = os.path.join(parent_dir, 'Output_Files', 'FTW_Corridor_Profiles.gpkg')

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
        df_hwys = read_excel_safe(xlsx_path, sheet_name=0)
        
        # Check required columns exist in FTW_Corridors.xlsx
        required_xlsx_columns = ['Order', 'HWY_Code', 'HWY_Description', 'Corridor', 'HWY_Label', 'HWY_Shield']
        missing_xlsx_cols = [col for col in required_xlsx_columns if col not in df_hwys.columns]
        
        if missing_xlsx_cols:
            print("\n" + "="*80)
            print("ERROR: Missing required columns in FTW_Corridors.xlsx!")
            print("="*80)
            print(f"\nFile: {xlsx_path}")
            print(f"\nMissing columns: {missing_xlsx_cols}")
            print(f"\nRequired columns: {required_xlsx_columns}")
            print(f"\nAvailable columns in file:")
            for col in sorted(df_hwys.columns):
                print(f"  - {col}")
            print("\n" + "="*80)
            sys.exit(1)
        
        target_hwys = df_hwys['HWY_Label'].unique()
        print(f"Found {len(target_hwys)} target highways.")
        
        # Extract corridor names for project matching
        target_corridors = df_hwys['Corridor'].unique()
        # Create mapping from Corridor to HWY_Label for project aggregation
        corridor_to_hwy = dict(zip(df_hwys['Corridor'], df_hwys['HWY_Label']))
        print(f"Found {len(target_corridors)} target corridors for project matching.")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    try:
        gdf_raptor = gpd.read_file(gpkg_path)
        print(f"Loaded GeoPackage with {len(gdf_raptor)} rows.")
        
        # Define required columns for GeoPackage (before renaming)
        required_gpkg_columns = {
            'HWY': 'HWY',
            'Annual_Average_Daily_Traffic': 'AADT',
            'Truck_AADT': 'Truck_AADT',
            'Truck_Tonnage': 'Tons',
            'Roadway_Cross_Section': 'Roadway_Cross_Section',
            'Number_Of_Crashes': 'Number_Of_Crashes',
            'Number_Of_Fatal_Crashes': 'Number_Of_Fatal_Crashes'
        }
        
        # Check for missing required columns
        missing_columns = [col for col in required_gpkg_columns.keys() if col not in gdf_raptor.columns]
        if missing_columns:
            print("\n" + "="*80)
            print("ERROR: Missing required columns in GeoPackage file!")
            print("="*80)
            print(f"\nFile: {gpkg_path}")
            print(f"\nMissing columns: {missing_columns}")
            print(f"\nRequired columns: {list(required_gpkg_columns.keys())}")
            print(f"\nAvailable columns in file:")
            for col in sorted(gdf_raptor.columns):
                print(f"  - {col}")
            print("\n" + "="*80)
            sys.exit(1)
        
        # Rename columns to match expected names
        column_mapping = {
            'Annual_Average_Daily_Traffic': 'AADT',
            'Truck_Tonnage': 'Tons'
        }
        # Only rename columns that exist
        existing_renames = {k: v for k, v in column_mapping.items() if k in gdf_raptor.columns}
        if existing_renames:
            gdf_raptor.rename(columns=existing_renames, inplace=True)
            print(f"Renamed columns: {existing_renames}")
        
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
        
        # Rename columns to indicate they are miles, e.g., "2U" -> "two_U_miles"
        # Sanitize column names: replace + with _plus for Arcade compatibility
        # Also rename starting numbers 2 and 4 to text to avoid Arcade issues
        new_cols = []
        for col in df_pivot.columns:
            sanitized = col.replace('+', '_plus')
            if sanitized.startswith('2'):
                sanitized = "two_" + sanitized[1:]
            elif sanitized.startswith('4'):
                sanitized = "four_" + sanitized[1:]
            new_cols.append(f"{sanitized}_miles")
        df_pivot.columns = new_cols
        df_pivot.reset_index(inplace=True)
        print("Cross-section pivot created.")
    else:
        print("Warning: 'Roadway_Cross_Section' column not found. Skipping pivot step.")
        df_pivot = pd.DataFrame({'HWY': target_hwys}) # Empty placeholder with HWYs

    # 4. Dissolve Geometry and Aggregate Attributes
    print("Dissolving geometries...")
    
    # Calculate weighted values for AADT and Truck_AADT before dissolving
    if 'AADT' in gdf_filtered.columns:
        print(f"DEBUG: AADT column found. Sample values: {gdf_filtered['AADT'].head().tolist()}")
        gdf_filtered['AADT_weighted'] = gdf_filtered['AADT'] * gdf_filtered['segment_length_miles']
        print(f"DEBUG: AADT_weighted created. Sample values: {gdf_filtered['AADT_weighted'].head().tolist()}")
    else:
        print("WARNING: AADT column not found in filtered data!")
    if 'Truck_AADT' in gdf_filtered.columns:
        gdf_filtered['Truck_AADT_weighted'] = gdf_filtered['Truck_AADT'] * gdf_filtered['segment_length_miles']
    if 'Tons' in gdf_filtered.columns:
        gdf_filtered['Tons_weighted'] = gdf_filtered['Tons'] * gdf_filtered['segment_length_miles']
    
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
    if 'Tons_weighted' in gdf_filtered.columns:
        agg_dict['Tons_weighted'] = 'sum'
    
    # Sum segment lengths for weighted mean denominator
    if 'segment_length_miles' in gdf_filtered.columns:
        agg_dict['segment_length_miles'] = 'sum'

    # Dissolve
    gdf_dissolved = gdf_filtered.dissolve(by='HWY', aggfunc=agg_dict)
    gdf_dissolved.reset_index(inplace=True)
    
    # Calculate weighted means after dissolving
    if 'AADT_weighted' in gdf_dissolved.columns and 'segment_length_miles' in gdf_dissolved.columns:
        print(f"DEBUG: Calculating AADT weighted means...")
        print(f"DEBUG: AADT_weighted sum sample: {gdf_dissolved['AADT_weighted'].head().tolist()}")
        print(f"DEBUG: segment_length_miles sum sample: {gdf_dissolved['segment_length_miles'].head().tolist()}")
        # Avoid division by zero
        mask = gdf_dissolved['segment_length_miles'] > 0
        gdf_dissolved.loc[mask, 'AADT'] = (gdf_dissolved.loc[mask, 'AADT_weighted'] / gdf_dissolved.loc[mask, 'segment_length_miles']).round(0)
        gdf_dissolved.loc[~mask, 'AADT'] = None
        print(f"DEBUG: Final AADT values: {gdf_dissolved['AADT'].head().tolist()}")
        print(f"DEBUG: AADT column in gdf_dissolved: {'AADT' in gdf_dissolved.columns}")
        # Drop temporary weighted column
        gdf_dissolved.drop(columns=['AADT_weighted'], inplace=True)
    else:
        print("WARNING: Cannot calculate AADT - missing AADT_weighted or segment_length_miles columns!")
    
    if 'Truck_AADT_weighted' in gdf_dissolved.columns and 'segment_length_miles' in gdf_dissolved.columns:
        # Avoid division by zero
        mask = gdf_dissolved['segment_length_miles'] > 0
        gdf_dissolved.loc[mask, 'Truck_AADT'] = gdf_dissolved.loc[mask, 'Truck_AADT_weighted'] / gdf_dissolved.loc[mask, 'segment_length_miles']
        gdf_dissolved.loc[~mask, 'Truck_AADT'] = None
        # Drop temporary weighted column
        gdf_dissolved.drop(columns=['Truck_AADT_weighted'], inplace=True)
    
    if 'Tons_weighted' in gdf_dissolved.columns and 'segment_length_miles' in gdf_dissolved.columns:
        # Avoid division by zero
        mask = gdf_dissolved['segment_length_miles'] > 0
        gdf_dissolved.loc[mask, 'Tons'] = gdf_dissolved.loc[mask, 'Tons_weighted'] / gdf_dissolved.loc[mask, 'segment_length_miles']
        gdf_dissolved.loc[~mask, 'Tons'] = None
        # Round to 1 decimal place
        gdf_dissolved['Tons'] = gdf_dissolved['Tons'].round(1)
        # Drop temporary weighted column
        gdf_dissolved.drop(columns=['Tons_weighted'], inplace=True)
    
    # Calculate Truck_percentage after weighted averages
    if 'Truck_AADT' in gdf_dissolved.columns and 'AADT' in gdf_dissolved.columns:
        # Avoid division by zero and handle None values
        mask = (gdf_dissolved['AADT'].notna()) & (gdf_dissolved['AADT'] > 0)
        gdf_dissolved.loc[mask, 'Truck_percentage'] = (gdf_dissolved.loc[mask, 'Truck_AADT'] / gdf_dissolved.loc[mask, 'AADT']) * 100
        gdf_dissolved.loc[~mask, 'Truck_percentage'] = None
        # Round to 1 decimal place
        gdf_dissolved['Truck_percentage'] = gdf_dissolved['Truck_percentage'].round(1)
    
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
    
    # Load project data from master Excel file
    print("Loading project data from master Excel file...")
    project_excel_path = r"J:\FTW District Transportation Master Plan - Documents\70_Shared_FTW_Deliverables\06_District_Project_List\FTW District Project Tracker - Master.xlsx"
    
    if not os.path.exists(project_excel_path):
        print("\n" + "="*80)
        print("ERROR: Required project Excel file not found!")
        print("="*80)
        print(f"\nExpected location: {project_excel_path}")
        print("\nThis file is required for corridor project data enrichment.")
        print("Please ensure the file exists and the J: drive is accessible.")
        print("\n" + "="*80)
        sys.exit(1)
    else:
        # Read Construction Projects Sheet
        print("Reading Under_Construction_June2025 sheet...")
        try:
            df_construction = read_excel_safe(project_excel_path, sheet_name='Under_Construction_June2025')
        except ValueError as e:
            print("\n" + "="*80)
            print("ERROR: Required sheet 'Under_Construction_June2025' not found!")
            print("="*80)
            print(f"\nFile: {project_excel_path}")
            print(f"\nError: {e}")
            print("\nPlease verify the sheet name matches exactly (case-sensitive).")
            print("\n" + "="*80)
            sys.exit(1)
        except Exception as e:
            print(f"\nError reading Under_Construction_June2025 sheet: {e}")
            sys.exit(1)
        
        try:
            # Check required columns exist
            required_construction_columns = ['Highway', 'CSJ', 'Construction Cost/Estimate']
            missing_construction_cols = [col for col in required_construction_columns if col not in df_construction.columns]
            
            if missing_construction_cols:
                print("\n" + "="*80)
                print("ERROR: Missing required columns in Under_Construction_June2025 sheet!")
                print("="*80)
                print(f"\nFile: {project_excel_path}")
                print(f"Sheet: Under_Construction_June2025")
                print(f"\nMissing columns: {missing_construction_cols}")
                print(f"\nRequired columns: {required_construction_columns}")
                print(f"\nAvailable columns in sheet:")
                for col in sorted(df_construction.columns):
                    print(f"  - {col}")
                print("\n" + "="*80)
                sys.exit(1)
            
            if 'Highway' in df_construction.columns and 'CSJ' in df_construction.columns and 'Construction Cost/Estimate' in df_construction.columns:
                # Check for duplicate CSJs
                duplicate_csjs = df_construction[df_construction['CSJ'].duplicated(keep=False)]
                if len(duplicate_csjs) > 0:
                    print("\n" + "="*80)
                    print("ERROR: Duplicate CSJs found in Under_Construction_June2025 sheet!")
                    print("="*80)
                    print(f"\nFile: {project_excel_path}")
                    print(f"Sheet: Under_Construction_June2025")
                    print(f"\nDuplicate CSJs:")
                    for csj in duplicate_csjs['CSJ'].unique():
                        count = len(df_construction[df_construction['CSJ'] == csj])
                        print(f"  - {csj} (appears {count} times)")
                    print("\nEach CSJ must be unique. Please remove or consolidate duplicate entries.")
                    print("\n" + "="*80)
                    sys.exit(1)
                
                # Filter projects that match target corridors
                df_construction_filtered = df_construction[df_construction['Highway'].isin(target_corridors)].copy()
                
                # Map corridor names to HWY labels
                df_construction_filtered['HWY'] = df_construction_filtered['Highway'].map(corridor_to_hwy)
                
                # Group by HWY, count unique CSJ, sum Construction Cost/Estimate
                construction_summary = df_construction_filtered.groupby('HWY').agg({
                    'CSJ': 'nunique',
                    'Construction Cost/Estimate': lambda x: x.sum()
                }).reset_index()
                
                construction_summary.columns = ['HWY', 'Projects_Construction', 'Project_Cost_Construction']
                
                # Round cost to 1 decimal place
                construction_summary['Project_Cost_Construction'] = construction_summary['Project_Cost_Construction'].round(1)
                
                print(f"Found {len(construction_summary)} highways with construction projects.")
            else:
                print("\n" + "="*80)
                print("ERROR: Required columns not found in Under_Construction_June2025 sheet!")
                print("="*80)
                print(f"\nRequired columns: {required_construction_columns}")
                print(f"\nAvailable columns: {df_construction.columns.tolist()}")
                print("\n" + "="*80)
                sys.exit(1)
        except Exception as e:
            if "Worksheet" in str(e) and "does not exist" in str(e):
                # Already handled by the ValueError catch above
                pass
            else:
                print(f"\nUnexpected error reading Under_Construction_June2025 sheet: {e}")
                sys.exit(1)
        
        # Read UTP Projects Sheet
        print("Reading UTP2026_TxC_Projects_Review sheet...")
        try:
            df_utp = read_excel_safe(project_excel_path, sheet_name='UTP2026_TxC_Projects_Review', header=1)
        except ValueError as e:
            print("\n" + "="*80)
            print("ERROR: Required sheet 'UTP2026_TxC_Projects_Review' not found!")
            print("="*80)
            print(f"\nFile: {project_excel_path}")
            print(f"\nError: {e}")
            print("\nPlease verify the sheet name matches exactly (case-sensitive).")
            print("\n" + "="*80)
            sys.exit(1)
        except Exception as e:
            print(f"\nError reading UTP2026_TxC_Projects_Review sheet: {e}")
            sys.exit(1)
        
        try:
            # Rename columns to match expected names
            if 'TxDOT CONNECT CSJ (highlighted projects are in UTP)' in df_utp.columns:
                df_utp.rename(columns={'TxDOT CONNECT CSJ (highlighted projects are in UTP)': 'CSJ'}, inplace=True)
            
            # Check required columns exist
            required_utp_columns = ['Highway', 'CSJ', 'Funding Status (UTP 2026)', 'Construction Cost', 'Funding Gap']
            missing_utp_cols = [col for col in required_utp_columns if col not in df_utp.columns]
            
            if missing_utp_cols:
                print("\n" + "="*80)
                print("ERROR: Missing required columns in UTP2026_TxC_Projects_Review sheet!")
                print("="*80)
                print(f"\nFile: {project_excel_path}")
                print(f"Sheet: UTP2026_TxC_Projects_Review")
                print(f"\nMissing columns: {missing_utp_cols}")
                print(f"\nRequired columns: {required_utp_columns}")
                print(f"\nAvailable columns in sheet:")
                for col in sorted(df_utp.columns):
                    print(f"  - {col}")
                print("\n" + "="*80)
                sys.exit(1)
            
            if 'Highway' in df_utp.columns and 'CSJ' in df_utp.columns and 'Funding Status (UTP 2026)' in df_utp.columns and 'Construction Cost' in df_utp.columns and 'Funding Gap' in df_utp.columns:
                # Check for duplicate CSJs
                duplicate_csjs = df_utp[df_utp['CSJ'].duplicated(keep=False)]
                if len(duplicate_csjs) > 0:
                    print("\n" + "="*80)
                    print("ERROR: Duplicate CSJs found in UTP2026_TxC_Projects_Review sheet!")
                    print("="*80)
                    print(f"\nFile: {project_excel_path}")
                    print(f"Sheet: UTP2026_TxC_Projects_Review")
                    print(f"\nDuplicate CSJs:")
                    for csj in duplicate_csjs['CSJ'].unique():
                        count = len(df_utp[df_utp['CSJ'] == csj])
                        print(f"  - {csj} (appears {count} times)")
                    print("\nEach CSJ must be unique. Please remove or consolidate duplicate entries.")
                    print("\n" + "="*80)
                    sys.exit(1)
                
                # Filter projects that match target corridors
                df_utp_filtered = df_utp[df_utp['Highway'].isin(target_corridors)].copy()
                
                # Map corridor names to HWY labels
                df_utp_filtered['HWY'] = df_utp_filtered['Highway'].map(corridor_to_hwy)
                
                # Normalize funding status for case-insensitive matching
                df_utp_filtered['Funding_Status_Normalized'] = df_utp_filtered['Funding Status (UTP 2026)'].str.strip().str.lower()
                
                # Process Funded projects
                df_funded = df_utp_filtered[df_utp_filtered['Funding_Status_Normalized'] == 'funded'].copy()
                funded_summary = df_funded.groupby('HWY').agg({
                    'CSJ': 'nunique',
                    'Construction Cost': lambda x: x.sum()
                }).reset_index()
                funded_summary.columns = ['HWY', 'Projects_Funded', 'Project_Cost_Funded']
                funded_summary['Project_Cost_Funded'] = funded_summary['Project_Cost_Funded'].round(1)
                
                # Process Partially Funded projects
                df_partial = df_utp_filtered[df_utp_filtered['Funding_Status_Normalized'].str.contains('partial', na=False)].copy()
                partial_summary = df_partial.groupby('HWY').agg({
                    'CSJ': 'nunique',
                    'Construction Cost': lambda x: x.sum(),
                    'Funding Gap': lambda x: x.sum()
                }).reset_index()
                partial_summary.columns = ['HWY', 'Projects_PartialFunded', 'Project_Cost_PartialFunded', 'Project_FundingGap_PartialFunded']
                partial_summary['Project_Cost_PartialFunded'] = partial_summary['Project_Cost_PartialFunded'].round(1)
                partial_summary['Project_FundingGap_PartialFunded'] = partial_summary['Project_FundingGap_PartialFunded'].round(1)
                
                # Process Unfunded projects
                df_unfunded = df_utp_filtered[df_utp_filtered['Funding_Status_Normalized'] == 'unfunded'].copy()
                unfunded_summary = df_unfunded.groupby('HWY').agg({
                    'CSJ': 'nunique',
                    'Construction Cost': lambda x: x.sum()
                }).reset_index()
                unfunded_summary.columns = ['HWY', 'Projects_Unfunded', 'Project_Cost_Unfunded']
                unfunded_summary['Project_Cost_Unfunded'] = unfunded_summary['Project_Cost_Unfunded'].round(1)
                
                print(f"Found {len(funded_summary)} highways with funded projects.")
                print(f"Found {len(partial_summary)} highways with partially funded projects.")
                print(f"Found {len(unfunded_summary)} highways with unfunded projects.")
            else:
                print("\n" + "="*80)
                print("ERROR: Required columns not found in UTP2026_TxC_Projects_Review sheet!")
                print("="*80)
                print(f"\nRequired columns: {required_utp_columns}")
                print(f"\nAvailable columns: {df_utp.columns.tolist()}")
                print("\n" + "="*80)
                sys.exit(1)
        except Exception as e:
            if "Worksheet" in str(e) and "does not exist" in str(e):
                # Already handled by the ValueError catch above
                pass
            else:
                print(f"\nUnexpected error reading UTP2026_TxC_Projects_Review sheet: {e}")
                sys.exit(1)
        
        # Merge all project data into gdf_final
        print("Merging project data into final GeoDataFrame...")
        gdf_final = gdf_final.merge(construction_summary, on='HWY', how='left')
        gdf_final = gdf_final.merge(funded_summary, on='HWY', how='left')
        gdf_final = gdf_final.merge(partial_summary, on='HWY', how='left')
        gdf_final = gdf_final.merge(unfunded_summary, on='HWY', how='left')
        
        # Fill NaN values with 0 for corridors with no projects
        project_columns = [
            'Projects_Construction', 'Project_Cost_Construction',
            'Projects_Funded', 'Project_Cost_Funded',
            'Projects_PartialFunded', 'Project_Cost_PartialFunded', 'Project_FundingGap_PartialFunded',
            'Projects_Unfunded', 'Project_Cost_Unfunded'
        ]
        for col in project_columns:
            if col in gdf_final.columns:
                gdf_final[col] = gdf_final[col].fillna(0)
    
    # Generate random project columns for each HWY
    # print("Generating random project columns...")
    # random.seed(42)  # Fixed seed for reproducibility
    # n_rows = len(gdf_final)
    
    # # Construction projects
    # gdf_final['Projects_Construction'] = [random.randint(10, 50) for _ in range(n_rows)]
    # gdf_final['Project_Length_Construction'] = [random.randint(50, 150) for _ in range(n_rows)]
    # gdf_final['Project_Cost_Construction'] = [random.randint(10, 500) for _ in range(n_rows)]
    
    # # Funded projects
    # gdf_final['Projects_Funded'] = [random.randint(10, 100) for _ in range(n_rows)]
    # gdf_final['Project_Length_Funded'] = [random.randint(100, 250) for _ in range(n_rows)]
    # gdf_final['Project_Cost_Funded'] = [random.randint(50, 1000) for _ in range(n_rows)]
    
    # # Partially funded projects
    # gdf_final['Projects_PartialFunded'] = [random.randint(100, 400) for _ in range(n_rows)]
    # gdf_final['Project_Length_PartialFunded'] = [random.randint(100, 500) for _ in range(n_rows)]
    # gdf_final['Project_Cost_PartialFunded'] = [random.randint(50, 1000) for _ in range(n_rows)]
    # gdf_final['Project_FundingGap_PartialFunded'] = [random.randint(50, 1000) for _ in range(n_rows)]
    
    # # Unfunded projects
    # gdf_final['Projects_Unfunded'] = [random.randint(100, 400) for _ in range(n_rows)]
    # gdf_final['Project_Length_Unfunded'] = [random.randint(100, 500) for _ in range(n_rows)]
    # gdf_final['Project_Cost_Unfunded'] = [random.randint(50, 1000) for _ in range(n_rows)]
    
    
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

    # Ensure numeric columns export with Arcade-friendly dtypes.
    # ArcGIS JS warns when fields are stored as 64-bit integers because values can exceed Number.MAX_SAFE_INTEGER.
    print("Converting numeric columns to Arcade-safe data types...")
    integer_like_columns = [
        'Number_Of_Crashes',
        'Number_Of_Fatal_Crashes',
        'Projects_Construction',
        'Projects_Funded',
        'Projects_PartialFunded',
        'Projects_Unfunded',
        'Order'
    ]
    for col in integer_like_columns:
        if col in gdf_final.columns:
            gdf_final[col] = (
                pd.to_numeric(gdf_final[col], errors='coerce')
                .round()
                .astype('float64')
            )

    float_columns = [
        'Project_Cost_Construction',
        'Project_Cost_Funded',
        'Project_Cost_PartialFunded',
        'Project_FundingGap_PartialFunded',
        'Project_Cost_Unfunded'
    ]
    for col in float_columns:
        if col in gdf_final.columns:
            gdf_final[col] = (
                pd.to_numeric(gdf_final[col], errors='coerce')
                .astype('float64')
            )

    # 6. Export Data
    print(f"Exporting to {output_path}...")
    print(f"DEBUG: Final columns before export: {gdf_final.columns.tolist()}")
    print(f"DEBUG: AADT in final columns: {'AADT' in gdf_final.columns}")
    if 'AADT' in gdf_final.columns:
        print(f"DEBUG: Final AADT sample values: {gdf_final['AADT'].head().tolist()}")
    try:
        gdf_final.to_file(output_path, driver="GPKG", layer='FTW_Corridor_Profiles')
        print("Export complete.")
    except Exception as e:
        print(f"Error exporting data: {e}")

if __name__ == "__main__":
    main()