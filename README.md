# Firefly Services CLI

A command-line interface for Adobe Firefly Services, providing easy access to image generation, text-to-speech, dubbing, and transcription capabilities.

## Features

### Image Generation
- Generate images from text prompts
- Support for multiple model versions (Image 3, Image 4, Image 4 Ultra)
- Multiple variations and style references
- Customizable image dimensions and content classes
- Token-based output filenames with automatic directory creation
- **Rate-limited parallel image generation:** Generate multiple image variations in parallel, with automatic throttling to respect the `THROTTLE_LIMIT_FIREFLY` environment variable (default: 5 calls per 60 seconds).
- **Configurable throttle limit:** Set the maximum number of API calls per minute using the `THROTTLE_LIMIT_FIREFLY` variable in your `.env` file.

### Image Editing
- **Generative Fill:** Fill masked areas in images with AI-generated content
- **Generative Expand:** Expand images beyond their original boundaries
- **Similar Image Generation:** Create variations of existing images

### Text-to-Speech
- Convert text to speech using various voices
- Support for multiple languages and locales
- Input from text or file
- Customizable output format

### Dubbing
- Dub audio or video content to different languages
- Support for multiple output formats (MP4, MP3)
- Automatic media type detection

### Transcription
- Transcribe audio or video content
- Support for multiple languages
- Optional SRT caption generation
- Text-only output option

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Mac Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/firefly-services-cli.git
cd firefly-services-cli
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Adobe credentials:
```bash
FIREFLY_SERVICES_CLIENT_ID=your_client_id
FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
THROTTLE_LIMIT_FIREFLY=5  # Optional: Set API rate limit (default: 5 calls per minute)
```

### Windows Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/firefly-services-cli.git
cd firefly-services-cli
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Adobe credentials:
```bash
FIREFLY_SERVICES_CLIENT_ID=your_client_id
FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
THROTTLE_LIMIT_FIREFLY=5  # Optional: Set API rate limit (default: 5 calls per minute)
```

## Usage

### Image Generation
Generate images using text prompts with various models and styles.

```bash
./ff.py image -p "your prompt" -o output.jpg
```

Options:
- `-p, --prompt`: Text prompt for image generation
- `-m, --model`: Model version (e.g., "firefly-2.0")
- `-s, --size`: Image size (e.g., "1024x1024")
- `-n, --numVariations`: Number of variations (1-4)
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

### Text-to-Speech
Convert text to speech using various voices and styles.

```bash
./ff.py tts -f input.txt -v "[John,Maria]" -vs "[Casual,Happy]" -o "outputs/speech_{voice_name}_{voice_style}.mp3"
```

Options:
- `-f, --file`: Input text file
- `-t, --text`: Direct text input
- `-v, --voice`: Voice names (comma-separated)
- `-vs, --voice-style`: Voice styles (comma-separated)
- `-o, --output`: Output file path with tokens
- `-l, --locale`: Locale code (e.g., "en-US")
- `-d, --debug`: Enable debug output

### Dubbing
Dub media files to different languages.

```bash
./ff.py dub -i input.mp4 -l "es-ES" -o output.mp4
```

Options:
- `-i, --input`: Input media file
- `-l, --locale`: Target locale code
- `-f, --format`: Output format
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

### Transcription
Transcribe media files to text.

```bash
./ff.py transcribe -i input.mp4 -l "en-US" -o output.txt
```

Options:
- `-i, --input`: Input media file
- `-l, --locale`: Target locale code
- `-t, --type`: Media type
- `-c, --captions`: Generate captions
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

### List Available Voices
List all available voices for text-to-speech.

```bash
./ff.py voices
```

Options:
- `-d, --debug`: Enable debug output

### Image Expansion
Expand images beyond their original boundaries.

```bash
./ff.py expand -i input.jpg -p "prompt" -o output.jpg
```

Options:
- `-i, --input`: Input image file
- `-p, --prompt`: Text prompt
- `-m, --mask`: Mask image file
- `-mi, --mask-invert`: Invert mask
- `-n, --numVariations`: Number of variations (1-4)
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

### Generative Fill
Fill masked areas in images.

```bash
./ff.py fill -i input.jpg -m mask.jpg -p "prompt" -o output.jpg
```

Options:
- `-i, --input`: Input image file
- `-m, --mask`: Mask image file
- `-p, --prompt`: Text prompt
- `-n, --numVariations`: Number of variations (1-4)
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

## Output File Tokens

The following tokens can be used in output filenames:

- `{date}`: Current date (YYYY-MM-DD)
- `{time}`: Current time (HH-MM-SS)
- `{datetime}`: Current date and time (YYYY-MM-DD_HH-MM-SS)
- `{voice_name}`: Voice name (for TTS)
- `{voice_style}`: Voice style (for TTS)
- `{voice_id}`: Voice ID (for TTS)
- `{locale_code}`: Locale code
- `{n}`: Variation number (for image generation)
- `{model}`: Model version
- `{size}`: Image size
- `{width}`: Image width
- `{height}`: Image height
- `{dimensions}`: Image dimensions (WxH)

## Rate Limiting

The CLI includes built-in rate limiting to prevent API throttling. The default rate limit is 5 calls per minute, but this can be adjusted by setting the `THROTTLE_LIMIT_FIREFLY` environment variable in your `.env` file.

## Debug Mode

Add the `-d` or `--debug` flag to any command to enable detailed debug output, including:
- API request/response details
- File operations
- Rate limiting information
- Error traces

## Directory Structure

```
firefly-services-cli/
├── ff.py                 # Main entry point
├── cli/
│   ├── commands.py      # Command handlers
│   └── parsers.py       # Argument parsers
├── services/
│   ├── image.py         # Image generation
│   ├── speech.py        # Text-to-speech
│   ├── dubbing.py       # Media dubbing
│   └── transcription.py # Media transcription
├── utils/
│   ├── auth.py          # Authentication
│   ├── filename.py      # Filename handling
│   └── storage.py       # Azure storage
└── config/
    └── settings.py      # Configuration settings
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 