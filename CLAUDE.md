# Jot Potato Path Library

## Project Overview

Path Library is a feature for **Jot Potato**, an AI-powered customer feedback intelligence platform. A Path represents the complete journey from identifying an issue to implementing a solution.

### Data Model Hierarchy

```
Issue → Root Cause → Initiative → Path
                                    └── Phases
                                          └── Steps
                                                └── Action Items
```

- **Issue**: Problem statement from customer feedback
- **Root Cause**: Why the issue is happening
- **Initiative**: Solution to fix the root cause
- **Path**: Implementation journey (active paths only in library)
- **Phase**: Major stage of implementation (e.g., "Research & Planning")
- **Step**: Specific activity within a phase
- **Action Item**: Individual task to complete a step

## Tech Stack

- **Backend**: Django 6.0 + Django REST Framework
- **Frontend**: Vue.js 3 (CDN) + Tailwind CSS (CDN)
- **Database**: SQLite (development), PostgreSQL (production)

## Development Setup

### Environment Variable
Always set `USE_SQLITE=true` for local development:
```bash
export USE_SQLITE=true
```

### Running the Server
```bash
source venv/bin/activate
export USE_SQLITE=true
python manage.py runserver
```

### Running Migrations
```bash
source venv/bin/activate
export USE_SQLITE=true
python manage.py migrate
```

### Django Shell
```bash
source venv/bin/activate
export USE_SQLITE=true
python manage.py shell
```

## Key Files

| File | Purpose |
|------|---------|
| `paths/models.py` | All data models (Issue, RootCause, Initiative, Path, Phase, Step, ActionItem) |
| `paths/serializers.py` | DRF serializers for API |
| `paths/views.py` | API viewsets and endpoints |
| `paths/urls.py` | URL routing |
| `templates/index.html` | Vue.js frontend (single-page app) |

## API Endpoints

Base URL: `/api/`

- `GET /api/paths/` - List all paths (supports `?status=` filter)
- `GET /api/paths/{id}/` - Path detail with phases, steps, action items
- `PATCH /api/paths/{id}/` - Update path
- `PATCH /api/action-items/{id}/status/` - Update action item status
- `GET /api/issues/` - List issues
- `GET /api/root-causes/` - List root causes
- `GET /api/initiatives/` - List initiatives

## Frontend Features

- **Path Library View**: Grid of path cards with status filters (All, Active, On Hold, Completed)
- **Path Detail Modal**: Shows issue chain, metrics, and implementation plan overview
- **Implementation Plan Modal**: Expandable table with phases → steps → action items
- **Detail Modals**: Drill-down views for Phase, Step, and Action Item

## Path Statuses

- `active` - Currently being worked on (max 3 recommended)
- `on_hold` - Paused with reason
- `completed` - Finished with learnings captured
- `archived` - No longer relevant

## Important Notes

1. **Template Syntax**: Use `[[ ]]` for Vue.js interpolation (Django uses `{{ }}`)
2. **Progress Calculation**: Automatically calculated from completed action items
3. **No Draft Paths**: All paths in the library are active (implementation started)
4. **Assignees**: Stored as `assignee_id` (UUID) and `assignee_name` (display string)

## Test Data

The database contains sample paths across different statuses with:
- Team members: Paul, Camille, Stephan, Marie, Lucas, Sophie
- Various phases, steps, and action items with due dates
- Progress tracking based on completed action items
