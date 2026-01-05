"""
Export GeoPackage layers to CSV files

This script exports all layers from a GeoPackage file to individual CSV files.
It can handle single or multiple GeoPackage files.

Usage:
    python export_gpkg_to_csv.py <gpkg_file_path> [output_directory]
    
    If no output directory is specified, the CSV will be saved in the _ignore folder
    relative to the GPKG file location.
    
Example:
    python export_gpkg_to_csv.py "Input_GeoFiles/raptor_results_FTW.gpkg"
    python export_gpkg_to_csv.py "Input_GeoFiles/raptor_results_FTW.gpkg" "../_ignore"
"""

import geopandas as gpd
import os
import sys
from pathlib import Path


def export_gpkg_to_csv(gpkg_file, output_dir=None):
    """
    Export all layers from a GeoPackage file to CSV files.
    
    Parameters:
    -----------
    gpkg_file : str
        Path to the GeoPackage file
    output_dir : str, optional
        Output directory for CSV files. If None, uses _ignore folder
        relative to the GPKG file location.
    
    Returns:
    --------
    dict : Dictionary with export results
    """
    
    # Validate input file
    if not os.path.exists(gpkg_file):
        print(f"Error: File not found: {gpkg_file}")
        return False
    
    if not gpkg_file.lower().endswith('.gpkg'):
        print(f"Error: File is not a GeoPackage (.gpkg): {gpkg_file}")
        return False
    
    # Determine output directory
    if output_dir is None:
        gpkg_dir = os.path.dirname(gpkg_file)
        output_dir = os.path.join(os.path.dirname(gpkg_dir), '_ignore')
    
    # Create output directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}")
        return False
    
    # Get the base name for the output file
    base_name = Path(gpkg_file).stem
    
    try:
        # Read the GeoPackage file
        gdf = gpd.read_file(gpkg_file)
        
        # Generate output filename
        output_file = os.path.join(output_dir, f"{base_name}.csv")
        
        # Export to CSV (geometry column will be included)
        gdf.to_csv(output_file, index=False)
        
        print(f"✓ Successfully exported: {output_file}")
        print(f"  - Rows: {len(gdf)}")
        print(f"  - Columns: {len(gdf.columns)}")
        print(f"  - Column names: {', '.join(gdf.columns.tolist()[:5])}{'...' if len(gdf.columns) > 5 else ''}")
        
        return True
        
    except Exception as e:
        print(f"Error reading/exporting GeoPackage: {e}")
        return False


def main():
    """Main function to handle command-line arguments."""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python export_gpkg_to_csv.py <gpkg_file_path> [output_directory]")
        sys.exit(1)
    
    gpkg_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Processing GeoPackage: {gpkg_file}")
    print(f"Output directory: {output_dir or '_ignore folder (auto-determined)'}")
    print("-" * 60)
    
    success = export_gpkg_to_csv(gpkg_file, output_dir)
    
    if not success:
        sys.exit(1)
    else:
        print("-" * 60)
        print("Export completed successfully!")


if __name__ == "__main__":
    main()
