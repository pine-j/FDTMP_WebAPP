"""
Script to download ArcGIS Online layers as GeoPackage (.gpkg) files.

This script downloads layers from ArcGIS Online and saves them as GPKG files.
It supports both public and authenticated access to ArcGIS Online.

Requirements:
    - arcgis (install with: pip install arcgis)
    - geopandas (install with: pip install geopandas)
    - pandas (install with: pip install pandas)

Usage:
    python download_arcgis_layers.py

Optional: Set environment variables for authentication:
    ARCGIS_USERNAME=your_username
    ARCGIS_PASSWORD=your_password
"""

import os
import re
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import geopandas as gpd
from pathlib import Path


def extract_item_id(url):
    """Extract the item ID from an ArcGIS Online URL."""
    match = re.search(r'id=([a-f0-9]+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Could not extract item ID from URL: {url}")


def download_arcgis_layer_as_gpkg(item_id, output_path, gis=None, username=None, password=None):
    """
    Download an ArcGIS Online layer as a GeoPackage file.
    
    Parameters:
    -----------
    item_id : str
        The ArcGIS Online item ID
    output_path : str
        Path where the GPKG file should be saved
    gis : arcgis.gis.GIS, optional
        An authenticated GIS object. If None, will attempt to connect.
    username : str, optional
        Username for ArcGIS Online authentication (if needed)
    password : str, optional
        Password for ArcGIS Online authentication (if needed)
    
    Returns:
    --------
    bool
        True if successful, False otherwise
    """
    try:
        # Connect to ArcGIS Online if not provided
        if gis is None:
            if username and password:
                print(f"Connecting to ArcGIS Online as {username}...")
                gis = GIS("https://www.arcgis.com", username=username, password=password)
            else:
                print("Connecting to ArcGIS Online anonymously...")
                gis = GIS()
        
        # Get the item
        print(f"Fetching item {item_id}...")
        item = gis.content.get(item_id)
        
        if item is None:
            print(f"Error: Could not find item with ID {item_id}")
            return False
        
        print(f"Found item: {item.title}")
        
        # Check if item has layers
        if hasattr(item, 'layers') and len(item.layers) > 0:
            # If it's a feature service with layers, download each layer
            for idx, layer in enumerate(item.layers):
                layer_name = layer.properties.name if hasattr(layer.properties, 'name') else f'Layer_{idx + 1}'
                print(f"Downloading layer {idx + 1}/{len(item.layers)}: {layer_name}")
                
                # Query all features
                try:
                    feature_set = layer.query(where="1=1", return_geometry=True, out_sr=4326)
                except Exception as e:
                    print(f"Warning: Error querying with return_geometry=True: {e}")
                    print("Trying without explicit geometry return...")
                    feature_set = layer.query(where="1=1")
                
                # Convert to GeoDataFrame using sdf property
                gdf = None
                if hasattr(feature_set, 'sdf'):
                    df = feature_set.sdf
                    if isinstance(df, gpd.GeoDataFrame):
                        gdf = df
                    elif 'SHAPE' in df.columns:
                        # Convert SHAPE column (arcgis geometry) to shapely geometry
                        import pandas as pd
                        from shapely.geometry import shape
                        geometries = []
                        for idx, row in df.iterrows():
                            if pd.notna(row['SHAPE']):
                                geom_obj = row['SHAPE']
                                # Try to get __geo_interface__ from arcgis geometry
                                if hasattr(geom_obj, '__geo_interface__'):
                                    try:
                                        geom = shape(geom_obj.__geo_interface__)
                                    except:
                                        geom = None
                                else:
                                    geom = None
                            else:
                                geom = None
                            geometries.append(geom)
                        # Only create GeoDataFrame if we have valid geometries
                        if any(g is not None for g in geometries):
                            gdf = gpd.GeoDataFrame(df.drop(columns=['SHAPE']), geometry=geometries, crs='EPSG:4326')
                
                # Fallback: use features if sdf didn't work
                if gdf is None or len(gdf) == 0:
                    features = feature_set.features
                    if len(features) == 0:
                        print(f"Warning: No features found in layer {layer_name}")
                        continue
                    # Convert using features with __geo_interface__
                    from shapely.geometry import shape
                    feature_dicts = []
                    for f in features:
                        try:
                            # Try __geo_interface__ first (GeoJSON standard)
                            if hasattr(f, '__geo_interface__'):
                                geo_int = f.__geo_interface__
                                if geo_int and isinstance(geo_int, dict) and geo_int.get('geometry'):
                                    feature_dicts.append(geo_int)
                        except Exception as e:
                            continue
                    
                    if len(feature_dicts) > 0:
                        gdf = gpd.GeoDataFrame.from_features(feature_dicts)
                    else:
                        print(f"Warning: Could not convert features for layer {layer_name}")
                        continue
                
                if len(gdf) == 0:
                    print(f"Warning: Layer {layer_name} has no features, skipping...")
                    continue
                
                # Generate output filename
                if len(item.layers) > 1:
                    base_path = Path(output_path)
                    safe_layer_name = layer_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                    layer_output = base_path.parent / f"{base_path.stem}_{safe_layer_name}.gpkg"
                    layer_output = str(layer_output)
                else:
                    layer_output = output_path
                
                # Save as GPKG
                print(f"Saving to {layer_output}...")
                safe_layer_name_gpkg = layer_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
                gdf.to_file(layer_output, driver="GPKG", layer=safe_layer_name_gpkg)
                print(f"Successfully saved {len(gdf)} features to {layer_output}")
        
        elif hasattr(item, 'type') and item.type in ['Feature Layer', 'Feature Service']:
            # Single feature layer or feature service
            print("Downloading feature layer...")
            try:
                if hasattr(item, 'url'):
                    feature_layer = FeatureLayer(item.url, gis=gis)
                else:
                    # Try to construct URL from item
                    feature_layer = item.layers[0] if hasattr(item, 'layers') and len(item.layers) > 0 else None
                    if feature_layer is None:
                        raise ValueError("Could not access feature layer")
                
                feature_set = feature_layer.query(where="1=1", return_geometry=True, out_sr=4326)
                
                # Convert to GeoDataFrame using sdf property
                gdf = None
                if hasattr(feature_set, 'sdf'):
                    df = feature_set.sdf
                    if isinstance(df, gpd.GeoDataFrame):
                        gdf = df
                    elif 'SHAPE' in df.columns:
                        # Convert SHAPE column (arcgis geometry) to shapely geometry
                        import pandas as pd
                        from shapely.geometry import shape
                        geometries = []
                        for idx, row in df.iterrows():
                            if pd.notna(row['SHAPE']):
                                geom_obj = row['SHAPE']
                                # Try to get __geo_interface__ from arcgis geometry
                                if hasattr(geom_obj, '__geo_interface__'):
                                    try:
                                        geom = shape(geom_obj.__geo_interface__)
                                    except:
                                        geom = None
                                else:
                                    geom = None
                            else:
                                geom = None
                            geometries.append(geom)
                        # Only create GeoDataFrame if we have valid geometries
                        if any(g is not None for g in geometries):
                            gdf = gpd.GeoDataFrame(df.drop(columns=['SHAPE']), geometry=geometries, crs='EPSG:4326')
                
                # Fallback: use features if sdf didn't work
                if gdf is None or len(gdf) == 0:
                    features = feature_set.features
                    if len(features) == 0:
                        print("Warning: Layer has no features")
                        return False
                    # Convert using features with __geo_interface__
                    from shapely.geometry import shape
                    feature_dicts = []
                    for f in features:
                        try:
                            # Try __geo_interface__ first (GeoJSON standard)
                            if hasattr(f, '__geo_interface__'):
                                geo_int = f.__geo_interface__
                                if geo_int and isinstance(geo_int, dict) and geo_int.get('geometry'):
                                    feature_dicts.append(geo_int)
                        except Exception as e:
                            continue
                    
                    if len(feature_dicts) > 0:
                        gdf = gpd.GeoDataFrame.from_features(feature_dicts)
                    else:
                        print("Warning: Could not convert features")
                        return False
                
                if len(gdf) == 0:
                    print("Warning: Layer has no features")
                    return False
                
                # Save as GPKG
                print(f"Saving to {output_path}...")
                layer_name = item.title.replace(" ", "_").replace("/", "_").replace("\\", "_")
                gdf.to_file(output_path, driver="GPKG", layer=layer_name)
                print(f"Successfully saved {len(gdf)} features to {output_path}")
            except Exception as e:
                print(f"Error accessing feature layer: {e}")
                return False
        
        else:
            # Try to download as a file if it's a file-based item
            print(f"Item type: {item.type}")
            if hasattr(item, 'download'):
                print("Attempting to download as file...")
                download_path = item.download(output_path.replace('.gpkg', ''))
                print(f"Downloaded to: {download_path}")
                # If it's already a GPKG or shapefile, we might need to convert
                if download_path.endswith('.shp'):
                    gdf = gpd.read_file(download_path)
                    gdf.to_file(output_path, driver="GPKG")
                    print(f"Converted and saved to {output_path}")
            else:
                print(f"Error: Item type '{item.type}' is not supported for direct download.")
                return False
        
        return True
        
    except Exception as e:
        print(f"Error downloading layer {item_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to download ArcGIS layers."""
    
    # ArcGIS Online item URLs
    urls = [
        "https://jacobs.maps.arcgis.com/home/item.html?id=97dcc38a5686487e9214a49e6fb918cb",
        "https://jacobs.maps.arcgis.com/home/item.html?id=fc5105d85d824c54b171300c429c3150"
    ]
    
    # Set output directory (same as script directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = script_dir
    
    # Optional: Set ArcGIS Online credentials if needed
    # You can set these as environment variables or modify here
    username = os.environ.get('ARCGIS_USERNAME', None)
    password = os.environ.get('ARCGIS_PASSWORD', None)
    
    # If you need to authenticate, uncomment and set these:
    # username = "your_username"
    # password = "your_password"
    
    # Connect to ArcGIS Online
    gis = None
    if username and password:
        print(f"Connecting to ArcGIS Online as {username}...")
        gis = GIS("https://www.arcgis.com", username=username, password=password)
    else:
        print("Connecting to ArcGIS Online anonymously...")
        gis = GIS()
    
    # Download each layer
    for url in urls:
        try:
            item_id = extract_item_id(url)
            print(f"\n{'='*60}")
            print(f"Processing item ID: {item_id}")
            print(f"{'='*60}")
            
            # Get the item to retrieve its title
            item = gis.content.get(item_id)
            if item is None:
                print(f"Error: Could not find item with ID {item_id}")
                continue
            
            # Create output filename based on item title
            # Sanitize the title for use as filename (replace spaces, special chars)
            item_title = item.title
            safe_title = item_title.replace(" ", "_").replace("/", "_").replace("\\", "_")
            safe_title = "".join(c for c in safe_title if c.isalnum() or c in ('_', '-', '.'))
            output_path = os.path.join(output_dir, f"{safe_title}.gpkg")
            
            # Download the layer
            success = download_arcgis_layer_as_gpkg(
                item_id=item_id,
                output_path=output_path,
                gis=gis
            )
            
            if success:
                print(f"✓ Successfully downloaded layer: {item_title}")
            else:
                print(f"✗ Failed to download layer: {item_title}")
                
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Download process completed!")
    print("="*60)


if __name__ == "__main__":
    main()

