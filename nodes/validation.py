import os
import json
from datetime import datetime
from openai import OpenAI
from config import (MIN_TEXT_LENGTH, MAX_TEXT_LENGTH, MAX_SPEAKER_LENGTH,
                   MIN_VALID_ITEMS_FOR_ANALYSIS, REQUIRED_MESSAGE_FIELDS,
                   INVALID_SPEAKER_NAMES, VALID_COMMUNICATION_TYPES,
                   TIMESTAMP_VALIDATION_FORMATS, OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
                   STRUCTURE_EXTRACTION_JSON_SCHEMA, LLM_FUNCTION_CONFIG, REMEDIATION_SYSTEM_PROMPT,
                   REMEDIATION_PROMPT_TEMPLATE)

def validate_schema(state):
    """Validate data against expected schema."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    state.add_log("Validating schema and data integrity...")

    # Check if we have data to validate
    data_to_validate = state.validated_data or state.structured_data

    if not data_to_validate:
        state.add_error("validation: No data to validate", 1)
        return state

    if not isinstance(data_to_validate, list):
        state.add_error("validation: Data must be a list of communication items", 1)
        return state

    state.add_log(f"Starting validation of {len(data_to_validate)} items...")
    # Validate each item
    valid_items = []
    invalid_count = 0

    for i, item in enumerate(data_to_validate):
        validation_result = _validate_single_item(item, i, reporter)

        if validation_result['valid']:
            valid_items.append(item)
        else:
            invalid_count += 1

    # Check if we have enough valid items for meaningful analysis
    if len(valid_items) < MIN_VALID_ITEMS_FOR_ANALYSIS:
        state.add_error(f"validation: Need at least {MIN_VALID_ITEMS_FOR_ANALYSIS} valid items for analysis, got {len(valid_items)}")
        return state

    # Log validation summary
    if invalid_count > 0:
        state.add_log(f"Found {invalid_count} invalid items but proceeding with {len(valid_items)} valid items")

    # Update state with validated data
    state.validated_data = valid_items
    state.add_log(f"Schema validation completed. {len(valid_items)} items validated successfully.")

    return state

def _validate_single_item(item, index, reporter):
    """Validate a single communication item."""
    reporter.add_log(f"Validating item {index}...", 1, flush=True)

    is_valid = True

    if not isinstance(item, dict):
        reporter.add_error(f"validation: Item {index} is not a dictionary")
        return {'valid': False}

    # Required field validation
    reporter.add_log("Checking required fields...", 1, flush=True)
    for field in REQUIRED_MESSAGE_FIELDS:
        if field not in item or not item[field]:
            reporter.add_error(f"validation: Item {index} missing required field '{field}'")
            reporter.add_log(f"Item {index} missing required field '{field}'", 1, flush=True)
            is_valid = False
        elif isinstance(item[field], str) and len(item[field].strip()) == 0:
            reporter.add_error(f"validation: Item {index} has empty '{field}' field")
            reporter.add_log(f"Item {index} has empty '{field}' field", 1, flush=True)
            is_valid = False

    # Text content validation
    reporter.add_log("Validating text content...", 1, flush=True)
    if 'text' in item and item['text']:
        text = str(item['text']).strip()

        if len(text) < MIN_TEXT_LENGTH:
            reporter.add_log(f"Item {index} text too short (minimum {MIN_TEXT_LENGTH} characters)", 1, flush=True)
            reporter.add_error(f"validation: Item {index} text too short (minimum {MIN_TEXT_LENGTH} characters)")
            is_valid = False
        elif len(text) > MAX_TEXT_LENGTH:
            reporter.add_log(f"Item {index} text too long (maximum {MAX_TEXT_LENGTH} characters)", 1, flush=True)
            reporter.add_error(f"validation: Item {index} text too long (maximum {MAX_TEXT_LENGTH} characters)")
            is_valid = False

    # Speaker validation
    reporter.add_log("Validating speaker...", 1, flush=True)
    if 'speaker' in item and item['speaker']:
        speaker = str(item['speaker']).strip()

        if len(speaker) > MAX_SPEAKER_LENGTH:
            reporter.add_log(f"Item {index} speaker name too long (maximum {MAX_SPEAKER_LENGTH} characters)", 1, flush=True)
            reporter.add_error(f"validation: Item {index} speaker name too long (maximum {MAX_SPEAKER_LENGTH} characters)")
            is_valid = False

        # Check for suspicious speaker patterns
        if speaker.lower() in INVALID_SPEAKER_NAMES:
            reporter.add_error(f"validation: Item {index} has invalid speaker name '{speaker}'")
            is_valid = False

    # Timestamp validation (if present)
    reporter.add_log("Validating timestamp...", 1, flush=True)
    if 'timestamp' in item and item['timestamp']:
        if not _is_valid_timestamp(item['timestamp'], reporter):
            reporter.add_error(f"validation: Item {index} has invalid timestamp format")
            is_valid = False

    # Type validation (if present)
    reporter.add_log("Validating communication type...", 1, flush=True)
    if 'type' in item and item['type']:
        if item['type'].lower() not in VALID_COMMUNICATION_TYPES:
            # Not an error, just normalize to 'message'
            item['type'] = 'message'

    return {'valid': is_valid}

def _is_valid_timestamp(timestamp_str, reporter):
    """Check if timestamp is in valid format."""
    reporter.add_log(f"Checking timestamp format: {timestamp_str}", 2, flush=True)

    if not isinstance(timestamp_str, str):
        reporter.add_log("Timestamp is not a string", 2, flush=True)
        return False

    # Try to parse common formats
    for fmt in TIMESTAMP_VALIDATION_FORMATS:
        try:
            datetime.strptime(timestamp_str.strip(), fmt)
            reporter.add_log(f"Timestamp successfully parsed with format: {fmt}", 2, flush=True)
            return True
        except ValueError as e:
            reporter.add_log(f"Failed parsing with format {fmt}: {str(e)}", 2, flush=True)

    reporter.add_log("All timestamp format validations failed", 2, flush=True)
    return False

def remediation_llm(state):
    """Use LLM to fix validation errors."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    state.add_log("Attempting LLM-based error remediation...")

    # Get the problematic data
    data_to_fix = state.validated_data or state.structured_data

    if not data_to_fix or not state.errors:
        state.add_log("No data or errors to remediate")
        return state

    # Filter validation errors (ignore other types)
    validation_errors = [error for error in state.errors if 'validation:' in error]

    if not validation_errors:
        state.add_log("No validation errors found to remediate")
        return state

    state.add_log(f"Found {len(validation_errors)} validation errors to fix")

    try:
        # Attempt to fix the data using LLM
        fixed_data = _fix_data_with_llm(data_to_fix, validation_errors, reporter)

        if fixed_data:
            # Re-validate the fixed data
            state.add_log("Re-validating fixed data...")
            temp_state = type(state)(structured_data=fixed_data, errors=[], log_enabled=False)
            temp_reporter = temp_state.get_reporter()

            valid_items = []
            remaining_errors = 0

            for i, item in enumerate(fixed_data):
                validation_result = _validate_single_item(item, i, temp_reporter)
                if validation_result['valid']:
                    valid_items.append(item)
                else:
                    remaining_errors += 1

            if len(valid_items) >= MIN_VALID_ITEMS_FOR_ANALYSIS:
                state.add_log(f"Remediation successful! Fixed {len(valid_items)} items (was {len(data_to_fix)})")
                state.validated_data = valid_items
                # Clear validation errors since they've been fixed
                state.errors = [error for error in state.errors if 'validation:' not in error]
            else:
                state.add_error(f"Remediation insufficient: only {len(valid_items)} valid items after fixing")
        else:
            state.add_error("LLM remediation failed to produce valid data")

    except Exception as e:
        state.add_error(f"remediation: LLM call failed - {str(e)}")

    return state

