import os
import json
import xml.etree.ElementTree as ET
import concurrent.futures
import cairosvg

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        print("tqdm library not found. For a progress bar, run: pip install tqdm")
        return iterable

# --- Path Configuration ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# --- File Configuration ---
INPUT_PETAL_DIR = os.path.join(SCRIPT_DIR, "florr_petals")
INPUT_MOB_DIR = os.path.join(SCRIPT_DIR, "florr_mobs")
OUTPUT_PETAL_DIR_PNG = os.path.join(PROJECT_DIR, "Petals")
OUTPUT_MOB_DIR_PNG = os.path.join(PROJECT_DIR, "Mobs")
DATA_FILE = os.path.join(PROJECT_DIR, "florr_data.json")

PNG_WIDTH = 512
PNG_HEIGHT = 512
RARITIES = range(9) # 0-8
MAX_WORKERS = 30
# --------------------

def load_game_data():
    """Loads the mob/petal definitions from the JSON file."""
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found. Please ensure it's in the main project directory.")
        return None

def find_fallback_asset(directory, item_id, target_rarity):
    """
    Finds an asset file path, falling back to the next lowest rarity if needed.
    Handles both numeric IDs and string-based group_ids.
    """
    # Handle string-based group IDs (e.g., "beetle", "ladybug")
    if isinstance(item_id, str):
        potential_file = os.path.join(directory, f"{item_id}.svg")
        if os.path.exists(potential_file):
            return potential_file
        return None

    # Original logic for numeric IDs
    for r in range(target_rarity, -1, -1):
        potential_file = os.path.join(directory, f"{item_id}_{r}.svg")
        if os.path.exists(potential_file):
            return potential_file
        if r == 0:
            potential_file = os.path.join(directory, f"{item_id}.svg")
            if os.path.exists(potential_file):
                return potential_file
    return None

def process_and_convert(item_info, item_type):
    """
    The core worker function. It finds assets, merges them in memory,
    and converts the result directly to a PNG.
    """
    input_dir = INPUT_MOB_DIR if item_type == 'mob' else INPUT_PETAL_DIR
    output_dir = OUTPUT_MOB_DIR_PNG if item_type == 'mob' else OUTPUT_PETAL_DIR_PNG
    item_id = item_info['id'] # This can be a number or a string (e.g., "beetle")

    for rarity in RARITIES:
        # Background is always based on rarity
        background_path = find_fallback_asset(input_dir, 0, rarity)
        # Foreground is based on the specific item and rarity
        foreground_path = find_fallback_asset(input_dir, item_id, rarity)

        if not background_path or not foreground_path:
            continue

        try:
            ET.register_namespace('', "http://www.w3.org/2000/svg")
            bg_tree = ET.parse(background_path)
            bg_root = bg_tree.getroot()
            fg_tree = ET.parse(foreground_path)
            fg_root = fg_tree.getroot()

            for element in fg_root:
                bg_root.append(element)
            
            merged_svg_bytestring = ET.tostring(bg_root, encoding='utf-8')

        except (ET.ParseError, FileNotFoundError):
            continue

        output_filename = f"{item_id}_{rarity}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            cairosvg.svg2png(
                bytestring=merged_svg_bytestring,
                write_to=output_path,
                output_width=PNG_WIDTH,
                output_height=PNG_HEIGHT
            )
        except Exception:
            continue

def run_combined_process():
    """Main function to orchestrate the entire merge-and-convert pipeline."""
    game_data = load_game_data()
    if not game_data:
        return

    os.makedirs(OUTPUT_PETAL_DIR_PNG, exist_ok=True)
    os.makedirs(OUTPUT_MOB_DIR_PNG, exist_ok=True)

    # --- Prepare mob tasks, ensuring both individual leaders and groups are included ---
    mob_tasks = []
    
    # 1. Add ALL individual mobs from the main list, including leaders.
    #    The `if` condition that excluded leaders has been removed.
    for mob in game_data['mobs']:
        mob_tasks.append(mob)

    # 2. Add the special spawn groups themselves as new tasks.
    #    This uses the string-based ID (e.g., "beetle") to find the question mark SVG.
    for group in game_data.get('shared_spawns', []):
        mob_tasks.append({
            "id": group['group_id'], # Use the string ID like "beetle"
            "name": group['group_name'],
            "display_name": group['group_name'],
            "abbreviation": group.get('abbreviation', '')
        })
        
    all_tasks = []
    for item in game_data['petals']:
        all_tasks.append((item, 'petal'))
    for item in mob_tasks:
        all_tasks.append((item, 'mob'))
        
    print(f"Starting combined merge & convert process for {len(all_tasks)} items...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        list(tqdm(executor.map(lambda p: process_and_convert(*p), all_tasks), total=len(all_tasks), desc="Processing assets"))

    print("\n" + "="*40)
    print("Asset processing complete!")
    print(f"Final PNG images for your bot are in:")
    print(f"  - {OUTPUT_PETAL_DIR_PNG}")
    print(f"  - {OUTPUT_MOB_DIR_PNG}")
    print("="*40)

if __name__ == "__main__":
    run_combined_process()