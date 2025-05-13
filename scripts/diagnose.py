#!/usr/bin/env python
"""
Diagnostic utility for analyzing logs and troubleshooting WhatsApp chatbot errors

Usage:
  python scripts/diagnose.py --error-id <error_id>
  python scripts/diagnose.py --analyze-logs
  python scripts/diagnose.py --check-context <client_id>
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional


def setup_arg_parser():
    parser = argparse.ArgumentParser(
        description="Diagnostic utility for troubleshooting"
    )
    parser.add_argument("--error-id", help="Error ID to analyze")
    parser.add_argument(
        "--analyze-logs", action="store_true", help="Analyze recent logs"
    )
    parser.add_argument("--check-context", help="Check context history for a client ID")
    parser.add_argument("--days", type=int, default=1, help="Number of days to analyze")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser


def find_error_file(error_id: str) -> Optional[str]:
    """Find error file by error ID"""
    debug_dir = "logs/debug"
    for filename in os.listdir(debug_dir):
        if filename.startswith("error_") and error_id in filename:
            return os.path.join(debug_dir, filename)
    return None


def analyze_error(error_id: str, verbose: bool = False) -> Dict[str, Any]:
    """Analyze a specific error by ID"""
    error_file = find_error_file(error_id)
    if not error_file:
        print(f"Error file for ID {error_id} not found")
        return {}

    with open(error_file, "r") as f:
        error_data = json.load(f)

    # Extract key information
    result = {
        "error_id": error_id,
        "timestamp": error_data.get("timestamp"),
        "error_type": error_data.get("error_type"),
        "error_message": error_data.get("error_message"),
    }

    if verbose:
        result["traceback"] = error_data.get("traceback")
        result["context"] = error_data.get("context")

    # Look for similar errors
    similar_errors = find_similar_errors(error_data.get("error_type"))
    if similar_errors:
        result["similar_errors"] = similar_errors

    # Check if this is a common error
    is_common = len(similar_errors) > 3
    if is_common:
        result["is_common"] = True
        result["suggestion"] = (
            "This appears to be a common error. Check for patterns in the affected client IDs or states."
        )

    return result


def find_similar_errors(error_type: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Find errors of the same type"""
    similar_errors = []
    debug_dir = "logs/debug"

    for filename in os.listdir(debug_dir):
        if not filename.startswith("error_"):
            continue

        try:
            with open(os.path.join(debug_dir, filename), "r") as f:
                data = json.load(f)
                if data.get("error_type") == error_type:
                    similar_errors.append(
                        {
                            "error_id": data.get("error_id"),
                            "timestamp": data.get("timestamp"),
                            "client_id": data.get("client_id"),
                            "state": data.get("state"),
                        }
                    )

                    if len(similar_errors) >= limit:
                        break
        except Exception:
            continue

    return similar_errors


def analyze_logs(days: int = 1, verbose: bool = False) -> Dict[str, Any]:
    """Analyze recent logs for patterns"""
    log_dir = "logs"
    debug_dir = "logs/debug"

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Find log files in date range
    log_files = []
    for i in range(days + 1):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{date}.log")
        error_log_file = os.path.join(log_dir, f"{date}-errors.log")

        if os.path.exists(log_file):
            log_files.append(log_file)
        if os.path.exists(error_log_file):
            log_files.append(error_log_file)

    # Process log files
    error_counts = Counter()
    state_error_counts = defaultdict(Counter)
    client_error_counts = Counter()

    # Check debug directory for error files
    error_files = glob.glob(os.path.join(debug_dir, "error_*.json"))
    for error_file in error_files:
        try:
            with open(error_file, "r") as f:
                data = json.load(f)

                # Skip old errors
                timestamp = data.get("timestamp")
                if timestamp:
                    error_date = datetime.strptime(timestamp.split("_")[0], "%Y%m%d")
                    if error_date < start_date:
                        continue

                error_type = data.get("error_type", "Unknown")
                error_counts[error_type] += 1

                state = data.get("state")
                if state:
                    state_error_counts[state][error_type] += 1

                client_id = data.get("client_id")
                if client_id:
                    client_error_counts[client_id] += 1
        except Exception:
            continue

    # Process log files for error patterns
    error_patterns = defaultdict(list)
    for log_file in log_files:
        if verbose:
            print(f"Analyzing log file: {log_file}")

        try:
            with open(log_file, "r") as f:
                log_content = f.readlines()

            for line in log_content:
                if "ERROR" in line or "Exception" in line:
                    for error_type in error_counts:
                        if error_type in line:
                            error_patterns[error_type].append(line.strip())
        except Exception:
            continue

    # Prepare results
    results = {
        "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_errors": sum(error_counts.values()),
        "error_types": dict(error_counts.most_common()),
        "most_affected_states": {
            state: dict(errors.most_common(3))
            for state, errors in state_error_counts.items()
        },
        "most_affected_clients": dict(client_error_counts.most_common(5)),
    }

    if verbose:
        results["error_patterns"] = {
            error_type: patterns[:5] for error_type, patterns in error_patterns.items()
        }

    # Generate suggestions
    suggestions = []
    if results["total_errors"] > 0:
        most_common_error = error_counts.most_common(1)[0][0]
        most_affected_state = max(
            state_error_counts.items(),
            key=lambda x: sum(x[1].values()),
            default=(None, Counter()),
        )[0]

        if most_affected_state:
            suggestions.append(
                f"The state '{most_affected_state}' has the most errors. "
                f"Check the handler for this state."
            )

        suggestions.append(
            f"The most common error is '{most_common_error}'. "
            f"This occurred {error_counts[most_common_error]} times."
        )

    results["suggestions"] = suggestions
    return results


