import re
from config import TIMESTAMP_PATTERNS, INPUT_DETECTION_TIMESTAMP_FIELDS

def detect_input_type(state):
    """Detect whether input is raw text or structured data and set routing flags."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    # Progress tracking
    state.current_step += 1
    state.add_log(f"[{state.current_step}/{state.total_steps}] INPUT_DETECTION: Analyzing input type...")

    # Check if we have raw text input
    if state.raw_input and not state.structured_data:
        state.is_raw_text = True
        # For raw text, try to detect if it contains timestamps
        state.has_timestamps = _contains_timestamps(reporter, state.raw_input)
        timestamps_info = "timestamps found" if state.has_timestamps else "no timestamps"
        state.add_log(f"✓ [{state.current_step}/{state.total_steps}] INPUT_DETECTION: Raw text detected ({len(state.raw_input)} chars, {timestamps_info})")

    # Check if we have structured data
    elif state.structured_data and not state.raw_input:
        state.is_raw_text = False
        # Check if structured data has timestamp fields
        state.has_timestamps = _has_timestamp_fields(reporter, state.structured_data)
        timestamps_info = "timestamps found" if state.has_timestamps else "no timestamps"
        state.add_log(f"✓ [{state.current_step}/{state.total_steps}] INPUT_DETECTION: Structured data detected ({len(state.structured_data)} items, {timestamps_info})")

    # Error case - no input provided
    elif not state.raw_input and not state.structured_data:
        state.add_error("No input provided - need either raw_input or structured_data")
        state.add_log(f"✗ [{state.current_step}/{state.total_steps}] INPUT_DETECTION: No input provided")
        state.is_raw_text = False
        state.has_timestamps = False

    # Error case - both inputs provided (should choose one path)
    else:
        state.add_error("Both raw_input and structured_data provided - defaulting to structured_data")
        state.is_raw_text = False
        state.has_timestamps = _has_timestamp_fields(reporter, state.structured_data)
        state.add_log(f"⚠ [{state.current_step}/{state.total_steps}] INPUT_DETECTION: Both inputs provided, using structured data")

    return state

def _contains_timestamps(reporter, text):
    """Check if raw text contains timestamp patterns."""
    for pattern in TIMESTAMP_PATTERNS:
        if re.search(pattern, text):
            reporter.add_log("Timestamp pattern detected in raw text.", 1, flush=True)
            return True
    reporter.add_log("No timestamp patterns found in raw text. Returning False.", 1)
    return False

def _has_timestamp_fields(reporter, data):
    """Check if structured data contains timestamp fields."""
    if not data or not isinstance(data, list) or len(data) == 0:
        reporter.add_log("Structured data is empty or not a list. Returning False.", 1)
        return False

    # Check first item for timestamp fields
    first_item = data[0]
    if not isinstance(first_item, dict):
        reporter.add_log("First item in structured data is not a dictionary. Returning False.", 1)
        return False

    # Use configured timestamp field names
    for field in INPUT_DETECTION_TIMESTAMP_FIELDS:
        if field in first_item:
            reporter.add_log(f"Timestamp field '{field}' detected in structured data.", 1)
            return True
    reporter.add_log("No timestamp fields found in structured data. Returning False.", 1)
    return False