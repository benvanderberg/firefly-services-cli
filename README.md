# Adobe Firefly Services CLI

A command-line interface for Adobe Firefly Services, providing access to image generation, text-to-speech, dubbing, and transcription capabilities.

## Features

### Image Generation
- Generate images from text prompts
- Support for multiple model versions (Image 3, Image 4, Image 4 Ultra)
- Multiple variations and style references
- Customizable image dimensions and content classes
- Token-based output filenames with automatic directory creation
- **Rate-limited parallel image generation:** Generate multiple image variations in parallel, with automatic throttling to respect the `THROTTLE_LIMIT_FIREFLY` environment variable (default: 5 calls per 60 seconds).
- **Configurable throttle limit:** Set the maximum number of API calls per minute using the `THROTTLE_LIMIT_FIREFLY` variable in your `.env` file.

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

1. Clone the repository:
```bash
git clone https://github.com/yourusername/firefly-services-cli.git
cd firefly-services-cli
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file with your Adobe Firefly Services credentials:
```
FIREFLY_SERVICES_CLIENT_ID=your_client_id
FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
THROTTLE_LIMIT_FIREFLY=5  # Maximum number of image generation API calls per 60 seconds
```

## Usage

### Image Generation
```bash
# Basic image generation
ff.py image -prompt "a cute husky dog" -o output.jpg

# Multiple variations
ff.py image -prompt "a [cute,playful] husky dog" -o output.jpg

# Multiple models
ff.py image -prompt "a cute husky dog" -m "[image3,image4_ultra]" -o output.jpg

# Style reference
ff.py image -prompt "a cute husky dog" -sr style.jpg -o output.jpg

# Custom size
ff.py image -prompt "a cute husky dog" -s "2048x2048" -o output.jpg

# Token-based output path
ff.py image -prompt "a cute husky dog" -o "outputs/{model}/{var1}_{dimensions}_{sr}_{n}.jpg"

# Parallel generation with throttling (respects THROTTLE_LIMIT_FIREFLY)
ff.py image -prompt "a [cute,playful] husky dog" -o "outputs/{model}/{var1}_{n}.jpg" -n 4
```

### Text-to-Speech
```bash
# Basic text-to-speech
ff.py tts -t "Hello, world!" -v voice_id -o output.mp3

# From file
ff.py tts -f input.txt -v voice_id -o output.mp3

# Different locale
ff.py tts -t "Hello, world!" -v voice_id -l fr-FR -o output.mp3
```

### Dubbing
```bash
# Dub video
ff.py dub -i input.mp4 -l fr-FR -o output.mp4

# Dub audio
ff.py dub -i input.mp3 -l fr-FR -o output.mp3
```

### Transcription
```bash
# Transcribe video
ff.py transcribe -i input.mp4 -t video -o output.txt

# Transcribe audio with captions
ff.py transcribe -i input.mp3 -t audio -c -o output.srt

# Text-only output
ff.py transcribe -i input.mp4 -t video -text -o output.txt
```

## Output Filename Tokens

When using the `-o` option, you can use the following tokens in the filename:

- `{prompt}`: The text prompt (truncated to 30 chars)
- `{date}`: Current date (YYYYMMDD)
- `{time}`: Current time (HHMMSS)
- `{datetime}`: Current date and time (YYYYMMDD_HHMMSS)
- `{seed}`: Seed values used
- `{sr}`: Style reference filename (without extension)
- `{model}`: Model version used
- `{width}`: Image width
- `{height}`: Image height
- `{dimensions}`: Image dimensions (WIDTHxHEIGHT)
- `{n}`: Iteration number
- `{var1}`, `{var2}`, etc.: Variation values

Example:
```bash
ff.py image -prompt "a [cute,playful] husky dog" -o "outputs/{model}/{var1}_{dimensions}_{n}.jpg"
```

## Additional Options

### Debug Mode
Add `-d` or `--debug` to any command to see detailed request and response information.

### Silent Mode
Add `-silent` or `--silent` to minimize output messages.

### Overwrite Files
Add `-ow` or `--overwrite` to overwrite existing files instead of adding a number suffix.

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