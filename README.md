# ff - Adobe Firefly Services CLI

A command-line interface for Adobe Firefly Services, providing easy access to image generation, text-to-speech, dubbing, and transcription capabilities. 

## Why Use ff CLI?

The ff CLI tool streamlines your creative workflow by providing direct command-line access to Adobe's powerful Firefly Services. Whether you're a developer, content creator, or digital marketer, this tool eliminates the need to navigate through web interfaces or write complex API integrations.

**Key Benefits:**
- **Batch Processing**: Generate multiple images, convert text to speech, or transcribe audio files in bulk
- **Automation**: Integrate Adobe Firefly capabilities into your scripts, CI/CD pipelines, or automated workflows
- **Rapid Prototyping**: Quickly test ideas and generate content without leaving your terminal
- **Developer-Friendly**: Perfect for incorporating AI-generated content into applications, websites, or digital products
- **Time Efficiency**: Skip the web interface and generate content directly from your command line
- **Scriptable**: Combine with other command-line tools for powerful content generation pipelines

**Perfect for:**
- Content creators who need to generate multiple variations of images or audio
- Developers building applications that require AI-generated assets
- Marketing teams creating campaign materials at scale
- Researchers and experimenters exploring AI content generation
- Anyone who prefers command-line tools over web interfaces




## Quick Installation

The easiest way to install the ff CLI is using the provided installation script:

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
- **Background Replacement:** Replace image backgrounds with AI-generated content. This uses a combination of generating the mask, using Imagemagick to invert the mask, and then use Generative Fill to fill in the image.
- **Mask Generation:** Create masks for images with optional optimization and post-processing

### Text-to-Speech
- Convert text to speech using various voices
- Support for multiple languages and locales
- Input from text or file
- Customizable output format
- Paragraph splitting for long texts
- Voice and style variations
- Automatic directory creation for output files

### Dubbing
- Dub audio or video content to different languages
- Support for multiple output formats (MP4, MP3)
- Automatic media type detection

### Transcription
- Transcribe audio or video content
- Support for multiple languages
- Multiple output formats (text, markdown, PDF)
- Text-only output option
- Speaker identification
- Timestamp formatting

### CSV-Driven Batch Image Generation

You can generate images in batch using a CSV file. Use the `--csv-input` argument to specify the CSV file, and optionally `--subject` to inject a value into `{subject}` placeholders in your prompts, models, or output paths.

**Environment Variables:**
- `THROTTLE_LIMIT_FIREFLY`: Maximum concurrent requests (default: 5)
- `THROTTLE_PAUSE_SECONDS`: Delay between processing CSV rows in seconds (default: 0.5)
- `API_MAX_RETRIES`: Maximum retry attempts for server errors (default: 3)
- `API_RETRY_DELAY`: Base delay for retry backoff in seconds (default: 2.0)

**CSV Format:**
- The CSV must have columns: `Prompt` and `Output`. The `Model` column is optional.
- `Prompt`: The text prompt for image generation. Supports bracketed variations (e.g., `a [cat,dog] in a [garden,forest]`).
- `Model` (optional): The model to use. Can be a standard model, a custom model display name/assetId, or `{Model}` to use the CLI `-m/--model` value. If omitted or empty, the CLI `-m/--model` value is used.
- `Output`: The output file path. Supports tokens: `{subject}`, `{prompt}`, `{model}`, `{date}`, `{time}`, `{datetime}`, etc.

**Usage Examples:**
```bash
# Basic CSV batch generation
ff image --csv-input Prompts.csv --subject "Shantanu" -m "BOD - Shantanu Narayen"

# With custom throttling
export THROTTLE_LIMIT_FIREFLY=3
export THROTTLE_PAUSE_SECONDS=1.0
ff image --csv-input Prompts.csv --subject "Shantanu" -m "BOD - Shantanu Narayen"
```

**Features:**
- Bracketed prompt variations: `[option1,option2]` expands to all combinations.
- Model can be a standard model, custom model display name/assetId, or `{Model}`.
- Output filenames can use tokens: `{prompt}`, `{model}`, `{var1}`, `{var2}`, `{subject}`, etc.
- Full throttling and parallelism are supported.

**Troubleshooting:**
- If a custom model is not found, check the display name or assetId in the Firefly UI or with `ff cm-list`.
- If you see errors about missing columns, ensure your CSV has `Prompt`, `Model`, and `Output` headers.
- For debugging, use the `--debug` flag to see detailed output.

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

