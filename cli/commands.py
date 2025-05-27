import os
import sys
import json
import time
import requests
import concurrent.futures
from datetime import datetime
from tabulate import tabulate
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

from utils.auth import retrieve_access_token
from utils.storage import upload_to_azure_storage
from utils.rate_limiter import RateLimiter
from utils.filename import parse_size, parse_prompt_variations, get_variation_filename, get_unique_filename, replace_filename_tokens
from services.image import generate_image, parse_model_variations, parse_style_ref_variations, generate_similar_image, expand_image
from services.speech import generate_speech, get_available_voices
from services.dubbing import dub_media
from services.transcription import transcribe_media
from config.settings import (
    IMAGE_GENERATION_API_URL,
    SPEECH_API_URL,
    DUBBING_API_URL,
    TRANSCRIPTION_API_URL,
    VOICES_API_URL,
    MODEL_VERSIONS,
    CONTENT_CLASSES,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_PERIOD
)

# Load environment variables
load_dotenv()

def handle_command(args):
    """
    Handle the command based on the parsed arguments.
    
    Args:
        args: Parsed command line arguments
    """
    # Get access token
    access_token = retrieve_access_token()
    
    # Handle different commands
    if args.command in ['image', 'img']:
        handle_image_command(args, access_token)
    elif args.command in ['similar-image', 'sim']:
        handle_similar_image_command(args, access_token)
    elif args.command in ['tts', 'speech']:
        handle_tts_command(args, access_token)
    elif args.command == 'dub':
        handle_dub_command(args, access_token)
    elif args.command in ['voices', 'v']:
        handle_voices_command(args, access_token)
    elif args.command in ['transcribe', 'trans']:
        handle_transcribe_command(args, access_token)
    elif args.command == 'expand':
        handle_expand_command(args, access_token)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

def handle_image_command(args, access_token):
    """Handle the image generation command with rate limiting and parallelism."""
    # Parse model variations first
    model_versions = parse_model_variations(args.model, args.debug)
    total_models = len(model_versions)

    # Parse size if provided, using the first model version for size mapping
    size = None
    if args.size:
        try:
            size = parse_size(args.size, model_versions[0], args.debug)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    # Parse prompt variations
    prompts, variation_blocks = parse_prompt_variations(args.prompt)
    total_variations = len(prompts)

    # Parse style reference variations
    style_refs = parse_style_ref_variations(args.style_reference) if args.style_reference else [None]
    total_style_refs = len(style_refs)

    # Parse composition reference variations
    composition_refs = parse_style_ref_variations(args.composition_reference) if args.composition_reference else [None]
    total_composition_refs = len(composition_refs)

    # Calculate total number of generations
    total_generations = total_variations * total_models * total_style_refs * total_composition_refs * args.numVariations

    # Get throttle limit from environment
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    rate_limiter = RateLimiter(throttle_limit, 60)

    if not args.silent:
        print(f'Generating {total_generations} total variations:')
        print(f'  • {total_variations} prompt variations')
        print(f'  • {total_models} model versions')
        print(f'  • {total_style_refs} style references')
        print(f'  • {total_composition_refs} composition references')
        print(f'  • {args.numVariations} variations per combination')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')

    def image_task(prompt, model_version, style_ref, composition_ref, j):
        rate_limiter.acquire()
        tokens = {
            'prompt': prompt,
            'model': model_version,
            'size': size,
            'seeds': args.seeds,
            'style_ref': style_ref,
            'composition_ref': composition_ref,
            'iteration': j + 1
        }
        base_filename = get_variation_filename(args.output, prompt, args.prompt, tokens, args.debug)
        output_filename = get_unique_filename(base_filename, args.overwrite, args.debug)
        try:
            job_info = generate_image(
                access_token=access_token,
                prompt=prompt,
                num_generations=1,
                model_version=model_version,
                content_class=args.content_class,
                negative_prompt=args.negative_prompt,
                prompt_biasing_locale=args.locale,
                size=size,
                seeds=args.seeds,
                debug=args.debug,
                visual_intensity=args.visual_intensity,
                style_ref_path=style_ref,
                style_ref_strength=args.style_reference_strength,
                composition_ref_path=composition_ref,
                composition_ref_strength=args.composition_reference_strength
            )
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print("Polling for job completion...")
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            if 'result' in result and 'outputs' in result['result']:
                outputs = result['result']['outputs']
                if outputs:
                    image_url = outputs[0]['image']['url']
                    if args.debug:
                        print(f"Downloading image to {output_filename}...")
                    download_file(image_url, output_filename, args.silent, args.debug)
                    return True
            return False
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return False

    # Create a list to store all generation tasks
    generation_tasks = []
    current_generation = 0

    # Prepare the table header
    if not args.silent:
        print("Generation Tasks:")
        print(f"{'#':<4} {'Model':<15} {'Prompt':<40} {'SRef':<20} {'SRef-Strength':<15} {'CRef':<20} {'CRef-Strength':<15}")
        print("-" * 120)

    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
        for model_version in model_versions:
            for style_ref in style_refs:
                for composition_ref in composition_refs:
                    for i, prompt in enumerate(prompts, 1):
                        for j in range(args.numVariations):
                            current_generation += 1
                            if not args.silent:
                                print(f"{current_generation:<4} {model_version:<15} {prompt[:40]:<40} {os.path.basename(style_ref) if style_ref else 'None':<20} {args.style_reference_strength:<15} {os.path.basename(composition_ref) if composition_ref else 'None':<20} {args.composition_reference_strength:<15}")
                            tasks.append(executor.submit(image_task, prompt, model_version, style_ref, composition_ref, j))
        for future in concurrent.futures.as_completed(tasks):
            future.result()
    if not args.silent:
        print("\nAll image generation tasks completed.")

