import requests
import time
import os
from typing import Dict, Any, Optional

# Video generation API URL
VIDEO_GENERATION_API_URL = "https://firefly-beta.adobe.io/v3/videos/generate"

# Supported video sizes
VIDEO_SIZES = {
    '960x540': {'width': 960, 'height': 540},
    '540x960': {'width': 540, 'height': 960},
    '540x540': {'width': 540, 'height': 540},
    'sq540p': {'width': 540, 'height': 540},
    '1280x720': {'width': 1280, 'height': 720},
    '720p': {'width': 1280, 'height': 720},
    '720x1280': {'width': 720, 'height': 1280},
    'v720p': {'width': 720, 'height': 1280},
    '720x720': {'width': 720, 'height': 720},
    'sq720p': {'width': 720, 'height': 720},
    '1920x1080': {'width': 1920, 'height': 1080},
    '1080p': {'width': 1920, 'height': 1080},
    '1080x1920': {'width': 1080, 'height': 1920},
    'v1080p': {'width': 1080, 'height': 1920},
    '1080x1080': {'width': 1080, 'height': 1080},
    'sq1080p': {'width': 1080, 'height': 1080},
}

def parse_video_size(size_str: str) -> Dict[str, int]:
    """
    Parse video size string and return width/height dictionary.
    
    Args:
        size_str (str): Size string (e.g., "1080x1080", "1080p", "sq1080p")
        
    Returns:
        Dict[str, int]: Dictionary with 'width' and 'height' keys
        
    Raises:
        ValueError: If size is not supported
    """
    if size_str not in VIDEO_SIZES:
        raise ValueError(f"Unsupported video size: {size_str}. Supported sizes: {', '.join(VIDEO_SIZES.keys())}")
    
    return VIDEO_SIZES[size_str]

def generate_video(
    access_token: str,
    prompt: str,
    size: str,
    debug: bool = False
) -> Dict[str, Any]:
    """
    Generate a video using the Adobe Firefly video API.
    
    Args:
        access_token (str): OAuth access token
        prompt (str): Text prompt for video generation
        size (str): Video size (e.g., "1080x1080", "1080p")
        debug (bool): Enable debug output
        
    Returns:
        Dict[str, Any]: API response with jobId and statusUrl
        
    Raises:
        requests.RequestException: If API request fails
    """
    # Parse size
    size_dict = parse_video_size(size)
    
    # Prepare request headers
    headers = {
        'x-model-version': 'video1_8_standard',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': os.getenv('FIREFLY_SERVICES_CLIENT_ID'),
        'Authorization': f'Bearer {access_token}'
    }
    
    # Prepare request payload
    payload = {
        'prompt': prompt,
        'sizes': [size_dict]
    }
    
    if debug:
        print(f"DEBUG: Video generation request:")
        print(f"  URL: {VIDEO_GENERATION_API_URL}")
        print(f"  Headers: {headers}")
        print(f"  Payload: {payload}")
    
    # Make API request
    response = requests.post(VIDEO_GENERATION_API_URL, headers=headers, json=payload)
    
    if debug:
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response headers: {dict(response.headers)}")
        print(f"DEBUG: Response body: {response.text}")
    
    # Check for errors
    response.raise_for_status()
    
    return response.json()

def check_video_job_status(status_url: str, access_token: str, debug: bool = False) -> Dict[str, Any]:
    """
    Check the status of a video generation job.
    
    Args:
        status_url (str): Status URL from the generation response
        access_token (str): OAuth access token
        debug (bool): Enable debug output
        
    Returns:
        Dict[str, Any]: Job status response
        
    Raises:
        requests.RequestException: If API request fails
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    if debug:
        print(f"DEBUG: Checking video job status: {status_url}")
    
    response = requests.get(status_url, headers=headers)
    
    if debug:
        print(f"DEBUG: Status response: {response.status_code}")
        print(f"DEBUG: Status body: {response.text}")
    
    response.raise_for_status()
    return response.json()

def download_video(url: str, output_file: str, debug: bool = False) -> None:
    """
    Download a video from a URL and save it to a file.
    
    Args:
        url (str): Video URL to download
        output_file (str): Output file path
        debug (bool): Enable debug output
        
    Raises:
        requests.RequestException: If download fails
    """
    if debug:
        print(f"DEBUG: Downloading video from: {url}")
        print(f"DEBUG: Saving to: {output_file}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    
    # Download the video
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    if debug:
        print(f"DEBUG: Video downloaded successfully to: {output_file}") 