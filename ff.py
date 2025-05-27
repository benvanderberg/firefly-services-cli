#!/usr/bin/env python3

import os
import sys
import requests
import argparse
import time
from dotenv import load_dotenv
from urllib.parse import urlparse
from tabulate import tabulate
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import mimetypes
import json

def get_size_mapping(model_version):
    """
    Get the size mapping for the specified model version.
    
    Args:
        model_version (str): The model version ('image3', 'image4_standard', or 'image4_ultra')
    
    Returns:
        dict: Mapping of size names to dimensions
    """
    image3_sizes = {
        'square': '2048x2048',
        'square1024': '1024x1024',
        'landscape': '2304x1792',
        'portrait': '1792x2304',
        'widescreen': '2688x1536',
        '7:4': '1344x768',
        '9:7': '1152x896',
        '7:9': '896x1152',
        '16:9': '2688x1536',
        '1:1': '2048x2048',
        '4:3': '1792x2304',
        '3:4': '1792x2304'
    }
    
    image4_sizes = {
        'square': '2048x2048',
        'landscape': '2304x1792',
        'portrait': '1792x2304',
        'widescreen': '2688x1536',
        '9:16': '1440x2560',
        '1:1': '2048x2048',
        '4:3': '2304x1792',
        '3:4': '1792x2304',
        '16:9': '2688x1536'
    }
    
    if model_version == 'image3':
        return image3_sizes
    elif model_version in ['image4_standard', 'image4_ultra']:
        return image4_sizes
    else:
        return {}

def parse_size(size_str, model_version):
    """
    Parse the size string into width and height.
    Supports both dimension format (WIDTHxHEIGHT) and named sizes.
    
    Args:
        size_str (str): Size string in either format
        model_version (str): The model version to use for named sizes
    
    Returns:
        dict: Size dictionary with width and height
    
    Raises:
        ValueError: If the size format is invalid
    """
    # First check if it's a named size
    size_mapping = get_size_mapping(model_version)
    if size_str in size_mapping:
        size_str = size_mapping[size_str]
    
    # Parse the dimensions
    try:
        width, height = map(int, size_str.split('x'))
        return {'width': width, 'height': height}
    except ValueError:
        raise ValueError(f"Invalid size format. Must be either WIDTHxHEIGHT or one of the named sizes: {', '.join(size_mapping.keys())}")

def retrieve_access_token(silent=False):
    """
    Retrieve an access token from Adobe's authentication service.
    Uses client credentials from environment variables or .env file.
    
    Args:
        silent (bool): Whether to suppress output messages
    
    Returns:
        str: The access token for API authentication
    """
    load_dotenv()  # Load environment variables from .env file
    
    if 'FIREFLY_SERVICES_CLIENT_ID' not in os.environ or 'FIREFLY_SERVICES_CLIENT_SECRET' not in os.environ:
        print("Error: FIREFLY_SERVICES_CLIENT_ID and FIREFLY_SERVICES_CLIENT_SECRET must be set in environment variables or .env file")
        sys.exit(1)

    client_id = os.environ['FIREFLY_SERVICES_CLIENT_ID']
    client_secret = os.environ['FIREFLY_SERVICES_CLIENT_SECRET']

    token_url = 'https://ims-na1.adobelogin.com/ims/token/v3'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis'
    }

    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    token_data = response.json()
    if not silent:
        print("Access Token Retrieved")
    return token_data['access_token']

