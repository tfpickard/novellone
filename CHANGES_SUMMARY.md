# Changes Summary - Chaos Parameters & Logging Enhancement

## Overview
This update adds chaos parameters (absurdity, surrealism, ridiculousness, insanity) to stories and chapters, improves logging with the Rich library, and makes story evaluation more strict.

## Changes Made

### 1. Logging Enhancement
- **Added `rich` library** to `requirements.txt`
- **Updated `logging_config.py`** to use Rich's `RichHandler` for beautiful console output
- Added `PrettyJsonFormatter` for pretty-printing JSON in logs
- Enhanced tracebacks with local variables

### 2. Database Schema Changes
- **Created migration `0004_add_chaos_parameters.py`**
- Added to `Story` model:
  - `absurdity_initial`, `surrealism_initial`, `ridiculousness_initial`, `insanity_initial` (initial values)
  - `absurdity_increment`, `surrealism_increment`, `ridiculousness_increment`, `insanity_increment` (per-chapter increments)
- Added to `Chapter` model:
  - `absurdity`, `surrealism`, `ridiculousness`, `insanity` (actual values returned by OpenAI)

### 3. Story Generation Updates
- **`story_generator.py`**:
  - Randomly generates initial chaos parameters (0.05-0.25) for new stories
  - Randomly generates increment values (0.02-0.15) per chapter
  - Calculates expected chaos values per chapter
  - Instructs OpenAI to return chaos parameter values in structured JSON responses
  - Falls back to expected values if OpenAI doesn't return structured data

### 4. Story Evaluation - More Strict
- **`story_evaluator.py`**:
  - Enhanced prompt with STRICT criteria
  - Added harsh evaluation guidelines
  - Stories should be terminated if:
    - Any score is below 5.0
    - Story is repetitive or going in circles
    - Quality has degraded
    - Plot is exhausted or forced
    - Story exceeds 10 chapters without development
  - Emphasizes that most stories should NOT continue

### 5. API Updates
- **`main.py`**:
  - Updated `ChapterRead` model to include chaos parameters
  - Updated `StorySummary` model to include initial values and increments
  - Updated `admin_spawn_story` endpoint to save chaos parameters
  - Enhanced `/api/stats` endpoint with average chaos parameters
- **`background_worker.py`**:
  - Updated story spawning to include chaos parameters
  - WebSocket broadcasts now include chapter chaos parameters

### 6. Frontend Updates
- **Story Detail Page (`story/[id]/+page.svelte`)**:
  - Added "Chaos Parameters" panel showing initial values, increments, and visual bars
  - Added per-chapter chaos badges (A/S/R/I) with color coding:
    - Absurdity: Orange (#f59e0b)
    - Surrealism: Purple (#8b5cf6)
    - Ridiculousness: Pink (#ec4899)
    - Insanity: Red (#ef4444)

- **Stats Page (`stats/+page.svelte`)**:
  - Added "Average Chaos Parameters" section
  - Shows aggregate statistics with color-coded bars
  - Visual representation of average chaos across all chapters

## How It Works

### Story Creation Flow
1. New story is spawned
2. Random chaos parameters are generated (initial + increment)
3. Story is saved with these parameters in the database

### Chapter Generation Flow
1. Calculate expected chaos values: `initial + (chapter_number - 1) * increment`
2. Pass expected values to OpenAI in the prompt
3. OpenAI generates chapter content with these parameters in mind
4. OpenAI returns structured JSON with chapter content and chaos values
5. Actual chaos values are saved with the chapter

### Display
- **Story level**: Shows starting values and increments per chapter
- **Chapter level**: Shows actual chaos values for that specific chapter
- **Stats**: Shows averages across all chapters in the system

## Migration Instructions

To apply the database changes:

```bash
cd backend
alembic upgrade head
```

## Installation

Install the new dependency:

```bash
cd backend
pip install -r requirements.txt
```

## Configuration

No configuration changes required. The system will automatically:
- Generate random chaos parameters for new stories
- Calculate and track them per chapter
- Display them in the UI
- Include them in stats

## Visual Features

### Story Detail
- Chaos parameter panel with color-coded bars
- Shows initial value + increment notation (e.g., "0.15 +0.08/ch")
- Per-chapter badges showing actual values

### Stats Page
- Four new cards showing average chaos across all chapters
- Color-coded bars for visual representation
- Matches the color scheme of individual chapter badges

## Technical Notes

- OpenAI is instructed to return chaos parameters in structured JSON responses
- If parsing fails, the system falls back to expected calculated values
- All chaos values are floats between 0.0 and 1.0
- Frontend handles null/undefined values gracefully
- Logging now pretty-prints all JSON objects automatically