def check_client_context(client_id: str, verbose: bool = False) -> Dict[str, Any]:
    """Check context history for a specific client"""
    debug_dir = "logs/debug"

    # Find context files for this client
    context_files = []
    for filename in os.listdir(debug_dir):
        if client_id[-6:] in filename and "context" in filename:
            context_files.append(os.path.join(debug_dir, filename))

    context_files.sort()  # Sort by timestamp

    # Process context files
    context_history = []
    states_seen = set()

    for file_path in context_files:
        try:
            with open(file_path, "r") as f:
                context_data = json.load(f)

            # Extract timestamp from filename
            filename = os.path.basename(file_path)
            timestamp_part = filename.split("_")[0]

            # Determine state from filename
            state = "unknown"
            if "before_" in filename:
                state = filename.split("before_")[1].split(".")[0]
            elif "after_" in filename:
                state = filename.split("after_")[1].split(".")[0]

            states_seen.add(state)

            entry = {
                "timestamp": timestamp_part,
                "state": state,
                "filename": filename,
            }

            if verbose:
                # Extract key information
                for key in [
                    "selected_content_type",
                    "selected_platforms",
                    "template_id",
                    "caption",
                    "is_video_content",
                ]:
                    if key in context_data:
                        entry[key] = context_data[key]

            context_history.append(entry)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    # Find errors for this client
    client_errors = []
    for filename in os.listdir(debug_dir):
        if filename.startswith("error_") and client_id[-6:] in filename:
            try:
                with open(os.path.join(debug_dir, filename), "r") as f:
                    error_data = json.load(f)

                client_errors.append(
                    {
                        "error_id": error_data.get("error_id"),
                        "timestamp": error_data.get("timestamp"),
                        "error_type": error_data.get("error_type"),
                        "state": error_data.get("state"),
                        "error_message": error_data.get("error_message"),
                    }
                )
            except Exception:
                continue

    # Prepare results
    results = {
        "client_id": client_id,
        "context_files_count": len(context_history),
        "states_seen": list(states_seen),
        "context_history": context_history[:10] if verbose else context_history[:5],
        "errors_count": len(client_errors),
        "errors": client_errors[:5],
    }

    # Generate suggestions
    suggestions = []
    if results["errors_count"] > 0:
        suggestions.append(
            f"Client experienced {results['errors_count']} errors. "
            f"Check the most recent error: {client_errors[0]['error_id']}"
        )

    if (
        "media_source_selection" in states_seen
        and "waiting_for_media_upload" not in states_seen
    ):
        suggestions.append(
            "Client selected media source but didn't reach media upload state. "
            "Check the media selection handling."
        )

    results["suggestions"] = suggestions
    return results


def main():
    parser = setup_arg_parser()
    args = parser.parse_args()

    if not any([args.error_id, args.analyze_logs, args.check_context]):
        parser.print_help()
        sys.exit(1)

    if args.error_id:
        result = analyze_error(args.error_id, args.verbose)
        print(json.dumps(result, indent=2))

    if args.analyze_logs:
        result = analyze_logs(args.days, args.verbose)
        print(json.dumps(result, indent=2))

    if args.check_context:
        result = check_client_context(args.check_context, args.verbose)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
