import os
import sys
import json
import time
import asyncio
import aiohttp
import requests
import concurrent.futures
from datetime import datetime, timedelta, UTC
from tabulate import tabulate
from typing import List, Dict, Any, Optional, Union, Tuple
from dotenv import load_dotenv
import re
import glob
import csv
import io

from utils.auth import retrieve_access_token
from utils.storage import upload_to_azure_storage
from utils.rate_limiter import RateLimiter
from utils.filename import parse_size, parse_prompt_variations, get_variation_filename, get_unique_filename, replace_filename_tokens
from services.image import generate_image, parse_model_variations, parse_style_ref_variations, generate_similar_image, expand_image, fill_image, create_mask
from services.speech import generate_speech, get_available_voices, get_available_avatars, parse_voice_variations, get_voice_id_by_name, generate_avatar, get_avatar_id_by_name
from services.dubbing import dub_media
from services.transcription import transcribe_media
from services.video import generate_video, check_video_job_status, download_video
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

def log_image_generation(prompt, model, output_filename, elapsed_time, success, error_msg=None, **kwargs):
    """
    Log image generation details to logs/image.txt
    
    Args:
        prompt (str): The prompt used
        model (str): The model used
        output_filename (str): The output filename
        elapsed_time (float): Time taken in seconds
        success (bool): Whether generation was successful
        error_msg (str): Error message if failed
        **kwargs: Additional parameters to log
    """
    try:
        print(f"DEBUG: Attempting to log image generation - {output_filename} ({elapsed_time:.1f}s)")
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists('logs/image.txt')
        
        # Prepare log entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = [
            timestamp,  # Date/Time
            f"{elapsed_time:.1f}",  # Seconds
            prompt,  # Prompt
            model,  # Model
            output_filename,  # Output filename
            "SUCCESS" if success else "FAILED",  # Status
            error_msg or "",  # Error message
            kwargs.get('content_class', ''),  # Content class
            kwargs.get('negative_prompt', ''),  # Negative prompt
            kwargs.get('locale', ''),  # Locale
            str(kwargs.get('size', '')),  # Size
            str(kwargs.get('seeds', '')),  # Seeds
            kwargs.get('visual_intensity', ''),  # Visual intensity
            kwargs.get('style_ref', ''),  # Style reference
            kwargs.get('style_ref_strength', ''),  # Style reference strength
            kwargs.get('composition_ref', ''),  # Composition reference
            kwargs.get('composition_ref_strength', ''),  # Composition reference strength
            kwargs.get('num_variations', ''),  # Number of variations
            kwargs.get('debug', ''),  # Debug mode
            kwargs.get('silent', ''),  # Silent mode
            kwargs.get('overwrite', ''),  # Overwrite mode
        ]
        
        # Write to log file
        with open('logs/image.txt', 'a', encoding='utf-8') as f:
            # Write header if file is new
            if not file_exists:
                header = [
                    'Date/Time',
                    'Seconds',
                    'Prompt',
                    'Model',
                    'Output_Filename',
                    'Status',
                    'Error_Message',
                    'Content_Class',
                    'Negative_Prompt',
                    'Locale',
                    'Size',
                    'Seeds',
                    'Visual_Intensity',
                    'Style_Reference',
                    'Style_Reference_Strength',
                    'Composition_Reference',
                    'Composition_Reference_Strength',
                    'Num_Variations',
                    'Debug',
                    'Silent',
                    'Overwrite'
                ]
                f.write('\t'.join(header) + '\n')
            
            # Write data row
            f.write('\t'.join(str(item) for item in log_entry) + '\n')
            print(f"DEBUG: Successfully logged to logs/image.txt")
            
    except Exception as e:
        # Don't let logging errors break the main functionality
        print(f"Warning: Could not write to log file: {e}")
        import traceback
        traceback.print_exc()

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
    elif args.command == 'avatar':
        handle_avatar_command(args, access_token)
    elif args.command == 'dub':
        handle_dub_command(args, access_token)
    elif args.command in ['voices', 'v']:
        handle_voices_command(args, access_token)
    elif args.command in ['avatar-list', 'al']:
        handle_avatar_list_command(args, access_token)
    elif args.command in ['transcribe', 'trans']:
        handle_transcribe_command(args, access_token)
    elif args.command == 'expand':
        handle_expand_command(args, access_token)
    elif args.command == 'fill':
        handle_fill_command(args, access_token)
    elif args.command == 'mask':
        handle_mask_command(args, access_token)
    elif args.command == 'replace-bg':
        handle_replace_bg_command(args, access_token)
    elif args.command in ['models', 'cm-list', 'ml']:
        handle_list_custom_models_command(args, access_token)
    elif args.command == 'video':
        handle_video_command(args, access_token)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

