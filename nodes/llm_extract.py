import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict
from config import (OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
                   HEALTH_ANALYSIS_SYSTEM_PROMPT, LLM_FUNCTION_CONFIG,
                   HEALTH_ANALYSIS_PROMPT_TEMPLATE, HEALTH_INSIGHTS_JSON_SCHEMA)

class HealthInsights(BaseModel):
    """Schema for LLM-extracted communication health insights."""
    tone_indicators: List[str] = Field(description="List of tone descriptors found in messages")
    clarity_score: float = Field(ge=0, le=10, description="Clarity rating 0-10")
    responsiveness_patterns: List[str] = Field(description="Patterns of response behavior observed")
    engagement_level: float = Field(ge=0, le=10, description="Overall engagement level 0-10")
    conflict_indicators: List[str] = Field(description="Signs of tension or conflict")
    collaboration_indicators: List[str] = Field(description="Signs of positive collaboration")
    communication_issues: List[str] = Field(description="Specific communication problems identified")
    positive_patterns: List[str] = Field(description="Healthy communication patterns observed")
    key_topics: List[str] = Field(description="Main topics discussed in this chunk")
    emotional_indicators: Dict[str, int] = Field(description="Emotional tone counts (positive, negative, neutral)")

def llm_extract(state):
    """Extract semantic insights from conversation chunks using LLM analysis."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    # Progress tracking
    state.current_step += 1
    state.add_log(f"[{state.current_step}/{state.total_steps}] LLM_EXTRACT: Analyzing conversation insights...")

    if not hasattr(state, 'chunks') or not state.chunks:
        state.add_error("llm_extract: No chunks available for analysis")
        return state

    try:
        state.add_log("Initializing OpenAI client...")
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Store insights for each chunk
        chunk_insights = []

        for chunk_idx, chunk in enumerate(state.chunks):
            state.add_log(f"Analyzing chunk {chunk_idx + 1}/{len(state.chunks)}...")
            # Create prompt for this chunk
            prompt = _create_analysis_prompt(chunk, chunk_idx, reporter)

            # Use the JSON schema from config
            schema = HEALTH_INSIGHTS_JSON_SCHEMA

            # Call OpenAI with JSON schema enforcement
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": HEALTH_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": LLM_FUNCTION_CONFIG['health_schema_name'],
                        "schema": schema
                    }
                },
                temperature=OPENAI_TEMPERATURE,
                max_tokens=OPENAI_MAX_TOKENS
            )

            # Parse the response
            insights = json.loads(response.choices[0].message.content)

            # Add chunk metadata
            insights['chunk_index'] = chunk_idx
            insights['chunk_size'] = len(chunk)
            insights['chunk_speakers'] = list(set(msg['speaker'] for msg in chunk))

            chunk_insights.append(insights)

        # Store insights in state
        state.llm_insights = chunk_insights
        state.add_log(f"✓ [{state.current_step}/{state.total_steps}] LLM_EXTRACT: {len(chunk_insights)} chunks analyzed successfully")

    except Exception as e:
        state.add_error(f"llm_extract: LLM analysis failed - {str(e)}")
        state.add_log(f"✗ [{state.current_step}/{state.total_steps}] LLM_EXTRACT: LLM analysis failed - {str(e)}")

    return state

def _create_analysis_prompt(chunk, chunk_idx, reporter):
    """Create analysis prompt for a conversation chunk."""
    reporter.add_log(f"Creating analysis prompt for chunk {chunk_idx + 1}...", 1, flush=True)
    # Format the conversation messages
    formatted_messages = []
    for msg in chunk:
        timestamp = f" [{msg.get('timestamp', 'no timestamp')}]" if msg.get('timestamp') else ""
        formatted_messages.append(f"{msg['speaker']}{timestamp}: {msg['text']}")

    conversation_text = "\n".join(formatted_messages)

    # Use the template from config
    prompt = HEALTH_ANALYSIS_PROMPT_TEMPLATE.format(
        chunk_idx=chunk_idx + 1,
        conversation_text=conversation_text
    )

    return prompt