"""
Highway Shield Downloader and Converter
Downloads highway shield SVG files from Wikimedia Commons and converts them to PNG format.
Automatically reads FTW_Corridors.xlsx to determine which shields are needed.
Updates the spreadsheet with GitHub URLs for accessing the shields.

Usage:
    python download_shields_wikipedia.py
"""

import os
import requests
import sys
import base64
from PIL import Image
from io import BytesIO
import time
import pandas as pd

try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    from selenium.webdriver.chrome.service import Service
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

# Configuration
SPREADSHEET_PATH = '../Input_Files/FTW_Corridors.xlsx'
OUTPUT_DIR = '../HWY_Shields'
GITHUB_BASE_URL = 'https://pine-j.github.io/FDTMP_WebAPP/Corridor_Profile/HWY_Shields/'
TARGET_HEIGHT = 500  # Exact height for all shields in pixels
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def build_wikipedia_url(shield_code):
    """Build Wikipedia Commons URL for a given shield code"""
    # Extract highway type and number
    if shield_code.startswith('IH'):
        # Interstate: IH0030 -> I-30
        number = shield_code[2:].lstrip('0')
        if 'W' in shield_code:
            return f'https://commons.wikimedia.org/wiki/Special:FilePath/I-{number}.svg'
        return f'https://commons.wikimedia.org/wiki/Special:FilePath/I-{number}.svg'
    elif shield_code.startswith('US'):
        # US Highway: US0287 -> US_287
        number = shield_code[2:].lstrip('0')
        return f'https://commons.wikimedia.org/wiki/Special:FilePath/US_{number}.svg'
    elif shield_code.startswith('SH'):
        # State Highway: SH0360 -> Texas_360
        number = shield_code[2:].lstrip('0')
        return f'https://commons.wikimedia.org/wiki/Special:FilePath/Texas_{number}.svg'
    elif shield_code.startswith('FM'):
        # Farm Road: FM0156 -> Texas_FM_156
        number = shield_code[2:].lstrip('0')
        return f'https://commons.wikimedia.org/wiki/Special:FilePath/Texas_FM_{number}.svg'
    else:
        return None


def read_spreadsheet_shields():
    """Read the spreadsheet and extract unique highway labels"""
    try:
        print(f"[READING] {SPREADSHEET_PATH}...")
        df = pd.read_excel(SPREADSHEET_PATH)
        
        if 'HWY_Label' not in df.columns:
            print(f"[ERROR] 'HWY_Label' column not found in spreadsheet")
            return None, None
        
        shields = df['HWY_Label'].unique().tolist()
        print(f"[FOUND] {len(shields)} unique highways in spreadsheet")
        return shields, df
    except Exception as e:
        print(f"[ERROR] Failed to read spreadsheet: {str(e)}")
        return None, None


def get_existing_shields():
    """Get list of existing valid shield PNG files with correct dimensions"""
    existing = []
    if os.path.exists(OUTPUT_DIR):
        for file in os.listdir(OUTPUT_DIR):
            if file.endswith('.png'):
                path = os.path.join(OUTPUT_DIR, file)
                size = os.path.getsize(path)
                # Only count files > 1000 bytes as valid (not placeholders)
                if size > 1000:
                    # Check if shield has exactly the target height
                    try:
                        img = Image.open(path)
                        width, height = img.size
                        if height == TARGET_HEIGHT:
                            shield_code = file.replace('.png', '')
                            existing.append(shield_code)
                        else:
                            print(f"  [INVALID] {file} - Height {height}px != {TARGET_HEIGHT}px (will re-download)")
                    except Exception as e:
                        print(f"  [ERROR] {file} - Cannot read image: {str(e)}")
    return existing


def determine_shields_to_download(spreadsheet_shields, existing_shields):
    """Determine which shields need to be downloaded"""
    missing = []
    for shield in spreadsheet_shields:
        if shield not in existing_shields:
            missing.append(shield)
    return missing


def determine_shields_to_delete(spreadsheet_shields, existing_shields):
    """Determine which shields should be deleted (not in spreadsheet)"""
    extra = []
    for shield in existing_shields:
        if shield not in spreadsheet_shields:
            extra.append(shield)
    return extra


def delete_extra_shields(extra_shields):
    """Delete shield PNG files that are not in the spreadsheet"""
    deleted = 0
    failed = 0
    
    if len(extra_shields) == 0:
        return deleted, failed
    
    print(f"\n[CLEANUP] Deleting {len(extra_shields)} extra shield(s) not in spreadsheet...")
    
    for shield_code in extra_shields:
        png_file = os.path.join(OUTPUT_DIR, f'{shield_code}.png')
        try:
            if os.path.exists(png_file):
                os.remove(png_file)
                print(f"  [DELETED] {shield_code}.png")
                deleted += 1
        except Exception as e:
            print(f"  [ERROR] Failed to delete {shield_code}.png: {str(e)}")
            failed += 1
    
    return deleted, failed


