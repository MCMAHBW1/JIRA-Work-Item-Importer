"""
Jira Work Item Import Script

This script reads work items from a CSV file and imports them into Jira.
Supports the following Jira issue types:
- Epic (top-level)
- Story (child of Epic)
- Task (child of Epic)
- Sub-task (child of Story or Task)
"""

import csv
import json
import requests
from typing import Dict, List, Optional
import sys

# Configuration - UPDATE THESE VALUES
JIRA_URL = "https://starlims.atlassian.net"  # e.g., https://yourcompany.atlassian.net
JIRA_EMAIL = ""
JIRA_API_TOKEN = ""
JIRA_PROJECT_KEY = ""
CSV_FILE_PATH = ""  # Path to your CSV file with work items


# Default status for all imported items
DEFAULT_STATUS = "Pending"

# Valid Jira priorities and default
VALID_PRIORITIES = [
    "Critical",
    "Trivial",
    "High",
    "Low",
    "Medium"
]
DEFAULT_PRIORITY = "Medium"




class JiraImporter:
    def __init__(self, jira_url: str, email: str, api_token: str, project_key: str):
        self.jira_url = jira_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

        # Track created issues: Internal ID -> Jira Key
        self.created_issues: Dict[str, str] = {}
        # Track parent-child relationships: Child Internal ID -> Parent Internal ID
        self.relationships: Dict[str, str] = {}

    def read_csv(self, file_path: str) -> List[Dict]:
        """Read the CSV file containing work items."""
        work_items = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                # Skip empty rows (check if Work Item Type exists)
                if not row.get('Work Item Type') or not row.get('Work Item Type').strip():
                    continue
                # Add a unique ID for tracking relationships
                row['_internal_id'] = str(idx)
                work_items.append(row)
        return work_items

    def organize_work_items(self, work_items: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Organize work items by type and establish parent-child relationships.
        Hierarchy: Epic → Story/Task → Sub-task
        Returns a dictionary with work items grouped by type in import order.
        """
        organized = {
            "Epic": [],
            "Story": [],
            "Task": [],
            "Sub-task": []
        }

        current_epic = None
        current_parent = None  # Can be Story or Task

        for item in work_items:
            work_type = item.get('Work Item Type', '').strip()
            work_type_lower = work_type.lower()

            if work_type_lower == "epic":
                current_epic = item
                current_parent = None
                organized["Epic"].append(item)

            elif work_type_lower == "story":
                current_parent = item
                organized["Story"].append(item)
                # Link Story to Epic
                if current_epic:
                    self.relationships[item['_internal_id']] = current_epic['_internal_id']

            elif work_type_lower == "task":
                current_parent = item
                organized["Task"].append(item)
                # Link Task to Epic
                if current_epic:
                    self.relationships[item['_internal_id']] = current_epic['_internal_id']

            elif work_type_lower in ["sub-task", "subtask"]:
                organized["Sub-task"].append(item)
                # Link Sub-task to current parent (Story or Task)
                if current_parent:
                    self.relationships[item['_internal_id']] = current_parent['_internal_id']
                else:
                    print(f"  ⚠ Warning: Sub-task '{item.get('Title')}' has no parent Story or Task")

        return organized

    def create_jira_issue(self, work_item: Dict, issue_type: str, parent_key: Optional[str] = None) -> Optional[str]:
        """Create a Jira issue and return its key."""
        internal_id = work_item['_internal_id']
        title = work_item.get('Title', 'Untitled')
        description = work_item.get('Description', '')
        tags = work_item.get('Tags', '')
        priority = work_item.get('Priority', '').strip()

        # Build description in Atlassian Document Format (ADF)
        description_content = []

        # Add description paragraph if exists
        if description:
            description_content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": description
                    }
                ]
            })

        # Create ADF document structure
        jira_description = {
            "version": 1,
            "type": "doc",
            "content": description_content if description_content else [
                {
                    "type": "paragraph",
                    "content": []
                }
            ]
        }

        # Parse tags into labels (split by semicolon and clean up)
        labels = []
        if tags:
            # Split tags by semicolon, strip whitespace, and remove empty strings
            labels = [tag.strip() for tag in tags.split(';') if tag.strip()]
            # Replace spaces with underscores (Jira labels don't allow spaces)
            labels = [label.replace(' ', '_') for label in labels]

        # Build the issue payload
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": title,
                "description": jira_description,
                "issuetype": {"name": issue_type}
            }
        }

        # Add labels if available
        if labels:
            payload["fields"]["labels"] = labels

        # Set priority (validate against allowed priorities)
        jira_priority = DEFAULT_PRIORITY
        if priority and priority in VALID_PRIORITIES:
            jira_priority = priority
        elif priority:
            print(f"  ⚠ Invalid priority '{priority}', using default: {DEFAULT_PRIORITY}")

        payload["fields"]["priority"] = {"name": jira_priority}

        # Add parent link for sub-tasks, stories, and tasks under epics
        if parent_key:
            if issue_type == "Sub-task":
                payload["fields"]["parent"] = {"key": parent_key}
            elif issue_type in ["Story", "Task"]:
                # Link Story or Task to Epic (if parent is an Epic)
                payload["fields"]["parent"] = {"key": parent_key}

        try:
            # Create the issue
            response = self.session.post(
                f"{self.jira_url}/rest/api/3/issue",
                data=json.dumps(payload)
            )
            response.raise_for_status()

            issue_key = response.json().get('key')
            print(f"✓ Created {issue_type}: {issue_key} - {title}")

            # Transition to Pending status
            self.transition_issue(issue_key, DEFAULT_STATUS)

            return issue_key

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to create {issue_type} '{title}': {e}")
            if hasattr(e.response, 'text'):
                print(f"  Response: {e.response.text}")
            return None

    def transition_issue(self, issue_key: str, target_status: str):
        """Transition an issue to a target status."""
        try:
            # Get available transitions
            response = self.session.get(
                f"{self.jira_url}/rest/api/3/issue/{issue_key}/transitions"
            )
            response.raise_for_status()

            transitions = response.json().get('transitions', [])

            # Find the transition ID for the target status
            transition_id = None
            for transition in transitions:
                if transition['to']['name'].lower() == target_status.lower():
                    transition_id = transition['id']
                    break

            if transition_id:
                # Execute the transition
                payload = {"transition": {"id": transition_id}}
                response = self.session.post(
                    f"{self.jira_url}/rest/api/3/issue/{issue_key}/transitions",
                    data=json.dumps(payload)
                )
                response.raise_for_status()
                print(f"  → Transitioned {issue_key} to '{target_status}'")

        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Could not transition {issue_key} to '{target_status}': {e}")

    def import_work_items(self, file_path: str):
        """Main import process."""
        print(f"\n{'='*60}")
        print("Jira Work Item Import")
        print(f"{'='*60}\n")

        # Read and organize work items
        print("Reading CSV file...")
        work_items = self.read_csv(file_path)
        print(f"Found {len(work_items)} work items\n")

        organized = self.organize_work_items(work_items)

        # Import in order: Epics -> Stories -> Tasks -> Sub-tasks
        # This ensures parent issues are created before children

        print("\n--- Importing Epics ---")
        for item in organized["Epic"]:
            jira_key = self.create_jira_issue(item, "Epic")
            if jira_key:
                self.created_issues[item['_internal_id']] = jira_key

        print("\n--- Importing Stories ---")
        for item in organized["Story"]:
            parent_internal_id = self.relationships.get(item['_internal_id'])
            parent_key = self.created_issues.get(parent_internal_id) if parent_internal_id else None
            jira_key = self.create_jira_issue(item, "Story", parent_key)
            if jira_key:
                self.created_issues[item['_internal_id']] = jira_key

        print("\n--- Importing Tasks ---")
        for item in organized["Task"]:
            parent_internal_id = self.relationships.get(item['_internal_id'])
            parent_key = self.created_issues.get(parent_internal_id) if parent_internal_id else None
            jira_key = self.create_jira_issue(item, "Task", parent_key)
            if jira_key:
                self.created_issues[item['_internal_id']] = jira_key

        print("\n--- Importing Sub-tasks ---")
        for item in organized["Sub-task"]:
            parent_internal_id = self.relationships.get(item['_internal_id'])
            parent_key = self.created_issues.get(parent_internal_id) if parent_internal_id else None
            if parent_key:
                jira_key = self.create_jira_issue(item, "Sub-task", parent_key)
                if jira_key:
                    self.created_issues[item['_internal_id']] = jira_key
            else:
                print(f"⚠ Skipping Sub-task '{item.get('Title')}' - No parent found")

        print(f"\n{'='*60}")
        print(f"Import Complete!")
        print(f"Successfully created {len(self.created_issues)} issues in Jira")
        print(f"{'='*60}\n")

        # Print mapping summary
        print("\nInternal ID -> Jira Key Mapping:")
        for internal_id, jira_key in sorted(self.created_issues.items(), key=lambda x: int(x[0])):
            print(f"  Row {internal_id} -> {jira_key}")


def main():
    # Validate configuration
    if JIRA_URL == "YOUR_JIRA_URL":
        print("ERROR: Please update the JIRA_URL in the script")
        sys.exit(1)

    if JIRA_EMAIL == "YOUR_EMAIL":
        print("ERROR: Please update the JIRA_EMAIL in the script")
        sys.exit(1)

    if JIRA_API_TOKEN == "YOUR_API_TOKEN":
        print("ERROR: Please update the JIRA_API_TOKEN in the script")
        sys.exit(1)

    # Check if CSV file exists
    import os
    if not os.path.exists(CSV_FILE_PATH):
        print(f"ERROR: CSV file not found: {CSV_FILE_PATH}")
        print(f"Please update CSV_FILE_PATH in the script or ensure the file exists")
        sys.exit(1)

    # Create importer and run
    importer = JiraImporter(JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY)
    importer.import_work_items(CSV_FILE_PATH)


if __name__ == "__main__":
    main()
