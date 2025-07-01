import argparse

def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Adobe Firefly Services CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Common arguments
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument('--debug', action='store_true', help='Enable debug output')
    common_args.add_argument('--silent', action='store_true', help='Suppress output messages')

    # Image generation command
    image_parser = subparsers.add_parser('image', aliases=['img'], parents=[common_args], help='Generate images')
    image_parser.add_argument('--prompt', required=True, help='Text prompt for image generation')
    image_parser.add_argument('--model', default='image3', help='Model version to use')
    image_parser.add_argument('--content-class', default='photo', help='Content class for the image')
    image_parser.add_argument('--negative-prompt', help='Negative prompt to guide generation')
    image_parser.add_argument('--locale', default='en-US', help='Locale for prompt biasing')
    image_parser.add_argument('--size', help='Image size (e.g., "1024x1024")')
    image_parser.add_argument('--seeds', type=int, nargs='+', help='Seeds for generation')
    image_parser.add_argument('--numVariations', type=int, default=1, help='Number of variations to generate')
    image_parser.add_argument('--output', required=True, help='Output file path')
    image_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    image_parser.add_argument('--visual-intensity', type=int, help='Visual intensity (1-10)')
    image_parser.add_argument('--style-reference', help='Path to style reference image')
    image_parser.add_argument('--style-reference-strength', type=int, default=50, help='Style reference strength (1-100)')
    image_parser.add_argument('--composition-reference', help='Path to composition reference image')
    image_parser.add_argument('--composition-reference-strength', type=int, default=50, help='Composition reference strength (1-100)')

    # Text-to-speech command
    tts_parser = subparsers.add_parser('tts', aliases=['speech'], parents=[common_args], help='Generate speech from text')
    tts_parser.add_argument('--text', help='Text to convert to speech')
    tts_parser.add_argument('--file', help='File containing text to convert')
    tts_parser.add_argument('--voice', required=True, help='Voice ID to use')
    tts_parser.add_argument('--locale', default='en-US', help='Locale code for the text')
    tts_parser.add_argument('--output', required=True, help='Output file path')

    # Dubbing command
    dub_parser = subparsers.add_parser('dub', parents=[common_args], help='Dub audio or video content')
    dub_parser.add_argument('--input', required=True, help='Input file path')
    dub_parser.add_argument('--locale', required=True, help='Target language locale code')
    dub_parser.add_argument('--format', default='mp4', help='Output format (mp4 or mp3)')
    dub_parser.add_argument('--output', required=True, help='Output file path')

    # List voices command
    voices_parser = subparsers.add_parser('voices', aliases=['v'], parents=[common_args], help='List available voices')

    # List avatars command
    avatar_list_parser = subparsers.add_parser('avatar-list', aliases=['al'], parents=[common_args], help='List available avatars/voices')

    # Transcription command
    transcribe_parser = subparsers.add_parser('transcribe', aliases=['trans'], parents=[common_args], help='Transcribe audio or video content')
    transcribe_parser.add_argument('--input', required=True, help='Input file path')
    transcribe_parser.add_argument('--type', default='video', help='Content type (video or audio)')
    transcribe_parser.add_argument('--locale', default='en-US', help='Target language locale code')
    transcribe_parser.add_argument('--captions', action='store_true', help='Generate captions')
    transcribe_parser.add_argument('--text-only', action='store_true', help='Output only the transcript text')
    transcribe_parser.add_argument('--output', required=True, help='Output file path')

    # List custom models command
    models_parser = subparsers.add_parser('models', aliases=['cm-list', 'ml'], parents=[common_args], help='List custom models')
    models_parser.add_argument('--csv', action='store_true', help='Output as CSV instead of table')

    # Create custom model command
    create_model_parser = subparsers.add_parser('create-model', aliases=['cm-create', 'mc'], parents=[common_args], help='Create a custom model')
    create_model_parser.add_argument('--name', required=True, help='Name of the custom model')
    create_model_parser.add_argument('--description', required=True, help='Description of the custom model')
    create_model_parser.add_argument('--training-images', required=True, nargs='+', help='Paths to training images')
    create_model_parser.add_argument('--wait', action='store_true', help='Wait for model training to complete')

    # Delete custom model command
    delete_model_parser = subparsers.add_parser('delete-model', aliases=['cm-delete', 'md'], parents=[common_args], help='Delete a custom model')
    delete_model_parser.add_argument('--model-id', required=True, help='ID of the model to delete')

    # Get custom model status command
    model_status_parser = subparsers.add_parser('model-status', aliases=['cm-status', 'ms'], parents=[common_args], help='Get custom model status')
    model_status_parser.add_argument('--model-id', required=True, help='ID of the model to check')

    # Replace background command
    replace_bg_parser = subparsers.add_parser('replace-bg', parents=[common_args], help='Replace image background')
    replace_bg_parser.add_argument('-i', '--input', required=True, help='Input image file path')
    replace_bg_parser.add_argument('-p', '--prompt', required=True, help='Text prompt for new background')
    replace_bg_parser.add_argument('-o', '--output', required=True, help='Output file path')
    replace_bg_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')

    # Video generation command
    video_parser = subparsers.add_parser('video', parents=[common_args], help='Generate videos')
    video_parser.add_argument('-p', '--prompt', required=True, help='Text prompt for video generation')
    video_parser.add_argument('-s', '--size', required=True, help='Video size (e.g., "1080x1080", "1080p", "sq1080p")')
    video_parser.add_argument('-o', '--output', required=True, help='Output file path (.mp4)')
    video_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')

    return parser.parse_args() 