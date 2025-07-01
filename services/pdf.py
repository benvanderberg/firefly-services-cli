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

def export_pdf(access_token: str, asset_id: str, target_format: str, ocr_lang: str = "en-US", debug: bool = False) -> Dict[str, Any]:
    """
    Export a PDF to another format using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded PDF
        target_format (str): Target format (doc, docx, pptx, xlsx, rtf)
        ocr_lang (str): OCR language code (default: en-US)
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If export request fails
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
        "assetID": asset_id,
        "targetFormat": target_format,
        "ocrLang": ocr_lang
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/exportpdf")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/exportpdf',
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

def get_target_format_from_extension(file_path: str) -> str:
    """
    Determine the target format from the output file extension.
    
    Args:
        file_path (str): The output file path
    
    Returns:
        str: The target format for the API
    
    Raises:
        ValueError: If the extension is not supported
    """
    _, ext = os.path.splitext(file_path.lower())
    
    format_mapping = {
        '.doc': 'doc',
        '.docx': 'docx', 
        '.pptx': 'pptx',
        '.xlsx': 'xlsx',
        '.rtf': 'rtf'
    }
    
    if ext not in format_mapping:
        raise ValueError(f"Unsupported output format: {ext}. Supported formats: .doc, .docx, .pptx, .xlsx, .rtf")
    
    return format_mapping[ext]

def validate_ocr_language(ocr_lang: str) -> bool:
    """
    Validate that the OCR language is supported.
    
    Args:
        ocr_lang (str): The OCR language code to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    supported_languages = [
        "en-GB", "en-US", "nl-NL", "fr-FR", "de-DE", "it-IT", "es-ES", "sv-SE", 
        "da-DK", "fi-FI", "nb-NO", "pt-BR", "pt-PT", "ca-CA", "nn-NO", "de-CH", 
        "ja-JP", "bg-BG", "hr-HR", "cs-CZ", "et-EE", "el-GR", "hu-HU", "lv-LV", 
        "lt-LT", "pl-PL", "ro-RO", "ru-RU", "zh-CN", "sl-SI", "zh-Hant", "tr-TR", 
        "ko-KR", "sk-SK", "eu-ES", "gl-ES", "mk-MK", "mt-MT", "sr-SR", "uk-UA", "iw-IL"
    ]
    
    return ocr_lang in supported_languages 

