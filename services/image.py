import os
import re
import json
import requests
import time
from itertools import product
from utils.storage import upload_to_azure_storage
from typing import Optional, List, Dict, Any, Union

def generate_image(access_token, prompt, num_generations=1, model_version='image3', content_class='photo',
                  negative_prompt=None, prompt_biasing_locale=None, size=None, seeds=None, debug=False,
                  visual_intensity=None, style_ref_path=None, style_ref_strength=50,
                  composition_ref_path=None, composition_ref_strength=50, custom_model=False):
    """
    Generate images using the Firefly API with retry logic for transient errors.
    """
    max_retries = int(os.getenv('API_MAX_RETRIES', 3))
    base_delay = float(os.getenv('API_RETRY_DELAY', 2.0))
    
    for attempt in range(max_retries + 1):
        try:
            return _generate_image_internal(
                access_token, prompt, num_generations, model_version, content_class,
                negative_prompt, prompt_biasing_locale, size, seeds, debug,
                visual_intensity, style_ref_path, style_ref_strength,
                composition_ref_path, composition_ref_strength, custom_model
            )
        except requests.HTTPError as e:
            # Retry on 5xx server errors (including 504 Gateway Timeout)
            if e.response and 500 <= e.response.status_code < 600:
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    if debug:
                        print(f"Server error {e.response.status_code}: {e}. Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(delay)
                    continue
                else:
                    if debug:
                        print(f"Max retries ({max_retries}) reached for server error {e.response.status_code}")
            # Re-raise non-retryable errors
            raise
        except requests.RequestException as e:
            # Retry on network errors
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                if debug:
                    print(f"Network error: {e}. Retrying in {delay:.1f} seconds... (attempt {attempt + 1}/{max_retries + 1})")
                time.sleep(delay)
                continue
            else:
                if debug:
                    print(f"Max retries ({max_retries}) reached for network error")
                raise

def _generate_image_internal(access_token, prompt, num_generations=1, model_version='image3', content_class='photo',
                           negative_prompt=None, prompt_biasing_locale=None, size=None, seeds=None, debug=False,
                           visual_intensity=None, style_ref_path=None, style_ref_strength=50,
                           composition_ref_path=None, composition_ref_strength=50, custom_model=False):
    """
    Internal function to generate images (without retry logic).
    """
    # Upload style reference if provided
    style_ref_url = None
    if style_ref_path:
        style_ref_url = upload_to_azure_storage(style_ref_path)
    
    # Upload composition reference if provided
    composition_ref_url = None
    if composition_ref_path:
        composition_ref_url = upload_to_azure_storage(composition_ref_path)
    
    # Prepare the request payload
    data = {
        "prompt": prompt,
        "numVariations": num_generations,
        "contentClass": content_class
    }
    
    # Add optional parameters if provided
    if negative_prompt:
        data["negativePrompt"] = negative_prompt
    if prompt_biasing_locale:
        data["promptBiasingLocale"] = prompt_biasing_locale
    if size:
        data["size"] = size
    if seeds:
        data["seeds"] = seeds
    if visual_intensity is not None:
        data["visualIntensity"] = visual_intensity
    if style_ref_url:
        data["style"] = {
            "imageReference": {
                "source": {"url": style_ref_url}
            },
            "strength": style_ref_strength
        }
    if composition_ref_url:
        data["structure"] = {
            "imageReference": {
                "source": {"url": composition_ref_url}
            },
            "strength": composition_ref_strength
        }
    if custom_model:
        data["customModelId"] = model_version
    
    # Prepare headers
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID']
    }
    
    # Set model version header based on whether it's a custom model
    if custom_model:
        headers['x-model-version'] = 'image4_custom'
    else:
        headers['x-model-version'] = model_version
    
    url = 'https://firefly-api.adobe.io/v3/images/generate-async'
    
    if debug:
        print("Request data:", json.dumps(data, indent=2))
        print("Request headers:", json.dumps(headers, indent=2))
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

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