def update_spreadsheet_with_github_urls(df, github_base_url):
    """Update HWY_Shield column with GitHub URLs where empty"""
    try:
        print(f"\n[UPDATE] Adding GitHub URLs to HWY_Shield column where empty...")
        
        # Check if HWY_Shield column exists, if not create it
        if 'HWY_Shield' not in df.columns:
            df['HWY_Shield'] = ''
        
        # Update HWY_Shield column only where it's empty (NaN or empty string)
        mask = df['HWY_Shield'].isna() | (df['HWY_Shield'] == '')
        df.loc[mask, 'HWY_Shield'] = df.loc[mask, 'HWY_Label'].apply(
            lambda x: f"{github_base_url}{x}.png"
        )
        
        # Count how many were updated
        updated_count = mask.sum()
        
        # Save updated spreadsheet
        df.to_excel(SPREADSHEET_PATH, index=False)
        print(f"[SUCCESS] Updated {updated_count} empty cells in HWY_Shield column")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update spreadsheet: {str(e)}")
        return False


def download_svg(shield_code, url):
    """Download SVG file from Wikimedia Commons"""
    try:
        print(f"[DOWNLOAD] {shield_code}...", end=' ', flush=True)
        response = requests.get(url, timeout=15, headers=HEADERS, verify=False, allow_redirects=True)
        response.raise_for_status()
        print(f"OK ({len(response.content)} bytes)")
        return response.content
    except Exception as e:
        print(f"FAILED: {str(e)}")
        return None


def setup_selenium_driver():
    """Setup Selenium WebDriver"""
    try:
        # Try Chrome first
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=100,100')
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        print("[DRIVER] Using Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to setup Chrome: {str(e)}")
        try:
            # Try Edge as fallback
            options = webdriver.EdgeOptions()
            options.add_argument('--headless')
            options.add_argument('--window-size=100,100')
            
            driver = webdriver.Edge(
                service=Service(EdgeChromiumDriverManager().install()),
                options=options
            )
            print("[DRIVER] Using Edge")
            return driver
        except Exception as e2:
            print(f"[ERROR] Failed to setup Edge: {str(e2)}")
            return None


