import os
import requests

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