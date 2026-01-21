# Jot Potato Path Library

A Django REST API for managing customer feedback improvement paths in the Jot Potato platform.

## Overview

A **Path** represents the complete improvement journey from identifying an issue to implementing a solution:

```
Issue → Root Cause → Initiative → Implementation Plan (Tasks)
```

The Path Library stores all paths (active, on-hold, completed, archived) so teams can track their improvement cycles.

## Data Model

- **Issue**: Problem statements extracted from customer feedback
- **Root Cause**: Reasons why issues are happening (AI-generated or human input)
- **Initiative**: Solutions to fix root causes
- **Path**: The complete improvement journey linking Issue → Root Cause → Initiative
- **Task**: Individual items in the implementation plan
- **PathComment**: Team collaboration comments on paths

## API Endpoints

### Paths (Path Library)
- `GET /api/paths/` - List all paths (with filtering)
- `POST /api/paths/` - Create a new path
- `GET /api/paths/{id}/` - Get path details
- `PUT /api/paths/{id}/` - Update a path
- `DELETE /api/paths/{id}/` - Delete a path
- `POST /api/paths/{id}/update_status/` - Update path status
- `POST /api/paths/{id}/add_task/` - Add a task to path
- `POST /api/paths/{id}/add_comment/` - Add a comment
- `GET /api/paths/{id}/tasks/` - Get all tasks for a path
- `POST /api/paths/{id}/bulk_update_tasks/` - Bulk update task statuses
- `GET /api/paths/library_stats/` - Get library statistics

### Issues
- `GET /api/issues/` - List issues
- `POST /api/issues/` - Create an issue
- `GET /api/issues/{id}/` - Get issue details
- `PUT /api/issues/{id}/` - Update an issue
- `DELETE /api/issues/{id}/` - Delete an issue

### Root Causes
- `GET /api/root-causes/` - List root causes
- `POST /api/root-causes/` - Create a root cause
- `GET /api/root-causes/{id}/` - Get root cause details
- `PUT /api/root-causes/{id}/` - Update a root cause
- `DELETE /api/root-causes/{id}/` - Delete a root cause

### Initiatives
- `GET /api/initiatives/` - List initiatives
- `POST /api/initiatives/` - Create an initiative
- `GET /api/initiatives/{id}/` - Get initiative details
- `PUT /api/initiatives/{id}/` - Update an initiative
- `DELETE /api/initiatives/{id}/` - Delete an initiative

### Tasks
- `GET /api/tasks/` - List tasks
- `POST /api/tasks/` - Create a task
- `GET /api/tasks/{id}/` - Get task details
- `PUT /api/tasks/{id}/` - Update a task
- `DELETE /api/tasks/{id}/` - Delete a task
- `POST /api/tasks/{id}/complete/` - Mark task as complete
- `POST /api/tasks/{id}/reorder/` - Reorder a task

## Filtering

### Path Filters
- `status` - Filter by status (draft, active, on_hold, completed, archived)
- `priority` - Filter by priority (low, medium, high, critical)
- `organization_id` - Filter by organization
- `owner_id` - Filter by owner
- `created_after` / `created_before` - Date range filters
- `min_progress` / `max_progress` - Progress percentage filters

### Search
Use `?search=` query parameter to search across title, goal_statement, and notes.

### Ordering
Use `?ordering=` with fields like `created_at`, `updated_at`, `priority`, `progress_percentage`.

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL (or SQLite for development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/charlotteeroy/jot_potato_path_library.git
cd jot_potato_path_library
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Start the server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### Using SQLite (Development)
Set `USE_SQLITE=True` in your `.env` file to use SQLite instead of PostgreSQL.

## Integration with Jot Potato

To integrate this module into the main Jot Potato backend:

1. Copy the `paths/` app directory into your Django project
2. Add `'paths'` to `INSTALLED_APPS` in settings
3. Add `path('api/', include('paths.urls'))` to your URL configuration
4. Run migrations: `python manage.py migrate paths`

## Path Statuses

| Status | Description |
|--------|-------------|
| `draft` | Path is being created, not yet started |
| `active` | Team is actively working on this path |
| `on_hold` | Temporarily paused |
| `completed` | All tasks done, path finished |
| `archived` | No longer relevant |

## License

Proprietary - Jot Potato
