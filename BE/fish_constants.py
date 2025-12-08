import csv
import os

# --- Configuration ---
# MODEL_ID = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
# MODEL_ID = "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
MODEL_ID =  "meta-llama/llama-3-2-90b-vision-instruct";
CSV_FILENAME = "Marine_Fish_Possible_Output.csv"

def load_fish_data_from_csv():
    """
    Reads the CSV file from the same directory and returns:
    1. A list of allowed species names.
    2. A formatted text description string.
    """
    allowed_species = []
    description_lines = []
    
    # Locate CSV file relative to this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, CSV_FILENAME)

    if not os.path.exists(file_path):
        # Fallback if file is missing (to prevent crash on import)
        print(f"⚠️ Warning: '{CSV_FILENAME}' not found in {base_dir}")
        return [], ""

    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check for required columns
            if 'Fish Name' not in reader.fieldnames or 'Physical Description' not in reader.fieldnames:
                print("⚠️ Error: CSV is missing 'Fish Name' or 'Physical Description' columns.")
                return [], ""

            for row in reader:
                name = row['Fish Name'].strip()
                desc = row['Physical Description'].strip()
                
                if name and desc:
                    allowed_species.append(name)
                    # Format: "FishName Description"
                    description_lines.append(f"{name} {desc}")
                    
        return allowed_species, "\n".join(description_lines)

    except Exception as e:
        print(f"⚠️ Error loading fish constants: {e}")
        return [], ""

# --- Load Data on Module Import ---
ALLOWED_FISH_SPECIES, FISH_BASE_DESCRIPTION = load_fish_data_from_csv()

# --- System Prompt ---
# Note: I used 'top_candidates' and 'english_name' to match your app.py logic
SYSTEM_CONTENT_SINGLE = f"""
You are an expert Ichthyologist and AI assistant. Your task is to analyze the image and identify exactly 5 potential candidate species from the allowed list. 

Allowed species list (exact English names): {', '.join(ALLOWED_FISH_SPECIES)}

Your task:
1. Visually analyze the fish in the image (shape, pattern, color).
3. Select the **Top 5** most likely species.
4. **IMPORTANT:** Recognize that marine animals vary in color/pattern. Focus on fundamental morphological features.

Output Requirements:
Produce ONLY valid JSON (no markdown fences). The 'top_candidates' list must contain exactly 5 entries sorted by confidence.

Schema:
{{
    "image_contains_fish": <true|false>,
    "results": [
        {{
            "fish_name": <string, must be from allowed list>,
            "score": <float, 0.0-1.0>,
            "score_reason": <string, brief explanation of visual match>
        }}
    ]
}}
"""