def get_available_voices(access_token):
    """
    Get the list of available voices for text-to-speech.
    
    Args:
        access_token (str): The authentication token
    
    Returns:
        list: List of available voices
    """
    headers = {
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get('https://audio-video-api.adobe.io/v1/voices', headers=headers)
    response.raise_for_status()
    voices_data = response.json()
    
    # Check if we have a valid response structure
    if not isinstance(voices_data, dict) or 'voices' not in voices_data:
        print("\nError: Unexpected API response format")
        return []
        
    return voices_data['voices']

def generate_speech(access_token, text, voice_id, locale_code="en-US", debug=False):
    """
    Generate speech from text using the specified voice.
    
    Args:
        access_token (str): The authentication token
        text (str): The text to convert to speech
        voice_id (str): The ID of the voice to use
        locale_code (str): The locale code for the text (default: en-US)
        debug (bool): Whether to print debug information
    
    Returns:
        dict: The job information including jobId and statusUrl
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    data = {
        'script': {
            'text': text,
            'mediaType': 'text/plain',
            'localeCode': locale_code
        },
        'voiceId': voice_id,
        'output': {
            'mediaType': 'audio/wav'
        }
    }

    if debug:
        print("\nDebug Information:")
        print("URL:", 'https://audio-video-api.adobe.io/v1/generate-speech')
        print("Headers:", headers)
        print("Request Body:", data)

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/generate-speech',
        headers=headers,
        json=data
    )
    
    if debug:
        print("\nResponse Status:", response.status_code)
        print("Response Headers:", dict(response.headers))
        print("Response Body:", response.text)
    
    response.raise_for_status()
    return response.json()

def dub_media(access_token, source_url, target_locale, output_format="mp4"):
    """
    Dub audio or video content to a different language.
    
    Args:
        access_token (str): The authentication token
        source_url (str): URL of the source media file
        target_locale (str): Target language locale code (e.g., 'fr-FR')
        output_format (str): Output format (mp4 or mp3)
    
    Returns:
        dict: The job information including jobId and statusUrl
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    # Determine if source is video or audio based on URL extension
    source_type = 'video' if source_url.lower().endswith(('.mp4', '.mov', '.avi')) else 'audio'
    
    data = {
        'source': {
            'url': source_url,
            'mediaType': source_type
        },
        'targetLocaleCode': target_locale,
        'output': {
            'format': output_format
        }
    }

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/dub',
        headers=headers,
        json=data
    )
    response.raise_for_status()
    return response.json()

def check_job_status(status_url, access_token, silent=False, debug=False):
    """
    Poll the status URL until the job is complete.
    
    Args:
        status_url (str): The URL to check job status
        access_token (str): The authentication token
        silent (bool): Whether to suppress output messages
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
        
        if status_data.get('status') == 'succeeded':
            return status_data
        elif status_data.get('status') == 'failed':
            raise Exception(f"Job failed: {status_data.get('error', 'Unknown error')}")
        
        if debug:
            print("Waiting for job completion...")
        time.sleep(2)  # Wait 2 seconds before checking again

def download_file(url, output_file, silent=False, debug=False):
    """
    Download a file from a URL and save it to a file.
    
    Args:
        url (str): The URL of the file to download
        output_file (str): The path where the file should be saved
        silent (bool): Whether to suppress output messages
        debug (bool): Whether to show debug information
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        if debug:
            print(f"File successfully downloaded to {output_file}")
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        sys.exit(1)

def get_output_filename(base_filename, index, total):
    """
    Generate an appropriate filename for multiple outputs.
    If there's only one output, return the original filename.
    Otherwise, add a number suffix (e.g., _1, _2) to the filename.
    
    Args:
        base_filename (str): The original filename
        index (int): The index of the current output (0-based)
        total (int): The total number of outputs
    
    Returns:
        str: The generated filename
    """
    if total == 1:
        return base_filename
    
    # Split the filename into name and extension
    name, ext = os.path.splitext(base_filename)
    return f"{name}_{index + 1}{ext}"

