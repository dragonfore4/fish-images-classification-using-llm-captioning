from dotenv import load_dotenv
import base64
import os
import http.client
import json
import requests
import pandas as pd

load_dotenv()

watsonx_api_key = os.getenv("WATSONX_APIKEY", None)
ibm_cloud_url = os.getenv("IBM_CLOUD_URL", None)
project_id = os.getenv("PROJECT_ID", None)
ibm_cloud_iam_url = os.getenv("IAM_IBM_CLOUD_URL", None)
chat_url = os.getenv("IBM_WATSONX_AI_INFERENCE_URL", None)


### input and descripe input image

def convert_image_to_base64(image_path):
    pic = open(image_path,"rb").read()
    pic_base64 = base64.b64encode(pic)
    pic_string = pic_base64.decode("utf-8")
    return pic_string


def get_fish_description_from_watsonxai(pic_string):
    conn_ibm_cloud_iam = http.client.HTTPSConnection(ibm_cloud_iam_url)
    payload = "grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey&apikey="+watsonx_api_key
    headers = { 'Content-Type': "application/x-www-form-urlencoded" }
    conn_ibm_cloud_iam.request("POST", "/identity/token", payload, headers)
    res = conn_ibm_cloud_iam.getresponse()
    data = res.read()
    decoded_json=json.loads(data.decode("utf-8"))
    access_token=decoded_json["access_token"]

    system_content = """
    You always answer the questions with markdown formatting using GitHub syntax. 
    The markdown formatting you support: headings, bold, italic, links, tables, lists, code blocks, and blockquotes. 
    You must omit that you answer the questions with markdown.

    Any HTML tags must be wrapped in block quotes, for example:
    ```<html>```. 
    You will be penalized for not rendering code in block quotes.

    When returning code blocks, specify the language.

    You are a helpful, respectful, and honest assistant. Always answer as helpfully as possible, while being safe. 
    Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. 
    Please ensure that your responses are socially unbiased and positive in nature.

    If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. 
    If you don't know the answer to a question, please don't share false information.
    """
    user_message = """Please provide a detailed description of what the image depicts and what you think it"""
    
    # system_content = """
    # You are an expert visual analysis and description assistant. Your primary goal is to provide a detailed, objective, and structured description of the image's contents, focusing specifically on **physical and visual characteristics** of the main subject. This description should be highly relevant for matching against a structured database field like 'physical_description'.

    # ## Output Format & Constraints
    # 1.  Always answer the questions with **markdown formatting** using GitHub syntax (headings, bold, italic, links, tables, lists, code blocks, and blockquotes). You must **omit** any mention that you are answering with markdown.
    # 2.  Any HTML tags or code snippets must be wrapped in language-specified **code blocks**. E.g., ```html <html>```. You will be penalized for not rendering code in block quotes.
    # 3.  Focus the description on elements such as **body shape/size, colors/patterns, distinctive features, and unique marks**.
    # 4.  Do not include subjective opinions or inferences. Stick strictly to observable facts in the image.

    # ## General AI Safety & Ethics
    # You are a helpful, respectful, and honest assistant. Always answer as helpfully as possible, while being safe. Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. Ensure your responses are socially unbiased and positive in nature. If a question is nonsensical or not factually coherent, explain why instead of answering incorrectly. If you don't know the answer, do not share false information.
    # """

    # user_message = """
    # Analyze the provided image and generate a **detailed, factual description of the main subject's physical characteristics** (e.g., a fish). Structure your description by focusing on the following attributes, as you would for a database entry:

    # 1.  **Body:** Describe its shape, estimated size/length relative to typical species (if identifiable), and overall form.
    # 2.  **Colors/Patterns:** Detail the primary colors, any secondary colors, and the nature of any spots, stripes, or bands.
    # 3.  **Features:** Describe specific anatomical features such as the head shape, snout, fin placement/shape (dorsal, pectoral, etc.), and mouth.
    # 4.  **Unique Marks:** Note any single, distinctive visual elements that could serve as a unique identifier (like a specific patch, unique spot pattern, or unusual fin shape).

    # Provide the description in a concise, paragraph format, ensuring all four points are covered. **Do not speculate on the species name.**
    # """

    body = {
    "messages": [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": user_message,
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64, {pic_string}"
                }
                }
            ]
        }
    ],
    "project_id": project_id,
    # "model_id": "meta-llama/llama3-llava-next-8b-hf",
    # "model_id": "meta-llama/llama-3-2-11b-vision-instruct",
    # "model_id": "meta-llama/llama-3-2-90b-vision-instruct",
    "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "decoding_method": "greedy",
    "repetition_penalty": 1.1,
    "max_tokens": 900
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.post(
        chat_url,
        headers=headers,
        json=body
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    return data['choices'][0]['message']['content']

def get_json_generated_image_details(pic_string):
    conn_ibm_cloud_iam = http.client.HTTPSConnection(ibm_cloud_iam_url)
    payload = "grant_type=urn%3Aibm%3Aparams%3Aoauth%3Agrant-type%3Aapikey&apikey="+watsonx_api_key
    headers = { 'Content-Type': "application/x-www-form-urlencoded" }
    conn_ibm_cloud_iam.request("POST", "/identity/token", payload, headers)
    res = conn_ibm_cloud_iam.getresponse()
    data = res.read()
    decoded_json=json.loads(data.decode("utf-8"))
    access_token=decoded_json["access_token"]

    system_content = """
    You are an expert Ichthyologist and AI assistant specializing in marine biology and taxonomy, particularly species found in Thailand. 
    
    Your task is to analyze the input image and generate a strictly formatted JSON response based on your internal knowledge base.

    --- STEP 1: VALIDATION ---
    Analyze the image to determine if it contains a VALID, LIVING, or FRESH biological specimen of a fish.
    
    You must set `image_contains_fish` to `false` if the image shows:
    1. Cooked food (fried, grilled, steamed, or plated dishes).
    2. Processed fish (fillets, heads removed, dried fish).
    3. Non-realistic images (cartoons, drawings).
    4. Poor visibility (too blurry to identify).

    --- STEP 2: GENERATION ---
    If the image is valid, generate the details using the schema below.

    --- OUTPUT SCHEMA ---
    Return ONLY a raw JSON object (no markdown formatting, no ```json fences).
    
    {
        "image_contains_fish": <boolean>,
        "fish_details": {
            "fish_name": "<string: Common name in Englsih)>",
            "scientific_name": "<string: Scientific Latin name in English>",
            "order_name": "<string: Taxonomic Order in English>",
            "physical_description": "<string: A comprehensive and detailed physical description (approx. 3-5 sentences). Must cover body shape, scale patterns, specific coloration (including gradients or spots), fin characteristics (dorsal/pectoral shapes), and distinct anatomical features like mouth structure or spines.>",
            "habitat": "<string: A detailed description of the natural habitat. Include specific environments (e.g., coral reefs, mangroves, sandy bottoms), preferred water depth, water type (freshwater/brackish/marine), and behavior (solitary vs. schooling).>"
        }
    }

    If `image_contains_fish` is false, `fish_details` must be an empty object {}.
    """
    
    user_message = """
    Analyze the provided image. Identify the species and return the detailed JSON object as defined in your system instructions.
    """

    body = {
    "messages": [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": user_message,
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64, {pic_string}"
                }
                }
            ]
        }
    ],
    "project_id": project_id,
    # "model_id": "meta-llama/llama3-llava-next-8b-hf",
    # "model_id": "meta-llama/llama-3-2-11b-vision-instruct",
    # "model_id": "meta-llama/llama-3-2-90b-vision-instruct",
    "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "decoding_method": "greedy",
    "repetition_penalty": 1.1,
    "max_tokens": 900
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.post(
        chat_url,
        headers=headers,
        json=body
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    json_string = data['choices'][0]['message']['content']

    # Validate and parse the JSON response
    try:
        json_data = json.loads(json_string)
        if not isinstance(json_data, dict):
            raise ValueError("Response is not a valid JSON object")
        if "image_contains_fish" not in json_data or "fish_details" not in json_data:
            raise ValueError("Response JSON is missing required keys")
        if json_data["image_contains_fish"] and not json_data["fish_details"]:
            raise ValueError("Fish details should not be empty if image_contains_fish is true")
        return json_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e} returned: {json_string}")
