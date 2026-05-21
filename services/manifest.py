import os
import json
import requests
import time
from utils.storage import upload_to_azure_storage
from typing import Dict, Any, Optional

def create_manifest(
    access_token: str,
    input_file_path: str,
    output_file_path: str,
    debug: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Create a manifest for a PSD file using Adobe PIE API.
    
    Args:
        access_token (str): Adobe authentication token
        input_file_path (str): Path to the input PSD file
        output_file_path (str): Path to save the manifest JSON
        debug (bool): Whether to show debug information
        verbose (bool): Whether to show verbose output
    
    Returns:
        dict: Manifest data
    """
    if debug or verbose:
        print(f"Creating manifest for: {input_file_path}")
    
    # Upload the PSD file to Azure Storage
    if debug or verbose:
        print("Uploading PSD file to Azure Storage...")
    
    presigned_url = upload_to_azure_storage(input_file_path, debug=debug)
    
    if debug or verbose:
        print(f"File uploaded successfully. Presigned URL: {presigned_url[:50]}...")
    
    # Prepare the request payload for Adobe PIE API
    payload = {
        "inputs": [
            {
                "href": presigned_url,
                "storage": "azure"
            }
        ],
        "options": {
            "thumbnails": {
                "type": "image/jpeg"
            }
        }
    }
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'x-gw-ims-org-id': os.environ.get('FIREFLY_SERVICES_ORG_ID', '')
    }
    
    # Check if required environment variables are set
    if not os.environ.get('FIREFLY_SERVICES_ORG_ID'):
        raise ValueError("FIREFLY_SERVICES_ORG_ID environment variable is required for manifest creation")
    
    # Make the API request to Adobe PIE
    url = 'https://image.adobe.io/pie/psdService/documentManifest'
    
    if debug:
        print("Making request to Adobe PIE API...")
        print("Request URL:", url)
        print("Request headers:", json.dumps(headers, indent=2))
        print("Request payload:", json.dumps(payload, indent=2))
    elif verbose:
        print("Making request to Adobe PIE API...")
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if debug:
            print(f"Response status: {response.status_code}")
            print("Response headers:", json.dumps(dict(response.headers), indent=2))
        elif verbose:
            print(f"API request successful (status: {response.status_code})")
        
        response.raise_for_status()
        
        manifest_data = response.json()
        
        if debug:
            print("Response data:", json.dumps(manifest_data, indent=2))
        
        # Save the manifest to the output file
        with open(output_file_path, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        if debug or verbose:
            print(f"Manifest saved to: {output_file_path}")
        
        return manifest_data
        
    except requests.exceptions.HTTPError as e:
        if debug:
            print(f"HTTP Error: {e}")
            print(f"Response content: {e.response.text}")
        raise Exception(f"Failed to create manifest: HTTP {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        if debug:
            print(f"Request Error: {e}")
        raise Exception(f"Failed to create manifest: {str(e)}")
    except Exception as e:
        if debug:
            print(f"Unexpected error: {e}")
        raise Exception(f"Failed to create manifest: {str(e)}")
