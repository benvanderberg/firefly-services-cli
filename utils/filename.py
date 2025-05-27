import os
import re
from datetime import datetime, UTC
from itertools import product

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
        '3:4': '1792x2304',
        'ultrawide': '2688x1536',
        'wide': '2688x1536'
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
        '16:9': '2688x1536',
        'ultrawide': '2688x1536',
        'wide': '2688x1536'
    }
    
    if model_version == 'image3':
        return image3_sizes
    elif model_version in ['image4_standard', 'image4_ultra', 'image4']:
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
    print(f"Parsing size: {size_str} for model: {model_version}")  # Debug output
    
    # First check if it's a named size
    size_mapping = get_size_mapping(model_version)
    print(f"Available sizes: {list(size_mapping.keys())}")  # Debug output
    
    if size_str in size_mapping:
        size_str = size_mapping[size_str]
        print(f"Found named size: {size_str}")  # Debug output
    
    # Parse the dimensions
    try:
        if 'x' in size_str:
            width, height = map(int, size_str.split('x'))
            print(f"Parsed dimensions: {width}x{height}")  # Debug output
            return {'width': width, 'height': height}
        else:
            raise ValueError(f"Invalid size format. Must be either WIDTHxHEIGHT or one of the named sizes: {', '.join(size_mapping.keys())}")
    except ValueError as e:
        print(f"Error parsing size: {str(e)}")  # Debug output
        raise ValueError(f"Invalid size format. Must be either WIDTHxHEIGHT or one of the named sizes: {', '.join(size_mapping.keys())}")

def get_unique_filename(base_filename, overwrite=False):
    """
    Generate a unique filename, either by overwriting or adding a number suffix.
    Creates any necessary directories in the path.
    
    Args:
        base_filename (str): The original filename
        overwrite (bool): Whether to overwrite existing files
    
    Returns:
        str: The unique filename
    """
    # Create directory if it doesn't exist
    directory = os.path.dirname(base_filename)
    if directory:
        print(f"Creating directory: {directory}")  # Debug output
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"Directory created or already exists: {directory}")  # Debug output
        except Exception as e:
            print(f"Error creating directory {directory}: {str(e)}")  # Debug output
            raise
    
    if overwrite or not os.path.exists(base_filename):
        return base_filename
    
    # Split the filename into name and extension
    name, ext = os.path.splitext(base_filename)
    counter = 1
    
    # Keep trying new filenames until we find one that doesn't exist
    while True:
        new_filename = f"{name}_{counter}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1

def parse_prompt_variations(prompt):
    """
    Parse a prompt string containing variations in [option1,option2,...] format.
    
    Args:
        prompt (str): The prompt string containing variations
    
    Returns:
        tuple: (list of prompts, list of variation blocks)
    """
    # Find all variation blocks in the prompt
    variation_blocks = re.findall(r'\[(.*?)\]', prompt)
    if not variation_blocks:
        return [prompt], []
    
    # Split each block into options
    options = [block.split(',') for block in variation_blocks]
    
    # Generate all possible combinations
    combinations = list(product(*options))
    
    # Generate all possible prompts
    prompts = []
    for combo in combinations:
        current_prompt = prompt
        for i, value in enumerate(combo):
            # Replace the first occurrence of [options] with the current value
            current_prompt = re.sub(r'\[.*?\]', value.strip(), current_prompt, count=1)
        prompts.append(current_prompt)
    
    return prompts, variation_blocks

def replace_filename_tokens(filename, tokens):
    """
    Replace tokens in the filename with their corresponding values.
    
    Args:
        filename (str): The filename containing tokens
        tokens (dict): Dictionary of token values to replace
    
    Returns:
        str: Filename with tokens replaced
    """
    print(f"Replacing tokens in filename: {filename}")  # Debug output
    print(f"Available tokens: {tokens}")  # Debug output
    
    # Define token patterns and their replacements
    token_patterns = {
        '{prompt}': lambda t: t.get('prompt', '').replace(' ', '_')[:30],  # Limit prompt length
        '{date}': lambda t: datetime.now(UTC).strftime('%Y%m%d'),
        '{time}': lambda t: datetime.now(UTC).strftime('%H%M%S'),
        '{datetime}': lambda t: datetime.now(UTC).strftime('%Y%m%d_%H%M%S'),
        '{seed}': lambda t: '_'.join(map(str, t.get('seeds', []))) if t.get('seeds') else '',
        '{sr}': lambda t: os.path.splitext(os.path.basename(t.get('style_ref', '')))[0] if t.get('style_ref') else '',
        '{model}': lambda t: t.get('model', ''),
        '{width}': lambda t: str(t.get('size', {}).get('width', '')),
        '{height}': lambda t: str(t.get('size', {}).get('height', '')),
        '{dimensions}': lambda t: f"{t.get('size', {}).get('width', '')}x{t.get('size', {}).get('height', '')}" if t.get('size') else '',
        '{n}': lambda t: str(t.get('iteration', '')),  # Add iteration number token
    }
    
    # Add variation tokens
    for i, var in enumerate(tokens.get('variations', []), 1):
        token_patterns[f'{{var{i}}}'] = lambda t, v=var: v.replace(' ', '_')
    
    # Replace all tokens in the filename
    result = filename
    for pattern, replacement_func in token_patterns.items():
        if pattern in result:
            replacement = replacement_func(tokens)
            print(f"Replacing {pattern} with {replacement}")  # Debug output
            result = result.replace(pattern, replacement)
    
    print(f"Final filename: {result}")  # Debug output
    return result

def get_variation_filename(base_filename, prompt, original_prompt, tokens=None):
    """
    Generate a filename with variation values appended.
    
    Args:
        base_filename (str): The original filename
        prompt (str): The current prompt with variations replaced
        original_prompt (str): The original prompt with variation blocks
        tokens (dict): Additional tokens for filename replacement
    
    Returns:
        str: The filename with variation values appended
    """
    name, ext = os.path.splitext(base_filename)
    
    # Find all variation blocks in the original prompt
    variation_blocks = re.findall(r'\[(.*?)\]', original_prompt)
    
    # Extract the values used in this prompt
    variation_values = []
    for block in variation_blocks:
        options = block.split(',')
        for option in options:
            option = option.strip()
            if option in prompt:
                variation_values.append(option)
                break
    
    # Join variation values with underscores and remove any special characters
    variation_suffix = '_'.join(''.join(c for c in v if c.isalnum() or c.isspace()) for v in variation_values)
    
    # If we have tokens, replace them in the filename
    if tokens:
        # Add variations to tokens
        tokens['variations'] = variation_values
        # Replace tokens in the name
        name = replace_filename_tokens(name, tokens)
        
        # If model token is not in the filename, append it
        if '{model}' not in base_filename and tokens.get('model'):
            name = f"{name}_{tokens['model']}"
    
    return f"{name}_{variation_suffix}{ext}" 