import os
import re
import json
import requests
from itertools import product

def generate_image(access_token, prompt, num_generations=1, model_version='image3', content_class='photo',
                  negative_prompt=None, prompt_biasing_locale=None, size=None, seeds=None, debug=False,
                  visual_intensity=None, style_ref_path=None):
    """
    Generate images using Adobe Firefly Services API.
    
    Args:
        access_token (str): Adobe Firefly Services access token
        prompt (str): Text prompt for image generation
        num_generations (int): Number of images to generate
        model_version (str): Model version to use
        content_class (str): Content class for the image
        negative_prompt (str): Negative prompt to guide generation
        prompt_biasing_locale (str): Locale for prompt biasing
        size (dict): Image size specification
        seeds (list): List of seeds for generation
        debug (bool): Enable debug output
        visual_intensity (int): Visual intensity of the generated image (1-10)
        style_ref_path (str): Path to style reference image file
    
    Returns:
        dict: Job information including job ID and status
    """
    url = "https://firefly-api.adobe.io/v3/images/generate-async"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        "Content-Type": "application/json"
    }
    
    data = {
        "prompt": prompt,
        "numVariations": num_generations,
        "modelVersion": model_version,
        "contentClass": content_class
    }
    
    if negative_prompt:
        data["negativePrompt"] = negative_prompt
    
    if prompt_biasing_locale:
        data["promptBiasingLocale"] = prompt_biasing_locale
    
    if size:
        data["size"] = size
    
    if seeds:
        data["seeds"] = seeds
        
    if visual_intensity is not None:
        # Convert 1-10 scale to 0.0-1.0 scale
        data["intensity"] = visual_intensity / 10.0

    # Handle style reference if provided
    if style_ref_path:
        if os.environ.get('STORAGE_TYPE') == 'azure':
            # Upload to Azure and get URL
            from utils.storage import upload_to_azure_storage
            style_ref_url = upload_to_azure_storage(style_ref_path)
            data["style"] = {
                "imageReference": {
                    "source": {
                        "url": style_ref_url
                    }
                },
                "strength": 100  # Full adherence to style
            }
        else:
            # Use local file path
            data["style"] = {
                "imageReference": {
                    "source": {
                        "url": f"file://{os.path.abspath(style_ref_path)}"
                    }
                },
                "strength": 100  # Full adherence to style
            }
    
    if debug:
        print("Request data:", json.dumps(data, indent=2))
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def normalize_model_name(model_name):
    """
    Normalize model name to its full version.
    
    Args:
        model_name (str): The model name to normalize
    
    Returns:
        str: The normalized model name
    """
    model_mapping = {
        'image4': 'image4_standard',
        'ultra': 'image4_ultra',
        'image4_ultra': 'image4_ultra',
        'image4_standard': 'image4_standard',
        'image3': 'image3',
        'image3_custom': 'image3_custom'
    }
    normalized = model_mapping.get(model_name, model_name)
    print(f"Normalized model name: {model_name} -> {normalized}")  # Debug output
    return normalized

def format_model_name_for_display(model_name):
    """
    Format model name for display in output messages.
    
    Args:
        model_name (str): The model name to format
    
    Returns:
        str: The formatted model name for display
    """
    model_display_names = {
        'image3': 'Image 3',
        'image3_custom': 'Image 3 Custom',
        'image4_standard': 'Image 4',
        'image4_ultra': 'Image 4 Ultra'
    }
    return model_display_names.get(model_name, model_name)

def parse_model_variations(model_str):
    """
    Parse model string containing variations in [option1,option2,...] format.
    
    Args:
        model_str (str): The model string containing variations
    
    Returns:
        list: List of model versions to use
    """
    # Check if the string contains variations
    if '[' in model_str and ']' in model_str:
        # Extract the variations
        match = re.search(r'\[(.*?)\]', model_str)
        if match:
            # Split the options and strip whitespace
            models = [m.strip() for m in match.group(1).split(',')]
            # Normalize each model name
            return [normalize_model_name(m) for m in models]
    
    # If no variations, return single model
    return [normalize_model_name(model_str)]

def parse_style_ref_variations(style_ref_str):
    """
    Parse style reference string containing variations in [option1,option2,...] format.
    
    Args:
        style_ref_str (str): The style reference string containing variations
    
    Returns:
        list: List of style reference files to use
    """
    # Check if the string contains variations
    if '[' in style_ref_str and ']' in style_ref_str:
        # Extract the variations
        match = re.search(r'\[(.*?)\]', style_ref_str)
        if match:
            # Split the options and strip whitespace
            return [s.strip() for s in match.group(1).split(',')]
    
    # If no variations, return single style reference
    return [style_ref_str] if style_ref_str else [] 