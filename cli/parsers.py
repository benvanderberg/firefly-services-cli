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

    # Avatar generation command
    avatar_parser = subparsers.add_parser('avatar', help='Generate avatar video with speech')
    avatar_parser.add_argument('-t', '--text', help='Text for the avatar to speak')
    avatar_parser.add_argument('-f', '--file', help='Path to text file for the avatar to speak')
    avatar_parser.add_argument('-o', '--output', required=True, help='Output file path for the generated video')
    avatar_parser.add_argument('-v', '--voice', help='Voice name to use. Can be a single name or a list in [name1,name2,...] format')
    avatar_parser.add_argument('-vid', '--voice-id', help='Voice ID to use. Can be a single ID or a list in [id1,id2,...] format')
    avatar_parser.add_argument('-a', '--avatar', help='Avatar name to use. Can be a single name or a list in [name1,name2,...] format')
    avatar_parser.add_argument('-aid', '--avatar-id', help='Avatar ID to use. Can be a single ID or a list in [id1,id2,...] format')
    avatar_parser.add_argument('-l', '--locale', default='en-US', help='Locale code for the text (default: en-US)')
    avatar_parser.add_argument('--p-split', action='store_true', help='Split text file into paragraphs and process each separately')
    avatar_parser.add_argument('-d', '--debug', action='store_true',
                          help='Show debug information including full HTTP request details')
    avatar_parser.add_argument('-silent', '--silent', action='store_true',
                          help='Minimize output messages')
    avatar_parser.add_argument('-ow', '--overwrite', action='store_true',
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

    # List avatars command
    avatar_list_parser = subparsers.add_parser('avatar-list', aliases=['al'], help='List available avatars/voices')

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
    video_parser.add_argument('--firstFrame', help='Path to first frame reference image')
    video_parser.add_argument('--lastFrame', help='Path to last frame reference image')
    video_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    video_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')
    video_parser.add_argument('-ow', '--overwrite', action='store_true', help='Overwrite existing files')

    # List custom models command
    models_parser = subparsers.add_parser('models', aliases=['cm-list', 'ml'], help='List custom models')
    models_parser.add_argument('--csv', action='store_true', help='Output as CSV instead of table')
    models_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information including full API response')

    # PDF upload command
    pdf_upload_parser = subparsers.add_parser('pdfupload', help='Upload a PDF file to Adobe PDF Services')
    pdf_upload_parser.add_argument('-f', '--file', required=True, help='Path to the PDF file to upload')
    pdf_upload_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    pdf_upload_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')

    # PDF conversion command
    pdf_parser = subparsers.add_parser('pdf', help='Convert, export, compress, OCR, linearize, auto-tag, or watermark PDF files using Adobe PDF Services')
    pdf_parser.add_argument('--export', action='store_true', help='Export PDF to another format (instead of converting to PDF)')
    pdf_parser.add_argument('--compress', action='store_true', help='Compress PDF file (instead of converting to PDF)')
    pdf_parser.add_argument('--ocr', action='store_true', help='Perform OCR on PDF file (instead of converting to PDF)')
    pdf_parser.add_argument('--linearize', action='store_true', help='Linearize PDF file for web optimization (instead of converting to PDF)')
    pdf_parser.add_argument('--autotag', action='store_true', help='Auto-tag PDF for accessibility (instead of converting to PDF)')
    pdf_parser.add_argument('--watermark', '--wm', action='store_true', help='Add watermark to PDF (instead of converting to PDF)')
    pdf_parser.add_argument('--protect', action='store_true', help='Protect PDF with password and encryption (instead of converting to PDF)')
    pdf_parser.add_argument('-opw', '--owner-password', required=False, help='Owner password for PDF protection')
    pdf_parser.add_argument('-upw', '--user-password', required=False, help='User password for PDF protection')
    pdf_parser.add_argument('--encryption-algorithm', choices=['AES_256', 'AES_128'], default='AES_256', help='Encryption algorithm (default: AES_256)')
    pdf_parser.add_argument('--content-to-encrypt', choices=['ALL_CONTENT', 'ALL_CONTENT_EXCEPT_METADATA', 'ONLY_EMBEDDED_FILES'], default='ALL_CONTENT', help='Content to encrypt (default: ALL_CONTENT)')
    pdf_parser.add_argument('--permissions', nargs='+', choices=['PRINT_LOW_QUALITY', 'PRINT_HIGH_QUALITY', 'EDIT_CONTENT', 'EDIT_FILL_AND_SIGN_FORM_FIELDS', 'EDIT_ANNOTATIONS', 'EDIT_DOCUMENT_ASSEMBLY', 'COPY_CONTENT'], help='Permissions to allow (can specify multiple)')
    pdf_parser.add_argument('--shiftHeadings', action='store_true', help='Shift headings when auto-tagging PDF')
    pdf_parser.add_argument('--generateReport', action='store_true', help='Generate Excel report when auto-tagging PDF')
    pdf_parser.add_argument('-w', '--watermark-file', help='Path to the watermark PDF file')
    pdf_parser.add_argument('--appearOnForeground', action='store_true', default=True, help='Show watermark on foreground (default: True)')
    pdf_parser.add_argument('--opacity', type=int, default=50, help='Watermark opacity percentage (default: 50)')
    pdf_parser.add_argument('-i', '--input', required=True, help='Path to the input file to convert')
    pdf_parser.add_argument('-o', '--output', required=True, help='Path to the output file')
    pdf_parser.add_argument('--ocrLang', default='en-US', 
                          choices=['da-DK', 'lt-LT', 'sl-SI', 'el-GR', 'ru-RU', 'en-US', 'zh-HK', 'hu-HU', 'et-EE', 
                                  'pt-BR', 'uk-UA', 'nb-NO', 'pl-PL', 'lv-LV', 'fi-FI', 'ja-JP', 'es-ES', 'bg-BG', 
                                  'en-GB', 'cs-CZ', 'mt-MT', 'de-DE', 'hr-HR', 'sk-SK', 'sr-SR', 'ca-CA', 'mk-MK', 
                                  'ko-KR', 'de-CH', 'nl-NL', 'zh-CN', 'sv-SE', 'it-IT', 'no-NO', 'tr-TR', 'fr-FR', 
                                  'ro-RO', 'iw-IL'],
                          help='OCR language for PDF export/OCR (default: en-US)')
    pdf_parser.add_argument('--ocrType', default='searchable_image',
                          choices=['searchable_image', 'searchable_image_exact'],
                          help='OCR type for PDF OCR (default: searchable_image)')
    pdf_parser.add_argument('--compressionLevel', default='MEDIUM', 
                          choices=['LOW', 'MEDIUM', 'HIGH', 'low', 'medium', 'high'],
                          help='Compression level for PDF compression (default: MEDIUM)')
    pdf_parser.add_argument('-d', '--debug', action='store_true', help='Show debug information')
    pdf_parser.add_argument('-silent', '--silent', action='store_true', help='Minimize output messages')

    return parser 