def fill_image(
    access_token: str,
    image_path: str,
    mask_path: str,
    prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    prompt_biasing_locale: Optional[str] = None,
    num_variations: int = 1,
    mask_invert: bool = False,
    height: Optional[int] = None,
    width: Optional[int] = None,
    seeds: Optional[List[int]] = None,
    debug: bool = False
) -> dict:
    """
    Perform Generative Fill on an image using a mask.
    
    Args:
        access_token (str): Adobe authentication token
        image_path (str): Path to the input image file
        mask_path (str): Path to the mask image file
        prompt (str, optional): Text prompt for the fill
        negative_prompt (str, optional): Text describing what to avoid in the generation
        prompt_biasing_locale (str, optional): Locale code for prompt biasing
        num_variations (int): Number of variations to generate (1-4)
        mask_invert (bool): Whether to invert the mask
        height (int, optional): Output height in pixels
        width (int, optional): Output width in pixels
        seeds (list, optional): List of seed values for consistent generation
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Job information including status URL
    """
    image_url = upload_to_azure_storage(image_path)
    mask_url = upload_to_azure_storage(mask_path)

    payload = {
        "image": {"source": {"url": image_url}},
        "mask": {
            "invert": mask_invert,
            "source": {"url": mask_url}
        },
        "numVariations": num_variations
    }

    if prompt:
        payload["prompt"] = prompt
    if negative_prompt:
        payload["negativePrompt"] = negative_prompt
    if prompt_biasing_locale:
        payload["promptBiasingLocaleCode"] = prompt_biasing_locale
    if seeds:
        payload["seeds"] = seeds

    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        "Content-Type": "application/json"
    }
    url = "https://firefly-api.adobe.io/v3/images/fill-async"
    if debug:
        print("Fill payload:", json.dumps(payload, indent=2))
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def create_mask(
    access_token: str,
    image_path: str,
    output_path: str,
    optimize: str = "performance",
    postprocess: bool = True,
    service_version: str = "4.0",
    mask_format: str = "soft",
    debug: bool = False
) -> dict:
    """
    Create a mask from an input image using Adobe Sensei API.
    
    Args:
        access_token (str): Adobe authentication token
        image_path (str): Path to the input image file
        output_path (str): Path where the mask will be saved
        optimize (str): Optimization mode ("performance" or "quality")
        postprocess (bool): Whether to apply post-processing
        service_version (str): Service version to use
        mask_format (str): Mask format ("soft" or "hard")
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Job information including status URL
    """
    # Upload the input image to Azure Storage
    input_url = upload_to_azure_storage(image_path, debug=debug)
    
    # Create output URL by modifying the input URL
    output_url = input_url.rsplit('.', 1)[0] + '_masked.' + input_url.rsplit('.', 1)[1]
    
    # Prepare the request payload
    payload = {
        "input": {
            "href": input_url,
            "storage": "azure"
        },
        "output": {
            "href": output_url,
            "storage": "azure",
            "overwrite": True,
            "color": {
                "space": "rgb"
            },
            "mask": {
                "format": mask_format
            }
        },
        "options": {
            "optimize": optimize,
            "postprocess": postprocess,
            "serviceVersion": service_version
        }
    }
    
    # Prepare headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "x-api-key": os.environ['FIREFLY_SERVICES_CLIENT_ID']
    }
    
    # Make the API request
    url = "https://image.adobe.io/sensei/mask"
    if debug:
        print("Mask creation payload:", json.dumps(payload, indent=2))
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    
    # Get the status URL from the response
    status_data = response.json()
    status_url = status_data['_links']['self']['href']
    
    if debug:
        print(f"Status URL: {status_url}")
    
    # Poll the status URL until the job is complete
    while True:
        status_response = requests.get(status_url, headers=headers)
        status_response.raise_for_status()
        status_data = status_response.json()
        
        if debug:
            print("Status response:", json.dumps(status_data, indent=2))
        
        if status_data['status'] == 'succeeded':
            # Get the output URL and download the mask
            output_url = status_data['output']['href']
            try:
                # Download the file from Azure
                mask_response = requests.get(output_url)
                mask_response.raise_for_status()
                
                # Save to output file
                with open(output_path, 'wb') as f:
                    f.write(mask_response.content)
                
                if debug:
                    print(f"Mask downloaded successfully to {output_path}")
                break
            except Exception as e:
                if debug:
                    print(f"Error downloading mask: {str(e)}")
                raise
        elif status_data['status'] == 'failed':
            raise Exception(f"Mask creation failed: {status_data.get('error', 'Unknown error')}")
        
        # Wait before polling again
        time.sleep(2)
    
    return status_data 