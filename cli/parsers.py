import argparse
from datetime import datetime, timedelta, UTC

def create_parser():
    """
    Create the main argument parser with all subcommands and their arguments.
    """
    parser = argparse.ArgumentParser(description='Adobe Firefly Services CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Image generation command
    image_parser = subparsers.add_parser('image', help='Generate images')
    image_parser.add_argument('-prompt', '--prompt', required=True, help='Text prompt for image generation. Use [option1,option2,...] for variations')
    image_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated image. Supports tokens: {prompt}, {date}, {time}, {datetime}, {seed}, {sr}, {model}, {width}, {height}, {dimensions}, {var1}, {var2}, {n}, etc.')
    image_parser.add_argument('-n', '--numVariations', type=int, default=1, choices=range(1, 5),
                            help='Number of variations to generate (1-4, default: 1)')
    image_parser.add_argument('-m', '--model', default='image3',
                            help='Firefly model version to use. Can be a single model or variations in [model1,model2,...] format. Choices: image3, image3_custom, image4, image4_standard, image4_ultra, ultra')
    image_parser.add_argument('-c', '--content-class', choices=['photo', 'art'], default='photo',
                            help='Type of content to generate (default: photo)')
    image_parser.add_argument('-np', '--negative-prompt', help='Text describing what to avoid in the generation')
    image_parser.add_argument('-l', '--locale', help='Locale code for prompt biasing (e.g., en-US)')
    image_parser.add_argument('-s', '--size', help='Output size (e.g., 2048x2048 or square, landscape, portrait, etc.)')
    image_parser.add_argument('--seeds', type=int, nargs='+', help='Seed values for consistent generation (1-4 values)')
    image_parser.add_argument('-d', '--debug', action='store_true',
                            help='Show debug information including full HTTP request details')
    image_parser.add_argument('-vi', '--visual-intensity', type=int, choices=range(1, 11),
                            help='Visual intensity of the generated image (1-10)')
    image_parser.add_argument('-silent', '--silent', action='store_true',
                            help='Minimize output messages')
    image_parser.add_argument('-ow', '--overwrite', action='store_true',
                            help='Overwrite existing files instead of adding number suffix')
    image_parser.add_argument('-sref', '--style-reference', help='Path to a style reference image file. Can be a single file or variations in [file1,file2,...] format.')
    image_parser.add_argument('-sref-strength', '--style-reference-strength', type=int, default=50, choices=range(1, 101), metavar='[1-100]', help='Strength of the style reference (1-100, default: 50)')
    image_parser.add_argument('-cref', '--composition-reference', help='Path to a composition reference image file. Can be a single file or variations in [file1,file2,...] format.')
    image_parser.add_argument('-cref-strength', '--composition-reference-strength', type=int, default=50, choices=range(1, 101), metavar='[1-100]', help='Strength of the composition reference (1-100, default: 50)')

    # Text-to-speech command
    tts_parser = subparsers.add_parser('tts', help='Generate text-to-speech')
    tts_parser.add_argument('-t', '--text', help='Text to convert to speech')
    tts_parser.add_argument('-f', '--file', help='Path to text file to convert to speech')
    tts_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated audio')
    tts_parser.add_argument('-v', '--voice', required=True, help='Voice ID to use for speech generation')
    tts_parser.add_argument('-l', '--locale', default='en-US', help='Locale code for the text (default: en-US)')
    tts_parser.add_argument('-d', '--debug', action='store_true',
                          help='Show debug information including full HTTP request details')
    tts_parser.add_argument('-silent', '--silent', action='store_true',
                          help='Minimize output messages')

    # Dubbing command
    dub_parser = subparsers.add_parser('dub', help='Dub audio or video content')
    dub_parser.add_argument('-i', '--input', required=True, help='URL of the source media file')
    dub_parser.add_argument('-o', '--output', required=True, help='Output file path for the dubbed media')
    dub_parser.add_argument('-l', '--locale', required=True, help='Target language locale code (e.g., fr-FR)')
    dub_parser.add_argument('-f', '--format', choices=['mp4', 'mp3'], default='mp4',
                          help='Output format (default: mp4)')
    dub_parser.add_argument('-d', '--debug', action='store_true',
                          help='Show debug information including full HTTP request details')
    dub_parser.add_argument('-silent', '--silent', action='store_true',
                          help='Minimize output messages')

    # List voices command
    voices_parser = subparsers.add_parser('voices', help='List available voices')

    # Transcription command
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio or video content')
    transcribe_parser.add_argument('-i', '--input', required=True, help='Path to the media file to transcribe')
    transcribe_parser.add_argument('-o', '--output', required=True, help='Output file path for the transcription')
    transcribe_parser.add_argument('-t', '--type', choices=['audio', 'video'], required=True,
                                help='Type of media to transcribe')
    transcribe_parser.add_argument('-l', '--locale', default='en-US',
                                help='Target language locale code (default: en-US)')
    transcribe_parser.add_argument('-c', '--captions', action='store_true',
                                help='Generate SRT captions')
    transcribe_parser.add_argument('-text', '--text-only', action='store_true',
                                help='Output only the transcript text without timestamps')
    transcribe_parser.add_argument('-d', '--debug', action='store_true',
                                help='Show debug information including full HTTP request details')
    transcribe_parser.add_argument('-silent', '--silent', action='store_true',
                                help='Minimize output messages')

    return parser 