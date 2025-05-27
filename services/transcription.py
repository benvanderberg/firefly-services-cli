import os
import requests

def transcribe_media(access_token, source_url, target_locale, content_type="video", text_only=False):
    """
    Transcribe audio or video content.
    
    Args:
        access_token (str): The authentication token
        source_url (str): URL of the source media file
        target_locale (str): Target language locale code (e.g., 'en-US')
        content_type (str): Type of content ('video' or 'audio')
        text_only (bool): Whether to return only the transcript text
    
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
        'source': {
            'url': source_url,
            'mediaType': content_type
        },
        'targetLocaleCode': target_locale,
        'output': {
            'format': 'text' if text_only else 'json'
        }
    }

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/transcribe',
        headers=headers,
        json=data
    )
    response.raise_for_status()
    return response.json() 