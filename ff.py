#!/usr/bin/env python3

import sys
from cli.parsers import create_parser
from cli.commands import handle_command

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        handle_command(args)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
