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