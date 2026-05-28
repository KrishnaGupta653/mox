"""
Mox Music System - Modern CLI Music Player
Main entry point for terminal-based music control
"""

import argparse
import sys
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Mox Music System - Terminal Music Player",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mox play "song.mp3"           Play a specific file
  mox play --queue              Add to queue
  mox pause                     Pause playback
  mox next                      Next track
  mox search "artist name"      Search for music
  mox ui                        Launch web UI
  mox plugin list               List installed plugins
        """
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["play", "pause", "resume", "stop", "next", "prev", 
                 "search", "queue", "ui", "plugin", "share", "schedule"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "args",
        nargs="*",
        help="Command arguments"
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port (default: 8080)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Import command handlers
    from src.server.commands import CommandHandler
    
    handler = CommandHandler(verbose=args.verbose)
    
    try:
        if args.command == "play":
            result = handler.play(args.args, add_to_queue="--queue" in args.args)
        elif args.command == "pause":
            result = handler.pause()
        elif args.command == "resume":
            result = handler.resume()
        elif args.command == "stop":
            result = handler.stop()
        elif args.command == "next":
            result = handler.next_track()
        elif args.command == "prev":
            result = handler.prev_track()
        elif args.command == "search":
            result = handler.search(" ".join(args.args))
        elif args.command == "queue":
            result = handler.show_queue()
        elif args.command == "ui":
            result = handler.launch_ui(host=args.host, port=args.port)
        elif args.command == "plugin":
            result = handler.plugin_command(args.args)
        elif args.command == "share":
            result = handler.share(args.args)
        elif args.command == "schedule":
            result = handler.schedule(args.args)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
        
        if result and args.verbose:
            print(result)
            
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
