# Adobe Firefly Services CLI

A command-line interface for Adobe Firefly Services, supporting image generation, text-to-speech, media dubbing, and transcription capabilities.

## Prerequisites

- Python 3.x
- Adobe Firefly Services API credentials (Client ID and Client Secret)
- Azure Storage account and container

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file with your credentials:
```
FIREFLY_SERVICES_CLIENT_ID=your_client_id
FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
AZURE_STORAGE_CONNECTION_STRING=your_azure_storage_connection_string
AZURE_STORAGE_CONTAINER=your_azure_storage_container_name
```

## Available Commands

### Image Generation

Generate images using Adobe Firefly's image generation API.

```bash
python ff.py image -prompt "your prompt" -o output.jpg [options]
```

Options:
- `-prompt, --prompt`: Text prompt for image generation (required)
- `-o, --output`: Output file path (required)
- `-n, --number`: Number of images to generate (1-4, default: 1)
- `-m, --model`: Firefly model version to use
  - Choices: `image3`, `image3_custom`, `image4`, `image4_standard`, `image4_ultra`, `ultra`
  - Shorthand: `image4` = `image4_standard`, `ultra` = `image4_ultra`
  - Default: `image3`
- `-c, --content-class`: Type of content to generate
  - Choices: `photo`, `art`
  - Default: `photo`
- `-np, --negative-prompt`: Text describing what to avoid in the generation
- `-l, --locale`: Locale code for prompt biasing (e.g., en-US)
- `-s, --size`: Output size in format WIDTHxHEIGHT (e.g., 2048x2048) or named sizes:
  - For image3: square, square1024, landscape, portrait, widescreen, 7:4, 9:7, 7:9, 16:9, 1:1, 4:3, 3:4
  - For image4: square, landscape, portrait, widescreen, 9:16, 1:1, 4:3, 3:4, 16:9
- `--seeds`: Seed values for consistent generation (1-4 values)
- `-vi, --visual-intensity`: Visual intensity of the generated image (1-10)
- `-d, --debug`: Show debug information including full HTTP request details
- `-silent, --silent`: Minimize output messages (only shows final result)
- `-ow, --overwrite`: Overwrite existing files instead of adding number suffix

File Handling:
- If the output file already exists and `-ow` is not used, a number suffix will be added (e.g., `output_1.jpg`, `output_2.jpg`, etc.)
- If `-ow` is used, the existing file will be overwritten
- When generating multiple images (`-n > 1`), files are always numbered sequentially

Examples:
```bash
# Basic image generation
python ff.py image -prompt "a beautiful sunset over mountains" -o sunset.jpg

# Generate multiple images with specific model (using shorthand)
python ff.py image -prompt "a futuristic city" -o city.jpg -n 4 -m ultra

# Generate art with negative prompt and visual intensity
python ff.py image -prompt "a peaceful garden" -o garden.jpg -c art -np "no people, no buildings" -vi 8

# Generate image with specific size and seeds
python ff.py image -prompt "a mountain landscape" -o mountain.jpg -s landscape --seeds 12345 67890

# Generate image with minimal output
python ff.py image -prompt "a cute dog" -o dog.jpg -silent

# Generate image and overwrite if exists
python ff.py image -prompt "a cute dog" -o dog.jpg -ow
```

The command will display the model name in a user-friendly format:
- `image3` → "Firefly Image 3"
- `image4_standard` or `image4` → "Firefly Image 4"
- `image4_ultra` or `ultra` → "Firefly Image 4 Ultra"

### Text-to-Speech

Convert text to speech using Adobe's text-to-speech API. You can provide the text directly or from a file.

```bash
# Using direct text input
python ff.py tts -t "your text" -v "voice_id" -o output.wav [options]

# Using text from a file
python ff.py tts -f input.txt -v "voice_id" -o output.wav [options]
```

Options:
- `-t, --text`: Text to convert to speech (required if not using -f)
- `-f, --file`: Path to text file containing the content to convert to speech (required if not using -t)
- `-v, --voice`: Voice ID to use (required)
- `-o, --output`: Output file path (required, will be saved as WAV)
- `-l, --locale`: Locale code for the text
  - Default: `en-US`
- `-d, --debug`: Show debug information

Examples:
```bash
# Basic text-to-speech with direct text
python ff.py tts -t "Hello, this is a test" -v "v101_1" -o test.wav

# Text-to-speech from a file
python ff.py tts -f speech.txt -v "v101_1" -o test.wav

# Text-to-speech with different locale
python ff.py tts -f french.txt -v "v101_1" -o hello.wav -l "fr-FR"

# Text-to-speech with debug information
python ff.py tts -t "Hello world" -v "v101_1" -o test.wav -d
```

### List Available Voices

Get a list of all available voices for text-to-speech.

```bash
python ff.py voices
```

This command will display a table of available voices with their:
- ID
- Name
- Gender
- Style
- Type
- Status

Voices are sorted by status (Active first) and then by name.

### Media Dubbing

Dub audio or video content to a different language.

```bash
python ff.py dub -i "source_url" -l "target_locale" -o output.mp4 [options]
```

Options:
- `-i, --input`: URL of the source media file (required)
- `-l, --locale`: Target language locale code (e.g., fr-FR) (required)
- `-o, --output`: Output file path (required)
- `-f, --format`: Output format
  - Choices: `mp4`, `mp3`
  - Default: `mp4`

Examples:
```bash
# Dub video to French
python ff.py dub -i "https://example.com/video.mp4" -l "fr-FR" -o dubbed.mp4

# Dub audio to Spanish
python ff.py dub -i "https://example.com/audio.mp3" -l "es-ES" -o dubbed.mp3 -f mp3
```

### Transcribe Media

Transcribe audio or video content using Adobe's transcription service. The file will be automatically uploaded to Azure Storage and a presigned URL will be generated for the transcription service.

```bash
python ff.py transcribe -i <input_file> -t <media_type> -o <output_file> [options]
```

Options:
- `-i, --input`: Path to the media file to transcribe (required)
- `-t, --type`: Type of media (audio or video) (required)
- `-o, --output`: Path to save the transcription output (required)
- `-l, --locale`: Target language locale code (default: en-US)
- `-c, --captions`: Generate SRT captions
- `-text, --text-only`: Extract and save only the transcript text (without timestamps)
- `-d, --debug`: Show debug information

Supported media formats:
- Audio: mp3, wav, m4a, aac
- Video: mp4, mov, avi, mkv

Examples:
```bash
# Transcribe a video file with captions
python ff.py transcribe -i video.mp4 -t video -o transcript.json -l "en-US" -c

# Transcribe an audio file and save only the text
python ff.py transcribe -i audio.wav -t audio -o transcript.txt -l "fr-FR" -text

# Transcribe with debug information
python ff.py transcribe -i video.mp4 -t video -o transcript.json -d
```

The command will:
1. Upload the file to Azure Blob Storage
2. Generate a presigned URL valid for 1 hour
3. Submit the transcription job using the presigned URL
4. Poll for completion
5. Return the transcription results

If captions are requested, they will be generated in SRT format. When using `--text-only`, the output will be a plain text file with the transcript content.

## Error Handling

The CLI provides detailed error messages and, when using the debug flag (`-d`), shows:
- Full HTTP request details
- Response headers
- Response body
- Status codes

## Notes

- All generated files are downloaded to the specified output path
- For image generation, if multiple images are requested, they will be saved with numbered suffixes
- The API requires valid Adobe Firefly Services credentials
- Some features may require specific API access levels
- When using transcription with `--text-only`, the output will be formatted as paragraphs with double line breaks between segments 