def compress_pdf(access_token: str, asset_id: str, compression_level: str, debug: bool = False) -> Dict[str, Any]:
    """
    Compress a PDF using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded PDF
        compression_level (str): Compression level (LOW, MEDIUM, HIGH)
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If compression request fails
    """
    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
    if not api_key:
        raise ValueError("FIREFLY_SERVICES_CLIENT_ID is not set in environment")
    
    # Normalize compression level to uppercase
    compression_level = compression_level.upper()
    
    # Validate compression level
    if compression_level not in ['LOW', 'MEDIUM', 'HIGH']:
        raise ValueError(f"Invalid compression level: {compression_level}. Must be LOW, MEDIUM, or HIGH")
    
    headers = {
        'x-api-key': api_key,
        'x-request-id': f'ffcli-{int(time.time())}',
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "assetID": asset_id,
        "compressionLevel": compression_level
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/compresspdf")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/compresspdf',
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

def validate_compression_level(compression_level: str) -> bool:
    """
    Validate that the compression level is supported.
    
    Args:
        compression_level (str): The compression level to validate (case insensitive)
    
    Returns:
        bool: True if valid, False otherwise
    """
    valid_levels = ['LOW', 'MEDIUM', 'HIGH']
    return compression_level.upper() in valid_levels 

def ocr_pdf(access_token: str, asset_id: str, ocr_lang: str = "en-US", ocr_type: str = "searchable_image", debug: bool = False) -> Dict[str, Any]:
    """
    Perform OCR on a PDF using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded PDF
        ocr_lang (str): OCR language code (default: en-US)
        ocr_type (str): OCR type (searchable_image or searchable_image_exact)
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If OCR request fails
    """
    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
    if not api_key:
        raise ValueError("FIREFLY_SERVICES_CLIENT_ID is not set in environment")
    
    # Validate OCR type
    if ocr_type not in ['searchable_image', 'searchable_image_exact']:
        raise ValueError(f"Invalid OCR type: {ocr_type}. Must be 'searchable_image' or 'searchable_image_exact'")
    
    headers = {
        'x-api-key': api_key,
        'x-request-id': f'ffcli-{int(time.time())}',
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        "assetID": asset_id,
        "ocrLang": ocr_lang,
        "ocrType": ocr_type
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/ocr")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/ocr',
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

def validate_ocr_language_for_ocr(ocr_lang: str) -> bool:
    """
    Validate that the OCR language is supported for OCR operations.
    
    Args:
        ocr_lang (str): The OCR language code to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    supported_languages = [
        "da-DK", "lt-LT", "sl-SI", "el-GR", "ru-RU", "en-US", "zh-HK", "hu-HU", "et-EE", 
        "pt-BR", "uk-UA", "nb-NO", "pl-PL", "lv-LV", "fi-FI", "ja-JP", "es-ES", "bg-BG", 
        "en-GB", "cs-CZ", "mt-MT", "de-DE", "hr-HR", "sk-SK", "sr-SR", "ca-CA", "mk-MK", 
        "ko-KR", "de-CH", "nl-NL", "zh-CN", "sv-SE", "it-IT", "no-NO", "tr-TR", "fr-FR", 
        "ro-RO", "iw-IL"
    ]
    
    return ocr_lang in supported_languages

def validate_ocr_type(ocr_type: str) -> bool:
    """
    Validate that the OCR type is supported.
    
    Args:
        ocr_type (str): The OCR type to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    valid_types = ['searchable_image', 'searchable_image_exact']
    return ocr_type in valid_types 

def linearize_pdf(access_token: str, asset_id: str, debug: bool = False) -> Dict[str, Any]:
    """
    Linearize a PDF using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded PDF
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If linearization request fails
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
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/linearizepdf")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/linearizepdf',
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

def autotag_pdf(access_token: str, asset_id: str, shift_headings: bool = False, generate_report: bool = False, debug: bool = False) -> Dict[str, Any]:
    """
    Auto-tag a PDF using Adobe PDF Services.
    
    Args:
        access_token (str): The authentication token
        asset_id (str): The asset ID of the uploaded PDF
        shift_headings (bool): Whether to shift headings (default: False)
        generate_report (bool): Whether to generate Excel report (default: False)
        debug (bool): Whether to show debug information
    
    Returns:
        dict: Response containing job ID and status URL
    
    Raises:
        Exception: If auto-tag request fails
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
        "assetID": asset_id,
        "shiftHeadings": shift_headings,
        "generateReport": generate_report
    }
    
    if debug:
        print(f"Making request to: https://pdf-services-ue1.adobe.io/operation/autotag")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
    
    response = requests.post(
        'https://pdf-services-ue1.adobe.io/operation/autotag',
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

def download_file(url: str, output_file: str, silent: bool = False, debug: bool = False) -> None:
    """
    Download a file from a URL to a local path.
    
    Args:
        url (str): The URL to download from
        output_file (str): The local file path to save to
        silent (bool): Whether to minimize output
        debug (bool): Whether to show debug information
    """
    if debug:
        print(f"Downloading from: {url}")
        print(f"Saving to: {output_file}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    if not silent:
        print(f"Downloaded: {output_file}")

def download_autotag_results(result: Dict[str, Any], output_path: str, access_token: str, silent: bool = False, debug: bool = False) -> None:
    """
    Download auto-tag results (tagged PDF and optionally report).
    
    Args:
        result (dict): The completed job result
        output_path (str): Path for the tagged PDF output
        access_token (str): The authentication token
        silent (bool): Whether to minimize output
        debug (bool): Whether to show debug information
    
    Raises:
        Exception: If download fails
    """
    # Download tagged PDF
    if 'tagged-pdf' in result and 'downloadUri' in result['tagged-pdf']:
        tagged_pdf_uri = result['tagged-pdf']['downloadUri']
        if debug:
            print(f"Downloading tagged PDF from: {tagged_pdf_uri}")
        download_file(tagged_pdf_uri, output_path, silent, debug)
        if not silent:
            print(f"✓ Tagged PDF saved: {output_path}")
    else:
        raise Exception("No tagged PDF download URI found in result")
    
    # Download report if generated
    if 'report' in result and 'downloadUri' in result['report']:
        report_uri = result['report']['downloadUri']
        # Generate report filename based on output path
        output_dir = os.path.dirname(output_path)
        output_basename = os.path.splitext(os.path.basename(output_path))[0]
        report_path = os.path.join(output_dir, f"{output_basename}.xlsx")
        
        if debug:
            print(f"Downloading report from: {report_uri}")
        download_file(report_uri, report_path, silent, debug)
        if not silent:
            print(f"✓ Report saved: {report_path}") 