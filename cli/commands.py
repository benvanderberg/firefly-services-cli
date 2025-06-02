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

from utils.auth import retrieve_access_token
from utils.storage import upload_to_azure_storage
from utils.rate_limiter import RateLimiter
from utils.filename import parse_size, parse_prompt_variations, get_variation_filename, get_unique_filename, replace_filename_tokens
from services.image import generate_image, parse_model_variations, parse_style_ref_variations, generate_similar_image, expand_image, fill_image, create_mask
from services.speech import generate_speech, get_available_voices, parse_voice_variations, get_voice_id_by_name
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
    elif args.command == 'fill':
        handle_fill_command(args, access_token)
    elif args.command == 'mask':
        handle_mask_command(args, access_token)
    elif args.command == 'replace-bg':
        handle_replace_bg_command(args, access_token)
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
    rate_limiter = RateLimiter(max_calls=throttle_limit, period=60)

    # Prepare voice combinations
    voice_combinations = []
    
    # Add direct voice IDs
    for voice_id in voice_ids:
        voice_combinations.append({
            'id': voice_id,
            'name': voice_id,  # Use ID as name for direct voice IDs
            'style': None
        })
    
    # Add voice name + style combinations
    for voice_name in voice_names:
        for style in voice_styles:
            voice_id = get_voice_id_by_name(access_token, voice_name, style)
            if voice_id:
                voice_combinations.append({
                    'id': voice_id,
                    'name': voice_name,
                    'style': style
                })
            else:
                print(f"Warning: No voice ID found for name '{voice_name}' with style '{style}'")

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
                        result = check_job_status(response['statusUrl'], access_token, args.silent, args.debug)
                        
                        if result.get('status') == 'succeeded' and 'output' in result and 'url' in result['output']:
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
    rate_limiter = RateLimiter(throttle_limit, 60)

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

    if not args.silent:
        print(f"Processing image: {args.input}")

    # Parse prompt variations
    prompts, variation_blocks = parse_prompt_variations(args.prompt)
    total_variations = len(prompts)

    # Get throttle limit from environment
    throttle_limit = int(os.getenv('THROTTLE_LIMIT_FIREFLY', 5))
    rate_limiter = RateLimiter(throttle_limit, 60)

    if not args.silent:
        print(f'Generating {total_variations} total variations:')
        print(f'  • {total_variations} prompt variations')
        print(f'Using parallel processing with rate limit of {throttle_limit} calls per minute\n')

    # Create temporary directory for mask files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Create mask
        mask_path = os.path.join(temp_dir, "mask.png")
        if not args.silent:
            print("Creating mask...")
        mask_result = create_mask(
            access_token=access_token,
            image_path=args.input,
            output_path=mask_path,
            debug=args.debug
        )
        if not mask_result:
            print("Failed to create mask")
            sys.exit(1)

        # Step 2: Invert mask using ImageMagick
        inverted_mask_path = os.path.join(temp_dir, "inverted_mask.png")
        if not args.silent:
            print("Inverting mask...")
        try:
            subprocess.run(['magick', mask_path, '-negate', inverted_mask_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error inverting mask: {str(e)}")
            sys.exit(1)

        def replace_bg_task(prompt, index):
            rate_limiter.acquire()
            # Use the output pattern with {var1} directly
            output_filename = args.output.replace("{var1}", str(index + 1))
            output_filename = get_unique_filename(output_filename, args.overwrite, args.debug)

            if not args.silent:
                print(f"Generating new background with prompt: {prompt}")
            
            fill_result = fill_image(
                access_token=access_token,
                image_path=args.input,
                mask_path=inverted_mask_path,
                prompt=prompt,
                num_variations=1,
                mask_invert=True,
                debug=args.debug
            )

            if not fill_result:
                print(f"Failed to generate new background for prompt: {prompt}")
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
                    print(f"No outputs found in response for prompt: {prompt}")
                    return False
            else:
                print(f"Failed to get result from job for prompt: {prompt}")
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
            for i, prompt in enumerate(prompts):
                current_generation += 1
                if not args.silent:
                    print(f"{current_generation:<4} {prompt[:40]:<40}")
                tasks.append(executor.submit(replace_bg_task, prompt, i))
            for future in concurrent.futures.as_completed(tasks):
                future.result()

    if not args.silent:
        print("\nAll background replacement tasks completed.")

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