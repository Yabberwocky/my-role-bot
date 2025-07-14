import requests
import os
import json
import concurrent.futures
from lxml import etree

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        print("tqdm library not found. For a progress bar, run: pip install tqdm")
        return iterable

# --- Get the absolute path of the directory where the script is located ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# --- Main Configuration ---
# The output directories are placed relative to this script's location.
ASSET_CONFIGS = [
    {
        "name": "Petals",
        "type": "petal",
        "base_url": "https://florr.io/petals/",
        "output_dir": os.path.join(SCRIPT_DIR, "florr_petals"),
        "min_id": 0,
        "max_id": 110,
        "has_rarity": True,
    },
    {
        "name": "Mobs",
        "type": "mob",
        "base_url": "https://florr.io/mobs/",
        "output_dir": os.path.join(SCRIPT_DIR, "florr_mobs"),
        "min_id": 0,
        "max_id": 85,
        "has_rarity": True,
    }
]
DATA_FILE = os.path.join(PROJECT_DIR, "florr_data.json")

RARITIES = range(9)
MAX_WORKERS = 30
# --------------------

# --- SVG Transformation Functions ---

def hex_to_dark_grayscale(hex_color, darkening_factor=0.6):
    """Converts a hex color string to a darkened grayscale hex string."""
    if not isinstance(hex_color, str) or not hex_color.startswith('#'):
        return hex_color
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = "".join([c*2 for c in hex_color])
    if len(hex_color) != 6:
        return f"#{hex_color}"
    try:
        r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return f"#{hex_color}"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    dark_gray_val = int(luminance * darkening_factor)
    dark_gray_val = max(0, min(255, dark_gray_val))
    return f'#{dark_gray_val:02x}{dark_gray_val:02x}{dark_gray_val:02x}'

def create_unknown_mob_svg(input_svg_path, output_svg_path):
    """Reads an SVG, converts it to darkened grayscale, and adds a question mark."""
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(input_svg_path, parser)
        root = tree.getroot()

        # Convert all fills and strokes to darkened grayscale
        for element in root.xpath('//*'):
            if 'fill' in element.attrib and element.attrib['fill'] != 'none':
                element.attrib['fill'] = hex_to_dark_grayscale(element.attrib['fill'])
            if 'stroke' in element.attrib and element.attrib['stroke'] != 'none':
                element.attrib['stroke'] = hex_to_dark_grayscale(element.attrib['stroke'])

        # Get viewBox for dimensions
        viewBox = root.get('viewBox')
        if viewBox:
            _, _, width, height = [float(v) for v in viewBox.split()]
        else:
            width = float(root.get('width', 0))
            height = float(root.get('height', 0))

        if width > 0 and height > 0:
            font_size = min(width, height) * 0.55
            stroke_width = min(width, height) * 0.02
            text_attributes = {
                'x': str(width / 2), 'y': str(height / 2),
                'fill': 'white', 'stroke': 'black', 'stroke-width': str(stroke_width),
                'stroke-linejoin': 'round',
                'font-family': "'Arial Rounded MT Bold', 'Helvetica Rounded', 'Arial Black', sans-serif",
                'font-size': str(font_size), 'font-weight': 'bold',
                'text-anchor': 'middle', 'dominant-baseline': 'central'
            }
            question_mark = etree.Element('text', attrib=text_attributes)
            question_mark.text = '?'
            root.append(question_mark)

        tree.write(output_svg_path, pretty_print=True, xml_declaration=True, encoding='UTF-8')
        return True
    except (FileNotFoundError, etree.XMLSyntaxError):
        return False

# --- Downloader Functions ---

def generate_filenames(asset_type, item_id, rarity):
    """Generates a list of possible filenames based on asset type and rarity."""
    if rarity == 0:
        return [f"{item_id}.svg", f"{item_id}_0.svg"]
    else:
        return [f"{item_id}_{rarity}.svg"]

def check_and_download(asset_config, item_id, rarity):
    """Checks possible URLs and downloads the first valid SVG found."""
    filenames = generate_filenames(asset_config['type'], item_id, rarity)
    for filename in filenames:
        url = f"{asset_config['base_url']}{filename}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200 and 'image/svg+xml' in response.headers.get('Content-Type', ''):
                filepath = os.path.join(asset_config['output_dir'], filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
        except requests.RequestException:
            continue
    return False

def run_downloader():
    """Main function to orchestrate the concurrent download of all defined asset types."""
    grand_total_found = 0
    mob_config = next((config for config in ASSET_CONFIGS if config["type"] == "mob"), None)

    for config in ASSET_CONFIGS:
        asset_name = config['name']
        output_dir = config['output_dir']
        
        print("\n" + "="*40)
        print(f"--- Starting Download for: {asset_name} ---")
        print("="*40)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")

        tasks_to_run = []
        for pid in range(config['min_id'], config['max_id'] + 1):
            if config['has_rarity']:
                for r in RARITIES:
                    tasks_to_run.append((config, pid, r))
            else:
                tasks_to_run.append((config, pid, None))

        print(f"Checking {len(tasks_to_run)} possible URL combinations with {MAX_WORKERS} parallel workers...")
        total_found_for_type = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_task = {executor.submit(check_and_download, cfg, pid, r): (pid, r) for cfg, pid, r in tasks_to_run}
            progress_bar = tqdm(concurrent.futures.as_completed(future_to_task), total=len(tasks_to_run), desc=f"Scanning {asset_name}")
            for future in progress_bar:
                if future.result():
                    total_found_for_type += 1

        print(f"\n{asset_name} download complete. Found and saved {total_found_for_type} SVGs.")
        print(f"Files are located in: '{output_dir}'")
        grand_total_found += total_found_for_type
        
    # --- Generate "Unknown Mob" SVGs after main downloads ---
    if mob_config:
        print("\n" + "="*40)
        print("--- Generating 'Unknown Mob' SVGs ---")
        print("="*40)
        try:
            with open(DATA_FILE, 'r') as f:
                game_data = json.load(f)
            
            mob_output_dir = mob_config['output_dir']
            unknown_created_count = 0
            
            for group in tqdm(game_data.get('shared_spawns', []), desc="Creating grouped mob SVGs"):
                leader_id = group['leader_id']
                group_id_name = group['group_id']
                
                # Find the base SVG for the leader mob (try id_0.svg then id.svg)
                input_svg_path = os.path.join(mob_output_dir, f"{leader_id}_0.svg")
                if not os.path.exists(input_svg_path):
                    input_svg_path = os.path.join(mob_output_dir, f"{leader_id}.svg")

                if os.path.exists(input_svg_path):
                    output_svg_path = os.path.join(mob_output_dir, f"{group_id_name}.svg")
                    if create_unknown_mob_svg(input_svg_path, output_svg_path):
                        unknown_created_count += 1
                else:
                    print(f"Warning: Could not find leader SVG for group '{group_id_name}' (Leader ID: {leader_id}). Skipping.")

            print(f"\n'Unknown Mob' generation complete. Created {unknown_created_count} new SVGs.")
            grand_total_found += unknown_created_count

        except FileNotFoundError:
            print(f"Warning: {DATA_FILE} not found. Could not generate 'Unknown Mob' SVGs.")
        except Exception as e:
            print(f"An error occurred during 'Unknown Mob' SVG generation: {e}")

    print("\n" + "="*40)
    print(f"All downloads finished. Total files saved: {grand_total_found}")
    print("="*40)

if __name__ == "__main__":
    run_downloader()