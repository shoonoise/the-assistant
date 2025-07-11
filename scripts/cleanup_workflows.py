#!/usr/bin/env python3
"""
Script to clean up old workflow files and references.

This script helps with the codebase simplification by removing workflow-related
files and references that are no longer needed.
"""

import os
import re
import shutil
from pathlib import Path


def main():
    """Main function to clean up workflow files."""
    print("Starting workflow cleanup...")

    # Define paths
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src" / "the_assistant"
    tests_dir = project_root / "tests"

    # 1. Remove workflow directory if it exists
    workflows_dir = src_dir / "workflows"
    if workflows_dir.exists():
        print(f"Removing workflows directory: {workflows_dir}")
        shutil.rmtree(workflows_dir)
    else:
        print("Workflows directory already removed.")

    # 2. Remove workflow test files
    workflow_test_files = []
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if "workflow" in file.lower() and file.endswith(".py"):
                workflow_test_files.append(Path(root) / file)

    for file in workflow_test_files:
        print(f"Removing workflow test file: {file}")
        file.unlink()

    # 3. Update worker.py to remove workflow references
    worker_file = src_dir / "worker.py"
    if worker_file.exists():
        print("Updating worker.py to remove workflow references")
        content = worker_file.read_text()

        # Remove workflow imports
        content = re.sub(r"from the_assistant\.workflows\.[^\n]+\n", "", content)

        # Remove workflow registration
        content = re.sub(r"worker\.register_workflow\([^\)]+\)\n", "", content)

        # Remove scheduling code
        content = re.sub(r"# Schedule workflows[^\n]*\n", "", content)
        content = re.sub(r"await schedule_workflows\(\)\n", "", content)

        # Write updated content
        worker_file.write_text(content)

    print("Workflow cleanup completed!")


if __name__ == "__main__":
    main()
