from datetime import datetime
import re
from config import (NORMALIZATION_SPEAKER_FIELDS, NORMALIZATION_TEXT_FIELDS,
                   NORMALIZATION_TYPE_FIELDS, NORMALIZATION_TIMESTAMP_FIELDS,
                   NORMALIZATION_EXCLUDED_METADATA_FIELDS, NORMALIZATION_SPEAKER_CLEANING_PATTERN,
                   NORMALIZATION_MIN_TEXT_LENGTH, NORMALIZATION_TIMESTAMP_FORMATS)

def normalize_structured(state):
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    """Clean and normalize structured input data."""
    state.add_log("Normalizing structured data...")
    if not state.structured_data:
        state.add_error("No structured data to normalize")
        return state

    normalized_data = []

    for item in state.structured_data:
        if not isinstance(item, dict):
            state.add_log(f"Skipping non-dict item: {item}", 0)
            continue  # Skip non-dict items

        normalized_item = _normalize_single_item(item, reporter)
        if normalized_item:  # Only add if normalization succeeded
            state.add_log(f"Adding normalized item: {normalized_item}", 0, flush=True)
            normalized_data.append(normalized_item)

    # Update state with normalized data
    state.structured_data = normalized_data

    # Set validated_data for the next step
    state.validated_data = normalized_data
    state.add_log(f"Normalized {len(normalized_data)} items. State updated.")
    return state

def _normalize_single_item(item, reporter):
    """Normalize a single communication item."""
    reporter.add_log("Normalizing single item...", 1, flush=True)
    normalized = {}

    # Normalize timestamp field
    timestamp = _extract_timestamp(item, reporter)
    if timestamp:
        normalized['timestamp'] = timestamp

    # Normalize speaker field
    speaker = _extract_speaker(item, reporter)
    if speaker:
        normalized['speaker'] = speaker

    # Normalize text content
    text = _extract_text(item, reporter)
    if text:
        normalized['text'] = text
    else:
        return None  # Skip items without text content

    # Normalize communication type
    comm_type = _extract_type(item, reporter)
    normalized['type'] = comm_type

    # Add any additional fields as metadata
    reporter.add_log("Adding metadata...", 1, flush=True)
    metadata = {}
    for key, value in item.items():
        # Skip already normalized fields
        if key.lower() not in [field.lower() for field in NORMALIZATION_EXCLUDED_METADATA_FIELDS]:
            metadata[key] = value

    if metadata:
        normalized['metadata'] = metadata

    return normalized

def _extract_timestamp(item, reporter):
    """Extract and normalize timestamp from various field names."""
    reporter.add_log("Extracting timestamp...", 2, flush=True)

    timestamp_fields = NORMALIZATION_TIMESTAMP_FIELDS

    for field in timestamp_fields:
        if field in item and item[field]:
            reporter.add_log(f"Found timestamp field: {field}", 2, flush=True)
            return _parse_timestamp(item[field], reporter)
    reporter.add_log("No timestamp found. returning None", 2, flush=True)
    return None

def _parse_timestamp(timestamp_str, reporter):
    """Parse timestamp string into ISO format."""
    reporter.add_log(f"Parsing timestamp: {timestamp_str}", 3, flush=True)

    if isinstance(timestamp_str, datetime):
        reporter.add_log(f"Found datetime object: {timestamp_str}", 3, flush=True)
        return timestamp_str.isoformat()

    if not isinstance(timestamp_str, str):
        reporter.add_log("Timestamp is not a string or datetime.", 3, flush=True)
        return None

    # Common timestamp formats to try
    formats = NORMALIZATION_TIMESTAMP_FORMATS

    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str.strip(), fmt)
            reporter.add_log(f"Parsed timestamp: {dt.isoformat()}", 3, flush=True)
            return dt.isoformat()
        except ValueError as e:
            reporter.add_error(f"Error parsing timestamp with format {fmt}: {str(e)}")
    reporter.add_log(f"Failed to parse timestamp: {timestamp_str}", 3, flush=True)
    return timestamp_str  # Return original if can't parse

def _extract_speaker(item, reporter):
    """Extract speaker name from various field names."""
    reporter.add_log("Extracting speaker...", 2, flush=True)

    speaker_fields = NORMALIZATION_SPEAKER_FIELDS

    for field in speaker_fields:
        if field in item and item[field]:
            speaker = str(item[field]).strip()
            # Clean up speaker name
            speaker = re.sub(NORMALIZATION_SPEAKER_CLEANING_PATTERN, '', speaker)
            reporter.add_log(f"Extracted speaker: {speaker}", 2, flush=True)
            return speaker
    reporter.add_log("No speaker found. returning 'Unknown'", 2, flush=True)
    return "Unknown"

def _extract_text(item, reporter):
    """Extract text content from various field names."""
    reporter.add_log("Extracting text content...", 2, flush=True)
    text_fields = NORMALIZATION_TEXT_FIELDS

    for field in text_fields:
        if field in item and item[field]:
            text = str(item[field]).strip()
            if len(text) >= NORMALIZATION_MIN_TEXT_LENGTH:
                reporter.add_log(f"Extracted text content: {text}", 2, flush=True)
                return text
    reporter.add_log("No valid text content found.", 2, flush=True)
    return None

def _extract_type(item, reporter):
    """Extract communication type from various field names."""
    reporter.add_log("Extracting communication type...", 2, flush=True)
    type_fields = NORMALIZATION_TYPE_FIELDS

    for field in type_fields:
        if field in item and item[field]:
            reporter.add_log(f"Extracted communication type: {item[field]}", 2, flush=True)
            return str(item[field]).strip().lower()
    reporter.add_log("No communication type found. returning 'message'", 2, flush=True)
    return "message"  # Default type