def read_text_file(file_path):
    """
    Read text from a file and remove all newline characters.
    
    Args:
        file_path (str): Path to the text file
    
    Returns:
        str: Contents of the file with newlines replaced by spaces
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If there's an error reading the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read the file and replace all types of newlines with spaces
            content = f.read()
            # Replace all types of newlines (\n, \r, \r\n) with spaces
            content = content.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
            # Remove any multiple spaces that might have been created
            content = ' '.join(content.split())
            return content.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Text file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading text file: {str(e)}")

def generate_image(access_token, prompt, num_generations=1, model_version='image3', content_class='photo',
                  negative_prompt=None, prompt_biasing_locale=None, size=None, seeds=None, debug=False,
                  visual_intensity=None):
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
        "n": num_generations,
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
    
    if debug:
        print("\nRequest Details:")
        print(f"URL: {url}")
        print("Headers:", json.dumps(headers, indent=2))
        print("Request Body:", json.dumps(data, indent=2))

    response = requests.post(
        url,
        headers=headers,
        json=data
    )
    
    if debug:
        print("\nResponse Status:", response.status_code)
        print("Response Headers:", dict(response.headers))
        print("Response Body:", response.text)
    
    response.raise_for_status()
    return response.json()

def upload_to_azure_storage(file_path):
    """
    Upload a file to Azure Blob Storage and return a presigned URL.
    
    Args:
        file_path (str): Path to the file to upload
        
    Returns:
        str: Presigned URL for the uploaded file
    """
    # Get Azure Storage credentials from environment variables
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.environ.get('AZURE_STORAGE_CONTAINER')
    
    if not connection_string or not container_name:
        raise ValueError("Azure Storage credentials not found in environment variables")
    
    # Create the BlobServiceClient
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service_client.get_container_client(container_name)
    
    # Get file name and content type
    file_name = os.path.basename(file_path)
    content_type, _ = mimetypes.guess_type(file_path)
    
    # Upload the file
    with open(file_path, "rb") as data:
        blob_client = container_client.upload_blob(
            name=file_name,
            data=data,
            overwrite=True,
            content_type=content_type
        )
    
    # Generate SAS token for the blob
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=file_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    
    # Generate the presigned URL
    presigned_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{file_name}?{sas_token}"
    
    return presigned_url

def transcribe_media(access_token, file_path, media_type, target_locale="en-US", generate_captions=False, debug=False):
    """
    Transcribe audio or video content.
    
    Args:
        access_token (str): The authentication token
        file_path (str): Path to the media file to transcribe
        media_type (str): Type of media ('audio' or 'video')
        target_locale (str): Target language locale code (e.g., 'en-US')
        generate_captions (bool): Whether to generate SRT captions
        debug (bool): Whether to print debug information
    
    Returns:
        dict: The job information including jobId and statusUrl
    """
    # Upload file to Azure Storage and get presigned URL
    source_url = upload_to_azure_storage(file_path)
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    # Map media type to proper mediaType value
    media_type_map = {
        'audio': {
            'mp3': 'audio/mp3',
            'wav': 'audio/wav',
            'm4a': 'audio/x-m4a',
            'aac': 'audio/aac'
        },
        'video': {
            'mp4': 'video/mp4',
            'mov': 'video/mov',
            'avi': 'video/x-msvideo',
            'mkv': 'video/x-matroska'
        }
    }

    # Get file extension and determine media type
    file_ext = file_path.lower().split('.')[-1]
    if media_type == 'audio':
        if file_ext not in media_type_map['audio']:
            raise ValueError(f"Unsupported audio format: {file_ext}")
        media_type_value = media_type_map['audio'][file_ext]
        data = {
            'audio': {
                'source': {
                    'url': source_url
                },
                'mediaType': media_type_value
            },
            'targetLocaleCodes': [target_locale]
        }
    else:  # video
        if file_ext not in media_type_map['video']:
            raise ValueError(f"Unsupported video format: {file_ext}")
        media_type_value = media_type_map['video'][file_ext]
        data = {
            'video': {
                'source': {
                    'url': source_url
                },
                'mediaType': media_type_value
            },
            'targetLocaleCodes': [target_locale]
        }

    # Add captions if requested
    if generate_captions:
        data['captions'] = {
            'targetFormats': ['SRT']
        }

    if debug:
        print("\nDebug Information:")
        print("URL:", 'https://audio-video-api.adobe.io/v1/transcribe')
        print("Headers:", headers)
        print("Request Body:", data)

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/transcribe',
        headers=headers,
        json=data
    )
    
    if debug:
        print("\nResponse Status:", response.status_code)
        print("Response Headers:", dict(response.headers))
        print("Response Body:", response.text)
    
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
        'ultra': 'image4_ultra'
    }
    return model_mapping.get(model_name, model_name)

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

def main():
    """
    Main function that handles command line arguments and orchestrates the process.
    """
    parser = argparse.ArgumentParser(description='Adobe Firefly Services CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Image generation command
    image_parser = subparsers.add_parser('image', help='Generate images')
    image_parser.add_argument('-prompt', '--prompt', required=True, help='Text prompt for image generation')
    image_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated image')
    image_parser.add_argument('-n', '--number', type=int, default=1, choices=range(1, 5),
                            help='Number of images to generate (1-4, default: 1)')
    image_parser.add_argument('-m', '--model', choices=['image3', 'image3_custom', 'image4', 'image4_standard', 'image4_ultra', 'ultra'],
                            default='image3', help='Firefly model version to use (image4 = image4_standard, ultra = image4_ultra)')
    image_parser.add_argument('-c', '--content-class', choices=['photo', 'art'], default='photo',
                            help='Type of content to generate (default: photo)')
    image_parser.add_argument('-np', '--negative-prompt', help='Text describing what to avoid in the generation')
    image_parser.add_argument('-l', '--locale', help='Locale code for prompt biasing (e.g., en-US)')
    image_parser.add_argument('-s', '--size', help='Output size (e.g., 2048x2048 or square, landscape, portrait, etc.)')
    image_parser.add_argument('--seeds', type=int, nargs='+', help='Seed values for consistent generation (1-4 values)')
    image_parser.add_argument('-d', '--debug', action='store_true',
                            help='Show debug information including full HTTP request details')
    image_parser.add_argument('-vi', '--visual-intensity', type=int, choices=range(1, 11),
                            help='Visual intensity of the generated image (1-10)')
    image_parser.add_argument('-silent', '--silent', action='store_true',
                            help='Minimize output messages')

    # Text-to-speech command
    tts_parser = subparsers.add_parser('tts', help='Generate speech from text')
    tts_group = tts_parser.add_mutually_exclusive_group(required=True)
    tts_group.add_argument('-t', '--text', help='Text to convert to speech')
    tts_group.add_argument('-f', '--file', help='Path to text file containing the content to convert to speech')
    tts_parser.add_argument('-v', '--voice', required=True, help='Voice ID to use')
    tts_parser.add_argument('-o', '--output', required=True, help='Output file path (will be saved as WAV)')
    tts_parser.add_argument('-l', '--locale', default='en-US',
                          help='Locale code for the text (default: en-US)')
    tts_parser.add_argument('-d', '--debug', action='store_true',
                          help='Show debug information')

    # Dubbing command
    dub_parser = subparsers.add_parser('dub', help='Dub audio or video content')
    dub_parser.add_argument('-i', '--input', required=True, help='URL of the source media file')
    dub_parser.add_argument('-l', '--locale', required=True, help='Target language locale code (e.g., fr-FR)')
    dub_parser.add_argument('-o', '--output', required=True, help='Output file path')
    dub_parser.add_argument('-f', '--format', choices=['mp4', 'mp3'], default='mp4',
                          help='Output format (default: mp4)')

    # List voices command
    voices_parser = subparsers.add_parser('voices', help='List available voices')

    # Transcription command
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio or video content')
    transcribe_parser.add_argument('-i', '--input', required=True, help='Path to the media file to transcribe')
    transcribe_parser.add_argument('-t', '--type', choices=['audio', 'video'], required=True,
                                 help='Type of media (audio or video)')
    transcribe_parser.add_argument('-l', '--locale', default='en-US',
                                 help='Target language locale code (default: en-US)')
    transcribe_parser.add_argument('-c', '--captions', action='store_true',
                                 help='Generate SRT captions')
    transcribe_parser.add_argument('-d', '--debug', action='store_true',
                                 help='Show debug information')
    transcribe_parser.add_argument('-o', '--output', required=True, help='Path to save the transcription output')
    transcribe_parser.add_argument('-text', '--text-only', action='store_true',
                                 help='Extract and save only the transcript text')

    args = parser.parse_args()

    try:
        # Get authentication token
        access_token = retrieve_access_token(args.silent)

        if args.command == 'image':
            # Parse size if provided
            size = None
            if args.size:
                try:
                    size = parse_size(args.size, args.model)
                except ValueError as e:
                    print(str(e))
                    sys.exit(1)

            # Normalize model name
            model_version = normalize_model_name(args.model)

            if not args.silent:
                display_model = format_model_name_for_display(model_version)
                print(f'Firefly {display_model}: Generating image "{args.prompt}"...')

            # Submit the image generation job
            job_info = generate_image(
                access_token=access_token,
                prompt=args.prompt,
                num_generations=args.number,
                model_version=model_version,
                content_class=args.content_class,
                negative_prompt=args.negative_prompt,
                prompt_biasing_locale=args.locale,
                size=size,
                seeds=args.seeds,
                debug=args.debug,
                visual_intensity=args.visual_intensity
            )
            
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print(f"Requested {args.number} image(s)")
                print("Polling for job completion...")
            
            # Poll the status URL until the job is complete
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            
            # Extract and download the generated images
            if 'result' in result and 'outputs' in result['result']:
                outputs = result['result']['outputs']
                total_outputs = len(outputs)
                
                if args.debug:
                    print(f"\nFound {total_outputs} generated image(s)")
                
                # Download each output
                for i, output in enumerate(outputs):
                    image_url = output['image']['url']
                    output_filename = get_output_filename(args.output, i, total_outputs)
                    if args.debug:
                        print(f"Downloading image {i + 1} of {total_outputs} to {output_filename}...")
                    download_file(image_url, output_filename, args.silent, args.debug)
                
                print(f"Saved to {args.output}")

        elif args.command == 'tts':
            # Get text from either direct input or file
            text = args.text if args.text is not None else read_text_file(args.file)
            
            # Generate speech
            job_info = generate_speech(
                access_token=access_token,
                text=text,
                voice_id=args.voice,
                locale_code=args.locale,
                debug=args.debug
            )
            
            print(f"Job ID: {job_info['jobId']}")
            print("Polling for job completion...")
            
            # Poll the status URL until the job is complete
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            
            # Download the generated audio
            if result.get('status') == 'succeeded' and 'output' in result and 'url' in result['output']:
                audio_url = result['output']['url']
                print(f"Downloading audio to {args.output}...")
                download_file(audio_url, args.output, args.silent, args.debug)
            else:
                print("Error: No output URL found in the response")
                if args.debug:
                    print("Response:", result)
                sys.exit(1)

        elif args.command == 'dub':
            # Dub the media
            job_info = dub_media(
                access_token=access_token,
                source_url=args.input,
                target_locale=args.locale,
                output_format=args.format
            )
            
            print(f"Job ID: {job_info['jobId']}")
            print("Polling for job completion...")
            
            # Poll the status URL until the job is complete
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            
            # Download the dubbed media
            if 'result' in result and 'output' in result['result']:
                media_url = result['result']['output']['url']
                print(f"Downloading dubbed media to {args.output}...")
                download_file(media_url, args.output, args.silent, args.debug)

        elif args.command == 'voices':
            # List available voices
            voices = get_available_voices(access_token)
            if voices:
                # Sort voices by status (Active first) and then by name
                active_voices = [v for v in voices if v.get('status') == 'Active']
                inactive_voices = [v for v in voices if v.get('status') == 'Inactive']
                
                # Prepare table data
                def prepare_voice_data(voice_list):
                    return [[
                        voice.get('voiceId', 'N/A'),
                        voice.get('displayName', 'N/A'),
                        voice.get('gender', 'N/A'),
                        voice.get('style', 'N/A'),
                        voice.get('voiceType', 'N/A'),
                        voice.get('status', 'N/A')
                    ] for voice in sorted(voice_list, key=lambda x: x.get('displayName', ''))]
                
                # Print active voices first
                if active_voices:
                    print("\nActive Voices:")
                    active_table = prepare_voice_data(active_voices)
                    print(tabulate(
                        active_table,
                        headers=['ID', 'Name', 'Gender', 'Style', 'Type', 'Status'],
                        tablefmt='grid'
                    ))
                
                # Print inactive voices
                if inactive_voices:
                    print("\nInactive Voices:")
                    inactive_table = prepare_voice_data(inactive_voices)
                    print(tabulate(
                        inactive_table,
                        headers=['ID', 'Name', 'Gender', 'Style', 'Type', 'Status'],
                        tablefmt='grid'
                    ))
            else:
                print("No voices found or error occurred")

        elif args.command == 'transcribe':
            # Transcribe media
            job_info = transcribe_media(
                access_token=access_token,
                file_path=args.input,
                media_type=args.type,
                target_locale=args.locale,
                generate_captions=args.captions,
                debug=args.debug
            )
            
            print(f"Job ID: {job_info['jobId']}")
            print("Polling for job completion...")
            
            # Poll the status URL until the job is complete
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            
            # Process the transcription results
            if result.get('status') == 'succeeded':
                print("\nTranscription completed successfully!")
                # Get the transcription URL from the response
                if 'outputs' in result and len(result['outputs']) > 0:
                    transcription_url = result['outputs'][0]['destination']['url']
                    print(f"Downloading transcription to {args.output}...")
                    response = requests.get(transcription_url)
                    response.raise_for_status()
                    
                    if args.text_only:
                        # Parse the JSON response and extract just the transcript text
                        try:
                            transcript_data = response.json()
                            # Create a paragraph for each segment
                            paragraphs = []
                            for segment in transcript_data:
                                # Clean up the text of each segment
                                text = ' '.join(segment[2].split())
                                paragraphs.append(text)
                            # Join paragraphs with double newlines
                            transcript_text = '\n\n'.join(paragraphs)
                            # Write the formatted text to the output file
                            with open(args.output, 'w', encoding='utf-8') as f:
                                f.write(transcript_text)
                        except Exception as e:
                            print(f"Error parsing transcript: {str(e)}")
                            if args.debug:
                                print("Raw response:", response.text)
                            sys.exit(1)
                    else:
                        # Save the full JSON response
                        with open(args.output, 'w', encoding='utf-8') as f:
                            f.write(response.text)
                    
                    print(f"Transcription saved to {args.output}")
                else:
                    print("Error: No transcription output found in response")
                if args.debug:
                    print("Full response:", result)
            else:
                print("Error: Transcription failed")
                if args.debug:
                    print("Response:", result)
                sys.exit(1)

        else:
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
