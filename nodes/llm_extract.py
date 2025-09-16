import os
import json
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Dict
from config import (OPENAI_MODEL, OPENAI_TEMPERATURE, OPENAI_MAX_TOKENS,
                   HEALTH_ANALYSIS_SYSTEM_PROMPT, LLM_FUNCTION_CONFIG)

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

    print("Extracting insights using LLM...")

    if not hasattr(state, 'chunks') or not state.chunks:
        if not state.errors:
            state.errors = []
        state.errors.append("llm_extract: No chunks available for analysis")
        return state

    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Store insights for each chunk
        chunk_insights = []

        for chunk_idx, chunk in enumerate(state.chunks):
            # Create prompt for this chunk
            prompt = _create_analysis_prompt(chunk, chunk_idx)

            # Define the JSON schema for health insights
            schema = {
                "type": "object",
                "properties": {
                    "tone_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tone descriptors found in messages"
                    },
                    "clarity_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 10,
                        "description": "Clarity rating 0-10"
                    },
                    "responsiveness_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Patterns of response behavior observed"
                    },
                    "engagement_level": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 10,
                        "description": "Overall engagement level 0-10"
                    },
                    "conflict_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Signs of tension or conflict"
                    },
                    "collaboration_indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Signs of positive collaboration"
                    },
                    "communication_issues": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific communication problems identified"
                    },
                    "positive_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Healthy communication patterns observed"
                    },
                    "key_topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Main topics discussed in this chunk"
                    },
                    "emotional_indicators": {
                        "type": "object",
                        "properties": {
                            "positive": {"type": "integer", "minimum": 0},
                            "negative": {"type": "integer", "minimum": 0},
                            "neutral": {"type": "integer", "minimum": 0}
                        },
                        "required": ["positive", "negative", "neutral"],
                        "additionalProperties": False,
                        "description": "Emotional tone counts (positive, negative, neutral)"
                    }
                },
                "required": [
                    "tone_indicators", "clarity_score", "responsiveness_patterns",
                    "engagement_level", "conflict_indicators", "collaboration_indicators",
                    "communication_issues", "positive_patterns", "key_topics", "emotional_indicators"
                ],
                "additionalProperties": False
            }

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

    except Exception as e:
        if not state.errors:
            state.errors = []
        state.errors.append(f"llm_extract: LLM analysis failed - {str(e)}")
        print(f"❌ Error: {e}")

    return state

def _create_analysis_prompt(chunk, chunk_idx):
    """Create analysis prompt for a conversation chunk."""
    print(f"Creating analysis prompt for chunk {chunk_idx + 1}...")
    # Format the conversation messages
    formatted_messages = []
    for msg in chunk:
        timestamp = f" [{msg.get('timestamp', 'no timestamp')}]" if msg.get('timestamp') else ""
        formatted_messages.append(f"{msg['speaker']}{timestamp}: {msg['text']}")

    conversation_text = "\n".join(formatted_messages)

    prompt = f"""You are analyzing communication health in a workplace conversation.

CONVERSATION CHUNK #{chunk_idx + 1}:
{conversation_text}

ANALYSIS TASK:
Analyze this conversation segment for communication health indicators. Focus on:

1. **Tone Analysis**: Identify tone descriptors (professional, friendly, tense, supportive, etc.)
2. **Clarity**: Rate how clear and understandable the communication is (0-10)
3. **Responsiveness**: Identify patterns in how people respond to each other
4. **Engagement**: Rate overall participant engagement level (0-10)
5. **Conflict Detection**: Look for signs of tension, disagreement, or conflict
6. **Collaboration**: Identify positive teamwork and collaboration indicators
7. **Communication Issues**: Spot problems like unclear requests, ignored questions, etc.
8. **Positive Patterns**: Identify healthy communication behaviors
9. **Key Topics**: Extract the main subjects being discussed
10. **Emotional Tone**: Count messages with positive, negative, or neutral emotional tone

IMPORTANT GUIDELINES:
- Be objective and evidence-based in your analysis
- Look for subtle patterns, not just obvious ones
- Consider context and workplace communication norms
- Focus on actionable insights for improving communication health
- Rate clarity and engagement on realistic scales (5-7 is average, 8+ is excellent)

The output will be automatically structured according to the required schema."""

    return prompt