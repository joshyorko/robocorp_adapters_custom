#!/usr/bin/env python3
"""Seed Amazon DocumentDB with initial work items for testing.

This script creates initial work items in the DocumentDB database for the producer task to process.
Compatible with Amazon DocumentDB clusters and supports callid-based duplicate prevention.
"""

import json
import os
import sys
import base64
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env(env_json: Path):
    """Load environment variables from JSON file."""
    if env_json and env_json.exists():
        data = json.loads(env_json.read_text())
        for k, v in data.items():
            os.environ[k] = os.path.expandvars(v)


def main():
    """Main seeding function."""
    ap = argparse.ArgumentParser(
        description="Seed Amazon DocumentDB with initial work items."
    )
    ap.add_argument(
        "--env",
        default="devdata/env-docdb-local-producer.json",
        help="Environment JSON file that sets DOCDB_* variables",
    )
    ap.add_argument(
        "--json",
        default="devdata/work-items-in/test-input-for-producer/work-items.json",
        help="Path to work-items.json (array of objects with at least 'payload')",
    )
    ap.add_argument("--queue", help="Override queue name from environment")
    ap.add_argument(
        "--callid-field", help="Field name to use as callid for duplicate prevention"
    )
    args = ap.parse_args()

    # Load environment configuration
    load_env(Path(args.env))

    # Import adapter after environment is loaded
    try:
        from robocorp_adapters_custom.docdb_adapter import DocumentDBAdapter
    except ImportError as e:
        print(
            f"Error: Could not import DocumentDBAdapter. Make sure pymongo is installed: {e}"
        )
        print("Install with: pip install pymongo")
        sys.exit(1)

    # Override queue name if provided
    if args.queue:
        os.environ["RC_WORKITEM_QUEUE_NAME"] = args.queue

    queue = os.getenv("RC_WORKITEM_QUEUE_NAME", "default")
    docdb_database = os.getenv("DOCDB_DATABASE")
    docdb_hostname = os.getenv("DOCDB_HOSTNAME", os.getenv("DOCDB_URI", "localhost"))

    if not docdb_database:
        print("Error: DOCDB_DATABASE environment variable is required")
        sys.exit(1)

    print(f"Seeding DocumentDB queue: {queue}")
    print(f"Database: {docdb_database}")
    print(f"Host: {docdb_hostname}")

    # Load work items from JSON
    try:
        items = json.loads(Path(args.json).read_text())
    except FileNotFoundError:
        print(f"Error: Work items file not found: {args.json}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in work items file: {e}")
        sys.exit(1)

    # Handle single object input
    if isinstance(items, dict):
        items = [items]

    if not items:
        print("Error: No work items found in JSON file")
        sys.exit(1)

    # Initialize DocumentDB adapter
    try:
        adapter = DocumentDBAdapter()
    except Exception as e:
        print(f"Error: Failed to connect to DocumentDB: {e}")
        print("\nPlease check your DocumentDB configuration:")
        print("- DOCDB_URI or (DOCDB_HOSTNAME + DOCDB_USERNAME + DOCDB_PASSWORD)")
        print("- DOCDB_DATABASE")
        print("- DOCDB_TLS_CERT (if using AWS DocumentDB)")
        sys.exit(1)

    # Seed work items
    created = 0
    duplicates = 0
    errors = 0

    for i, wi in enumerate(items):
        try:
            # Extract payload (be generous with input format)
            payload = wi.get("payload", wi)

            # Extract callid if specified
            callid = None
            if args.callid_field and args.callid_field in payload:
                callid = payload[args.callid_field]
            elif "callid" in wi:
                callid = wi["callid"]

            # Process file attachments
            file_tuples = []
            for file_info in wi.get("files", []):
                name = file_info["name"]
                if "content_base64" in file_info:
                    content = base64.b64decode(file_info["content_base64"])
                elif "path" in file_info:
                    file_path = Path(file_info["path"])
                    if not file_path.exists():
                        print(f"Warning: File not found: {file_path}")
                        continue
                    try:
                        content = file_path.read_bytes()
                    except (OSError, IOError) as e:
                        print(f"Warning: Could not read file {file_path}: {e}")
                        continue
                else:
                    print(f"Warning: Invalid file info for item {i}: {file_info}")
                    continue
                file_tuples.append((name, content))

            # Create work item
            item_id = adapter.seed_input(
                payload=payload, files=file_tuples, callid=callid
            )
            created += 1

            # Show progress
            payload_preview = str(list(payload.keys())[:6])
            if len(list(payload.keys())) > 6:
                payload_preview = payload_preview[:-1] + ", ...]"

            callid_info = f" (callid: {callid})" if callid else ""
            print(f"✓ seeded {item_id} payload keys={payload_preview}{callid_info}")

        except Exception as e:
            if "already exists" in str(e) and callid:
                duplicates += 1
                print(f"⚠ skipped duplicate callid: {callid}")
            else:
                errors += 1
                print(f"✗ error seeding item {i}: {e}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Seeding completed for queue: {queue}")
    print(f"✓ Created: {created} work items")
    if duplicates:
        print(f"⚠ Skipped: {duplicates} duplicates")
    if errors:
        print(f"✗ Errors: {errors} failures")
    print(f"{'='*50}")

    if created > 0:
        print("\nNext steps:")
        print(f"  rcc run -e {args.env} -t Producer")
        print(f"  rcc run -e devdata/env-docdb-local-consumer.json -t Consumer")
        print(f"  rcc run -e devdata/env-docdb-local-reporter.json -t Reporter")

    # Close adapter connection
    adapter.close()


if __name__ == "__main__":
    main()