def handle_similar_image_command(args, access_token):
    """Handle the similar image generation command."""
    # Parse model variations
    model_versions = parse_model_variations(args.model, args.debug)
    total_models = len(model_versions)

    # Parse size if provided
    size = None
    if args.size:
        try:
            size = parse_size(args.size, model_versions[0], args.debug)
        except ValueError as e:
            print(str(e))
            sys.exit(1)

    # Validate numVariations
    if not 1 <= args.numVariations <= 4:
        print("Error: Number of variations (-n) must be between 1 and 4")
        sys.exit(1)

    # Calculate total number of generations
    total_generations = total_models * args.numVariations

    # Get throttle limit from environment
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    rate_limiter = RateLimiter(throttle_limit, 60)

    if not args.silent:
        print(f'Generating {total_generations} total variations:')
        print(f'  • {total_models} model versions')
        print(f'  • {args.numVariations} variations per model')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')

    def similar_image_task(model_version, j):
        rate_limiter.acquire()
        tokens = {
            'model': model_version,
            'size': size,
            'seeds': args.seeds,
            'iteration': j + 1,
            'n': args.numVariations,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H-%M-%S'),
            'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        }
        if size:
            tokens.update({
                'width': size['width'],
                'height': size['height'],
                'dimensions': f"{size['width']}x{size['height']}"
            })
        base_filename = replace_filename_tokens(args.output, tokens)
        output_filename = get_unique_filename(base_filename, args.overwrite, args.debug)
        try:
            job_info = generate_similar_image(
                access_token=access_token,
                image_path=args.input,
                num_variations=args.numVariations,  # Pass the validated numVariations to the API
                model_version=model_version,
                size=size,
                seeds=args.seeds,
                debug=args.debug
            )
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print("Polling for job completion...")
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
            if 'result' in result and 'outputs' in result['result']:
                outputs = result['result']['outputs']
                if outputs:
                    image_url = outputs[0]['image']['url']
                    if args.debug:
                        print(f"Downloading image to {output_filename}...")
                    download_file(image_url, output_filename, args.silent, args.debug)
                    return True
            return False
        except Exception as e:
            print(f"Error generating similar image: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return False

    # Create a list to store all generation tasks
    tasks = []
    current_generation = 0

    # Prepare the table header
    if not args.silent:
        print("Generation Tasks:")
        print(f"{'#':<4} {'Model':<15}")
        print("-" * 20)

    with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
        for model_version in model_versions:
            for j in range(args.numVariations):
                current_generation += 1
                if not args.silent:
                    print(f"{current_generation:<4} {model_version:<15}")
                tasks.append(executor.submit(similar_image_task, model_version, j))
        for future in concurrent.futures.as_completed(tasks):
            future.result()
    if not args.silent:
        print("\nAll similar image generation tasks completed.")

def handle_tts_command(args, access_token):
    """Handle the text-to-speech command."""
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

def handle_dub_command(args, access_token):
    """Handle the dubbing command."""
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

def handle_voices_command(args, access_token):
    """Handle the list voices command."""
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

def handle_transcribe_command(args, access_token):
    """Handle the transcription command."""
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

def handle_expand_command(args, access_token):
    # Validate numVariations
    if not 1 <= args.numVariations <= 4:
        print("Error: Number of variations (-n) must be between 1 and 4")
        sys.exit(1)
    # Validate mask-invert
    if args.mask_invert and not args.mask:
        print("Error: --mask-invert can only be used if --mask is set")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Call expand_image
    job_info = expand_image(
        access_token=access_token,
        image_path=args.input,
        prompt=args.prompt,
        mask_path=args.mask,
        mask_invert=args.mask_invert if args.mask else None,
        num_variations=args.numVariations,
        align_h=args.align_h,
        align_v=args.align_v,
        left=args.left,
        right=args.right,
        top=args.top,
        bottom=args.bottom,
        height=args.height,
        width=args.width,
        seeds=args.seeds,
        debug=args.debug
    )
    print(f"Job ID: {job_info['jobId']}")
    print("Polling for job completion...")
    result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
    if 'result' in result and 'outputs' in result['result']:
        outputs = result['result']['outputs']
        for idx, output in enumerate(outputs, 1):
            image_url = output['image']['url']
            output_filename = args.output.replace("{n}", str(idx))
            print(f"Downloading expanded image to {output_filename}...")
            download_file(image_url, output_filename, args.silent, args.debug)
    else:
        print("No outputs found in response.")

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