## Usage Examples

### Image Generation
Generate images using text prompts with various models and styles.

To create a basic image:
```bash
ff image -p "your prompt" -o output.jpg
```

This will generate an image using Firefly Image 4 and will include the 
```bash
ff image -p "a puppy on a giraffe" -m image4 -o "output_{model}.jpg" -s widescreen
```
Options:
- `-p, --prompt`: Your text description of the image
- `-m, --model`: Model version. Available options:
  - `image3`: Standard Image 3 model
  - `image4`: Standard Image 4 model
  - `image4_standard`: Standard Image 4 model (alias for image4)
  - `image4_ultra`: Ultra Image 4 model
  - `ultra`: Ultra Image 4 model (alias for image4_ultra)
- `-s, --size`: Image size. You can use either:
  - Preset names:
    - `square`: 1024x1024 (1:1 ratio)
    - `portrait`: 1024x1408 (3:4 ratio)
    - `landscape`: 1408x1024 (4:3 ratio)
    - `widescreen`: 1344x768 (16:9 ratio)
  - Custom dimensions in "WIDTHxHEIGHT" format (e.g., "1024x1024")
  - Supported dimensions:
    - Square (1:1): 1024x1024, 2048x2048
    - Portrait (3:4): 1024x1408, 1792x2304
    - Landscape (4:3): 1408x1024, 2304x1792
    - Widescreen (16:9): 1344x768, 2688x1536
    - Other ratios: 1152x896, 896x1152, 1216x832, 832x1216
- `-vi, --visual-intensity`: Control the overall intensity of image characteristics like contrast, shadows, and hue (1-10, where 1 is subtle and 10 is very intense)
- `-sref, --style-reference`: Path to a style reference image file that influences the artistic style of the generated image
- `-sref-strength, --style-reference-strength`: How strongly the style reference affects the output (1-100, default: 50)
- `-cref, --composition-reference`: Path to a composition reference image that influences the structure and layout
- `-cref-strength, --composition-reference-strength`: How strongly the composition reference affects the output (1-100, default: 50)
- `-n, --numVariations`: Number of variations (1-4)
- `-o, --output`: Where to save the image

Examples with reference images and intensity:
```bash
# Generate with high visual intensity
ff image -p "a futuristic city" -vi 9 -o city.jpg

# Use a style reference image
ff image -p "a portrait" -sref style_photo.jpg -sref-strength 75 -o portrait.jpg

# Use both style and composition references
ff image -p "a landscape" -sref art_style.jpg -sref-strength 60 -cref composition.jpg -cref-strength 80 -o landscape.jpg
```

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

The variations will be reflected in the output filenames using the `{var1}`, `{var2}`, etc. tokens.

#### Model Variations
You can specify multiple model versions to generate images using different models. Use square brackets with comma-separated model names.

Example:
```bash
ff image -p "a cat in a garden" -m "[image3,image4_ultra]" -o output_{model}.jpg
```

Available model versions:
- `image3`: Standard Image 3 model
- `image4`: Standard Image 4 model
- `image4_standard`: Standard Image 4 model (alias for image4)
- `image4_ultra`: Ultra Image 4 model
- `ultra`: Ultra Image 4 model (alias for image4_ultra)

### Background Replacement
Replace image backgrounds with AI-generated content.

#### Background Replacement
Replace image backgrounds:
```bash
ff replace-bg -i input.jpg -p "a cosmic nebula" -o output.jpg
```

Examples with variations and tokens:
```bash
# Generate multiple background variations
ff replace-bg -i portrait.jpg -p "a [sunset,sunrise,moonlit] [beach,mountain,forest]" -o bg_{var1}_{var2}.jpg

# Process multiple files with wildcards and use input filename token
ff replace-bg -i "photos/*.jpg" -p "a professional studio background" -o "processed/studio_{input_filename}.jpg"

# Use date/time tokens for organization
ff replace-bg -i selfie.jpg -p "a [modern office,cozy cafe,outdoor garden]" -o "backgrounds/{date}/{input_filename}_{var1}_{time}.jpg"

# Combine multiple tokens
ff replace-bg -i "portraits/*.jpg" -p "a [blue,green,purple] gradient background" -o "output/{input_filename}_bg_{var1}_{datetime}.jpg"
```

