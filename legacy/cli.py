#!/usr/bin/env python3
"""
Tencent Cloud StreamLink & StreamLive CLI

Usage:
    python cli.py <service> <command> [options]

Services:
    streamlink (sl)   - StreamLink service (media transport)
    streamlive (sv)   - StreamLive service (encoding/transcoding)

Examples:
    python cli.py sl list-regions
    python cli.py sl list-flows
    python cli.py sv list-channels
    python cli.py sv list-inputs
"""

import sys
import json
import argparse
from tencent_cloud_client import TencentCloudClient


def format_output(data):
    """Format output as JSON."""
    print(json.dumps(data, indent=2, ensure_ascii=False))


def streamlink_commands(client, args):
    """Handle StreamLink commands."""
    command = args.command

    if command == "list-regions":
        result = client.list_streamlink_regions()
        format_output(result)

    elif command == "list-flows":
        result = client.list_streamlink_inputs()
        format_output(result)

    elif command == "get-flow":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_streamlink_input_status(args.id)
        format_output({"flow_id": args.id, "status": result})

    elif command == "start-flow":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.start_streamlink_input(args.id)
        format_output(result)

    elif command == "stop-flow":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.stop_streamlink_input(args.id)
        format_output(result)

    elif command == "get-logs":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_streamlink_flow_logs(args.id)
        format_output(result)

    elif command == "get-status":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_streamlink_realtime_status(args.id)
        format_output(result)

    else:
        print(f"Unknown command: {command}")
        print_streamlink_help()
        sys.exit(1)


def streamlive_commands(client, args):
    """Handle StreamLive commands."""
    command = args.command

    if command == "list-regions":
        result = client.list_mdl_regions()
        format_output(result)

    elif command == "list-channels":
        result = client.list_mdl_channels()
        format_output(result)

    elif command == "list-inputs":
        result = client.list_mdl_inputs()
        format_output(result)

    elif command == "get-channel":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_mdl_channel_status(args.id)
        format_output({"channel_id": args.id, "status": result})

    elif command == "start-channel":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.start_mdl_channel(args.id)
        format_output(result)

    elif command == "stop-channel":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.stop_mdl_channel(args.id)
        format_output(result)

    elif command == "list-security-groups":
        result = client.list_mdl_security_groups()
        format_output(result)

    elif command == "get-alerts":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_mdl_channel_alerts(args.id)
        format_output(result)

    elif command == "get-logs":
        if not args.id:
            print("Error: --id required")
            sys.exit(1)
        result = client.get_mdl_channel_logs(args.id)
        format_output(result)

    else:
        print(f"Unknown command: {command}")
        print_streamlive_help()
        sys.exit(1)


def print_streamlink_help():
    """Print StreamLink help."""
    print("""
StreamLink Commands:
====================
  list-regions              List available regions
  list-flows                List all flows
  get-flow --id <flowId>    Get flow status
  start-flow --id <flowId>  Start a flow
  stop-flow --id <flowId>   Stop a flow
  get-logs --id <flowId>    Get flow logs
  get-status --id <flowId>  Get realtime status
""")


def print_streamlive_help():
    """Print StreamLive help."""
    print("""
StreamLive Commands:
====================
  list-regions              List available regions
  list-channels             List all channels
  list-inputs               List all inputs
  get-channel --id <id>     Get channel status
  start-channel --id <id>   Start a channel
  stop-channel --id <id>    Stop a channel
  list-security-groups      List security groups
  get-alerts --id <id>      Get channel alerts
  get-logs --id <id>        Get channel logs
""")


def main():
    parser = argparse.ArgumentParser(
        description="Tencent Cloud StreamLink & StreamLive CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Services:
  streamlink (sl)   - StreamLink service for media transport
  streamlive (sv)   - StreamLive service for encoding/transcoding

Examples:
  python cli.py sl list-regions
  python cli.py sl list-flows
  python cli.py sl start-flow --id flow-123
  python cli.py sv list-channels
  python cli.py sv start-channel --id channel-123
        """
    )

    parser.add_argument("service", choices=["streamlink", "sl", "streamlive", "sv"],
                        help="Service to use")
    parser.add_argument("command", help="Command to execute")
    parser.add_argument("--id", help="Resource ID")

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    # Handle help for specific service
    if len(sys.argv) == 2 and sys.argv[1] in ["streamlink", "sl"]:
        print_streamlink_help()
        sys.exit(0)
    if len(sys.argv) == 2 and sys.argv[1] in ["streamlive", "sv"]:
        print_streamlive_help()
        sys.exit(0)

    args = parser.parse_args()

    try:
        client = TencentCloudClient()

        if args.service in ["streamlink", "sl"]:
            streamlink_commands(client, args)
        elif args.service in ["streamlive", "sv"]:
            streamlive_commands(client, args)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
