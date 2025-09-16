import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from config import (OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
                   STRUCTURE_EXTRACTION_SYSTEM_PROMPT, LLM_FUNCTION_CONFIG)

class CommunicationTurn(BaseModel):
    """Schema for a single communication turn/message."""
    speaker: str = Field(description="Name of the speaker/participant")
    text: str = Field(description="The message content")
    timestamp: Optional[str] = Field(default=None, description="ISO format timestamp if detectable, otherwise null")
    type: str = Field(default="message", description="Type of communication: message, meeting, email, chat")

class CommunicationData(BaseModel):
    """Schema for the complete structured communication data."""
    messages: List[CommunicationTurn] = Field(description="List of communication turns/messages")

def structure_from_text(state):
    """Convert raw text into structured JSON format using LLM."""

    if not state.raw_input:
        if not state.errors:
            state.errors = []
        state.errors.append("structure_from_text: No raw input to process")
        return state

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Create the prompt for structure extraction
        prompt = _create_structure_prompt(state.raw_input)

        # Define the JSON schema
        schema = {
            "type": "object",
            "properties": {
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "speaker": {"type": "string", "description": "Name of the speaker/participant"},
                            "text": {"type": "string", "description": "The message content"},
                            "timestamp": {"type": ["string", "null"], "description": "ISO format timestamp if detectable, otherwise null"},
                            "type": {"type": "string", "description": "Type of communication: message, meeting, email, chat"}
                        },
                        "required": ["speaker", "text", "type"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["messages"],
            "additionalProperties": False
        }

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

        # Parse the response
        result = json.loads(response.choices[0].message.content)
        structured_data = result.get("messages", [])

        if structured_data:
            state.structured_data = structured_data
            state.is_raw_text = False  # Now it's structured
        else:
            if not state.errors:
                state.errors = []
            state.errors.append("structure_from_text: Failed to extract messages from LLM response")

    except Exception as e:
        if not state.errors:
            state.errors = []
        state.errors.append(f"structure_from_text: LLM call failed - {str(e)}")
        print(f"Error: {e}")


    return state

def _create_structure_prompt(raw_text):
    """Create the prompt for the LLM to structure the text."""

    prompt = f"""You are a communication analyst. Convert this raw text into structured messages for analysis.

INPUT TEXT:
{raw_text}

TASK: Parse this conversation and extract each distinct speaker contribution as a separate message.

RULES:
1. Extract each distinct speaker contribution as a separate message
2. Clean up speaker names (remove ":", ">>", email addresses, etc.)
3. Extract timestamps if present in any format, convert to ISO (YYYY-MM-DDTHH:MM:SS)
4. If no timestamps are present, set timestamp to null
5. Detect conversation type: "message", "meeting", "email", "chat"
6. Preserve the original message content but clean up formatting
7. Skip system messages like "joined the call", "left the meeting"

The output will be automatically structured according to the required schema."""

    return prompt