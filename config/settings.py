import os

# API Endpoints
IMAGE_GENERATION_API_URL = "https://firefly-api.adobe.io/v3/images/generate"
SPEECH_API_URL = "https://firefly-api.adobe.io/v3/speech/generate"
DUBBING_API_URL = "https://firefly-api.adobe.io/v3/dubbing"
TRANSCRIPTION_API_URL = "https://firefly-api.adobe.io/v3/transcription"
VOICES_API_URL = "https://firefly-api.adobe.io/v3/voices"

# Model Versions
MODEL_VERSIONS = {
    'image3': 'image3',
    'image4': 'image4',
    'image4_standard': 'image4_standard',
    'image4_ultra': 'image4_ultra',
    'ultra': 'ultra'
}

# Content Classes
CONTENT_CLASSES = ['photo', 'art']

# Rate Limiting
RATE_LIMIT_REQUESTS = 10  # Number of requests
RATE_LIMIT_PERIOD = 60    # Time period in seconds

# Azure Storage Settings
AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
AZURE_STORAGE_CONTAINER = os.getenv('AZURE_STORAGE_CONTAINER')
AZURE_STORAGE_ACCOUNT = os.getenv('AZURE_STORAGE_ACCOUNT')
AZURE_STORAGE_KEY = os.getenv('AZURE_STORAGE_KEY')
AZURE_STORAGE_SAS_TOKEN = os.getenv('AZURE_STORAGE_SAS_TOKEN')
AZURE_STORAGE_BLOB_URL = os.getenv('AZURE_STORAGE_BLOB_URL')

# Default settings
DEFAULT_MODEL_VERSION = "image3"
DEFAULT_CONTENT_CLASS = "photo"
DEFAULT_LOCALE = "en-US"
DEFAULT_OUTPUT_FORMAT = "mp4"

# Output formats
OUTPUT_FORMATS = {
    "mp4": "mp4",
    "mp3": "mp3"
}

# Job status polling
POLL_INTERVAL = 2  # seconds
MAX_RETRIES = 30  # maximum number of retries for job status polling 