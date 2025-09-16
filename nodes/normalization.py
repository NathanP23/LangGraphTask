from datetime import datetime
import re
from config import (NORMALIZATION_SPEAKER_FIELDS, NORMALIZATION_TEXT_FIELDS,
                   NORMALIZATION_TYPE_FIELDS, NORMALIZATION_TIMESTAMP_FIELDS,
                   NORMALIZATION_EXCLUDED_METADATA_FIELDS, NORMALIZATION_SPEAKER_CLEANING_PATTERN,
                   NORMALIZATION_MIN_TEXT_LENGTH, NORMALIZATION_TIMESTAMP_FORMATS)

def normalize_structured(state):
    """Clean and normalize structured input data."""
    print("Normalizing structured data...")
    if not state.structured_data:
        if not state.errors:
            state.errors = []
        state.errors.append("No structured data to normalize")
        return state

    normalized_data = []

    for item in state.structured_data:
        if not isinstance(item, dict):
            continue  # Skip non-dict items

        normalized_item = _normalize_single_item(item)
        if normalized_item:  # Only add if normalization succeeded
            normalized_data.append(normalized_item)

    # Update state with normalized data
    state.structured_data = normalized_data

    # Set validated_data for the next step
    state.validated_data = normalized_data
    print(f"Normalized {len(normalized_data)} items. State updated.")
    return state

def _normalize_single_item(item):
    """Normalize a single communication item."""
    print("Normalizing single item...")
    normalized = {}

    # Normalize timestamp field
    timestamp = _extract_timestamp(item)
    if timestamp:
        normalized['timestamp'] = timestamp

    # Normalize speaker field
    speaker = _extract_speaker(item)
    if speaker:
        normalized['speaker'] = speaker

    # Normalize text content
    text = _extract_text(item)
    if text:
        normalized['text'] = text
    else:
        return None  # Skip items without text content

    # Normalize communication type
    comm_type = _extract_type(item)
    normalized['type'] = comm_type

    # Add any additional fields as metadata
    print("Adding metadata...")
    metadata = {}
    for key, value in item.items():
        # Skip already normalized fields
        if key.lower() not in [field.lower() for field in NORMALIZATION_EXCLUDED_METADATA_FIELDS]:
            metadata[key] = value

    if metadata:
        normalized['metadata'] = metadata

    return normalized

def _extract_timestamp(item):
    """Extract and normalize timestamp from various field names."""
    print("Extracting timestamp...")
    timestamp_fields = NORMALIZATION_TIMESTAMP_FIELDS

    for field in timestamp_fields:
        if field in item and item[field]:
            return _parse_timestamp(item[field])

    return None

def _parse_timestamp(timestamp_str):
    """Parse timestamp string into ISO format."""
    print(f"Parsing timestamp: {timestamp_str}")
    if isinstance(timestamp_str, datetime):
        return timestamp_str.isoformat()

    if not isinstance(timestamp_str, str):
        return None

    # Common timestamp formats to try
    formats = NORMALIZATION_TIMESTAMP_FORMATS

    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            print(f"Error: {ValueError}")

    return timestamp_str  # Return original if can't parse

def _extract_speaker(item):
    """Extract speaker name from various field names."""
    print("Extracting speaker...")
    speaker_fields = NORMALIZATION_SPEAKER_FIELDS

    for field in speaker_fields:
        if field in item and item[field]:
            speaker = str(item[field]).strip()
            # Clean up speaker name
            speaker = re.sub(NORMALIZATION_SPEAKER_CLEANING_PATTERN, '', speaker)
            return speaker

    return "Unknown"

def _extract_text(item):
    """Extract text content from various field names."""
    print("Extracting text content...")
    text_fields = NORMALIZATION_TEXT_FIELDS

    for field in text_fields:
        if field in item and item[field]:
            text = str(item[field]).strip()
            if len(text) >= NORMALIZATION_MIN_TEXT_LENGTH:
                return text

    return None

def _extract_type(item):
    """Extract communication type from various field names."""
    print("Extracting communication type...")
    type_fields = NORMALIZATION_TYPE_FIELDS

    for field in type_fields:
        if field in item and item[field]:
            return str(item[field]).strip().lower()

    return "message"  # Default type