def render_svg_to_png_selenium(svg_content, png_file):
    """Render SVG to PNG using Selenium"""
    driver = None
    try:
        driver = setup_selenium_driver()
        if driver is None:
            return False
        
        # Create data URL from SVG content
        svg_b64 = base64.b64encode(svg_content).decode('utf-8')
        data_url = f'data:image/svg+xml;base64,{svg_b64}'
        
        # Load in browser
        driver.get('about:blank')
        
        # Inject SVG into page and render at target height
        driver.execute_script(f"""
            var svg = `data:image/svg+xml;base64,{svg_b64}`;
            var canvas = document.createElement('canvas');
            canvas.width = {TARGET_HEIGHT * 2};  // Wide enough for most shields
            canvas.height = {TARGET_HEIGHT};
            document.body.appendChild(canvas);
            
            var img = new Image();
            img.onload = function() {{
                var ctx = canvas.getContext('2d');
                var aspectRatio = img.width / img.height;
                var newWidth = {TARGET_HEIGHT} * aspectRatio;
                ctx.drawImage(img, 0, 0, newWidth, {TARGET_HEIGHT});
            }};
            img.src = svg;
        """)
        
        time.sleep(1)
        
        # Take screenshot
        screenshot = driver.get_screenshot_as_png()
        
        # Crop to appropriate size
        img = Image.open(BytesIO(screenshot))
        img = img.crop((0, 0, TARGET_HEIGHT * 2, TARGET_HEIGHT))
        img.save(png_file, 'PNG')
        
        return True
    except Exception as e:
        print(f"    Selenium render failed: {str(e)}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


def render_svg_to_png_cairosvg(svg_content, png_file):
    """Render SVG to PNG using CairoSVG (Python library)"""
    try:
        # Render at target height, width will be calculated to maintain aspect ratio
        cairosvg.svg2png(bytestring=svg_content, write_to=png_file, output_height=TARGET_HEIGHT)
        return True
    except Exception as e:
        print(f"    CairoSVG render failed: {str(e)}")
        return False


def download_png_thumbnail(shield_code, png_file):
    """Download PNG thumbnail directly from Wikipedia as fallback (using 500px size)"""
    try:
        # Build thumbnail URL based on shield type
        # Using 500px size to match our target height
        if shield_code.startswith('IH'):
            number = shield_code[2:].lstrip('0')
            thumb_url = f'https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/I-{number}.svg/{TARGET_HEIGHT}px-I-{number}.svg.png'
        elif shield_code.startswith('US'):
            number = shield_code[2:].lstrip('0')
            thumb_url = f'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/US_{number}.svg/{TARGET_HEIGHT}px-US_{number}.svg.png'
        elif shield_code.startswith('SH'):
            number = shield_code[2:].lstrip('0')
            # Use the correct path format for Texas state highways
            thumb_url = f'https://upload.wikimedia.org/wikipedia/commons/thumb/7/72/Texas_{number}.svg/{TARGET_HEIGHT}px-Texas_{number}.svg.png'
        elif shield_code.startswith('FM'):
            number = shield_code[2:].lstrip('0')
            thumb_url = f'https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Texas_FM_{number}.svg/{TARGET_HEIGHT}px-Texas_FM_{number}.svg.png'
        else:
            return False
        
        time.sleep(2)  # Wait to avoid rate limiting
        response = requests.get(thumb_url, headers=HEADERS, verify=False, allow_redirects=True, timeout=30)
        
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Resize to target height while maintaining aspect ratio
            width, height = img.size
            if height != TARGET_HEIGHT:
                aspect_ratio = width / height
                new_width = int(TARGET_HEIGHT * aspect_ratio)
                img = img.resize((new_width, TARGET_HEIGHT), Image.Resampling.LANCZOS)
            img.save(png_file, 'PNG')
            return True
        else:
            print(f"    PNG thumbnail download failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"    PNG thumbnail download failed: {str(e)}")
        return False


def render_svg_to_png_imagemagick(svg_content, png_file):
    """Render SVG to PNG using ImageMagick (if available)"""
    try:
        import subprocess
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp:
            tmp.write(svg_content)
            tmp_path = tmp.name
        
        try:
            # Resize to target height, maintaining aspect ratio (x prefix means height)
            subprocess.run([
                'magick', 'convert',
                tmp_path,
                '-density', '300',
                '-resize', f'x{TARGET_HEIGHT}',
                png_file
            ], check=True, capture_output=True, timeout=10)
            return True
        finally:
            try:
                os.remove(tmp_path)
            except:
                pass
    except Exception as e:
        print(f"    ImageMagick render failed: {str(e)}")
        return False


def render_svg_to_png_online(svg_content, png_file):
    """Use online converter as last resort"""
    try:
        print(f"    Trying online converter...", end=' ', flush=True)
        # This would require uploading to a service, which may have limitations
        # Skipping for now
        return False
    except Exception as e:
        print(f"Failed: {str(e)}")
        return False


def validate_shield_dimensions(png_file):
    """Validate that the shield has exactly the target height"""
    try:
        img = Image.open(png_file)
        width, height = img.size
        if height == TARGET_HEIGHT:
            return True, width, height
        else:
            return False, width, height
    except Exception as e:
        return False, 0, 0


def convert_svg_to_png(shield_code, svg_content, png_file):
    """Convert SVG to PNG using best available method"""
    print(f"[RENDER] {shield_code}...", end=' ', flush=True)
    
    # Try CairoSVG first (most reliable Python-based solution)
    if HAS_CAIROSVG:
        if render_svg_to_png_cairosvg(svg_content, png_file):
            valid, width, height = validate_shield_dimensions(png_file)
            if valid:
                print(f"OK (CairoSVG) - {width}x{height}px")
                return True
            else:
                print(f"Invalid dimensions ({width}x{height}px), trying another method...")
    
    # Try ImageMagick as fallback
    if render_svg_to_png_imagemagick(svg_content, png_file):
        valid, width, height = validate_shield_dimensions(png_file)
        if valid:
            print(f"OK (ImageMagick) - {width}x{height}px")
            return True
        else:
            print(f"Invalid dimensions ({width}x{height}px), trying another method...")
    
    # Try downloading PNG thumbnail directly from Wikipedia
    print("Trying PNG thumbnail...", end=' ', flush=True)
    if download_png_thumbnail(shield_code, png_file):
        valid, width, height = validate_shield_dimensions(png_file)
        if valid:
            print(f"OK (PNG thumbnail) - {width}x{height}px")
            return True
        else:
            print(f"Invalid dimensions ({width}x{height}px), trying another method...")
    
    # Try Selenium as last resort
    if HAS_SELENIUM:
        try:
            if render_svg_to_png_selenium(svg_content, png_file):
                valid, width, height = validate_shield_dimensions(png_file)
                if valid:
                    print(f"OK (Selenium) - {width}x{height}px")
                    return True
                else:
                    print(f"Invalid dimensions ({width}x{height}px)")
        except Exception as e:
            pass
    
    # No conversion method available
    print("FAILED - No converter available or dimensions invalid")
    return False


def main():
    """Main function"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("="*70)
    print("Highway Shield Downloader - Automatic from Spreadsheet")
    print("="*70)
    print(f"Spreadsheet: {SPREADSHEET_PATH}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Target height: {TARGET_HEIGHT}px (exact, width varies to maintain aspect ratio)\n")
    
    # Step 1: Read spreadsheet to get required shields
    spreadsheet_shields, df = read_spreadsheet_shields()
    if spreadsheet_shields is None:
        print("[ERROR] Cannot proceed without spreadsheet data")
        return
    
    # Step 2: Get existing valid shields
    print(f"\n[CHECK] Checking existing shields...")
    existing_shields = get_existing_shields()
    print(f"[FOUND] {len(existing_shields)} valid shields already downloaded")
    
    # Step 3: Determine which shields to download
    missing_shields = determine_shields_to_download(spreadsheet_shields, existing_shields)
    print(f"[NEEDED] {len(missing_shields)} shields need to be downloaded")
    
    if len(missing_shields) == 0:
        print("\n[INFO] All shields are already downloaded!")
    else:
        print(f"\n[MISSING] Shields to download: {', '.join(missing_shields)}")
    
    # Step 3.5: Determine which shields to delete (not in spreadsheet)
    extra_shields = determine_shields_to_delete(spreadsheet_shields, existing_shields)
    if len(extra_shields) > 0:
        print(f"\n[EXTRA] {len(extra_shields)} shield(s) not in spreadsheet: {', '.join(extra_shields)}")
    
    # Show available converters
    print(f"\n[CONVERTERS]")
    print(f"  - CairoSVG: {'Available' if HAS_CAIROSVG else 'Not available'}")
    print(f"  - Selenium: {'Available' if HAS_SELENIUM else 'Not available'}")
    
    # Step 4: Download and convert missing shields
    downloaded = 0
    converted = 0
    failed = 0
    
    if len(missing_shields) > 0:
        print(f"\n{'='*70}")
        print("Downloading and converting shields...")
        print(f"{'='*70}\n")
        
        for shield_code in missing_shields:
            png_file = os.path.join(OUTPUT_DIR, f'{shield_code}.png')
            
            # Build Wikipedia URL
            wiki_url = build_wikipedia_url(shield_code)
            if not wiki_url:
                print(f"[ERROR] {shield_code} - Cannot build Wikipedia URL")
                failed += 1
                continue
            
            # Download SVG
            svg_content = download_svg(shield_code, wiki_url)
            if not svg_content:
                failed += 1
                continue
            
            downloaded += 1
            
            # Convert to PNG
            if convert_svg_to_png(shield_code, svg_content, png_file):
                converted += 1
            else:
                failed += 1
    
    # Step 4.5: Delete extra shields not in spreadsheet
    deleted = 0
    delete_failed = 0
    if len(extra_shields) > 0:
        deleted, delete_failed = delete_extra_shields(extra_shields)
    
    # Step 5: Update spreadsheet with GitHub URLs
    print(f"\n{'='*70}")
    print(f"[UPDATE] Using configured GitHub URL: {GITHUB_BASE_URL}")
    update_spreadsheet_with_github_urls(df, GITHUB_BASE_URL)
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Total shields in spreadsheet: {len(spreadsheet_shields)}")
    print(f"  Already downloaded: {len(existing_shields)}")
    print(f"  Newly downloaded: {downloaded}")
    print(f"  Successfully converted: {converted}")
    print(f"  Failed downloads: {failed}")
    print(f"  Extra shields deleted: {deleted}")
    if delete_failed > 0:
        print(f"  Failed deletions: {delete_failed}")
    print(f"{'='*70}\n")
    
    # List all shields with dimensions
    print(f"All shields in {OUTPUT_DIR}:")
    print(f"{'Name':<20} {'Dimensions':<15} {'File Size':<12} {'Status':<15}")
    print("-" * 62)
    for file in sorted(os.listdir(OUTPUT_DIR)):
        if file.endswith('.png'):
            path = os.path.join(OUTPUT_DIR, file)
            size = os.path.getsize(path)
            try:
                img = Image.open(path)
                width, height = img.size
                dimensions = f"{width}x{height}"
                status = "Valid" if height == TARGET_HEIGHT else f"Invalid (≠{TARGET_HEIGHT}px)"
            except:
                dimensions = "Error"
                status = "Error"
            print(f"{file:<20} {dimensions:<15} {size:<12} {status:<15}")


if __name__ == "__main__":
    main()
