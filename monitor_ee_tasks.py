#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Monitor and manage Earth Engine tasks.

This script provides utilities to monitor, cancel, and retry Earth Engine tasks.
"""

import os
import argparse
import time
import json
from datetime import datetime
import ee

def initialize_ee(project=None):
    """
    Initialize Earth Engine.

    Args:
        project: Google Cloud project ID (optional)

    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        ee.Initialize(project=project)
        print("Earth Engine initialized successfully!")
        return True
    except Exception as e:
        print(f"Error initializing Earth Engine: {e}")
        return False

def list_tasks(status_filter=None, prefix=None, max_results=None):
    """
    List Earth Engine tasks.

    Args:
        status_filter: Filter tasks by status (e.g., 'RUNNING', 'COMPLETED', 'FAILED')
        prefix: Filter tasks by description prefix
        max_results: Maximum number of tasks to return

    Returns:
        List of Earth Engine tasks
    """
    tasks = ee.batch.Task.list()

    # Filter by status if specified
    if status_filter:
        tasks = [task for task in tasks if task.status()['state'] == status_filter]

    # Filter by prefix if specified
    if prefix:
        tasks = [task for task in tasks if task.config['description'].startswith(prefix)]

    # Limit results if specified
    if max_results and len(tasks) > max_results:
        tasks = tasks[:max_results]

    return tasks

def get_task_details(task):
    """
    Get details for a task.

    Args:
        task: Earth Engine task

    Returns:
        Dictionary with task details
    """
    status = task.status()
    config = task.config

    details = {
        'id': task.id,
        'description': config.get('description', 'N/A'),
        'state': status['state'],
        'creation_timestamp_ms': status.get('creation_timestamp_ms', 0),
        'start_timestamp_ms': status.get('start_timestamp_ms', 0),
        'update_timestamp_ms': status.get('update_timestamp_ms', 0),
        'task_type': status.get('task_type', 'N/A'),
        'destination_uris': config.get('fileExportOptions', {}).get('fileNamePrefix', 'N/A')
    }

    # Add error message if task failed
    if status['state'] == 'FAILED' and 'error_message' in status:
        details['error_message'] = status['error_message']

    return details

def cancel_tasks(tasks):
    """
    Cancel Earth Engine tasks.

    Args:
        tasks: List of Earth Engine tasks

    Returns:
        Number of tasks cancelled
    """
    count = 0
    for task in tasks:
        try:
            task.cancel()
            print(f"Cancelled task: {task.config['description']}")
            count += 1
        except Exception as e:
            print(f"Error cancelling task {task.id}: {e}")

    return count

def find_stalled_tasks(tasks, stall_threshold):
    """
    Find tasks that have been running for longer than the threshold.

    Args:
        tasks: List of Earth Engine tasks
        stall_threshold: Time in milliseconds after which a task is considered stalled

    Returns:
        List of stalled tasks
    """
    stalled_tasks = []
    current_time = int(time.time() * 1000)  # Current time in milliseconds

    for task in tasks:
        status = task.status()

        # Skip tasks that are not running
        if status['state'] != 'RUNNING':
            continue

        # Check if the task has a start timestamp
        if 'start_timestamp_ms' in status:
            start_time = status['start_timestamp_ms']
            running_time = current_time - start_time

            # Check if the task has been running for longer than the threshold
            if running_time > stall_threshold:
                stalled_tasks.append(task)
                print(f"Found stalled task: {task.config['description']}, running for {running_time/1000/60/60:.2f} hours")

    return stalled_tasks

def retry_failed_tasks(tasks, bucket):
    """
    Retry failed Earth Engine tasks.

    Args:
        tasks: List of failed Earth Engine tasks
        bucket: Google Cloud Storage bucket name

    Returns:
        List of new tasks
    """
    new_tasks = []

    for task in tasks:
        try:
            # Get task configuration
            config = task.config

            # Create a new export task with the same configuration
            new_task = ee.batch.Export.image.toCloudStorage(
                image=ee.Image(config['element']),
                description=config['description'] + '_retry',
                bucket=bucket,
                fileNamePrefix=config['fileExportOptions']['fileNamePrefix'],
                region=ee.Geometry(config['region']),
                scale=config['fileExportOptions']['geoTiffOptions']['scale'],
                crs=config['fileExportOptions']['geoTiffOptions']['crs'],
                maxPixels=config['fileExportOptions']['geoTiffOptions']['maxPixels'],
                fileFormat="GeoTIFF",
                formatOptions={"cloudOptimized": True}
            )

            # Start the new task
            new_task.start()
            new_tasks.append(new_task)

            print(f"Retried task: {config['description']}")
        except Exception as e:
            print(f"Error retrying task {task.id}: {e}")

    return new_tasks