def handle_image_command(args, access_token):
    """Handle the image generation command with rate limiting and parallelism, supporting custom models by displayName or assetId, and CSV-driven batch input."""
    import requests
    import os
    import sys
    import time
    import csv as csvmod
    # Standard models
    STANDARD_MODELS = {'image3', 'image4', 'image4_standard', 'image4_ultra', 'ultra'}
    # Helper for single job
    def run_image_job(prompt, model, output, style_ref, composition_ref, j, size, custom_model_asset_ids, rate_limiter=None):
        start_time = time.time()
        tokens = {
            'prompt': prompt,
            'model': model,
            'size': size,
            'style_ref': style_ref,
            'composition_ref': composition_ref,
            'iteration': j + 1
        }
        base_filename = get_variation_filename(output, prompt, prompt, tokens, args.debug)
        output_filename = get_unique_filename(base_filename, args.overwrite, args.debug)
        try:
            is_custom = model in custom_model_asset_ids
            job_info = generate_image(
                access_token=access_token,
                prompt=prompt,
                num_generations=1,
                model_version=model,
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
                composition_ref_strength=args.composition_reference_strength,
                custom_model=is_custom
            )
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print("Polling for job completion...")
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
            if 'result' in result and 'outputs' in result['result']:
                outputs = result['result']['outputs']
                if outputs:
                    image_url = outputs[0]['image']['url']
                    if args.debug:
                        print(f"Downloading image to {output_filename}...")
                    download_file(image_url, output_filename, args.silent, args.debug)
                    elapsed_time = time.time() - start_time
                    print(f"✓ Generated: {os.path.basename(output_filename)} ({elapsed_time:.1f}s)")
                    # Log successful generation
                    log_image_generation(
                        prompt=prompt,
                        model=model,
                        output_filename=os.path.basename(output_filename),
                        elapsed_time=elapsed_time,
                        success=True,
                        content_class=args.content_class,
                        negative_prompt=args.negative_prompt,
                        locale=args.locale,
                        size=size,
                        seeds=args.seeds,
                        visual_intensity=args.visual_intensity,
                        style_ref=style_ref,
                        style_ref_strength=args.style_reference_strength,
                        composition_ref=composition_ref,
                        composition_ref_strength=args.composition_reference_strength,
                        num_variations=1,
                        debug=args.debug,
                        silent=args.silent,
                        overwrite=args.overwrite
                    )
                    return True
            elapsed_time = time.time() - start_time
            print(f"✗ Failed: {os.path.basename(output_filename)} ({elapsed_time:.1f}s)")
            # Log failed generation
            log_image_generation(
                prompt=prompt,
                model=model,
                output_filename=os.path.basename(output_filename),
                elapsed_time=elapsed_time,
                success=False,
                error_msg="No outputs in response",
                content_class=args.content_class,
                negative_prompt=args.negative_prompt,
                locale=args.locale,
                size=size,
                seeds=args.seeds,
                visual_intensity=args.visual_intensity,
                style_ref=style_ref,
                style_ref_strength=args.style_reference_strength,
                composition_ref=composition_ref,
                composition_ref_strength=args.composition_reference_strength,
                num_variations=1,
                debug=args.debug,
                silent=args.silent,
                overwrite=args.overwrite
            )
            return False
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e)
            print(f"Error generating image: {error_msg} ({elapsed_time:.1f}s)")
            # Log failed generation with error
            log_image_generation(
                prompt=prompt,
                model=model,
                output_filename=os.path.basename(output_filename),
                elapsed_time=elapsed_time,
                success=False,
                error_msg=error_msg,
                content_class=args.content_class,
                negative_prompt=args.negative_prompt,
                locale=args.locale,
                size=size,
                seeds=args.seeds,
                visual_intensity=args.visual_intensity,
                style_ref=style_ref,
                style_ref_strength=args.style_reference_strength,
                composition_ref=composition_ref,
                composition_ref_strength=args.composition_reference_strength,
                num_variations=1,
                debug=args.debug,
                silent=args.silent,
                overwrite=args.overwrite
            )
            if args.debug:
                import traceback
                traceback.print_exc()
            # Check if it's a 529 error (overloaded service)
            if "529" in str(e) or "Too Many Requests" in str(e):
                if args.debug:
                    print("Detected 529 error - this task will be retried after all others complete")
            return False
    # CSV-driven batch mode
    if getattr(args, 'csv_input', None):
        csv_path = args.csv_input
        subject_val = getattr(args, 'subject', None)
        cli_model = getattr(args, 'model', None)
        throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
        throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
        throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
        rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)
        with open(csv_path, newline='', encoding='utf-8-sig') as csvfile:
            reader = csvmod.DictReader(csvfile)
            rows = list(reader)
            # Normalize BOM in header for first row if present
            if rows and any(k.startswith('\ufeff') for k in rows[0].keys()):
                for row in rows:
                    for k in list(row.keys()):
                        if k.startswith('\ufeff'):
                            row[k.lstrip('\ufeff')] = row.pop(k)
        if not rows:
            print(f"No rows found in CSV: {csv_path}")
            sys.exit(1)
        # Pre-fetch custom models if needed
        custom_model_asset_ids = {}
        all_models = set(row['Model'] for row in rows if row.get('Model'))
        resolved_model_versions = []
        
        # Resolve CLI model first if provided
        if cli_model:
            cli_model_variations = parse_model_variations(cli_model, args.debug)
            for model in cli_model_variations:
                model_stripped = model.strip()
                if model_stripped in STANDARD_MODELS:
                    resolved_model_versions.append(model_stripped)
                else:
                    # Query custom models API for CLI model
                    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
                    if not api_key:
                        print("Error: FIREFLY_SERVICES_CLIENT_ID is not set in environment.")
                        sys.exit(1)
                    headers = {
                        'x-api-key': api_key,
                        'x-request-id': f'ffcli-{int(time.time())}',
                        'Authorization': f'Bearer {access_token}'
                    }
                    url = 'https://firefly-api.adobe.io/v3/custom-models'
                    try:
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        data = response.json()
                        models = data.get('custom_models', [])
                        match = next((m for m in models if model_stripped.lower() == m.get('displayName', '').lower()), None)
                        if not match:
                            match = next((m for m in models if model_stripped == m.get('assetId', '')), None)
                        if not match:
                            match = next((m for m in models if model_stripped.lower() in m.get('displayName', '').lower()), None)
                        if match:
                            asset_id = match['assetId']
                            resolved_model_versions.append(asset_id)
                            custom_model_asset_ids[asset_id] = True
                            if args.debug:
                                print(f"Resolved CLI custom model '{model_stripped}' to assetId: {asset_id}")
                        else:
                            print(f"Error: Could not find a custom model with displayName or assetId matching '{model_stripped}'.")
                            sys.exit(1)
                    except Exception as e:
                        print(f"Error looking up custom models: {e}")
                        sys.exit(1)
        
        # Now resolve CSV models
        for model in all_models:
            if model and model not in STANDARD_MODELS and model != '{Model}':
                # Query custom models API
                api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
                if not api_key:
                    print("Error: FIREFLY_SERVICES_CLIENT_ID is not set in environment.")
                    sys.exit(1)
                headers = {
                    'x-api-key': api_key,
                    'x-request-id': f'ffcli-{int(time.time())}',
                    'Authorization': f'Bearer {access_token}'
                }
                url = 'https://firefly-api.adobe.io/v3/custom-models'
                try:
                    response = requests.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    models = data.get('custom_models', [])
                    match = next((m for m in models if model.lower() == m.get('displayName', '').lower()), None)
                    if not match:
                        match = next((m for m in models if model == m.get('assetId', '')), None)
                    if not match:
                        match = next((m for m in models if model.lower() in m.get('displayName', '').lower()), None)
                    if match:
                        asset_id = match['assetId']
                        custom_model_asset_ids[asset_id] = True
                        custom_model_asset_ids[model] = True  # allow both
                        if args.debug:
                            print(f"Resolved CSV custom model '{model}' to assetId: {asset_id}")
                    else:
                        print(f"Error: Could not find a custom model with displayName or assetId matching '{model}'.")
                        sys.exit(1)
                except Exception as e:
                    print(f"Error looking up custom models: {e}")
                    sys.exit(1)
        # Process each row
        all_tasks = []
        failed_tasks = []  # Track failed tasks for retry
        current_generation = 0
        throttle_pause = float(os.getenv('THROTTLE_PAUSE_SECONDS', 0.5))
        with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
            for row in rows:
                prompt = row.get('Prompt', '').strip()
                model = row.get('Model', '').strip() if 'Model' in row else None
                output = row.get('Output', '').strip()
                if not prompt or not output:
                    print(f"Skipping row with missing Prompt or Output: {row}")
                    continue
                # Inject subject
                if subject_val:
                    prompt = prompt.replace('{subject}', subject_val)
                    if model:
                        model = model.replace('{subject}', subject_val)
                    output = output.replace('{subject}', subject_val)
                # If Model is {Model}, missing, or empty, use CLI model
                if not model or model == '{Model}':
                    model = resolved_model_versions[0] if resolved_model_versions else cli_model
                else:
                    # Resolve CSV model to assetId if it's a custom model
                    if model not in STANDARD_MODELS:
                        # Find the assetId for this model
                        model_asset_id = None
                        for asset_id, is_custom in custom_model_asset_ids.items():
                            if asset_id == model or (isinstance(is_custom, str) and is_custom == model):
                                model_asset_id = asset_id
                                break
                        if model_asset_id:
                            model = model_asset_id
                        # If not found, assume it's already an assetId
                
                # Parse model variations (should be rare in CSV, but support)
                model_variations = [model]  # Use the resolved model directly
                for model_version in model_variations:
                    # Parse prompt variations (bracketed)
                    prompts, _ = parse_prompt_variations(prompt)
                    for prompt_var in prompts:
                        # Use output as template (inject subject, etc.)
                        out_path = output
                        # Throttle
                        rate_limiter.acquire()
                        task_info = {
                            'prompt': prompt_var,
                            'model': model_version,
                            'output': out_path,
                            'style_ref': None,
                            'composition_ref': None,
                            'j': 0,
                            'size': None,
                            'custom_model_asset_ids': custom_model_asset_ids
                        }
                        task = executor.submit(run_image_job, prompt_var, model_version, out_path, None, None, 0, None, custom_model_asset_ids, rate_limiter)
                        all_tasks.append((task, task_info))
                
                # Add delay between rows
                if throttle_pause > 0:
                    time.sleep(throttle_pause)
            
            # Process all tasks and track failures
            for future, task_info in all_tasks:
                try:
                    result = future.result()
                    if not result:
                        # Task failed, add to retry list
                        failed_tasks.append(task_info)
                        if args.debug:
                            print(f"Task failed: {task_info['prompt'][:50]}...")
                except Exception as e:
                    # Task raised an exception, add to retry list
                    failed_tasks.append(task_info)
                    if args.debug:
                        print(f"Task failed with exception: {e} - {task_info['prompt'][:50]}...")
        
        # Retry failed tasks if any
        if failed_tasks:
            print(f"\nRetrying {len(failed_tasks)} failed tasks...")
            retry_tasks = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
                for task_info in failed_tasks:
                    retry_task = executor.submit(
                        run_image_job, 
                        task_info['prompt'], 
                        task_info['model'], 
                        task_info['output'], 
                        task_info['style_ref'], 
                        task_info['composition_ref'], 
                        task_info['j'], 
                        task_info['size'], 
                        task_info['custom_model_asset_ids'], 
                        rate_limiter
                    )
                    retry_tasks.append(retry_task)
                
                for future in concurrent.futures.as_completed(retry_tasks):
                    try:
                        result = future.result()
                        if not result:
                            print("Task failed on retry")
                    except Exception as e:
                        print(f"Task failed on retry with exception: {e}")
        
        print("\nAll CSV-driven image generation tasks completed.")
        return
    # Parse model variations first
    model_variations = parse_model_variations(args.model, args.debug)
    resolved_model_versions = []
    custom_model_asset_ids = {}
    # Check each model variation
    for model in model_variations:
        model_stripped = model.strip()
        if model_stripped in STANDARD_MODELS:
            resolved_model_versions.append(model_stripped)
        else:
            # Query custom models API
            api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
            if not api_key:
                print("Error: FIREFLY_SERVICES_CLIENT_ID is not set in environment.")
                sys.exit(1)
            headers = {
                'x-api-key': api_key,
                'x-request-id': f'ffcli-{int(time.time())}',
                'Authorization': f'Bearer {access_token}'
            }
            url = 'https://firefly-api.adobe.io/v3/custom-models'
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if args.debug:
                    print("=== Full API Response ===")
                    print(json.dumps(data, indent=2))
                    print("=== End API Response ===\n")
                
                models = data.get('custom_models', [])
                if not models:
                    print('No custom models found.')
                    return
                # Try to match by displayName (case-insensitive, allow partial match)
                match = next((m for m in models if model_stripped.lower() == m.get('displayName', '').lower()), None)
                if not match:
                    # Try to match by assetId (exact)
                    match = next((m for m in models if model_stripped == m.get('assetId', '')), None)
                if not match:
                    # Try partial match on displayName
                    match = next((m for m in models if model_stripped.lower() in m.get('displayName', '').lower()), None)
                if match:
                    asset_id = match['assetId']
                    resolved_model_versions.append(asset_id)
                    custom_model_asset_ids[asset_id] = True
                    if args.debug:
                        print(f"Resolved custom model '{model_stripped}' to assetId: {asset_id}")
                else:
                    print(f"Error: Could not find a custom model with displayName or assetId matching '{model_stripped}'.")
                    sys.exit(1)
            except Exception as e:
                print(f"Error looking up custom models: {e}")
                sys.exit(1)
    total_models = len(resolved_model_versions)
    # Parse size if provided, using the first model version for size mapping
    size = None
    if args.size:
        try:
            size = parse_size(args.size, resolved_model_versions[0], args.debug)
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
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)
    if not args.silent:
        print(f'Generating {total_generations} total variations:')
        print(f'  • {total_variations} prompt variations')
        print(f'  • {total_models} model versions')
        print(f'  • {total_style_refs} style references')
        print(f'  • {total_composition_refs} composition references')
        print(f'  • {args.numVariations} variations per combination')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')
    def image_task(prompt, model_version, style_ref, composition_ref, j):
        start_time = time.time()
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
            # If this is a custom model, pass assetId as x-model-version header
            is_custom = model_version in custom_model_asset_ids
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
                composition_ref_strength=args.composition_reference_strength,
                custom_model=is_custom
            )
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print("Polling for job completion...")
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
            if 'result' in result and 'outputs' in result['result']:
                outputs = result['result']['outputs']
                if outputs:
                    image_url = outputs[0]['image']['url']
                    if args.debug:
                        print(f"Downloading image to {output_filename}...")
                    download_file(image_url, output_filename, args.silent, args.debug)
                    elapsed_time = time.time() - start_time
                    print(f"✓ Generated: {os.path.basename(output_filename)} ({elapsed_time:.1f}s)")
                    # Log successful generation
                    log_image_generation(
                        prompt=prompt,
                        model=model_version,
                        output_filename=os.path.basename(output_filename),
                        elapsed_time=elapsed_time,
                        success=True,
                        content_class=args.content_class,
                        negative_prompt=args.negative_prompt,
                        locale=args.locale,
                        size=size,
                        seeds=args.seeds,
                        visual_intensity=args.visual_intensity,
                        style_ref=style_ref,
                        style_ref_strength=args.style_reference_strength,
                        composition_ref=composition_ref,
                        composition_ref_strength=args.composition_reference_strength,
                        num_variations=1,
                        debug=args.debug,
                        silent=args.silent,
                        overwrite=args.overwrite
                    )
                    return True
            elapsed_time = time.time() - start_time
            print(f"✗ Failed: {os.path.basename(output_filename)} ({elapsed_time:.1f}s)")
            # Log failed generation
            log_image_generation(
                prompt=prompt,
                model=model_version,
                output_filename=os.path.basename(output_filename),
                elapsed_time=elapsed_time,
                success=False,
                error_msg="No outputs in response",
                content_class=args.content_class,
                negative_prompt=args.negative_prompt,
                locale=args.locale,
                size=size,
                seeds=args.seeds,
                visual_intensity=args.visual_intensity,
                style_ref=style_ref,
                style_ref_strength=args.style_reference_strength,
                composition_ref=composition_ref,
                composition_ref_strength=args.composition_reference_strength,
                num_variations=1,
                debug=args.debug,
                silent=args.silent,
                overwrite=args.overwrite
            )
            return False
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"Error generating image: {str(e)} ({elapsed_time:.1f}s)")
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
        for model_version in resolved_model_versions:
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
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)

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
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
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
    """Handle text-to-speech command"""
    # Get text from file or direct input
    text = get_text_from_file_or_input(args.text, args.file)
    if not text:
        print("Error: No text provided. Use -t for direct text or -f for a text file.")
        return

    # If input is a Markdown file, save the converted text to a .txt file
    if args.file and args.file.lower().endswith('.md'):
        txt_file = os.path.splitext(args.file)[0] + '.txt'
        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text)
            if args.debug:
                print(f"Converted Markdown to text and saved to: {txt_file}")
            # Update the file path to use the converted text file
            args.file = txt_file
        except Exception as e:
            print(f"Error saving converted text file: {str(e)}")
            return

    # Parse voice variations
    voice_ids = parse_voice_variations(args.voice_id) if args.voice_id else []
    voice_names = parse_voice_variations(args.voice) if args.voice else []
    voice_styles = parse_voice_variations(args.voice_style) if args.voice_style else []

    # Validate input
    if not voice_ids and not voice_names:
        print("Error: Either --voice-id or --voice must be specified")
        return

    if voice_names and not voice_styles:
        print("Error: --voice-style is required when using --voice")
        return

    # Create rate limiter for API calls using environment variable
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)

    # Prepare voice combinations
    voice_combinations = []
    
    # Add direct voice IDs
    for voice_id in voice_ids:
        voice_combinations.append({
            'id': voice_id,
            'name': voice_id,  # Use ID as name for direct voice IDs
            'style': None
        })
    
    # Add voice name combinations (without style)
    for voice_name in voice_names:
        voice_id = get_voice_id_by_name(access_token, voice_name, None)
        if voice_id:
            voice_combinations.append({
                'id': voice_id,
                'name': voice_name,
                'style': None
            })
        else:
            print(f"Warning: No voice ID found for name '{voice_name}'")

    if not voice_combinations:
        print("Error: No valid voice combinations found")
        return

    # Show progress table
    print(f"\nGenerating {len(voice_combinations)} total variations:")
    print(f"  • {len(voice_combinations)} voice combinations")
    print(f"\nUsing parallel processing with rate limit of {throttle_limit} calls per minute\n")

    # Print voice combinations
    print("\nVoice Combinations:")
    for i, combo in enumerate(voice_combinations, 1):
        print(f"{i}. ID: {combo['id']}, Name: {combo['name']}, Style: {combo['style']}")

    # Split text into paragraphs if requested
    paragraphs = []
    paragraph_info = []  # Store info about each paragraph
    if args.p_split and args.file:
        # Split by double newlines and filter out empty paragraphs
        raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if args.debug:
            print(f"\nFound {len(raw_paragraphs)} paragraphs in the text file")
            for i, p in enumerate(raw_paragraphs, 1):
                print(f"\nParagraph {i}:")
                print(f"  Length: {len(p)} characters")
                print(f"  Preview: {p[:100] + '...' if len(p) > 100 else p}")
        
        # Process each paragraph
        i = 0
        while i < len(raw_paragraphs):
            para = raw_paragraphs[i]
            para_num = i + 1
            
            # If paragraph is too short and not the last one, combine with next paragraph
            if len(para) < 15 and i < len(raw_paragraphs) - 1:
                if args.debug:
                    print(f"\nCombining short paragraph {para_num} with next paragraph")
                next_para = raw_paragraphs[i + 1]
                combined_para = f"{para} {next_para}"
                if args.debug:
                    print(f"  Combined length: {len(combined_para)} characters")
                    print(f"  Preview: {combined_para[:100] + '...' if len(combined_para) > 100 else combined_para}")
                para = combined_para
                i += 1  # Skip the next paragraph since we combined it
            
            # Split long paragraphs into sentences if they exceed 1000 characters
            if len(para) > 1000:
                # Split into sentences (basic split on period + space)
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if args.debug:
                    print(f"\nSplitting paragraph {para_num} into {len(sentences)} sentences")
                
                # Add each sentence as a separate paragraph if it's long enough
                for j, sentence in enumerate(sentences, 1):
                    if len(sentence) >= 15:  # Only include sentences longer than 15 chars
                        paragraphs.append(sentence)
                        paragraph_info.append({
                            'para_num': para_num,
                            'total_paras': len(raw_paragraphs),
                            'sentence_num': j,
                            'total_sentences': len(sentences),
                            'char_count': len(sentence),
                            'is_split': True
                        })
                        if args.debug:
                            print(f"  Split sentence {j}: {sentence[:50]}...")
            else:
                # Add the paragraph as is if it's not too long
                paragraphs.append(para)
                paragraph_info.append({
                    'para_num': para_num,
                    'total_paras': len(raw_paragraphs),
                    'sentence_num': 1,
                    'total_sentences': 1,
                    'char_count': len(para),
                    'is_split': False
                })
                if args.debug:
                    print(f"  Keeping as single paragraph: {para[:50]}...")
            
            i += 1
        
        if args.debug:
            print(f"\nFinal split into {len(paragraphs)} segments:")
            for i, (p, info) in enumerate(zip(paragraphs, paragraph_info), 1):
                print(f"\nSegment {i}:")
                print(f"  Paragraph {info['para_num']} of {info['total_paras']}")
                print(f"  Sentence {info['sentence_num']} of {info['total_sentences']}")
                print(f"  Characters: {info['char_count']}")
                print(f"  Split from longer paragraph: {info['is_split']}")
                print(f"  Preview: {p[:100] + '...' if len(p) > 100 else p}")
    else:
        # For non-split text, only process if it's long enough
        if len(text) >= 15:
            paragraphs = [text]
            paragraph_info = [{
                'para_num': 1,
                'total_paras': 1,
                'sentence_num': 1,
                'total_sentences': 1,
                'char_count': len(text),
                'is_split': False
            }]
        else:
            print("Error: Input text must be at least 15 characters long")
            return

    # Create tasks for parallel processing
    tasks = []
    for combo in voice_combinations:
        for i, (paragraph, info) in enumerate(zip(paragraphs, paragraph_info), 1):
            def tts_task(voice_combo, para, info):
                try:
                    # Generate speech
                    if args.debug:
                        print(f"\nGenerating speech with voice: {voice_combo['id']} ({voice_combo['name']} - {voice_combo['style']})")
                        print(f"Processing paragraph {info['para_num']} of {info['total_paras']}")
                        if info['is_split']:
                            print(f"Segment {info['sentence_num']} of {info['total_sentences']} sentences")
                    
                    # Create tokens for filename
                    tokens = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'time': datetime.now().strftime('%H-%M-%S'),
                        'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
                        'voice_id': voice_combo['id'],
                        'voice_name': voice_combo['name'],
                        'voice_style': voice_combo['style'] or '',
                        'locale_code': args.locale,
                        'para_num': f"{info['para_num']:02d}",
                        'total_paras': f"{info['total_paras']:02d}",
                        'sentence_num': f"{info['sentence_num']:02d}",
                        'total_sentences': f"{info['total_sentences']:02d}",
                        'char_count': f"{info['char_count']:02d}"
                    }
                    
                    # Add paragraph number to output path if splitting paragraphs
                    if args.p_split:
                        output_path = args.output.format(**tokens)
                    else:
                        output_path = args.output.format(**tokens)
                    
                    if args.debug:
                        print(f"Original output path: {args.output}")
                        print(f"Tokens: {tokens}")
                        print(f"Replaced output path: {output_path}")
                    
                    # Create output directory if it doesn't exist
                    output_dir = os.path.dirname(output_path)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                        if args.debug:
                            print(f"Created output directory: {output_dir}")
                    
                    # Generate speech
                    response = generate_speech(
                        access_token=access_token,
                        text=para,
                        voice_id=voice_combo['id'],
                        locale_code=args.locale,
                        debug=args.debug
                    )
                    
                    if response and 'jobId' in response and 'statusUrl' in response:
                        if args.debug:
                            print(f"Job ID: {response['jobId']}")
                            print("Polling for job completion...")
                        
                        # Poll the status URL until the job is complete
                        result = check_job_status(response['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
                        
                        if result.get('status') == 'succeeded' and 'output' in result:
                            # Download the audio file
                            audio_url = result['output']['url']
                            
                            # Download the file
                            try:
                                if args.debug:
                                    print(f"Making request to download file from {audio_url}")
                                response = requests.get(audio_url, stream=True)
                                response.raise_for_status()
                                
                                if args.debug:
                                    print(f"Response status: {response.status_code}")
                                    print(f"Response headers: {response.headers}")
                                
                                with open(output_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                if args.debug:
                                    print(f"Successfully downloaded to {output_path}")
                                    print(f"File size: {os.path.getsize(output_path)} bytes")
                                return True
                            except Exception as e:
                                print(f"Error downloading file for {voice_combo['name']}: {str(e)}")
                                if args.debug:
                                    import traceback
                                    traceback.print_exc()
                                return False
                        else:
                            if args.debug:
                                print("No output URL found in result")
                                print(f"Result: {result}")
                    return False
                except Exception as e:
                    print(f"Error generating speech for {voice_combo['name']}: {str(e)}")
                    if args.debug:
                        import traceback
                        traceback.print_exc()
                    return False

            tasks.append((tts_task, combo, paragraph, info))

    # Process tasks in parallel with rate limiting
    results = process_tasks_parallel(tasks, rate_limiter)

    # Print summary
    success_count = sum(1 for r in results if r)
    print(f"\nCompleted {success_count} of {len(tasks)} variations successfully")

def handle_avatar_command(args, access_token):
    """Handle avatar generation command"""
    # Get text from file or direct input
    text = get_text_from_file_or_input(args.text, args.file)
    if not text:
        print("Error: No text provided. Use -t for direct text or -f for a text file.")
        return

    # If input is a Markdown file, save the converted text to a .txt file
    if args.file and args.file.lower().endswith('.md'):
        txt_file = os.path.splitext(args.file)[0] + '.txt'
        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text)
            if args.debug:
                print(f"Converted Markdown to text and saved to: {txt_file}")
            # Update the file path to use the converted text file
            args.file = txt_file
        except Exception as e:
            print(f"Error saving converted text file: {str(e)}")
            return

    # Parse voice and avatar variations
    voice_ids = parse_voice_variations(args.voice_id) if args.voice_id else []
    voice_names = parse_voice_variations(args.voice) if args.voice else []
    avatar_ids = parse_voice_variations(args.avatar_id) if args.avatar_id else []
    avatar_names = parse_voice_variations(args.avatar) if args.avatar else []

    # Validate input
    if not voice_ids and not voice_names:
        print("Error: Either --voice-id or --voice must be specified")
        return

    if not avatar_ids and not avatar_names:
        print("Error: Either --avatar-id or --avatar must be specified")
        return

    # Create rate limiter for API calls using environment variable
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)

    # Prepare voice combinations
    voice_combinations = []
    
    # Add direct voice IDs
    for voice_id in voice_ids:
        voice_combinations.append({
            'id': voice_id,
            'name': voice_id,  # Use ID as name for direct voice IDs
            'style': None
        })
    
    # Add voice name combinations (without style)
    for voice_name in voice_names:
        voice_id = get_voice_id_by_name(access_token, voice_name, None)
        if voice_id:
            voice_combinations.append({
                'id': voice_id,
                'name': voice_name,
                'style': None
            })
        else:
            print(f"Warning: No voice ID found for name '{voice_name}'")

    if not voice_combinations:
        print("Error: No valid voice combinations found")
        return

    # Prepare avatar combinations
    avatar_combinations = []
    
    # Add direct avatar IDs
    for avatar_id in avatar_ids:
        avatar_combinations.append({
            'id': avatar_id,
            'name': avatar_id  # Use ID as name for direct avatar IDs
        })
    
    # Add avatar name combinations
    for avatar_name in avatar_names:
        avatar_id = get_avatar_id_by_name(access_token, avatar_name)
        if avatar_id:
            avatar_combinations.append({
                'id': avatar_id,
                'name': avatar_name
            })
        else:
            print(f"Warning: No avatar ID found for name '{avatar_name}'")

    if not avatar_combinations:
        print("Error: No valid avatar combinations found")
        return

    # Show progress table
    total_combinations = len(voice_combinations) * len(avatar_combinations)
    print(f"\nGenerating {total_combinations} total variations:")
    print(f"  • {len(voice_combinations)} voice combinations")
    print(f"  • {len(avatar_combinations)} avatar combinations")
    print(f"\nUsing parallel processing with rate limit of {throttle_limit} calls per minute\n")

    # Print voice combinations
    print("\nVoice Combinations:")
    for i, combo in enumerate(voice_combinations, 1):
        print(f"{i}. ID: {combo['id']}, Name: {combo['name']}, Style: {combo['style']}")

    # Print avatar combinations
    print("\nAvatar Combinations:")
    for i, combo in enumerate(avatar_combinations, 1):
        print(f"{i}. ID: {combo['id']}, Name: {combo['name']}")

    # Split text into paragraphs if requested
    paragraphs = []
    paragraph_info = []  # Store info about each paragraph
    if args.p_split and args.file:
        # Split by double newlines and filter out empty paragraphs
        raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        if args.debug:
            print(f"\nFound {len(raw_paragraphs)} paragraphs in the text file")
            for i, p in enumerate(raw_paragraphs, 1):
                print(f"\nParagraph {i}:")
                print(f"  Length: {len(p)} characters")
                print(f"  Preview: {p[:100] + '...' if len(p) > 100 else p}")
        
        # Process each paragraph
        i = 0
        while i < len(raw_paragraphs):
            para = raw_paragraphs[i]
            para_num = i + 1
            
            # If paragraph is too short and not the last one, combine with next paragraph
            if len(para) < 15 and i < len(raw_paragraphs) - 1:
                if args.debug:
                    print(f"\nCombining short paragraph {para_num} with next paragraph")
                next_para = raw_paragraphs[i + 1]
                combined_para = f"{para} {next_para}"
                if args.debug:
                    print(f"  Combined length: {len(combined_para)} characters")
                    print(f"  Preview: {combined_para[:100] + '...' if len(combined_para) > 100 else combined_para}")
                para = combined_para
                i += 1  # Skip the next paragraph since we combined it
            
            # Split long paragraphs into sentences if they exceed 1000 characters
            if len(para) > 1000:
                # Split into sentences (basic split on period + space)
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if args.debug:
                    print(f"\nSplitting paragraph {para_num} into {len(sentences)} sentences")
                
                # Add each sentence as a separate paragraph if it's long enough
                for j, sentence in enumerate(sentences, 1):
                    if len(sentence) >= 15:  # Only include sentences longer than 15 chars
                        paragraphs.append(sentence)
                        paragraph_info.append({
                            'para_num': para_num,
                            'total_paras': len(raw_paragraphs),
                            'sentence_num': j,
                            'total_sentences': len(sentences),
                            'char_count': len(sentence),
                            'is_split': True
                        })
                        if args.debug:
                            print(f"  Split sentence {j}: {sentence[:50]}...")
            else:
                # Add the paragraph as is if it's not too long
                paragraphs.append(para)
                paragraph_info.append({
                    'para_num': para_num,
                    'total_paras': len(raw_paragraphs),
                    'sentence_num': 1,
                    'total_sentences': 1,
                    'char_count': len(para),
                    'is_split': False
                })
                if args.debug:
                    print(f"  Keeping as single paragraph: {para[:50]}...")
            
            i += 1
        
        if args.debug:
            print(f"\nFinal split into {len(paragraphs)} segments:")
            for i, (p, info) in enumerate(zip(paragraphs, paragraph_info), 1):
                print(f"\nSegment {i}:")
                print(f"  Paragraph {info['para_num']} of {info['total_paras']}")
                print(f"  Sentence {info['sentence_num']} of {info['total_sentences']}")
                print(f"  Characters: {info['char_count']}")
                print(f"  Split from longer paragraph: {info['is_split']}")
                print(f"  Preview: {p[:100] + '...' if len(p) > 100 else p}")
    else:
        # For non-split text, only process if it's long enough
        if len(text) >= 15:
            paragraphs = [text]
            paragraph_info = [{
                'para_num': 1,
                'total_paras': 1,
                'sentence_num': 1,
                'total_sentences': 1,
                'char_count': len(text),
                'is_split': False
            }]
        else:
            print("Error: Input text must be at least 15 characters long")
            return

    # Create tasks for parallel processing
    tasks = []
    for voice_combo in voice_combinations:
        for avatar_combo in avatar_combinations:
            for i, (paragraph, info) in enumerate(zip(paragraphs, paragraph_info), 1):
                def create_avatar_task(vc, ac, para, info):
                    def avatar_task():
                        try:
                            # Generate avatar video
                            if args.debug:
                                print(f"\nGenerating avatar video with voice: {vc['id']} ({vc['name']} - {vc['style']})")
                                print(f"Avatar: {ac['id']} ({ac['name']})")
                                print(f"Processing paragraph {info['para_num']} of {info['total_paras']}")
                                if info['is_split']:
                                    print(f"Segment {info['sentence_num']} of {info['total_sentences']} sentences")
                            
                            # Create tokens for filename
                            tokens = {
                                'date': datetime.now().strftime('%Y-%m-%d'),
                                'time': datetime.now().strftime('%H-%M-%S'),
                                'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
                                'voice_id': vc['id'],
                                'voice_name': vc['name'],
                                'voice_style': vc['style'] or '',
                                'avatar_id': ac['id'],
                                'avatar_name': ac['name'],
                                'locale_code': args.locale,
                                'para_num': f"{info['para_num']:02d}",
                                'total_paras': f"{info['total_paras']:02d}",
                                'sentence_num': f"{info['sentence_num']:02d}",
                                'total_sentences': f"{info['total_sentences']:02d}",
                                'char_count': f"{info['char_count']:02d}"
                            }
                            
                            # Add paragraph number to output path if splitting paragraphs
                            if args.p_split:
                                output_path = args.output.format(**tokens)
                            else:
                                output_path = args.output.format(**tokens)
                            
                            if args.debug:
                                print(f"Original output path: {args.output}")
                                print(f"Tokens: {tokens}")
                                print(f"Replaced output path: {output_path}")
                            
                            # Create output directory if it doesn't exist
                            output_dir = os.path.dirname(output_path)
                            if output_dir:
                                os.makedirs(output_dir, exist_ok=True)
                                if args.debug:
                                    print(f"Created output directory: {output_dir}")
                            
                            # Generate avatar video
                            response = generate_avatar(
                                access_token=access_token,
                                text=para,
                                voice_id=vc['id'],
                                avatar_id=ac['id'],
                                locale_code=args.locale,
                                debug=args.debug
                            )
                            
                            if response and 'jobId' in response and 'statusUrl' in response:
                                if args.debug:
                                    print(f"Job ID: {response['jobId']}")
                                    print("Polling for job completion...")
                                
                                # Poll the status URL until the job is complete
                                result = check_job_status(response['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
                                
                                if result.get('status') == 'succeeded' and 'output' in result:
                                    # Extract video URL from the response
                                    output = result['output']
                                    video_url = None
                                    
                                    # Check for direct URL first
                                    if 'url' in output:
                                        video_url = output['url']
                                    # Check for nested destination URL (avatar API format)
                                    elif 'destination' in output and 'url' in output['destination']:
                                        video_url = output['destination']['url']
                                    
                                    if video_url:
                                        # Download the video file
                                        try:
                                            if args.debug:
                                                print(f"Making request to download file from {video_url}")
                                            response = requests.get(video_url, stream=True)
                                            response.raise_for_status()
                                            
                                            # Ensure the output file has .mp4 extension
                                            if not output_path.lower().endswith('.mp4'):
                                                output_path = os.path.splitext(output_path)[0] + '.mp4'
                                            
                                            # Download the file
                                            with open(output_path, 'wb') as f:
                                                for chunk in response.iter_content(chunk_size=8192):
                                                    if chunk:
                                                        f.write(chunk)
                                            
                                            if not args.silent:
                                                print(f"✓ Generated avatar video: {output_path}")
                                            
                                            return True
                                            
                                        except Exception as e:
                                            if args.debug:
                                                print(f"Error downloading file: {str(e)}")
                                            return False
                                    else:
                                        if args.debug:
                                            print(f"No video URL found in response: {result}")
                                        return False
                                else:
                                    if args.debug:
                                        print(f"Job failed or no output URL found: {result}")
                                    return False
                            else:
                                if args.debug:
                                    print(f"Invalid response from generate_avatar: {response}")
                                return False
                                
                        except Exception as e:
                            if args.debug:
                                print(f"Error in avatar task: {str(e)}")
                            return False
                    
                    return avatar_task
                
                task_func = create_avatar_task(voice_combo, avatar_combo, paragraph, info)
                tasks.append((task_func,))  # Wrap in tuple as expected by process_tasks_parallel

    # Process tasks in parallel
    results = process_tasks_parallel(tasks, rate_limiter)

    # Print summary
    success_count = sum(1 for r in results if r)
    print(f"\nCompleted {success_count} of {len(tasks)} variations successfully")

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

def handle_avatar_list_command(args, access_token):
    """Handle the avatar-list command."""
    # List available avatars
    avatars = get_available_avatars(access_token)
    if avatars:
        # Sort avatars by status (Active first) and then by name
        active_avatars = [v for v in avatars if v.get('status') == 'Active']
        inactive_avatars = [v for v in avatars if v.get('status') == 'Inactive']
        
        # Prepare table data with additional fields
        def prepare_avatar_data(avatar_list):
            return [[
                avatar.get('avatarId', 'N/A'),
                avatar.get('displayName', 'N/A'),
                avatar.get('gender', 'N/A'),
                avatar.get('style', 'N/A'),
                avatar.get('avatarType', 'N/A'),
                avatar.get('status', 'N/A'),
                avatar.get('wordsPerMinute', 'N/A'),
                'Yes' if avatar.get('sampleURL') else 'No'
            ] for avatar in sorted(avatar_list, key=lambda x: x.get('displayName', ''))]
        
        # Print active avatars first
        if active_avatars:
            print("\nActive Avatars:")
            active_table = prepare_avatar_data(active_avatars)
            print(tabulate(
                active_table,
                headers=['ID', 'Name', 'Gender', 'Style', 'Type', 'Status', 'WPM', 'Sample'],
                tablefmt='grid'
            ))
        
        # Print inactive avatars
        if inactive_avatars:
            print("\nInactive Avatars:")
            inactive_table = prepare_avatar_data(inactive_avatars)
            print(tabulate(
                inactive_table,
                headers=['ID', 'Name', 'Gender', 'Style', 'Type', 'Status', 'WPM', 'Sample'],
                tablefmt='grid'
            ))
    else:
        print("No avatars found or error occurred")

def format_time(seconds):
    """Convert seconds to MM:SS format"""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def handle_transcribe_command(args, access_token):
    """Handle the transcribe command"""
    try:
        # Validate file extension matches output type
        output_ext = os.path.splitext(args.output)[1].lower()
        if output_ext == '.pdf' and args.output_type != 'pdf':
            print(f"Error: Output file has .pdf extension but --output-type is set to '{args.output_type}'")
            print("Please either:")
            print("1. Change the output file extension to match the output type")
            print("2. Set --output-type to 'pdf' to match the file extension")
            sys.exit(1)
        elif output_ext == '.md' and args.output_type != 'markdown':
            print(f"Error: Output file has .md extension but --output-type is set to '{args.output_type}'")
            print("Please either:")
            print("1. Change the output file extension to match the output type")
            print("2. Set --output-type to 'markdown' to match the file extension")
            sys.exit(1)
        
        # Get access token
        access_token = retrieve_access_token(debug=args.debug)
        
        # Upload file to Azure Storage
        print(f"Uploading file to Azure Storage: {args.input}")
        source_url = upload_to_azure_storage(args.input, debug=args.debug)
        print(f"File uploaded successfully. Source URL: {source_url}")
        
        # Transcribe the media
        job_info = transcribe_media(
            access_token=access_token,
            source_url=source_url,
            target_locale=args.locale,
            content_type=args.type,
            text_only=args.text_only,
            debug=args.debug
        )
        
        if args.debug:
            print(f"Job ID: {job_info['jobId']}")
            print("Polling for job completion...")
        
        # Poll the status URL until the job is complete
        result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug)
        
        if 'outputs' not in result or not result['outputs']:
            raise Exception("No outputs found in job response")
            
        # Get the transcription URL from the first output
        transcription_url = result['outputs'][0]['destination']['url']
        
        if args.debug:
            print(f"Downloading transcription from: {transcription_url}")
        
        # Download the transcription
        response = requests.get(transcription_url)
        response.raise_for_status()
        transcription_data = response.json()
        
        # Convert output path to absolute path and create directory if needed
        output_path = os.path.abspath(args.output)
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Process the output based on the format
        if args.output_type == 'markdown':
            # Convert to markdown format
            markdown_content = "# Transcription\n\n"
            for item in transcription_data:
                start_time = item[0]
                end_time = item[1]
                text = item[2]
                speaker = item[3]
                
                markdown_content += f"### {speaker}\n\n"
                markdown_content += f"*Time Range:* {format_time(start_time)} - {format_time(end_time)}\n\n"
                markdown_content += f"{text}\n\n"
            
            # Write markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"Transcription saved as markdown to: {output_path}")
            
        elif args.output_type == 'pdf':
            # First create markdown content
            markdown_content = "# Transcription\n\n"
            for item in transcription_data:
                start_time = item[0]
                end_time = item[1]
                text = item[2]
                speaker = item[3]
                
                markdown_content += f"### {speaker}\n\n"
                markdown_content += f"*Time Range:* {format_time(start_time)} - {format_time(end_time)}\n\n"
                markdown_content += f"{text}\n\n"
            
            # Try to convert markdown to PDF
            try:
                import markdown
                from weasyprint import HTML, CSS
                from weasyprint.text.fonts import FontConfiguration
                
                pdf_path = output_path
                if not pdf_path.lower().endswith('.pdf'):
                    pdf_path = os.path.splitext(output_path)[0] + '.pdf'
                
                # Convert markdown to HTML
                html_content = markdown.markdown(markdown_content)
                
                # Add some basic styling
                html_content = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        h1 {{ color: #333; }}
                        h3 {{ color: #666; margin-top: 20px; }}
                        em {{ color: #888; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                
                # Configure fonts
                font_config = FontConfiguration()
                
                # Convert HTML to PDF
                HTML(string=html_content).write_pdf(
                    pdf_path,
                    font_config=font_config
                )
                print(f"Transcription saved as PDF to: {pdf_path}")
            except ImportError as e:
                print("\nError: PDF conversion requires additional packages.")
                print("To enable PDF output, please install the required packages using:")
                print("pip install markdown weasyprint")
                print("\nSaving as markdown instead...")
                # Save as markdown with .md extension
                md_path = os.path.splitext(output_path)[0] + '.md'
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                print(f"Transcription saved as markdown to: {md_path}")
                sys.exit(1)
            
        else:  # text format
            # Write only the text content with double newlines between items
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in transcription_data:
                    f.write(f"{item[2]}\n\n")
            
            print(f"Transcription saved as text to: {output_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        if args.debug:
            import traceback
            print(traceback.format_exc())
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

def handle_fill_command(args, access_token):
    """Handle the Generative Fill command."""
    import subprocess
    import os.path
    
    # Validate numVariations
    if not 1 <= args.numVariations <= 4:
        print("Error: Number of variations (-n) must be between 1 and 4")
        sys.exit(1)

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Parse prompt variations
    prompts, variation_blocks = parse_prompt_variations(args.prompt)
    total_variations = len(prompts)

    # Get throttle limit from environment
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)

    if not args.silent:
        print(f'Generating {total_variations} total variations:')
        print(f'  • {total_variations} prompt variations')
        print(f'  • {args.numVariations} variations per prompt')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')

    # Invert the mask if --mask-invert is set
    if args.mask_invert:
        if args.debug:
            print(f"Inverting mask: {args.mask}")
        
        # Get the original filename without path
        original_filename = os.path.basename(args.mask)
        # Create path in /tmp with same filename
        inverted_mask_path = os.path.join('/tmp', original_filename)
        
        try:
            # Run ImageMagick convert command
            result = subprocess.run(['convert', args.mask, '-negate', inverted_mask_path], 
                                 check=True, 
                                 capture_output=True, 
                                 text=True)
            if args.debug:
                print(f"ImageMagick output: {result.stdout}")
                print(f"Inverted mask saved to: {inverted_mask_path}")
            mask_path = inverted_mask_path
        except subprocess.CalledProcessError as e:
            print(f"Error inverting mask: {e.stderr}")
            sys.exit(1)
    else:
        mask_path = args.mask

    if args.debug:
        print(f"Using mask path: {mask_path}")

    def fill_task(prompt, j):
        rate_limiter.acquire()
        tokens = {
            'prompt': prompt,
            'seeds': args.seeds,
            'iteration': j + 1
        }
        base_filename = get_variation_filename(args.output, prompt, args.prompt, tokens, args.debug)
        output_filename = get_unique_filename(base_filename, args.overwrite, args.debug)
        try:
            job_info = fill_image(
                access_token=access_token,
                image_path=args.input,
                mask_path=mask_path,
                prompt=prompt,
                negative_prompt=args.negative_prompt,
                prompt_biasing_locale=args.locale,
                num_variations=1,
                mask_invert=False,  # We've already inverted the mask if needed
                height=args.height,
                width=args.width,
                seeds=args.seeds,
                debug=args.debug
            )
            if args.debug:
                print(f"Job ID: {job_info['jobId']}")
                print("Polling for job completion...")
            result = check_job_status(job_info['statusUrl'], access_token, args.silent, args.debug, rate_limiter)
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
            print(f"Error generating fill: {str(e)}")
            if args.debug:
                import traceback
                traceback.print_exc()
            return False

    # Create tasks for parallel processing
    tasks = []
    current_generation = 0

    # Prepare the table header
    if not args.silent:
        print("Generation Tasks:")
        print(f"{'#':<4} {'Prompt':<40}")
        print("-" * 45)

    with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
        for prompt in prompts:
            for j in range(args.numVariations):
                current_generation += 1
                if not args.silent:
                    print(f"{current_generation:<4} {prompt[:40]:<40}")
                tasks.append(executor.submit(fill_task, prompt, j))
        for future in concurrent.futures.as_completed(tasks):
            future.result()

    if not args.silent:
        print("\nAll fill generation tasks completed.")

def handle_mask_command(args, access_token):
    """Handle the mask command."""
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Get unique filename if needed
        output_filename = get_unique_filename(args.output, args.overwrite, args.debug)
        
        # Create the mask
        job_info = create_mask(
            access_token=access_token,
            image_path=args.input,
            output_path=output_filename,
            optimize=args.optimize,
            postprocess=not args.no_postprocess,
            service_version=args.service_version,
            mask_format=args.mask_format,
            debug=args.debug
        )
        
        # If mask-invert is set, use ImageMagick to invert the mask
        if args.mask_invert:
            import subprocess
            subprocess.run(['convert', output_filename, '-negate', output_filename], check=True)
        
        if args.debug:
            print(f"Mask created successfully: {output_filename}")
            print(f"Job ID: {job_info.get('jobID')}")
            print(f"Status: {job_info.get('status')}")
        
    except Exception as e:
        print(f"Error creating mask: {str(e)}")
        sys.exit(1)

def handle_replace_bg_command(args, access_token):
    """Handle the replace background command."""
    import tempfile
    import subprocess
    from utils.filename import get_unique_filename, parse_prompt_variations
    import time

    # Handle wildcard input files
    input_files = glob.glob(args.input)
    if not input_files:
        print(f"No files found matching pattern: {args.input}")
        sys.exit(1)

    if not args.silent:
        print(f"Found {len(input_files)} files to process")

    # Parse prompt variations
    prompts, variation_blocks = parse_prompt_variations(args.prompt)
    total_variations = len(prompts)

    # Get throttle limit from environment - reduce it for mask operations
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 2))  # Reduced from 5 to 2
    throttle_period = int(os.getenv('THROTTLE_PERIOD_SECONDS', 60))
    throttle_min_delay = float(os.getenv('THROTTLE_MIN_DELAY_SECONDS', 0.0))
    rate_limiter = RateLimiter(throttle_limit, throttle_period, throttle_min_delay)

    if not args.silent:
        print(f'Generating {total_variations} total variations:')
        print(f'  • {total_variations} prompt variations')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')

    def replace_bg_task(input_file, prompt, index):
        max_retries = 3
        retry_delay = 70  # seconds
        
        for attempt in range(max_retries):
            try:
                rate_limiter.acquire()
                
                # Get the base filename without extension
                input_filename = os.path.splitext(os.path.basename(input_file))[0]
                
                # Create output filename with input_filename token
                output_filename = args.output.replace("{input_filename}", input_filename)
                if "{var1}" in output_filename:
                    output_filename = output_filename.replace("{var1}", str(index + 1))
                output_filename = get_unique_filename(output_filename, args.overwrite, args.debug)

                if not args.silent:
                    print(f"Processing {input_file} with prompt: {prompt}")

                # Create temporary directory for mask files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Step 1: Create mask
                    mask_path = os.path.join(temp_dir, "mask.png")
                    if not args.silent:
                        print("Creating mask...")
                    mask_result = create_mask(
                        access_token=access_token,
                        image_path=input_file,
                        output_path=mask_path,
                        debug=args.debug
                    )
                    if not mask_result:
                        print(f"Failed to create mask for {input_file}")
                        return False

                    # Step 2: Invert mask using ImageMagick
                    inverted_mask_path = os.path.join(temp_dir, "inverted_mask.png")
                    if not args.silent:
                        print("Inverting mask...")
                    try:
                        subprocess.run(['magick', mask_path, '-negate', inverted_mask_path], check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Error inverting mask for {input_file}: {str(e)}")
                        return False

                    # Step 3: Generate new background
                    if not args.silent:
                        print("Generating new background...")
                    fill_result = fill_image(
                        access_token=access_token,
                        image_path=input_file,
                        mask_path=inverted_mask_path,
                        prompt=prompt,
                        num_variations=1,
                        mask_invert=True,
                        debug=args.debug
                    )

                    if not fill_result:
                        print(f"Failed to generate new background for {input_file}")
                        return False

                    # Poll for job completion
                    if args.debug:
                        print(f"Job ID: {fill_result['jobId']}")
                        print("Polling for job completion...")
                    result = check_job_status(fill_result['statusUrl'], access_token, args.silent, args.debug)

                    if 'result' in result and 'outputs' in result['result']:
                        outputs = result['result']['outputs']
                        if outputs:
                            if not args.silent:
                                print(f"Saving result to: {output_filename}")
                            download_file(outputs[0]['image']['url'], output_filename, args.silent, args.debug)
                            return True
                        else:
                            print(f"No outputs found in response for {input_file}")
                            return False
                    else:
                        print(f"Failed to get result from job for {input_file}")
                        return False
                        
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        print(f"\nReceived 429 (Too Many Requests) error for {input_file}. Waiting {retry_delay} seconds before retry {attempt + 2}/{max_retries}...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        print(f"\nFailed to process {input_file} after {max_retries} attempts due to rate limiting.")
                        return False
                else:
                    print(f"HTTP Error processing {input_file}: {str(e)}")
                    return False
            except Exception as e:
                print(f"Error processing {input_file}: {str(e)}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
                return False

    # Create tasks for parallel processing
    tasks = []
    current_generation = 0

    # Prepare the table header
    if not args.silent:
        print("Generation Tasks:")
        print(f"{'#':<4} {'Input File':<30} {'Prompt':<40}")
        print("-" * 75)

    with concurrent.futures.ThreadPoolExecutor(max_workers=throttle_limit) as executor:
        for input_file in input_files:
            for i, prompt in enumerate(prompts):
                current_generation += 1
                if not args.silent:
                    print(f"{current_generation:<4} {os.path.basename(input_file):<30} {prompt[:40]:<40}")
                tasks.append(executor.submit(replace_bg_task, input_file, prompt, i))
        for future in concurrent.futures.as_completed(tasks):
            future.result()

    if not args.silent:
        print("\nAll background replacement tasks completed.")

def check_job_status(status_url, access_token, silent=False, debug=False, rate_limiter=None):
    """
    Poll the status URL until the job is complete.
    
    Args:
        status_url (str): The URL to check job status
        access_token (str): The authentication token
        silent (bool): Whether to suppress output messages
        debug (bool): Whether to show debug information
        rate_limiter: Optional rate limiter for throttling requests
    
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

    # Check if status requests should be throttled
    throttle_status = os.getenv('THROTTLE_STATUS_REQUESTS', 'true').lower() == 'true'

    while True:
        # Apply rate limiting if provided and enabled for status requests
        if rate_limiter and throttle_status:
            rate_limiter.acquire()
            
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
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            if debug:
                print(f"Created output directory: {output_dir}")

        # Download the file
        if debug:
            print(f"Downloading from {url} to {output_file}")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if debug:
            print(f"Successfully downloaded to {output_file}")
        return True
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        return False

def read_text_file(file_path):
    """
    Read text from a file and preserve paragraph structure.
    If the file is a Markdown file, convert it to plain text by removing Markdown syntax.
    
    Args:
        file_path (str): Path to the text file
    
    Returns:
        str: Contents of the file with preserved paragraph structure
    
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If there's an error reading the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read the file and normalize line endings
            content = f.read()
            # Normalize all line endings to \n
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # If it's a Markdown file, convert to plain text
            if file_path.lower().endswith('.md'):
                # Remove Markdown headers
                content = re.sub(r'^#+\s+', '', content, flags=re.MULTILINE)
                # Remove bold/italic markers
                content = re.sub(r'[*_]{1,2}(.*?)[*_]{1,2}', r'\1', content)
                # Remove code blocks
                content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
                # Remove inline code
                content = re.sub(r'`(.*?)`', r'\1', content)
                # Remove links
                content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)
                # Remove horizontal rules
                content = re.sub(r'^[-*_]{3,}$', '', content, flags=re.MULTILINE)
                # Remove blockquotes
                content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)
                # Remove list markers
                content = re.sub(r'^[-*+]\s+', '', content, flags=re.MULTILINE)
                content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)
                # Remove HTML tags
                content = re.sub(r'<[^>]+>', '', content)
                # Remove multiple blank lines
                content = re.sub(r'\n{3,}', '\n\n', content)
                # Remove leading/trailing whitespace from each line
                content = '\n'.join(line.strip() for line in content.split('\n'))
            
            # Ensure paragraphs are separated by exactly two newlines
            content = re.sub(r'\n{3,}', '\n\n', content)
            return content.strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Text file not found: {file_path}")
    except Exception as e:
        raise Exception(f"Error reading text file: {str(e)}")

def get_text_from_file_or_input(text, file_path):
    """
    Get text from either direct input or a file.
    
    Args:
        text (str): Direct text input
        file_path (str): Path to text file
    
    Returns:
        str: The text content, or None if no text is provided
    """
    if text:
        return text
    elif file_path:
        try:
            return read_text_file(file_path)
        except Exception as e:
            print(f"Error reading text file: {str(e)}")
            return None
    return None

def process_tasks_parallel(tasks, rate_limiter):
    """
    Process tasks in parallel with rate limiting.
    
    Args:
        tasks (list): List of (task_function, *task_args) tuples
        rate_limiter (RateLimiter): Rate limiter instance
    
    Returns:
        list: Results from all tasks
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for task_tuple in tasks:
            task_func = task_tuple[0]
            task_args = task_tuple[1:]  # Get all remaining elements as arguments
            rate_limiter.acquire()
            futures.append(executor.submit(task_func, *task_args))
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    print("\nReceived 429 (Too Many Requests) error. Waiting 70 seconds before retrying...")
                    time.sleep(70)
                    # Resubmit the task
                    task_tuple = tasks[len(results)]  # Get the original task that failed
                    task_func = task_tuple[0]
                    task_args = task_tuple[1:]
                    rate_limiter.acquire()
                    new_future = executor.submit(task_func, *task_args)
                    try:
                        result = new_future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"Error after retry: {str(e)}")
                        results.append(False)
                else:
                    print(f"HTTP Error: {str(e)}")
                    results.append(False)
            except Exception as e:
                print(f"Error: {str(e)}")
                results.append(False)
    
    return results

def add_transcribe_command(subparsers):
    """Add the transcribe command to the CLI"""
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio or video content')
    transcribe_parser.add_argument('-i', '--input', required=True, help='Input file path')
    transcribe_parser.add_argument('-o', '--output', required=True, help='Output file path')
    transcribe_parser.add_argument('-l', '--locale', default='en-US', help='Target locale (default: en-US)')
    transcribe_parser.add_argument('-t', '--type', required=True, choices=['audio', 'video'], help='Media type (audio or video)')
    transcribe_parser.add_argument('--text-only', action='store_true', help='Return only the transcript text')
    transcribe_parser.add_argument('--output-type', choices=['text', 'markdown', 'pdf'], default='text',
                                 help='Output format (text, markdown, or pdf)')
    transcribe_parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    transcribe_parser.set_defaults(func=handle_transcribe_command)

def handle_list_custom_models_command(args, access_token):
    """List available custom models for Firefly."""
    import csv
    import io
    def truncate(val, length=16):
        if not val:
            return ''
        return val if len(val) <= length else val[:length-3] + '...'
    def base_model_short(name):
        if not name:
            return ''
        if 'image3' in name:
            return 'image3'
        if 'image4' in name:
            return 'image4'
        return name.split('_')[0]
    api_key = os.environ.get('FIREFLY_SERVICES_CLIENT_ID')
    if not api_key:
        print("Error: FIREFLY_SERVICES_CLIENT_ID is not set in environment.")
        sys.exit(1)
    headers = {
        'x-api-key': api_key,
        'x-request-id': f'ffcli-{int(time.time())}',
        'Authorization': f'Bearer {access_token}'
    }
    url = 'https://firefly-api.adobe.io/v3/custom-models'
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if args.debug:
            print("=== Full API Response ===")
            print(json.dumps(data, indent=2))
            print("=== End API Response ===\n")
        
        models = data.get('custom_models', [])
        if not models:
            print('No custom models found.')
            return
        # Output all fields from the response
        if args.csv:
            # Collect all unique keys from all models
            all_keys = set()
            for m in models:
                all_keys.update(m.keys())
            # Sort keys for consistency
            all_keys = sorted(all_keys)
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(all_keys)
            for m in models:
                row = [m.get(k, '') for k in all_keys]
                writer.writerow(row)
            print(output.getvalue())
        else:
            try:
                from rich.table import Table
                from rich.console import Console
                table = Table(show_header=True, header_style="bold magenta", show_lines=True)
                table.add_column('Name', overflow="fold", max_width=30)
                table.add_column('Asset ID', overflow="fold", max_width=72)
                table.add_column('Training Mode', overflow="fold", max_width=20)
                table.add_column('Base Model', overflow="fold", max_width=15)
                
                for model in models:
                    display_name = model.get('displayName', '')
                    asset_id = model.get('assetId', '')
                    training_mode = model.get('trainingMode', '')
                    base_model = model.get('baseModel', {}).get('name', '')
                    
                    table.add_row(
                        display_name,
                        asset_id,
                        training_mode,
                        base_model
                    )
                console = Console()
                console.print(table)
            except ImportError:
                print("The 'rich' library is required for pretty table output. Install it with: pip install rich")
                # fallback to tabulate if available
                try:
                    from tabulate import tabulate
                    table_data = []
                    for model in models:
                        table_data.append([
                            model.get('displayName', ''),
                            model.get('assetId', ''),
                            model.get('trainingMode', ''),
                            model.get('baseModel', {}).get('name', '')
                        ])
                    print(tabulate(table_data, headers=['Name', 'Asset ID', 'Training Mode', 'Base Model'], tablefmt='fancy_grid', maxcolwidths=[30, 72, 20, 15], stralign='left', numalign='left'))
                except ImportError:
                    # Plain text fallback
                    print("Name\tAsset ID\tTraining Mode\tBase Model")
                    for model in models:
                        print(f"{model.get('displayName', '')}\t{model.get('assetId', '')}\t{model.get('trainingMode', '')}\t{model.get('baseModel', {}).get('name', '')}")
    except Exception as e:
        print(f"Error fetching custom models: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

def handle_video_command(args, access_token):
    """Handle the video generation command."""
    import time
    import os
    
    # Validate output file extension
    if not args.output.lower().endswith('.mp4'):
        print("Error: Output file must have .mp4 extension")
        sys.exit(1)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Check if file exists and handle overwrite
    if os.path.exists(args.output) and not args.overwrite:
        print(f"Error: Output file '{args.output}' already exists. Use --overwrite to overwrite.")
        sys.exit(1)
    
    if not args.silent:
        print(f"Generating video with prompt: '{args.prompt}'")
        print(f"Size: {args.size}")
        print(f"Output: {args.output}")
    
    start_time = time.time()
    
    try:
        # Generate video
        if not args.silent:
            print("Submitting video generation request...")
        
        response = generate_video(
            access_token=access_token,
            prompt=args.prompt,
            size=args.size,
            first_frame=args.firstFrame,
            last_frame=args.lastFrame,
            debug=args.debug
        )
        
        if args.debug:
            print(f"DEBUG: Generation response: {response}")
        
        job_id = response.get('jobId')
        status_url = response.get('statusUrl')
        
        if not job_id or not status_url:
            print("Error: Invalid response from video generation API")
            sys.exit(1)
        
        if not args.silent:
            print(f"Job submitted successfully. Job ID: {job_id}")
            print("Polling for completion...")
        
        # Poll for completion
        max_retries = int(os.getenv('API_MAX_RETRIES', 3))
        retry_delay = float(os.getenv('API_RETRY_DELAY', 2.0))
        poll_interval = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                while True:
                    status_response = check_video_job_status(
                        status_url=status_url,
                        access_token=access_token,
                        debug=args.debug
                    )
                    
                    if args.debug:
                        print(f"DEBUG: Status response: {status_response}")
                    
                    status = status_response.get('status')
                    
                    if status == 'succeeded':
                        if not args.silent:
                            print("Video generation completed successfully!")
                        
                        # Extract video URL
                        result = status_response.get('result', {})
                        outputs = result.get('outputs', [])
                        
                        if not outputs:
                            print("Error: No video outputs in response")
                            sys.exit(1)
                        
                        video_url = outputs[0].get('video', {}).get('url')
                        if not video_url:
                            print("Error: No video URL in response")
                            sys.exit(1)
                        
                        # Download video
                        if not args.silent:
                            print(f"Downloading video to: {args.output}")
                        
                        download_video(
                            url=video_url,
                            output_file=args.output,
                            debug=args.debug
                        )
                        
                        elapsed_time = time.time() - start_time
                        if not args.silent:
                            print(f"Video saved successfully! (took {elapsed_time:.1f} seconds)")
                        
                        return
                    
                    elif status == 'failed':
                        error_msg = status_response.get('error', 'Unknown error')
                        print(f"Video generation failed: {error_msg}")
                        sys.exit(1)
                    
                    elif status == 'running':
                        progress = status_response.get('progress', 0)
                        if not args.silent:
                            print(f"Progress: {progress}%")
                        time.sleep(poll_interval)
                    
                    else:
                        print(f"Unknown status: {status}")
                        time.sleep(poll_interval)
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed after {max_retries} attempts: {e}")
                    sys.exit(1)
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"Error generating video: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)