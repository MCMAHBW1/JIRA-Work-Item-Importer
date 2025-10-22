# Jira Work Item Import Tool

This tool imports work items from a CSV file into Jira using the Jira REST API.

## Supported Issue Types

| Issue Type | Parent Type | Description |
|------------|-------------|-------------|
| Epic | None | Top-level work item |
| Story | Epic | Child of Epic; Development "Bucket" |
| Task | Epic | Child of Epic; Non-Development "Bucket" |
| Sub-task | Story or Task | Child of Story or Task |

> [!NOTE]
> Remember that the `Story` type is used for Development activities. The `Task` type is used for non-development activities.
> ## Development Activities (Stories) Examples
>
> - Feature Implementation
> - Bug Fixing
> - Code Refactoring
> - Performance Optimization
> - API Development
> - Creating Automated Test Cases (e.g., Unit, API, or E2E)
> - Creating Manual Test Cases
> 
> ## Non-Development Activities (Tasks) Examples
> 
> - Project Planning
>   - Outlining project goals, timelines, and deliverables.
>   - Example: Creating a project roadmap for the next quarter.
> 
> - Documentation Writing
>   - Writing user guides, technical documentation, and API > references.
>   - Example: Updating API documentation to reflect recent > changes.
> 
> - Requirement Gathering
>   - Collecting and analyzing client requirements for the > project.
>   - Example: Conducting interviews with stakeholders to > understand their needs.
> 
> - User Training
>   - Educating users on how to use a new system or feature.
>   - Example: Conducting workshops to demonstrate the > functionalities of a new CMS.
> 
> - Executing Test Cases
>   - Verifying that software functions as intended.
>   - Example: Performing manual testing or executing automated tests to ensure all features > work correctly before release.

## Prerequisites

1. Python 3.7 or higher
2. Jira Cloud account with API access
3. Work items prepared in CSV format

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Jira API Token

1. Log in to your Jira account
2. Go to https://id.atlassian.com/manage-profile/security/api-tokens
3. Click "Create API token"
4. Give it a name (e.g., "CSV Import") and copy the token

### 3. Configure the Script

Edit `jira_work_item_import.py` and update these values at the top:

```python
JIRA_URL = "https://yourcompany.atlassian.net"  # Your Jira instance URL
JIRA_EMAIL = "your.email@company.com"           # Your Jira email
JIRA_API_TOKEN = "your_api_token_here"          # API token from step 2
JIRA_PROJECT_KEY = "PROJECTKEY"                  # Your Jira project key (e.g., "QM")
```

### 4. Prepare Your CSV File

Create a CSV file named with the following columns:

**Required Columns:**
- `Work Item Type` - Must be: Epic, Story, Task, or Sub-Task
- `Title` - The summary/title of the work item

**Optional Columns:**
- `Description` - Detailed description
- `Tags` - Semicolon-separated tags (converted to Jira labels)
- `Priority` - Must match Jira priorities (Blocker, Critical, Major, Minor, Trivial, High, Medium, Low, or Default)

**Example CSV:**
```csv
Work Item Type,Title,Tags,Description,Priority
Epic,Search Features,Search,,High
Story,Implement Simple Search,Search,Basic search functionality,Medium
Sub-Task,Write unit tests,Testing,Unit tests for search,Low
Task,Create API documentation,Documentation,,Medium,
Sub-Task,Review documentation,Documentation,Peer review,Low
```

> [!IMPORTANT]
> The CSV must be ordered with parent items appearing before their children.

## Usage

Run the import script:

```bash
python jira_work_item_import.py
```

The script will:
1. Read the CSV file
2. Create issues in the correct order (Epics → Stories → Tasks → Sub-tasks)
3. Establish parent-child relationships
4. Set priorities and labels
5. Transition all issues to "Pending" status

## Features

- **Automatic Parent-Child Relationships**: The script intelligently links:
  - Stories and Tasks to their parent Epic
  - Sub-tasks to their parent Story or Task

- **Status Management**: All imported items are set to "Pending" status

- **Field Mapping**: Imports the following fields:
  - Work Item Type → Issue Type (Epic, Story, Task, Sub-task)
  - Title → Summary
  - Description → Description (in Atlassian Document Format)
  - Tags → Labels (semicolon-separated, spaces replaced with underscores)
  - Priority → Priority (validated against Jira priorities)

- **Error Handling**: Continues importing even if individual items fail

## Important Notes

1. **Issue Type Names**: Ensure your Jira project has these issue types enabled:
   - Epic
   - Story
   - Task
   - Sub-task

2. **Priority Values**: The script validates priorities against these values:
   - Critical, Trivial, High, Medium, Low
   - Invalid priorities default to "Low"

3. **Status Workflow**: The script assumes "Pending" status exists in your workflow. Update the `DEFAULT_STATUS` variable if your workflow uses a different name.

4. **CSV Order**: Parent items (Epic, Story, Task) must appear in the CSV before their children (Story, Task, Sub-task).

5. **Labels**: Tags are converted to Jira labels. Spaces are replaced with underscores (e.g., "Priority 1" becomes "Priority_1").

6. **Dry Run**: Consider testing on a separate Jira project first to verify the import works as expected, such as the R&D Template Project (RDT).

## Troubleshooting

### "Failed to create issue" errors

- Check that your API token is valid
- Verify the project key exists
- Ensure you have permission to create issues in the project
- Confirm the issue types are enabled in your project

### "Could not transition issue" warnings

- Your Jira workflow may not allow transitions to "Pending"
- Update `DEFAULT_STATUS` to match your workflow
- You can manually transition issues after import

### Sub-tasks not created

- Verify that Sub-task issue type is enabled in your project
- Ensure parent issues (Story or Task) were created successfully first
- Check that Sub-tasks appear AFTER their parent in the CSV

### Invalid priority warnings

- Check that priority values match Jira's priority names exactly
- Invalid priorities will default to "Trivial"

## Output

The script provides:
- Progress updates for each issue created
- Status transition confirmations
- A final mapping of CSV row numbers to Jira Keys
- Error messages for any failures

## Example Output

```
============================================================
Jira Work Item Import
============================================================

Reading CSV file...
Found 10 work items

--- Importing Epics ---
✓ Created Epic: RDT-1 - Search Features
  → Transitioned RDT-1 to 'Pending'

--- Importing Stories ---
✓ Created Story: RDT-2 - Implement Simple Search
  → Transitioned RDT-2 to 'Pending'

--- Importing Tasks ---
✓ Created Task: RDT-3 - Create API documentation
  → Transitioned RDT-3 to 'Pending'

--- Importing Sub-tasks ---
✓ Created Sub-task: RDT-4 - Write unit tests
  → Transitioned RDT-4 to 'Pending'

============================================================
Import Complete!
Successfully created 10 issues in Jira
============================================================

Internal ID → Jira Key Mapping:
  Row 1 → RDT-1
  Row 2 → RDT-2
  Row 3 → RDT-4
  ...
```

## CSV Template

Refer to the `example_workitem_import.csv` file in this project for an example CSV file.