Options:
- `-i, --input`: Input image file or pattern (supports wildcards, must be quoted)
- `-p, --prompt`: Background prompt with optional variations in [option1,option2] format
- `-o, --output`: Output file path with tokens:
  - `{var1}`, `{var2}`: Variation numbers from prompt variations
  - `{input_filename}`: Original input filename without extension
  - `{date}`: Current date (YYYY-MM-DD)
  - `{time}`: Current time (HH-MM-SS)
  - `{datetime}`: Current date and time (YYYY-MM-DD_HH-MM-SS)
- `-d, --debug`: Enable debug output

Note: When using wildcards in the input pattern, make sure to quote the pattern (e.g., `"photos/*.jpg"`) to prevent shell expansion.

### Generative Fill
Fill masked areas in images:
```bash
ff fill -i input.jpg -m mask.jpg -p "your prompt" -o output.jpg
```

Examples with variations and tokens:
```bash
# Generate multiple fill variations
ff fill -i photo.jpg -m mask.png -p "a [red,blue,green] [sports car,motorcycle,bicycle]" -o "filled_{var1}_{var2}.jpg"

# Process multiple images with the same mask
ff fill -i "photos/*.jpg" -m universal_mask.png -p "a beautiful garden with flowers" -o "filled/{input_filename}_garden_{datetime}.jpg"

# Use different masks for different effects
ff fill -i portrait.jpg -m "[face_mask.png,background_mask.png]" -p "a [happy,serious,surprised] expression" -o "expressions/{input_filename}_{var1}_{var2}_{time}.jpg"

# Batch process with organized output
ff fill -i "originals/*.jpg" -m "masks/{input_filename}_mask.png" -p "a [sunny,cloudy,starry] sky" -o "results/{date}/{input_filename}_sky_{var1}.jpg"

# Combine with visual intensity for different effects
ff fill -i base.jpg -m area_mask.png -p "a magical forest" -vi 8 -o "magic_{datetime}.jpg"
```

Options:
- `-i, --input`: Input image file or pattern (supports wildcards, must be quoted)
- `-m, --mask`: Mask image file that defines areas to fill (white areas will be filled, black areas preserved)
- `-p, --prompt`: Fill prompt with optional variations in [option1,option2] format
- `-o, --output`: Output file path with tokens:
  - `{var1}`, `{var2}`: Variation numbers from prompt variations
  - `{input_filename}`: Original input filename without extension
  - `{date}`: Current date (YYYY-MM-DD)
  - `{time}`: Current time (HH-MM-SS)
  - `{datetime}`: Current date and time (YYYY-MM-DD_HH-MM-SS)
- `-vi, --visual-intensity`: Control intensity of the fill effect (1-10)
- `--mask-invert`: Invert the mask before use (fill black areas instead of white)
- `-d, --debug`: Enable debug output

Note: Mask images should have white areas where you want to fill content and black areas where you want to preserve the original image.

### Image Expansion
Expand images beyond their original boundaries.

```bash
ff expand -i input.jpg -p "your prompt" -o output.jpg
```

Options:
- `-i, --input`: Input image file
- `-p, --prompt`: Expansion prompt
- `-o, --output`: Output file path
- `-m, --mask`: Optional mask file
- `--mask-invert`: Invert the mask before use
- `-d, --debug`: Enable debug output

### Mask Generation
Create masks for images.

```bash
ff mask -i input.jpg -o mask.png
```

Options:
- `-i, --input`: Input image file
- `-o, --output`: Output mask file
- `--optimize`: Optimize the mask
- `--no-postprocess`: Disable post-processing
- `--mask-format`: Mask format (default: png)
- `-d, --debug`: Enable debug output

### Text-to-Speech
Convert text to speech using various voices and styles.

```bash
ff tts -f input.txt -v "[John,Maria]" -vs "[Casual,Happy]" -o "outputs/speech_{voice_name}_{voice_style}.mp3"
```

Options:
- `-f, --file`: Input text file
- `-t, --text`: Direct text input- `-v, --voice`: Voice names (comma-separated)
- `-vs, --voice-style`: Voice styles (comma-separated)
- `-o, --output`: Output file path with tokens
- `-l, --locale`: Locale code (e.g., "en-US")
- `--p-split`: Split text file into paragraphs
- `-d, --debug`: Enable debug output

