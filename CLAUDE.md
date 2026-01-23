# Jot Potato Path Library

## Product Vision

**Jot Potato** is an AI-powered customer feedback intelligence platform designed to help small businesses turn messy, multi-channel feedback into clear, prioritized actions — and then actually track whether those actions improved the customer experience.

### The Problem

Small teams receive feedback everywhere (Google Reviews, Instagram DMs, emails, Shopify comments, Airbnb messages, forms…), but they lack the time, structure, and tools to convert all of it into a consistent improvement loop. Jot Potato becomes the system that captures what customers are really saying, reveals why issues happen, and guides teams toward the most impactful improvements.

### Vision Statement

> Make customer-driven improvement effortless — even for teams with no product, data, or research function.

Jot Potato gives small businesses the same advantage as mature product teams: a continuous feedback cycle where every customer comment becomes a signal, every signal becomes a decision, and every decision becomes measurable progress.

It's not "analytics for feedback." It's a **decision engine**: it transforms raw customer input into a roadmap, and a roadmap into outcomes.

### The End-to-End Loop

| Step | What It Does | Output |
|------|--------------|--------|
| **1. Feedback Centralization** | Collects and unifies feedback from multiple sources | Clean, structured feedback hub |
| **2. AI Interpretation** | Detects patterns, hidden pain points, themes, urgency signals, emotional intensity | Grouped themes + insight clarity |
| **3. Root Cause Analysis** | Uses heatmaps, cause diagrams to map operational causes | Problems become explainable and solvable |
| **4. Action Recommendations** | Proposes concrete initiatives, quick wins vs deeper fixes | Prioritized action plan |
| **5. Progress Tracking** | Follows initiative status, ownership, impact monitoring | Measurable customer experience improvement |

### Target Users

Small businesses that run on reputation and repeated customer trust:
- Restaurants
- Airbnb hosts
- Shopify boutiques
- E-commerce stores

These teams need simple clarity + fast execution (not enterprise complexity).

### What Makes It Different

Most tools either collect feedback (but don't transform it into actions) or offer analytics (but require time, expertise, and interpretation).

Jot Potato completes the loop:

**Feedback → Insight → Root Cause → Initiatives → Measurable Improvement**

It's a "customer experience operating system" built for small teams.

### One-Sentence Positioning

> Jot Potato helps small businesses turn customer feedback from every channel into prioritized improvements — and track the impact over time.

---

## Path Library Feature

Path Library is the **progress tracking** component of Jot Potato. A Path represents the complete journey from identifying an issue to implementing a solution.

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
- **Font**: Poppins (Google Fonts)
- **Brand Color**: `#1F2937` (dark blue-gray)

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
- `POST /api/paths/{id}/update_status/` - Update path status
- `POST /api/paths/{id}/ai_query/` - AI-powered path intelligence queries
- `POST /api/action-items/{id}/toggle_status/` - Toggle action item status
- `GET /api/issues/` - List issues
- `GET /api/root-causes/` - List root causes
- `GET /api/initiatives/` - List initiatives

## Frontend Features

### Navigation
- **Sidebar**: Fixed left sidebar with navigation icons (Paths, Analytics, Refresh, Messages, Notifications, Settings) - hidden on mobile
- **Top Navigation**: Breadcrumb navigation with mobile hamburger menu
- **Mobile Menu**: Horizontal navigation bar that appears on mobile devices

### Path Library
- **Path Cards**: Clean card design with title, description, status badge, and metadata
- **Status Filters**: Filter by All, Active, On Hold, Completed
- **Search**: Real-time search with debouncing

### Path Detail View
- **Header**: Status/priority badges, progress percentage, metadata (dates, duration, team size)
- **Project Summary**: Expandable section with on-hold reasons or completion learnings
- **Path Journey**: Visual cards showing Issue → Root Cause → Initiative chain
- **Implementation Plan**: Compact phase overview with progress bars

### Modals
- **Implementation Plan Modal**: Expandable table with phases → steps → action items (card view on mobile)
- **Phase Detail Modal**: Progress stats, description, and steps list
- **Step Detail Modal**: Action items with checkbox toggles
- **Action Item Modal**: Full details with status toggle

### AI Assistant
- **Floating Bubble**: Violet bubble in bottom-right corner (appears when viewing a path)
- **Hover-to-Open**: Chat popup opens on hover
- **Quick Actions**: Pre-built queries for Success Factors, Challenges, Improvements
- **Intelligent Responses**: Contextual answers about status, blockers, due dates, team, phases, accomplishments

### Responsive Design
- Fully responsive layout for mobile, tablet, and desktop
- Mobile-first approach with Tailwind breakpoints (sm, md, lg)

## Path Statuses

- `active` - Currently being worked on (max 3 recommended)
- `on_hold` - Paused with reason
- `completed` - Finished with learnings captured
- `archived` - No longer relevant

## Important Notes

1. **Template Syntax**: Vue.js uses `{{ }}` inside `{% verbatim %}` tags to avoid Django conflicts
2. **Progress Calculation**: Automatically calculated from completed action items
3. **No Draft Paths**: All paths in the library are active (implementation started)
4. **Assignees**: Stored as `assignee_id` (UUID) and `assignee_name` (display string)
5. **AI Assistant**: Uses keyword matching to generate contextual responses about path data
6. **Responsive Breakpoints**: `md:` prefix for tablet/desktop styles (768px+)

## AI Query Keywords

The AI assistant responds to queries containing these keywords:

| Keywords | Response Type |
|----------|---------------|
| status, progress, overview, how | Path status overview with completion stats |
| block, issue, problem, stuck | List of blocked tasks |
| due, deadline, upcoming, soon | Upcoming due dates with urgency indicators |
| accomplish, done, complete, finish, solved | Completed work and key learnings |
| team, who, assignee, member, person | Team members list |
| phase, stage, step | Implementation phases overview |
| *(default)* | General path information with suggestions |

## Test Data

The database contains sample paths across different statuses with:
- Team members: Paul, Camille, Stephan, Marie, Lucas, Sophie
- Various phases, steps, and action items with due dates
- Progress tracking based on completed action items
