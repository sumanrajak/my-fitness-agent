from datetime import datetime


def merge_reanalysis_predictions(existing_predictions: list, new_predictions: list, current_date: str | None = None) -> list:
    """Merge a freshly reanalyzed plan into the existing timeline without erasing completed weeks.

    The flow is:
    - keep the existing entries that already lie in the past,
    - determine the current week from the existing timeline and current date,
    - replace the current and future weeks with the newly generated reanalysis plan,
    - preserve the sequence by shifting the new plan to the current week index.
    """
    if not existing_predictions:
        return list(new_predictions or [])

    if not current_date:
        current_date = datetime.today().strftime('%Y-%m-%d')

    try:
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
    except ValueError:
        current_dt = datetime.today()

    def parse_date(value: str | None):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return None

    existing_sorted = sorted(existing_predictions, key=lambda p: int(p.get('week', 0)))
    new_sorted = sorted(new_predictions, key=lambda p: int(p.get('week', 0)))

    current_week_idx = 0
    for entry in existing_sorted:
        entry_date = parse_date(entry.get('date'))
        if entry_date and entry_date <= current_dt:
            current_week_idx = int(entry.get('week', 0))
        else:
            break

    past_predictions = [entry for entry in existing_sorted if int(entry.get('week', 0)) < current_week_idx]
    shifted_new_predictions = []
    for entry in new_sorted:
        adjusted_entry = dict(entry)
        try:
            adjusted_entry['week'] = current_week_idx + int(adjusted_entry.get('week', 0))
        except (TypeError, ValueError):
            adjusted_entry['week'] = current_week_idx
        shifted_new_predictions.append(adjusted_entry)

    merged = past_predictions + shifted_new_predictions

    if shifted_new_predictions:
        last_new_week = max(int(entry.get('week', 0)) for entry in shifted_new_predictions)
        tail_existing = [entry for entry in existing_sorted if int(entry.get('week', 0)) > last_new_week]
        merged.extend(tail_existing)

    merged = sorted(merged, key=lambda p: int(p.get('week', 0)))
    return merged
