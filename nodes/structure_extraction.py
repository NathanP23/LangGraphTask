import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from config import (OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
                   STRUCTURE_EXTRACTION_SYSTEM_PROMPT, LLM_FUNCTION_CONFIG,
                   STRUCTURE_EXTRACTION_PROMPT_TEMPLATE, STRUCTURE_EXTRACTION_JSON_SCHEMA)

def structure_from_text(state):
    """Convert raw text into structured JSON format using LLM."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    state.add_log("Converting raw text to structured format using LLM...")

    if not state.raw_input:
        state.add_error("structure_from_text: No raw input to process")
        return state

    try:
        state.add_log("Initializing OpenAI client...")
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create the prompt for structure extraction
        prompt = _create_structure_prompt(state.raw_input, reporter)

        # Use the JSON schema from config
        schema = STRUCTURE_EXTRACTION_JSON_SCHEMA
        state.add_log("JSON schema for structured output is ready to use.")

        state.add_log("Calling OpenAI API for text structuring...")
        # Call OpenAI with JSON schema enforcement
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": STRUCTURE_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": LLM_FUNCTION_CONFIG['structure_schema_name'],
                    "schema": schema
                }
            },
            temperature=OPENAI_TEMPERATURE,
            max_tokens=OPENAI_MAX_TOKENS
        )

        state.add_log("Parsing LLM response...")
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        structured_data = result.get("messages", [])

        if structured_data:
            state.add_log(f"Successfully extracted {len(structured_data)} messages from text")
            state.structured_data = structured_data
            state.is_raw_text = False  # Now it's structured
        else:
            state.add_error("structure_from_text: Failed to extract messages from LLM response")

    except Exception as e:
        state.add_error(f"structure_from_text: LLM call failed - {str(e)}")
    return state

def _create_structure_prompt(raw_text, reporter):
    """Create the prompt for the LLM to structure the text."""
    reporter.add_log("Structure extraction prompt created.", 1)
    return STRUCTURE_EXTRACTION_PROMPT_TEMPLATE.format(raw_text=raw_text)