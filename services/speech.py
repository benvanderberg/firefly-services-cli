import os
import requests

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

def get_available_avatars(access_token):
    """
    Get the list of available avatars.
    
    Args:
        access_token (str): The authentication token
    
    Returns:
        list: List of available avatars
    """
    headers = {
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get('https://audio-video-api.adobe.io/v1/avatars', headers=headers)
    response.raise_for_status()
    avatars_data = response.json()
    
    # Check if we have a valid response structure
    if not isinstance(avatars_data, dict) or 'avatars' not in avatars_data:
        print("\nError: Unexpected API response format")
        return []
        
    return avatars_data['avatars']

def parse_voice_variations(voice_input, debug=False):
    """
    Parse voice variations from input string.
    
    Args:
        voice_input (str): Voice input string in [value1,value2,...] format
        debug (bool): Whether to print debug information
    
    Returns:
        list: List of voice values
    """
    if not voice_input:
        return []
        
    # Remove brackets and split by comma
    if voice_input.startswith('[') and voice_input.endswith(']'):
        voice_input = voice_input[1:-1]
    
    voices = [v.strip() for v in voice_input.split(',')]
    
    if debug:
        print(f"Parsed voice variations: {voices}")
    
    return voices

def get_voice_id_by_name(access_token, voice_name, voice_style=None):
    """
    Get the voice ID for a given voice name and style.
    
    Args:
        access_token (str): The authentication token
        voice_name (str): The name of the voice to look up
        voice_style (str): The style of the voice (Casual or Happy)
    
    Returns:
        str: The voice ID if found, None otherwise
    """
    voices = get_available_voices(access_token)
    for voice in voices:
        if (voice.get('displayName', '').lower() == voice_name.lower() and 
            (voice_style is None or voice.get('style', '') == voice_style)):
            return voice.get('voiceId')
    return None

def get_avatar_id_by_name(access_token, avatar_name, avatar_style=None):
    """
    Get the avatar ID for a given avatar name and style.
    
    Args:
        access_token (str): The authentication token
        avatar_name (str): The name of the avatar to look up
        avatar_style (str): The style of the avatar
    
    Returns:
        str: The avatar ID if found, None otherwise
    """
    avatars = get_available_avatars(access_token)
    for avatar in avatars:
        if (avatar.get('displayName', '').lower() == avatar_name.lower() and 
            (avatar_style is None or avatar.get('style', '') == avatar_style)):
            return avatar.get('avatarId')
    return None

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
            'mediaType': 'audio/mp3'
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

def generate_avatar(access_token, text, voice_id, avatar_id, locale_code="en-US", debug=False):
    """
    Generate avatar video with speech using the specified voice and avatar.
    
    Args:
        access_token (str): The authentication token
        text (str): The text for the avatar to speak
        voice_id (str): The ID of the voice to use
        avatar_id (str): The ID of the avatar to use
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
        'avatarId': avatar_id,
        'output': {
            'mediaType': 'video/mp4'
        }
    }

    if debug:
        print("\nDebug Information:")
        print("URL:", 'https://audio-video-api.adobe.io/v1/generate-avatar')
        print("Headers:", headers)
        print("Request Body:", data)

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/generate-avatar',
        headers=headers,
        json=data
    )
    
    if debug:
        print("\nResponse Status:", response.status_code)
        print("Response Headers:", dict(response.headers))
        print("Response Body:", response.text)
    
    response.raise_for_status()
    return response.json() 