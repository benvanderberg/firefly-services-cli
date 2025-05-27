# API Endpoints
TOKEN_URL = "https://ims-na1.adobe.io/ims/token/v3"
IMAGE_API_URL = "https://image-api.adobe.io/v1/generate"
SPEECH_API_URL = "https://audio-video-api.adobe.io/v1/tts"
DUB_API_URL = "https://audio-video-api.adobe.io/v1/dub"
VOICES_API_URL = "https://audio-video-api.adobe.io/v1/voices"
TRANSCRIBE_API_URL = "https://audio-video-api.adobe.io/v1/transcribe"

# Default settings
DEFAULT_MODEL_VERSION = "image3"
DEFAULT_CONTENT_CLASS = "photo"
DEFAULT_LOCALE = "en-US"
DEFAULT_OUTPUT_FORMAT = "mp4"

# Model versions
MODEL_VERSIONS = {
    "image3": "image3",
    "image4_standard": "image4_standard",
    "image4_ultra": "image4_ultra"
}

# Content classes
CONTENT_CLASSES = {
    "photo": "photo",
    "art": "art",
    "product": "product"
}

# Output formats
OUTPUT_FORMATS = {
    "mp4": "mp4",
    "mp3": "mp3"
}

# Job status polling
POLL_INTERVAL = 2  # seconds
MAX_RETRIES = 30  # maximum number of retries for job status polling 