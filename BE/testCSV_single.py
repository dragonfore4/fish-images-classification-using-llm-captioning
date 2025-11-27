import requests
import json
import csv
import re
import os
import ibm_boto3
from ibm_botocore.client import Config
from dotenv import load_dotenv
from typing import List, Dict, Any, Tuple

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
API_URL = "http://localhost:8080/identify_and_search"
OUTPUT_CSV = "fish_identification_batch_results.csv"

# COS Configuration (assumed from your Flask App environment)
COS_API_KEY = os.getenv('IBM_COS_API_KEY')
COS_RESOURCE_INSTANCE_ID = os.getenv('IBM_COS_RESOURCE_INSTANCE_ID')
COS_ENDPOINT = os.getenv('IBM_COS_ENDPOINT')
COS_BUCKET_NAME = 'fish-image-bucket'  # Hardcoded based on Flask app
COS_PREFIX = 'fish-image/' # The folder/prefix to search within

def initialize_cos_client():
    """Initializes and returns the IBM COS client."""
    if not all([COS_API_KEY, COS_RESOURCE_INSTANCE_ID, COS_ENDPOINT]):
        print("🛑 Error: Missing one or more IBM COS environment variables.")
        return None
    try:
        cos = ibm_boto3.client(
            's3',
            ibm_api_key_id=COS_API_KEY,
            ibm_service_instance_id=COS_RESOURCE_INSTANCE_ID,
            config=Config(signature_version='oauth'),
            endpoint_url=COS_ENDPOINT
        )
        return cos
    except Exception as e:
        print(f"🛑 Error initializing COS client: {e}")
        return None

def list_s3_keys(cos_client, bucket_name: str, prefix: str) -> List[str]:
    """
    Dynamically fetches all object keys (file paths) from the specified S3 prefix,
    filtering only for image files.
    """
    print(f"🔍 Connecting to COS to list files under prefix: {prefix}")
    image_keys: List[str] = []
    paginator = cos_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    
    # Common image extensions to filter results
    image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

    try:
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    # Only add keys that are files (not the prefix itself) and have image extensions
                    if key.endswith(image_extensions):
                        image_keys.append(key)
        
        print(f"✅ Found {len(image_keys)} image files in COS.")
        return image_keys
    except Exception as e:
        print(f"🛑 Error listing objects from COS: {e}")
        return []


def extract_expected_species(s3_key: str) -> str:
    """
    Extracts the expected fish species name from the S3 folder path.
    e.g., "fish-image/Bigeye-snapper/bigeye-snapper-001.png" -> "Bigeye snapper"
    """
    # Use a regex to capture the part between the two slashes that defines the folder
    match = re.search(r"fish-image/([^/]+)/", s3_key)
    if match:
        # Replace hyphens with spaces for easier comparison
        return match.group(1).replace('-', ' ')
    return "UNKNOWN"

def run_identification_test() -> None:
    """
    Runs the batch identification process, calling the Flask endpoint for each image,
    and saves the results to a CSV file.
    
    NOTE: Currently configured to run a single test case for validation.
    """
    
    # 1. Dynamically load S3 keys - MODIFIED TO USE A SINGLE HARDCODED KEY FOR TESTING
    # You would typically call list_s3_keys(cos, COS_BUCKET_NAME, COS_PREFIX) here.
    # For a single file test, we override this logic.
    SINGLE_TEST_KEY = "fish-image/Argus-grouper/argus-grouper-001.png"
    S3_KEYS_TO_TEST = [SINGLE_TEST_KEY] 
    
    # We still need the COS client initialized to prevent errors in list_s3_keys if we uncomment it later.
    # But since we are hardcoding S3_KEYS_TO_TEST, we don't strictly need `cos` for the loop.
    cos = initialize_cos_client()
    if not cos:
        print("Cannot proceed without a valid COS connection.")
        return

    print(f"\n--- Starting Single File Test ({len(S3_KEYS_TO_TEST)} image) ---")
    
    # Define the CSV header
    csv_header = [
        "S3 Image Path",
        "Expected Species (Folder Name)",
        "AI Generated Caption",
        "Top Candidate (Elasticsearch Result)",
        "Top Candidate Score",
        "Expected Species In Top 5 Candidates",
        "All Top 5 Candidates"
    ]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)

        for s3_key in S3_KEYS_TO_TEST:
            expected_species = extract_expected_species(s3_key)
            print(f"\n-> Testing: {s3_key} (Expected: {expected_species})")
            
            payload = json.dumps({"image": s3_key})
            headers = {'Content-Type': 'application/json'}
            
            try:
                # 2. Call the Flask endpoint
                response = requests.post(API_URL, headers=headers, data=payload, timeout=60)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                result: Dict[str, Any] = response.json()

                # 3. Extract key results
                caption = result.get('ai_generated_caption', 'N/A')
                search_results: List[Dict[str, Any]] = result.get('elasticsearch_results', [])

                # 4. Process search results
                top_candidate_name = 'N/A'
                top_candidate_score = 'N/A'
                all_candidates_str = 'N/A'
                match_status = "FALSE"
                
                if search_results:
                    # Get the Top 1 Candidate details
                    top_candidate = search_results[0]
                    top_candidate_name = top_candidate.get('fish_name', 'N/A') # <--- FIXED HERE
                    top_candidate_score = f"{top_candidate.get('score', 0.0):.4f}"

                    # Check if the expected species is anywhere in the Top 5 list
                    expected_clean = expected_species.lower()
                    match_found = any(
                        cand.get('fish_name', '').lower().replace('-', ' ') == expected_clean # <--- FIXED HERE
                        for cand in search_results
                    )
                    match_status = "TRUE" if match_found else "FALSE"

                    # Format all candidates into a single string for the CSV
                    all_candidates_str = "; ".join([
                        f"R{i+1}: {cand.get('fish_name', 'N/A')} ({cand.get('score', 0.0):.4f})" # <--- FIXED HERE
                        for i, cand in enumerate(search_results)
                    ])

                # 5. Write the row data
                row_data = [
                    s3_key,
                    expected_species,
                    caption.replace('\n', ' ')[:100] + '...' if caption != 'N/A' else 'N/A', # Truncate and clean caption for CSV
                    top_candidate_name,
                    top_candidate_score,
                    match_status,
                    all_candidates_str
                ]
                writer.writerow(row_data)

                # Adjusted print statement to confirm the logic for "Match in Top 5"
                print(f"  -> Test Complete. Top Candidate: {top_candidate_name}. Expected ({expected_species}) was found in Top 5: {match_status}")

            except requests.exceptions.RequestException as e:
                print(f"  ❌ Error calling API: {e}")
                writer.writerow([s3_key, expected_species, f"API ERROR: {e}", "N/A", "0.0", "FALSE", "N/A"])
            except json.JSONDecodeError:
                # The response object must be defined here if we want to print response.text
                print(f"  ❌ Error decoding JSON response.")
                writer.writerow([s3_key, expected_species, "JSON DECODE ERROR", "N/A", "0.0", "FALSE", "N/A"])
            except Exception as e:
                print(f"  ❌ Unexpected Error: {e}")
                writer.writerow([s3_key, expected_species, f"UNEXPECTED ERROR: {e}", "N/A", "0.0", "FALSE", "N/A"])

    print(f"\n--- Single File Test Complete! Results saved to {OUTPUT_CSV} ---")

if __name__ == "__main__":
    run_identification_test()