# Firefly Services CLI

A command-line interface for Adobe Firefly Services, providing easy access to image generation, text-to-speech, dubbing, and transcription capabilities.

## Quick Installation

The easiest way to install the Firefly Services CLI is using the provided installation script:

```bash
# Make the install script executable
chmod +x install.sh

# Run the installation script
./install.sh
```

The installation script will:
1. Check for Python 3 installation
2. Create and activate a virtual environment
3. Install all required dependencies
4. Set up your environment file
5. Provide instructions for making the `ff` command available system-wide

## Manual Installation

If you prefer to install manually, follow these steps:

1. Ensure you have Python 3 installed
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment sample file and update it with your credentials:
   ```bash
   cp env_sample .env
   # Edit .env with your credentials
   ```

## Usage

After installation, you can use the CLI tool in two ways:

1. Using the full path:
   ```bash
   ./bin/ff [command] [options]
   ```

2. If you've added the bin directory to your PATH (as suggested during installation):
   ```bash
   ff [command] [options]
   ```

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

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
FIREFLY_SERVICES_CLIENT_ID=your_client_id
FIREFLY_SERVICES_CLIENT_SECRET=your_client_secret
```

## Azure Storage Configuration

The CLI uses Azure Blob Storage to temporarily store files that need to be referenced by the Firefly Services API. This is necessary because the API requires files to be accessible via a URL. The CLI uploads files to Azure Storage and then uses the resulting URLs in API calls.

To configure Azure Storage, add the following variables to your `.env` file:

```bash
AZURE_STORAGE_ACCOUNT=your_storage_account
AZURE_STORAGE_CONTAINER=your_container_name
AZURE_STORAGE_SAS_TOKEN=your_sas_token
```

### Getting a SAS Token

A SAS (Shared Access Signature) token is required to securely upload files to Azure Storage. Here's how to get one:

1. Go to the Azure Portal (https://portal.azure.com)
2. Navigate to your Storage Account
3. In the left menu, under "Security + networking", click on "Shared access signature"
4. Configure the following settings:
   - Allowed services: Blob
   - Allowed resource types: Container, Object
   - Allowed permissions: Read, Write, Delete, List
   - Start time: Current time
   - End time: Choose a future date (e.g., 1 year from now)
   - Allowed protocols: HTTPS only
5. Click "Generate SAS and connection string"
6. Copy the "SAS token" value (it starts with "?sv=")
7. Add it to your `.env` file as `AZURE_STORAGE_SAS_TOKEN`

The SAS token is used to:
- Securely upload input files (images, audio, video) to Azure Storage
- Make these files accessible to the Firefly Services API
- Allow the API to process files that are too large to be sent directly
- Enable processing of files that need to be referenced multiple times

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

#### Prompt Variations
You can include multiple options in your prompt using square brackets with comma-separated values. The CLI will generate all possible combinations of these variations.

Example:
```bash
ff image -p "a [cat,dog] in a [garden,forest]" -o output_{var1}_{var2}.jpg
```

This will generate 4 different images:
1. "a cat in a garden"
2. "a cat in a forest"
3. "a dog in a garden"
4. "a dog in a forest"

The variations will be reflected in the output filenames using the `{var1}`, `{var2}`, etc. tokens. You can use this syntax in any command that accepts a prompt, including image generation, expansion, and fill commands.

#### Model Variations
You can specify multiple model versions to generate images using different models. Use square brackets with comma-separated model names.

Example:
```bash
ff image -p "a cat in a garden" -m "[image3,image4_ultra]" -o output_{model}.jpg
```

This will generate 2 different images:
1. Using the Image 3 model
2. Using the Image 4 Ultra model

Available model versions:
- `image3`: Standard Image 3 model
- `image4`: Standard Image 4 model
- `image4_standard`: Standard Image 4 model (alias for image4)
- `image4_ultra`: Ultra Image 4 model
- `ultra`: Ultra Image 4 model (alias for image4_ultra)

The model version will be reflected in the output filename using the `{model}` token. You can combine model variations with prompt variations to generate images with all possible combinations.

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