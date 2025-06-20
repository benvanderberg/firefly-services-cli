import argparse
from datetime import datetime, timedelta, UTC
from cli.commands import handle_mask_command

def create_parser():
    """
    Create the main argument parser with all subcommands and their arguments.
    """
    parser = argparse.ArgumentParser(description='ff - Adobe Firefly Services CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Image generation command
    image_parser = subparsers.add_parser('image', aliases=['img'], help='Generate images')
    image_parser.add_argument('-prompt', '--prompt', required=False, help='Text prompt for image generation. Use [option1,option2,...] for variations')
    image_parser.add_argument('-o', '--output', required=False, help='Output file path for the generated image. Supports tokens: {prompt}, {date}, {time}, {datetime}, {seed}, {sr}, {model}, {width}, {height}, {dimensions}, {var1}, {var2}, {n}, etc.')
    image_parser.add_argument('-n', '--numVariations', type=int, default=1, choices=range(1, 5),
                            help='Number of variations to generate (1-4, default: 1)')
    image_parser.add_argument('-m', '--model', default='image3',
                            help='Firefly model version to use. Can be a single model or variations in [model1,model2,...] format. Choices: image3, image4, image4_standard, image4_ultra, ultra')
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
    image_parser.add_argument('--csv-input', help='CSV file with columns Prompt,Model,Output for batch image generation')
    image_parser.add_argument('--subject', help='Value to inject for {subject} in CSV-driven batch image generation')
    # Add a custom validation function after parsing
    def image_command_validate(args):
        if not args.csv_input and (not args.prompt or not args.output):
            parser.error('You must provide either both -prompt/--prompt and -o/--output, or --csv-input.')
    image_parser.set_defaults(validate=image_command_validate)

    # Similar image generation command
    similar_parser = subparsers.add_parser('similar-image', aliases=['sim'], help='Generate similar images based on a reference image')
    similar_parser.add_argument('-i', '--input', required=True, help='Path to the reference image file')
    similar_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated image. Supports tokens: {date}, {time}, {datetime}, {seed}, {model}, {width}, {height}, {dimensions}, {n}, etc.')
    similar_parser.add_argument('-n', '--numVariations', type=int, default=1, choices=range(1, 5),
                            help='Number of variations to generate (1-4, default: 1)')
    similar_parser.add_argument('-m', '--model', default='image3',
                            help='Firefly model version to use. Can be a single model or variations in [model1,model2,...] format. Choices: image3, image4, image4_standard, image4_ultra, ultra')
    similar_parser.add_argument('-s', '--size', help='Output size (e.g., 2048x2048 or square, landscape, portrait, etc.)')
    similar_parser.add_argument('--seeds', type=int, nargs='+', help='Seed values for consistent generation (1-4 values)')
    similar_parser.add_argument('-d', '--debug', action='store_true',
                            help='Show debug information including full HTTP request details')
    similar_parser.add_argument('-silent', '--silent', action='store_true',
                            help='Minimize output messages')
    similar_parser.add_argument('-ow', '--overwrite', action='store_true',
                            help='Overwrite existing files instead of adding number suffix')

    # Expand image command
    expand_parser = subparsers.add_parser('expand', help='Generative Expand (outpaint) an image')
    expand_parser.add_argument('-i', '--input', required=True, help='Path to the input image file')
    expand_parser.add_argument('-o', '--output', required=True, help='Output file path for the expanded image')
    expand_parser.add_argument('-p', '--prompt', help='Prompt for the expansion')
    expand_parser.add_argument('--mask', help='Path to the mask image file (optional)')
    expand_parser.add_argument('--mask-invert', action='store_true', help='Invert the mask (only if --mask is set)')
    expand_parser.add_argument('-n', '--numVariations', type=int, default=1, choices=range(1, 5), help='Number of variations (1-4, default: 1)')
    expand_parser.add_argument('--align-h', choices=['center', 'left', 'right'], default='center', help='Horizontal alignment (default: center)')
    expand_parser.add_argument('--align-v', choices=['center', 'top', 'bottom'], default='center', help='Vertical alignment (default: center)')
    expand_parser.add_argument('--left', type=int, default=0, help='Inset left')
    expand_parser.add_argument('--right', type=int, default=0, help='Inset right')
    expand_parser.add_argument('--top', type=int, default=0, help='Inset top')
    expand_parser.add_argument('--bottom', type=int, default=0, help='Inset bottom')
    expand_parser.add_argument('--height', type=int, help='Output height in pixels')
    expand_parser.add_argument('--width', type=int, help='Output width in pixels')
    expand_parser.add_argument('--seeds', type=int, nargs='+', help='Seed values for consistent generation (1-4 values)')
    expand_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    expand_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')
    expand_parser.add_argument('-ow', '--overwrite', action='store_true', help='Overwrite existing files')

    # Fill image command
    fill_parser = subparsers.add_parser('fill', help='Generative Fill an image using a mask')
    fill_parser.add_argument('-i', '--input', required=True, help='Path to the input image file')
    fill_parser.add_argument('-o', '--output', required=True, help='Output file path for the filled image')
    fill_parser.add_argument('-m', '--mask', required=True, help='Path to the mask image file')
    fill_parser.add_argument('-p', '--prompt', help='Prompt for the fill')
    fill_parser.add_argument('-np', '--negative-prompt', help='Text describing what to avoid in the generation')
    fill_parser.add_argument('-l', '--locale', help='Locale code for prompt biasing (e.g., en-US)')
    fill_parser.add_argument('-n', '--numVariations', type=int, default=1, choices=range(1, 5), help='Number of variations (1-4, default: 1)')
    fill_parser.add_argument('--mask-invert', action='store_true', help='Invert the mask')
    fill_parser.add_argument('--height', type=int, help='Output height in pixels')
    fill_parser.add_argument('--width', type=int, help='Output width in pixels')
    fill_parser.add_argument('--seeds', type=int, nargs='+', help='Seed values for consistent generation (1-4 values)')
    fill_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    fill_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')
    fill_parser.add_argument('-ow', '--overwrite', action='store_true', help='Overwrite existing files')

    # Text-to-speech command
    tts_parser = subparsers.add_parser('tts', aliases=['speech'], help='Generate text-to-speech')
    tts_parser.add_argument('-t', '--text', help='Text to convert to speech')
    tts_parser.add_argument('-f', '--file', help='Path to text file to convert to speech')
    tts_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated audio')
    tts_parser.add_argument('-v', '--voice', help='Voice name to use for speech generation. Can be a single name or a list in [name1,name2,...] format')
    tts_parser.add_argument('-vid', '--voice-id', help='Voice ID to use for speech generation. Can be a single ID or a list in [id1,id2,...] format')
    tts_parser.add_argument('-vs', '--voice-style', help='Voice style to use (Casual or Happy). Required when using --voice. Can be a single style or a list in [style1,style2,...] format')
    tts_parser.add_argument('-l', '--locale', default='en-US', help='Locale code for the text (default: en-US)')
    tts_parser.add_argument('--p-split', action='store_true', help='Split text file into paragraphs and process each separately')
    tts_parser.add_argument('-d', '--debug', action='store_true',
                          help='Show debug information including full HTTP request details')
    tts_parser.add_argument('-silent', '--silent', action='store_true',
                          help='Minimize output messages')
    tts_parser.add_argument('-ow', '--overwrite', action='store_true',
                          help='Overwrite existing files instead of adding number suffix')

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
    voices_parser = subparsers.add_parser('voices', aliases=['v'], help='List available voices')

    # Transcription command
    transcribe_parser = subparsers.add_parser('transcribe', aliases=['trans'], help='Transcribe audio or video content')
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
    transcribe_parser.add_argument('--output-type', choices=['text', 'markdown', 'pdf'], default='text',
                                help='Output format (text, markdown, or pdf)')
    transcribe_parser.add_argument('-d', '--debug', action='store_true',
                                help='Show debug information including full HTTP request details')
    transcribe_parser.add_argument('-silent', '--silent', action='store_true',
                                help='Minimize output messages')

    # Mask creation command
    mask_parser = subparsers.add_parser('mask', help='Create a mask from an image')
    mask_parser.add_argument('-i', '--input', required=True, help='Input image file path')
    mask_parser.add_argument('-o', '--output', default='output.png', help='Output mask file path')
    mask_parser.add_argument('--optimize', choices=['performance', 'quality'], default='performance',
                           help='Optimization mode (default: performance)')
    mask_parser.add_argument('--no-postprocess', action='store_true',
                           help='Disable post-processing of the mask')
    mask_parser.add_argument('--service-version', default='4.0', help='Service version to use')
    mask_parser.add_argument('--mask-format', choices=['soft', 'hard'], default='soft',
                           help='Mask format (default: soft)')
    mask_parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
    mask_parser.add_argument('-ow', '--overwrite', action='store_true',
                           help='Overwrite existing files instead of adding number suffix')
    mask_parser.add_argument('--mask-invert', action='store_true', help='Invert the generated mask')
    mask_parser.set_defaults(func=handle_mask_command)

    # Replace background command
    replace_bg_parser = subparsers.add_parser('replace-bg', help='Replace image background')
    replace_bg_parser.add_argument('-i', '--input', required=True, help='Input image file path')
    replace_bg_parser.add_argument('-p', '--prompt', required=True, help='Text prompt for new background')
    replace_bg_parser.add_argument('-o', '--output', required=True, help='Output file path')
    replace_bg_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    replace_bg_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')
    replace_bg_parser.add_argument('-ow', '--overwrite', action='store_true', help='Overwrite existing files')

    # Video generation command
    video_parser = subparsers.add_parser('video', help='Generate videos')
    video_parser.add_argument('-p', '--prompt', required=True, help='Text prompt for video generation')
    video_parser.add_argument('-s', '--size', required=True, help='Video size (e.g., "1080x1080", "1080p", "sq1080p")')
    video_parser.add_argument('-o', '--output', required=True, help='Output file path (.mp4)')
    video_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    video_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')
    video_parser.add_argument('-ow', '--overwrite', action='store_true', help='Overwrite existing files')

    # List custom models command
    models_parser = subparsers.add_parser('models', aliases=['cm-list', 'ml'], help='List custom models')
    models_parser.add_argument('--csv', action='store_true', help='Output as CSV instead of table')
    models_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information including full API response')

    return parser 