def save_task_report(tasks, output_path):
    """
    Save a report of tasks to a JSON file.

    Args:
        tasks: List of Earth Engine tasks
        output_path: Path to save the report

    Returns:
        Path to the saved report
    """
    # Get details for each task
    task_details = [get_task_details(task) for task in tasks]

    # Add timestamp to the report
    report = {
        'timestamp': datetime.now().isoformat(),
        'task_count': len(task_details),
        'tasks': task_details
    }

    # Save the report
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    return output_path

def monitor_tasks(tasks, interval=60, max_checks=100):
    """
    Monitor the status of Earth Engine tasks.

    Args:
        tasks: List of Earth Engine tasks
        interval: Interval in seconds between status checks
        max_checks: Maximum number of status checks

    Returns:
        Dictionary with task status counts
    """
    all_complete = False
    check_count = 0

    while not all_complete and check_count < max_checks:
        statuses = {}
        all_complete = True

        for task in tasks:
            status = task.status()['state']
            statuses[status] = statuses.get(status, 0) + 1

            if status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
                all_complete = False

        print(f"Task status: {statuses}")

        if not all_complete:
            print(f"Waiting {interval} seconds for tasks to complete...")
            time.sleep(interval)
            check_count += 1

    return statuses

def main():
    """Main function to monitor and manage Earth Engine tasks."""
    parser = argparse.ArgumentParser(description="Monitor and manage Earth Engine tasks")

    # Earth Engine initialization
    parser.add_argument("--project", default=None,
                        help="Google Cloud project ID (default: None)")

    # Task filtering options
    parser.add_argument("--status", choices=['READY', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'],
                        help="Filter tasks by status")
    parser.add_argument("--prefix", help="Filter tasks by description prefix")
    parser.add_argument("--max-results", type=int, help="Maximum number of tasks to return")

    # Task management options
    parser.add_argument("--cancel", action="store_true", help="Cancel filtered tasks")
    parser.add_argument("--retry", action="store_true", help="Retry failed tasks")
    parser.add_argument("--bucket", help="Google Cloud Storage bucket name (required for retry)")
    parser.add_argument("--cancel-stalled", action="store_true",
                        help="Cancel tasks that have been running for more than 24 hours")
    parser.add_argument("--stall-threshold", type=int, default=24*60*60*1000,
                        help="Time in milliseconds after which a task is considered stalled (default: 24 hours)")

    # Monitoring options
    parser.add_argument("--monitor", action="store_true", help="Monitor task status")
    parser.add_argument("--interval", type=int, default=60,
                        help="Interval in seconds between status checks (default: 60)")
    parser.add_argument("--max-checks", type=int, default=100,
                        help="Maximum number of status checks (default: 100)")

    # Reporting options
    parser.add_argument("--report", help="Save task report to specified file")

    args = parser.parse_args()

    # Initialize Earth Engine
    if not initialize_ee(args.project):
        return

    # List tasks
    tasks = list_tasks(args.status, args.prefix, args.max_results)
    print(f"Found {len(tasks)} tasks")

    # Print task details
    for i, task in enumerate(tasks):
        details = get_task_details(task)
        print(f"{i+1}. {details['description']} - {details['state']}")

    # Cancel tasks if requested
    if args.cancel:
        count = cancel_tasks(tasks)
        print(f"Cancelled {count} tasks")

    # Cancel stalled tasks if requested
    if args.cancel_stalled:
        # Find stalled tasks
        stalled_tasks = find_stalled_tasks(tasks, args.stall_threshold)
        print(f"Found {len(stalled_tasks)} stalled tasks")

        # Cancel stalled tasks
        if stalled_tasks:
            count = cancel_tasks(stalled_tasks)
            print(f"Cancelled {count} stalled tasks")

    # Retry failed tasks if requested
    if args.retry:
        if not args.bucket:
            print("Error: --bucket is required for --retry")
            return

        # Filter for failed tasks
        failed_tasks = [task for task in tasks if task.status()['state'] == 'FAILED']
        print(f"Found {len(failed_tasks)} failed tasks")

        # Retry failed tasks
        new_tasks = retry_failed_tasks(failed_tasks, args.bucket)
        print(f"Retried {len(new_tasks)} tasks")

        # Update tasks list to include new tasks
        tasks.extend(new_tasks)

    # Monitor tasks if requested
    if args.monitor:
        print("Monitoring task status...")
        monitor_tasks(tasks, args.interval, args.max_checks)

    # Save task report if requested
    if args.report:
        report_path = save_task_report(tasks, args.report)
        print(f"Saved task report to {report_path}")

if __name__ == "__main__":
    main()
