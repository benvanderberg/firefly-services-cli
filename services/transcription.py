import os
import requests
import json

def transcribe_media(access_token, source_url, target_locale, content_type="video", text_only=False, debug=False):
    """
    Transcribe audio or video content.
    
    Args:
        access_token (str): The authentication token
        source_url (str): URL of the source media file
        target_locale (str): Target language locale code (e.g., 'en-US')
        content_type (str): Type of content ('video' or 'audio')
        text_only (bool): Whether to return only the transcript text
        debug (bool): Whether to show debug information
    
    Returns:
        dict: The job information including jobId and statusUrl
    """
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': os.environ['FIREFLY_SERVICES_CLIENT_ID'],
        'Authorization': f'Bearer {access_token}'
    }
    
    # Determine media type based on content_type and file extension
    if content_type == "video":
        media_type = "video/mp4"
    else:
        # For audio, determine the type based on file extension
        if source_url.lower().endswith('.mp3'):
            media_type = "audio/mp3"
        elif source_url.lower().endswith('.wav'):
            media_type = "audio/wav"
        else:
            media_type = "audio/mp3"  # default to mp3
    
    # Construct request body based on content type
    if content_type == "video":
        data = {
            "video": {
                "source": {
                    "url": source_url
                },
                "mediaType": media_type
            },
            "targetLocaleCodes": [target_locale]
        }
    else:
        data = {
            "audio": {
                "source": {
                    "url": source_url
                },
                "mediaType": media_type
            },
            "targetLocaleCodes": [target_locale]
        }

    if debug:
        print("\nAPI Request Details:")
        print("URL:", 'https://audio-video-api.adobe.io/v1/transcribe')
        print("Headers:", json.dumps(headers, indent=2))
        print("Request Body:", json.dumps(data, indent=2))

    response = requests.post(
        'https://audio-video-api.adobe.io/v1/transcribe',
        headers=headers,
        json=data
    )
    
    if debug:
        print("\nAPI Response Details:")
        print("Status Code:", response.status_code)
        print("Response Headers:", json.dumps(dict(response.headers), indent=2))
        try:
            print("Response Body:", json.dumps(response.json(), indent=2))
        except:
            print("Response Body:", response.text)
    
    response.raise_for_status()
    return response.json() 