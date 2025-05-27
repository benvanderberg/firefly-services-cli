import os
import re
import json
import requests
from itertools import product
from utils.storage import upload_to_azure_storage
from typing import Optional, List, Dict, Any, Union

def generate_image(access_token, prompt, num_generations=1, model_version='image3', content_class='photo',
                  negative_prompt=None, prompt_biasing_locale=None, size=None, seeds=None, debug=False,
                  visual_intensity=None, style_ref_path=None, style_ref_strength=50,
                  composition_ref_path=None, composition_ref_strength=50):
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
        size (dict): Image size specification with width and height
        seeds (list): List of seeds for generation
        debug (bool): Enable debug output
        visual_intensity (int): Visual intensity of the generated image (1-10)
        style_ref_path (str): Path to style reference image file
        style_ref_strength (int): Strength of the style reference (1-100)
        composition_ref_path (str): Path to composition reference image file
        composition_ref_strength (int): Strength of the composition reference (1-100)
    
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
        if not (isinstance(size, dict) and 'width' in size and 'height' in size):
            raise ValueError("Size must be a dict with 'width' and 'height' keys.")
        data["size"] = size
    
    if seeds:
        data["seeds"] = seeds
    
    if visual_intensity:
        data["visualIntensity"] = visual_intensity
    
    # Style reference
    if style_ref_path:
        # Upload or resolve style_ref_path to a URL if needed
        style_url = style_ref_path
        if style_url.startswith('file://') or os.path.exists(style_url):
            style_url = upload_to_azure_storage(style_url)
        data["styles"] = [{
            "imageReference": {
                "source": {"url": style_url}
            },
            "strength": style_ref_strength
        }]
    
    # Composition reference (structure)
    if composition_ref_path:
        # Upload or resolve composition_ref_path to a URL if needed
        cref_url = composition_ref_path
        if cref_url.startswith('file://') or os.path.exists(cref_url):
            cref_url = upload_to_azure_storage(cref_url)
        data["structure"] = {
            "imageReference": {
                "source": {"url": cref_url}
            },
            "strength": composition_ref_strength
        }
    
    if debug:
        print("Request data:", json.dumps(data, indent=2))
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if debug and e.response is not None:
            print("API Error Response:", e.response.text)
        raise

def normalize_model_name(model_name, debug=False):
    """
    Normalize model name to its full version.
    
    Args:
        model_name (str): The model name to normalize
        debug (bool): Whether to show debug information
    
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
    if debug:
        print(f"Normalized model name: {model_name} -> {normalized}")
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

def parse_model_variations(model_str, debug=False):
    """
    Parse model string containing variations in [option1,option2,...] format.
    
    Args:
        model_str (str): The model string containing variations
        debug (bool): Whether to show debug information
    
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
            return [normalize_model_name(m, debug) for m in models]
    
    # If no variations, return single model
    return [normalize_model_name(model_str, debug)]

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

def generate_similar_image(
    access_token: str,
    image_path: str,
    num_variations: int = 1,
    model_version: str = 'image3',
    size: Optional[Dict[str, int]] = None,
    seeds: Optional[List[int]] = None,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Generate similar images based on a reference image.
    
    Args:
        access_token (str): Adobe authentication token
        image_path (str): Path to the reference image file
        num_variations (int): Number of variations to generate (1-4)
        model_version (str): Model version to use
        size (dict): Image size with width and height
        seeds (list): List of seed values for consistent generation
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Job information including status URL
    """
    # Upload the reference image to Azure Storage
    image_url = upload_to_azure_storage(image_path)
    
    # Prepare the request payload
    payload = {
        "image": {
            "source": {
                "url": image_url
            }
        },
        "numVariations": num_variations
    }
    
    # Add optional parameters if provided
    if size:
        payload["size"] = size
    if seeds:
        payload["seeds"] = seeds
    
    # Prepare headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'x-model-version': model_version
    }
    
    # Make the API request
    response = requests.post(
        'https://firefly-api.adobe.io/v3/images/generate-similar-async',
        headers=headers,
        json=payload
    )
    
    if debug:
        print("\nRequest Headers:", json.dumps(headers, indent=2))
        print("\nRequest Payload:", json.dumps(payload, indent=2))
        print("\nResponse Status:", response.status_code)
        print("\nResponse Headers:", json.dumps(dict(response.headers), indent=2))
        print("\nResponse Body:", json.dumps(response.json(), indent=2))
    
    response.raise_for_status()
    return response.json()

def expand_image(
    access_token: str,
    image_path: str,
    prompt: str,
    mask_path: Optional[str] = None,
    mask_invert: Optional[bool] = None,
    num_variations: int = 1,
    align_h: Optional[str] = None,
    align_v: Optional[str] = None,
    left: Optional[int] = None,
    right: Optional[int] = None,
    top: Optional[int] = None,
    bottom: Optional[int] = None,
    height: Optional[int] = None,
    width: Optional[int] = None,
    seeds: Optional[List[int]] = None,
    debug: bool = False
) -> dict:
    image_url = upload_to_azure_storage(image_path)
    mask_url = upload_to_azure_storage(mask_path) if mask_path else None

    payload = {
        "image": {"source": {"url": image_url}},
        "numVariations": num_variations,
        "prompt": prompt
    }

    # Only add placement if any alignment or inset parameters are set
    if any(param is not None for param in [align_h, align_v, left, right, top, bottom]):
        placement = {}
        if align_h is not None or align_v is not None:
            placement["alignment"] = {}
            if align_h is not None:
                placement["alignment"]["horizontal"] = align_h
            if align_v is not None:
                placement["alignment"]["vertical"] = align_v
        if any(param is not None for param in [left, right, top, bottom]):
            placement["inset"] = {}
            if left is not None:
                placement["inset"]["left"] = left
            if right is not None:
                placement["inset"]["right"] = right
            if top is not None:
                placement["inset"]["top"] = top
            if bottom is not None:
                placement["inset"]["bottom"] = bottom
        payload["placement"] = placement

    if mask_url:
        payload["mask"] = {
            "invert": mask_invert,
            "source": {"url": mask_url}
        }
    if height and width:
        payload["size"] = {"height": height, "width": width}
    if seeds:
        payload["seeds"] = seeds

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        "Content-Type": "application/json"
    }
    url = "https://firefly-api.adobe.io/v3/images/expand-async"
    if debug:
        print("Expand payload:", json.dumps(payload, indent=2))
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json() 