def _fix_data_with_llm(data, errors, reporter):
    """Use LLM to fix validation errors in communication data."""
    reporter.add_log("Preparing remediation prompt for LLM...", 1, flush=True)

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create the remediation prompt
        prompt = _create_remediation_prompt(data, errors)

        reporter.add_log("Calling OpenAI API for data remediation...", 1, flush=True)

        # Call OpenAI with JSON schema enforcement using existing schema
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": REMEDIATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": LLM_FUNCTION_CONFIG['remediation_schema_name'],
                    "schema": STRUCTURE_EXTRACTION_JSON_SCHEMA
                }
            },
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )

        reporter.add_log("Parsing LLM remediation response...", 1, flush=True)

        # Parse the response
        result = json.loads(response.choices[0].message.content)
        fixed_data = result.get("messages", [])

        if fixed_data:
            reporter.add_log(f"LLM successfully processed {len(fixed_data)} items", 1)
            return fixed_data
        else:
            reporter.add_error("LLM returned empty results", 1)
            return None

    except Exception as e:
        reporter.add_error(f"LLM remediation failed: {str(e)}", 1)
        return None

def _create_remediation_prompt(data, errors):
    """Create the prompt for LLM to fix validation errors."""

    # Limit data size for prompt (take first 10 items to avoid token limits)
    sample_data = data[:10] if len(data) > 10 else data

    return REMEDIATION_PROMPT_TEMPLATE.format(
        data=json.dumps(sample_data, indent=2),
        errors=chr(10).join(errors)
    )