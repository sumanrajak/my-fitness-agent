# Database Schema (Firestore)

## Collection: `users`
**Document ID:** `uid` (Firebase Auth UID)
- `uid`: string
- `email`: string
- `age`: integer
- `sex`: string
- `height`: float
- `weight`: float (latest tracked weight)
- `starting_weight`: float
- `current_weight`: float (same as weight)
- `target_weight`: float
- `activity_level`: string
- `context`: string (personal context for AI)
- `timeline`: string
- `maintenance_calories`: integer
- `target_calories`: integer
- `daily_deficit`: integer
- `insights_summary`: string (AI generated text)
- `journey_start_date`: string (YYYY-MM-DD)
- `last_reanalysis_at`: string (YYYY-MM-DD HH:MM:SS)

### Subcollection: `daily_tracker`
**Document ID:** `date` (YYYY-MM-DD)
- `date`: string
- `weight`: float
- `activity_description`: string
- `steps`: integer
- `exercise_minutes`: integer
- `went_to_gym`: boolean
- `total_consumed`: integer
- `total_protein`: float
- `total_fiber`: float
- `total_carbs`: float
- `logs`: array of maps
  - `timestamp`: string (HH:MM)
  - `meal_type`: string
  - `input_text`: string
  - `breakdown`: string
  - `calories`: integer
  - `protein`: float
  - `fiber`: float
  - `carbs`: float

### Subcollection: `reanalyze_logs`
**Document ID:** Auto-generated
- `timestamp`: string (YYYY-MM-DD HH:MM:SS)
- `current_weight`: float
- `input`: map
  - `age`: integer
  - `sex`: string
  - `height`: float
  - `target_weight`: float
  - `activity_level`: string
  - `timeline`: string
  - `context`: string
- `ai_insights`: map
  - `maintenance_calories`: integer
  - `target_calories`: integer
  - `daily_deficit`: integer
  - `goal_feasible`: boolean
  - `achievable_kg_by_deadline`: float
  - `days_remaining`: integer
  - `insights_summary`: string