### Dubbing
Dub media files to different languages.

```bash
ff dub -i input.mp4 -l "es-ES" -o output.mp4
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
ff transcribe -i input.mp4 -l "en-US" -o output.txt
```

Options:
- `-i, --input`: Input media file
- `-l, --locale`: Target locale code
- `-t, --type`: Media type (audio/video)
- `--text-only`: Return only transcript text
- `--output-type`: Output format (text/markdown/pdf)
- `-o, --output`: Output file path
- `-d, --debug`: Enable debug output

### List Available Voices
List all available voices for text-to-speech.

```bash
ff voices
```

### List Custom Models
List all available custom models for your Firefly credentials.

```bash
ff cm-list
```

- Outputs a pretty table (using Rich) with the most important fields.
- Use `--csv` to output **all fields** from the API response for scripting or analysis:

```bash
ff cm-list --csv
```

- You can search for custom models by display name or assetId using the `-m` flag in `ff image` (see below).
- The CLI supports partial/fuzzy matching for display names (case-insensitive, partial match allowed).

### Using Custom Models with Image Generation

You can use a custom model by its display name or assetId with the `-m`/`--model` flag:

```bash
# By display name (case-insensitive, partial match allowed)
ff image -p "shantanu eating a sandwich in a cafe" -o shantanu.jpg -m "BOD - Shantanu Narayen"

# By assetId (exact match)
ff image -p "shantanu eating a sandwich in a cafe" -o shantanu.jpg -m "urn:aaid:sc:VA6C2:0091660b-2d76-4394-b884-811474f69634"
```

- If you specify a standard model (e.g., `image3`, `image4`), the CLI uses the standard Firefly model.
- If you specify a custom model (by display name or assetId), the CLI will:
  - Look up the custom model using the Firefly Custom Models API.
  - If found, use the correct API headers and body:
    - Sets `x-model-version: image4_custom` in the request header
    - Adds `"customModelId": "{assetId}"` to the request body
  - If not found, prints an error and exits.
- If you use `--csv` with `ff cm-list`, all fields from the API are included in the CSV output.

#### Troubleshooting Custom Models
- If you get an error about a custom model not being found, check the spelling or try using the assetId directly.
- If multiple custom models have similar names, the CLI will use the first partial match it finds (case-insensitive).
- For best results, use the full display name or assetId.

## Common Features

### Output Filename Tokens
The following tokens can be used in output filenames:
- `{var1}`, `{var2}`, etc.: Variation numbers
- `{model}`: Model version
- `{size}`: Image size (e.g., "1024x1024")
- `{width}`: Image width
- `{height}`: Image height
- `{dimensions}`: Image dimensions (WxH)
- `{voice_name}`: Voice name
- `{voice_style}`: Voice style
- `{voice_id}`: Voice ID
- `{locale_code}`: Locale code
- `{date}`: Current date (YYYY-MM-DD)
- `{time}`: Current time (HH-MM-SS)
- `{datetime}`: Current date and time (YYYY-MM-DD_HH-MM-SS)
- `{para_num}`: Paragraph number (when using --p-split)
- `{total_paras}`: Total number of paragraphs
- `{sentence_num}`: Sentence number (when splitting paragraphs)
- `{total_sentences}`: Total number of sentences
- `{char_count}`: Character count

### Debug Mode
Add `-d` or `--debug` to any command to enable detailed debug output, including:
- API request/response details
- File operations
- Job status updates
- Rate limiting information

### Silent Mode
Add `-s` or `--silent` to minimize output:
```bash
ff image -p "sunset" -s
```

### Overwrite Protection

By default, the CLI will not overwrite existing files. Use `--overwrite` to allow overwriting of existing files:
```bash
ff image -p "sunset" -o existing_file.jpg --overwrite
```

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

## Getting Help

- List all available voices:
  ```bash
  ff voices
  ```
- Get help on any command:
  ```bash
  ff image --help
  ```

## Troubleshooting

1. **Command not found**
   - Make sure you've added the bin directory to your PATH
   - Try using the full path: `./bin/ff [command]`

2. **Authentication errors**
   - Check your `.env` file for correct credentials
   - Ensure your Adobe Firefly Services account is active

3. **File upload errors**
   - Verify your Azure Storage configuration
   - Check if your SAS token is still valid

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.