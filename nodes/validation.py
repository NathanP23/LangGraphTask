from datetime import datetime
from config import (MIN_TEXT_LENGTH, MAX_TEXT_LENGTH, MAX_SPEAKER_LENGTH,
                   MIN_VALID_ITEMS_FOR_ANALYSIS, REQUIRED_MESSAGE_FIELDS,
                   INVALID_SPEAKER_NAMES, VALID_COMMUNICATION_TYPES,
                   TIMESTAMP_VALIDATION_FORMATS)

def validate_schema(state):
    """Validate data against expected schema."""
    print("Validating schema...")
    # Initialize errors if not exists
    if not state.errors:
        state.errors = []

    # Check if we have data to validate
    data_to_validate = state.validated_data or state.structured_data

    if not data_to_validate:
        state.errors.append("validation: No data to validate")
        return state

    if not isinstance(data_to_validate, list):
        state.errors.append("validation: Data must be a list of communication items")
        return state

    # Validate each item
    valid_items = []
    validation_errors = []

    for i, item in enumerate(data_to_validate):
        validation_result = _validate_single_item(item, i)

        if validation_result['valid']:
            valid_items.append(item)
        else:
            validation_errors.extend(validation_result['errors'])

    # Check if we have enough valid items for meaningful analysis
    if len(valid_items) < MIN_VALID_ITEMS_FOR_ANALYSIS:
        state.errors.append(f"validation: Need at least {MIN_VALID_ITEMS_FOR_ANALYSIS} valid items for analysis, got {len(valid_items)}")
        return state

    # Add validation errors but don't fail completely if we have some valid items
    if validation_errors:
        state.errors.extend(validation_errors)

    # Update state with validated data
    state.validated_data = valid_items

    return state

def _validate_single_item(item, index):
    """Validate a single communication item."""
    print(f"Validating item {index}...")
    errors = []

    if not isinstance(item, dict):
        return {
            'valid': False,
            'errors': [f"validation: Item {index} is not a dictionary"]
        }

    # Required field validation
    print("Checking required fields...")
    for field in REQUIRED_MESSAGE_FIELDS:
        if field not in item or not item[field]:
            errors.append(f"validation: Item {index} missing required field '{field}'")
        elif isinstance(item[field], str) and len(item[field].strip()) == 0:
            errors.append(f"validation: Item {index} has empty '{field}' field")

    # Text content validation
    print("Validating text content...")
    if 'text' in item and item['text']:
        text = str(item['text']).strip()

        if len(text) < MIN_TEXT_LENGTH:
            errors.append(f"validation: Item {index} text too short (minimum {MIN_TEXT_LENGTH} characters)")
        elif len(text) > MAX_TEXT_LENGTH:
            errors.append(f"validation: Item {index} text too long (maximum {MAX_TEXT_LENGTH} characters)")

    # Speaker validation
    print("Validating speaker...")
    if 'speaker' in item and item['speaker']:
        speaker = str(item['speaker']).strip()

        if len(speaker) > MAX_SPEAKER_LENGTH:
            errors.append(f"validation: Item {index} speaker name too long (maximum {MAX_SPEAKER_LENGTH} characters)")

        # Check for suspicious speaker patterns
        if speaker.lower() in INVALID_SPEAKER_NAMES:
            errors.append(f"validation: Item {index} has invalid speaker name '{speaker}'")

    # Timestamp validation (if present)
    print("Validating timestamp...")
    if 'timestamp' in item and item['timestamp']:
        if not _is_valid_timestamp(item['timestamp']):
            errors.append(f"validation: Item {index} has invalid timestamp format")

    # Type validation (if present)
    print("Validating communication type...")
    if 'type' in item and item['type']:
        if item['type'].lower() not in VALID_COMMUNICATION_TYPES:
            # Not an error, just normalize to 'message'
            item['type'] = 'message'

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def _is_valid_timestamp(timestamp_str):
    """Check if timestamp is in valid format."""

    print(f"Checking timestamp format: {timestamp_str}")
    
    if not isinstance(timestamp_str, str):
        return False

    # Try to parse common formats
    for fmt in TIMESTAMP_VALIDATION_FORMATS:
        try:
            datetime.strptime(timestamp_str.strip(), fmt)
            return True
        except ValueError:
            print(f"❌ Error: {ValueError}")

    return False

def remediation_llm(state):
    """Use LLM to fix validation errors."""
    # For now, just log that remediation was attempted
    # TODO: Implement LLM-based error remediation

    if not state.errors:
        state.errors = []

    state.errors.append("remediation: LLM remediation attempted but not yet implemented")

    # For now, just return the state as-is
    # In a full implementation, this would use an LLM to try to fix validation issues
    return state