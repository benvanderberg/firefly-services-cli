import os
import time
import json
import requests
import mimetypes
from typing import Dict, Any, Optional

def upload_file_to_pdf_services(access_token: str, file_path: str, debug: bool = False) -> str:
    """
    Upload a file to Adobe PDF Services and return the asset ID.
    
    Args:
        access_token (str): The authentication token
        file_path (str): Path to the file to upload
        debug (bool): Whether to show debug information
    
    Returns:
        str: The asset ID of the uploaded file
    
    Raises:
        Exception: If upload fails
    """
    # Validate file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{file_path}' does not exist")
    
    # Get file MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        raise ValueError(f"Could not determine MIME type for file '{file_path}'")
    
    # Step 1: Request upload URL from Adobe PDF Services
    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
    if not api_key:
        raise ValueError("FIREFLY_SERVICES_CLIENT_ID is not set in environment")
    
    headers = {
        'x-api-key': api_key,
        'x-request-id': f'ffcli-{int(time.time())}',
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "mediaType": mime_type
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/assets")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/assets',
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    
    data = response.json()
    
    if debug:
        print(f"Response: {data}")
    
    asset_id = data.get('assetID')
    upload_uri = data.get('uploadUri')
    
    if not asset_id or not upload_uri:
        raise Exception("Invalid response from Adobe PDF Services API")
    
    if debug:
        print(f"Uploading file to: {upload_uri}")
        print(f"File size: {os.path.getsize(file_path)} bytes")
        print(f"Content-Type: {mime_type}")
    
    # Step 2: Upload the file to the provided URI
    upload_headers = {'Content-Type': mime_type}
    if debug:
        print(f"Upload headers: {upload_headers}")
    
    with open(file_path, 'rb') as f:
        upload_response = requests.put(upload_uri, data=f, headers=upload_headers)
        upload_response.raise_for_status()
    
    if debug:
        print(f"Upload response status: {upload_response.status_code}")
        print(f"Upload response headers: {dict(upload_response.headers)}")
        if upload_response.text:
            print(f"Upload response body: {upload_response.text}")
    
    return asset_id

def convert_to_pdf(access_token: str, asset_id: str, debug: bool = False) -> Dict[str, Any]:
    """
    Convert an uploaded file to PDF using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded file
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If conversion request fails
    """
    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
    if not api_key:
        raise ValueError("FIREFLY_SERVICES_CLIENT_ID is not set in environment")
    
    headers = {
        'x-api-key': api_key,
        'x-request-id': f'ffcli-{int(time.time())}',
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "assetID": asset_id
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/createpdf")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/createpdf',
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    
    if debug:
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response text: {response.text}")
    
    # For 201 responses, we expect the status URL in the location header, not JSON body
    if response.status_code == 201:
        # Extract status URL from location header
        status_url = response.headers.get('location')
        if not status_url:
            raise Exception("No location header in response from Adobe PDF Services API")
        
        if debug:
            print(f"Status URL from location header: {status_url}")
        
        # Extract job ID from the status URL
        job_id = status_url.split('/')[-2] if '/' in status_url else 'unknown'
        
        return {
            'jobId': job_id,
            'statusUrl': status_url
        }
    else:
        # For other status codes, try to parse JSON
        try:
            data = response.json()
            if debug:
                print(f"Parsed response: {data}")
            return data
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from Adobe PDF Services API: {e}")

def check_pdf_job_status(status_url: str, access_token: str, debug: bool = False) -> Dict[str, Any]:
    """
    Poll the PDF job status URL until the job is complete.
    
    Args:
        status_url (str): The URL to check job status
        access_token (str): The authentication token
        debug (bool): Whether to show debug information
    
    Returns:
        dict: The completed job result
    
    Raises:
        Exception: If the job fails or encounters an error
    """
    headers = {
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    while True:
        response = requests.get(status_url, headers=headers)
        response.raise_for_status()
        status_data = response.json()
        
        if debug:
            print("\nStatus Response:", status_data)
        
        if status_data.get('status') == 'succeeded' or status_data.get('status') == 'done':
            return status_data
        elif status_data.get('status') == 'failed':
            raise Exception(f"Job failed: {status_data.get('error', 'Unknown error')}")
        
        if debug:
            print("Waiting for job completion...")
        time.sleep(2)  # Wait 2 seconds before checking again 