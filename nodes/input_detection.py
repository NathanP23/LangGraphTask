import re
from config import TIMESTAMP_PATTERNS, INPUT_DETECTION_TIMESTAMP_FIELDS

def detect_input_type(state):
    """Detect whether input is raw text or structured data and set routing flags."""

    print("Detecting input type...")

    # Check if we have raw text input
    if state.raw_input and not state.structured_data:
        print("Raw text input detected.")
        state.is_raw_text = True
        # For raw text, try to detect if it contains timestamps
        state.has_timestamps = _contains_timestamps(state.raw_input)

    # Check if we have structured data
    elif state.structured_data and not state.raw_input:
        print("Structured data input detected.")
        state.is_raw_text = False
        # Check if structured data has timestamp fields
        state.has_timestamps = _has_timestamp_fields(state.structured_data)

    # Error case - no input provided
    elif not state.raw_input and not state.structured_data:
        print("No input provided.")
        if not state.errors:
            state.errors = []
        state.errors.append("No input provided - need either raw_input or structured_data")
        state.is_raw_text = False
        state.has_timestamps = False

    # Error case - both inputs provided (should choose one path)
    else:

        print("Both inputs provided - defaulting to structured data path.")

        if not state.errors:
            state.errors = []
        state.errors.append("Both raw_input and structured_data provided - using structured_data")
        state.is_raw_text = False
        state.has_timestamps = _has_timestamp_fields(state.structured_data)

    return state

def _contains_timestamps(text):
    """Check if raw text contains timestamp patterns."""
    for pattern in TIMESTAMP_PATTERNS:
        if re.search(pattern, text):
            return True

    return False

def _has_timestamp_fields(data):
    """Check if structured data contains timestamp fields."""

    print("Checking for timestamp fields in structured data...")

    if not data or not isinstance(data, list) or len(data) == 0:
        return False

    # Check first item for timestamp fields
    first_item = data[0]
    if not isinstance(first_item, dict):
        return False

    # Use configured timestamp field names
    for field in INPUT_DETECTION_TIMESTAMP_FIELDS:
        if field in first_item:
            return True

    return False