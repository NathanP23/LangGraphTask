# Configuration file for Communication Health Analysis
# Contains all hardcoded values and parameters used throughout the pipeline
# Variables organized by LangGraph node execution order

# =============================================================================
# GENERAL CONFIG
# =============================================================================

# Debug logging flag - set to False to disable debug print statements
DEBUG_LOGGING = True

# OpenAI configuration
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 1500

# LLM function configuration
LLM_FUNCTION_CONFIG = {
    'structure_schema_name': 'CommunicationData',
    'health_schema_name': 'HealthInsights',
    'remediation_schema_name': 'FixedCommunicationData'
}

# =============================================================================
# 1. INPUT DETECTION CONFIG (detect_input_type)
# =============================================================================

# Timestamp detection patterns for raw text analysis
TIMESTAMP_PATTERNS = [
    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',           # ISO format
    r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',          # ISO-like with space
    r'\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}',        # MM/DD/YYYY HH:MM
    r'\d{2}:\d{2}:\d{2}',                               # HH:MM:SS only
    r'\d{1,2}:\d{2}\s*(AM|PM)',                         # 12-hour format
]

# Input detection timestamp field names
INPUT_DETECTION_TIMESTAMP_FIELDS = ['ts', 'timestamp', 'time', 'date', 'created_at', 'sent_at']

# =============================================================================
# 2. STRUCTURE EXTRACTION CONFIG (structure_from_text)
# =============================================================================

STRUCTURE_EXTRACTION_SYSTEM_PROMPT = "You are a communication analyst that converts raw text into structured conversation data."

STRUCTURE_EXTRACTION_PROMPT_TEMPLATE = """You are a communication analyst. Convert this raw text into structured messages for analysis.

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

STRUCTURE_EXTRACTION_JSON_SCHEMA = {
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
                "required": ["speaker", "text", "timestamp", "type"],
                "additionalProperties": False
            }
        }
    },
    "required": ["messages"],
    "additionalProperties": False
}

# LLM prompt rules for structure extraction
STRUCTURE_EXTRACTION_RULES = [
    "Extract each distinct speaker contribution as a separate message",
    "Clean up speaker names (remove \":\", \">>\", email addresses, etc.)",
    "Extract timestamps if present in any format, convert to ISO (YYYY-MM-DDTHH:MM:SS)",
    "If no timestamps are present, set timestamp to null",
    "Detect conversation type: \"message\", \"meeting\", \"email\", \"chat\"",
    "Preserve the original message content but clean up formatting",
    "Skip system messages like \"joined the call\", \"left the meeting\""
]

# =============================================================================
# 3. NORMALIZATION CONFIG (normalize_structured)
# =============================================================================

# Field names for extracting different components during normalization
NORMALIZATION_TIMESTAMP_FIELDS = ['ts', 'timestamp', 'time', 'date', 'created_at', 'sent_at']
NORMALIZATION_SPEAKER_FIELDS = ['speaker', 'author', 'from', 'user', 'name']
NORMALIZATION_TEXT_FIELDS = ['text', 'content', 'message', 'body']
NORMALIZATION_TYPE_FIELDS = ['kind', 'type', 'category']

# Minimum meaningful text length
NORMALIZATION_MIN_TEXT_LENGTH = 3

# Timestamp parsing formats for normalization
NORMALIZATION_TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",      # ISO with Z (most specific first)
    "%Y-%m-%dT%H:%M:%S",       # ISO without Z
    "%Y-%m-%d %H:%M:%S",       # Standard datetime
    "%Y-%m-%d",                # Date only
    "%m/%d/%Y",                # US date only
    "%d/%m/%Y"                 # European date only
]

# Speaker name cleaning pattern (remove email brackets and @ symbols)
NORMALIZATION_SPEAKER_CLEANING_PATTERN = r'[<>@]'

# Field names to exclude from metadata (these are processed as main fields)
NORMALIZATION_EXCLUDED_METADATA_FIELDS = [
    'ts', 'timestamp', 'time', 'date', 'created_at', 'sent_at',
    'speaker', 'author', 'from', 'user', 'name',
    'text', 'content', 'message', 'body',
    'kind', 'type', 'category'
]

# =============================================================================
# 4. VALIDATION CONFIG (validate_schema + remediation_llm)
# =============================================================================

# System prompt for LLM-based data remediation
REMEDIATION_SYSTEM_PROMPT = "You are a data remediation specialist. Fix validation errors in communication data while preserving the original meaning and context."

# Prompt template for LLM-based data remediation
REMEDIATION_PROMPT_TEMPLATE = """You are tasked with fixing validation errors in communication data.

PROBLEMATIC DATA:
{data}

VALIDATION ERRORS FOUND:
{errors}

TASK:
Fix the above data to resolve ALL validation errors while preserving the original meaning and context.

FIXING RULES:
1. **Missing speakers**: Infer speaker names from context, conversation flow, or use "Participant_N" if impossible
2. **Invalid timestamps**: Convert to ISO format (YYYY-MM-DDTHH:MM:SS) or set to null if unparseable
3. **Empty/short text**: Remove items with insufficient content (less than 3 characters)
4. **Invalid types**: Use 'message', 'meeting', 'email', or 'chat' - default to 'message'
5. **Long content**: Truncate text that's too long while preserving key meaning
6. **Invalid speaker names**: Replace 'unknown', 'null', empty strings with meaningful names

CONTEXT CLUES FOR SPEAKER INFERENCE:
- Look for patterns like "Thanks John" → previous speaker might be John
- Email signatures, usernames, or @mentions
- Conversation flow and responses
- Use "Participant_1", "Participant_2" etc. as fallback

Return the fixed data in the same JSON structure with 'messages' array containing the corrected communication items."""

# Validation thresholds
MIN_VALID_ITEMS_FOR_ANALYSIS = 2
REQUIRED_MESSAGE_FIELDS = ['speaker', 'text']
INVALID_SPEAKER_NAMES = ['unknown', 'null', 'none', '']
VALID_COMMUNICATION_TYPES = ['message', 'meeting', 'email', 'chat', 'call', 'document']


# Text length constraints
MIN_TEXT_LENGTH = 3
MAX_TEXT_LENGTH = 10000

# Speaker name constraints
MIN_SPEAKER_LENGTH = 1
MAX_SPEAKER_LENGTH = 100


# Timestamp validation formats
TIMESTAMP_VALIDATION_FORMATS = [
    "%Y-%m-%dT%H:%M:%S",       # ISO without Z
    "%Y-%m-%dT%H:%M:%SZ",      # ISO with Z
    "%Y-%m-%d %H:%M:%S",       # Standard datetime
    "%Y-%m-%d",                # Date only
]



# =============================================================================
# 7. STATISTICS CONFIG (basic_stats_full/basic_stats_text)
# =============================================================================

# Question detection patterns
QUESTION_PATTERNS = [
    r'\?',                                              # Direct question mark
    r'\b(what|how|when|where|why|who|which|can|could|would|should|is|are|do|does|will)\b.*\?',
    r'\b(what about|how about|what if|what do you think|any thoughts)\b',
    r'\b(please clarify|can you explain|could you tell me)\b'
]

# Response time thresholds (minutes)
RESPONSE_TIME_THRESHOLDS = {
    'excellent': 5,      # < 5 minutes
    'good': 30,         # < 30 minutes
    'fair': 120,        # < 2 hours
    'poor': 480         # < 8 hours
}

# =============================================================================
# 5. PREPROCESSING CONFIG (dedupe_threads + chunk_if_needed)
# =============================================================================

# Email deduplication settings
EMAIL_SIGNATURE_PATTERNS = [
    r'^--\s*$',                                         # Standard signature delimiter
    r'^Best regards',
    r'^Best,',
    r'^Thanks,',
    r'^Sincerely,',
    r'^Cheers,',
    r'^Sent from my',
    r'^Get Outlook for',
]

EMAIL_QUOTE_PATTERNS = [
    r'^>',                                              # Lines starting with >
    r'^On .* wrote:',                                   # "On ... wrote:" headers
    r'^From:.*',                                        # Email headers
    r'^To:.*',
    r'^Subject:.*',
    r'^Date:.*',
    r'^Sent:.*',
    r'^.*@.*\..*:$',                                   # Email addresses followed by colon
    r'^\s*-+\s*Original Message\s*-+',                # Outlook style
    r'^\s*-+\s*Forwarded message\s*-+',               # Forward headers
]

# Chunking configuration
MAX_CHUNK_TOKENS = 3000                                # Conservative limit for LLM context
MIN_CHUNK_SIZE = 5                                     # Minimum messages per chunk
CHARS_PER_TOKEN_ESTIMATE = 4                           # Rough estimation for English text

# =============================================================================
# 8. LLM EXTRACTION CONFIG (llm_extract)
# =============================================================================

# System prompt for health analysis
HEALTH_ANALYSIS_SYSTEM_PROMPT = "You are an expert communication analyst specializing in workplace and team communication health assessment."

# Analysis focus areas for LLM
ANALYSIS_FOCUS_AREAS = [
    "Tone Analysis: Identify tone descriptors (professional, friendly, tense, supportive, etc.)",
    "Clarity: Rate how clear and understandable the communication is (0-10)",
    "Responsiveness: Identify patterns in how people respond to each other",
    "Engagement: Rate overall participant engagement level (0-10)",
    "Conflict Detection: Look for signs of tension, disagreement, or conflict",
    "Collaboration: Identify positive teamwork and collaboration indicators",
    "Communication Issues: Spot problems like unclear requests, ignored questions, etc.",
    "Positive Patterns: Identify healthy communication behaviors",
    "Key Topics: Extract the main subjects being discussed",
    "Emotional Tone: Count messages with positive, negative, or neutral emotional tone"
]

# LLM analysis guidelines
ANALYSIS_GUIDELINES = [
    "Be objective and evidence-based in your analysis",
    "Look for subtle patterns, not just obvious ones",
    "Consider context and workplace communication norms",
    "Focus on actionable insights for improving communication health",
    "Rate clarity and engagement on realistic scales (5-7 is average, 8+ is excellent)"
]

# Health analysis prompt template
HEALTH_ANALYSIS_PROMPT_TEMPLATE = """You are analyzing communication health in a workplace conversation.

CONVERSATION CHUNK #{chunk_idx}:
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

# Health insights JSON schema
HEALTH_INSIGHTS_JSON_SCHEMA = {
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

# =============================================================================
# 9. MERGE CHUNKS CONFIG (merge_chunks)
# =============================================================================

# Default chunk insight values
DEFAULT_CHUNK_INSIGHTS = {
    'chunk_index': 0,
    'chunk_size': 0,
    'clarity_score': 5.0,
    'engagement_level': 5.0,
    'top_topics_limit': 3,
    'top_issues_limit': 2
}

# Default emotional distribution
DEFAULT_EMOTIONAL_DISTRIBUTION = {
    'positive_ratio': 0.33,
    'negative_ratio': 0.33,
    'neutral_ratio': 0.34
}

# Health flag thresholds
HEALTH_FLAG_THRESHOLDS = {
    'high_clarity': 7.5,
    'good_engagement': 7.0,
    'collaboration_present': 0,
    'conflicts_detected': 0,
    'communication_issues': 0,
    'positive_tone': 0.4,
    'balanced_participation': 1,
    'topic_focus_max': 10,
    'positive_flags_multiplier': 1.5,
    'negative_flags_multiplier': 2,
    'base_health_score': 4,
    'health_score_min': 0,
    'health_score_max': 10
}

# Health categorization thresholds
HEALTH_CATEGORIZATION = {
    'excellent': 8.5,
    'good': 7.0,
    'fair': 5.5,
    'poor': 3.5
}

# Merge chunks limits
MERGE_LIMITS = {
    'top_items_default': 5,
    'top_items_topics': 8,
    'weighted_average_default': 5.0
}

# =============================================================================
# 10. EVIDENCE COLLECTION CONFIG (evidence_collect)
# =============================================================================

# Pattern matching for evidence collection
COLLABORATION_PATTERNS = [
    r'\b(great idea|good point|i agree|let\'s work together|team effort)\b',
    r'\b(thanks for|thank you|appreciate|helpful|nice work)\b',
    r'\b(we can|let\'s|together we|our team|collaboration)\b',
    r'\b(build on|expand on|add to|contribute|support)\b'
]

CONFLICT_PATTERNS = [
    r'\b(disagree|wrong|terrible idea|bad|awful|hate)\b',
    r'\b(frustrated|annoyed|upset|angry|disappointed)\b',
    r'\b(never|always|impossible|ridiculous|stupid)\b',
    r'\b(what\'s wrong with|why don\'t you|you should)\b'
]

CLARITY_PATTERNS = [
    r'\b(to clarify|let me explain|specifically|in other words)\b',
    r'\b(the goal is|the objective|the purpose|what i mean)\b',
    r'\b(step by step|first|second|finally|in summary)\b',
    r'\b(can you clarify|could you explain|what do you mean)\b'
]

ENGAGEMENT_PATTERNS = [
    r'\?',                                              # Contains questions
    r'\b(what about|how about|what if|thoughts on)\b',
    r'\b(interesting|excited|love this|great|awesome)\b',
    r'\b(let\'s discuss|what do you think|your opinion|feedback)\b'
]

RESPONSIVENESS_PATTERNS = [
    r'\b(yes|no|i think|regarding|about your|in response to)\b',
    r'\b(you mentioned|as you said|following up|to answer)\b',
    r'\b(re:|regarding:|about:|concerning:)\b'
]

# Positive/negative tone indicators
POSITIVE_TONE_PATTERNS = [
    r'\b(great|good|excellent|awesome|wonderful|amazing|love|like)\b',
    r'\b(thank|thanks|appreciate|grateful|pleased|happy)\b',
    r'\b(perfect|brilliant|fantastic|outstanding|impressive)\b',
    r'\b(excited|enthusiastic|optimistic|confident|positive)\b'
]

NEGATIVE_TONE_PATTERNS = [
    r'\b(terrible|awful|hate|dislike|wrong|bad|poor)\b',
    r'\b(frustrated|confused|disappointed|concerned|worried)\b',
    r'\b(problem|issue|error|mistake|failure|broken)\b',
    r'\b(can\'t|won\'t|shouldn\'t|impossible|difficult)\b'
]

# Evidence collection limits
MAX_EXAMPLES_PER_CATEGORY = 5

# =============================================================================
# 11. SCORE CALIBRATION CONFIG (calibrate_scores)
# =============================================================================

# Dimension weights for overall health score
DIMENSION_WEIGHTS = {
    'participation_score': 0.25,
    'clarity_score': 0.20,
    'engagement_score': 0.20,
    'responsiveness_score': 0.15,
    'collaboration_score': 0.20
}

# Health score thresholds
HEALTH_SCORE_THRESHOLDS = {
    'excellent': 9.0,
    'good': 7.5,
    'fair': 6.0,
    'poor': 4.0,
    'critical': 0.0
}

# Confidence score factors
CONFIDENCE_FACTORS = {
    'has_timestamps': 1.0,
    'no_timestamps': 0.5,
    'sufficient_messages_threshold': 10,
    'sufficient_messages_score': 1.0,
    'insufficient_messages_score': 0.7,
    'multiple_speakers_score': 1.0,
    'single_speaker_score': 0.5,
    'evidence_available_score': 1.0,
    'no_evidence_score': 0.6
}

# Score calculation sub-configurations

# Participation scoring
PARTICIPATION_SCORING = {
    'max_score': 10.0,
    'default_balance': 0.5,
    'balance_multiplier': 20
}

# Clarity scoring
CLARITY_SCORING = {
    'default_llm_score': 5.0,
    'default_question_ratio': 0.1,
    'question_ratio_low_threshold': 0.3,
    'question_ratio_high_threshold': 0.6,
    'adjustment_neutral': 0,
    'adjustment_negative': -1.0,
    'adjustment_positive': 0.5
}

# Engagement scoring
ENGAGEMENT_SCORING = {
    'default_llm_score': 5.0,
    'default_avg_words': 20,
    'word_threshold_high': 30,
    'word_threshold_medium': 15,
    'word_factor_high': 1.0,
    'word_factor_medium': 0.5,
    'word_factor_low': 0.0
}

# Responsiveness scoring
RESPONSIVENESS_SCORING = {
    'default_no_timestamp_score': 6.0,
    'default_no_response_score': 5.0,
    'pattern_bonus_max': 2.0,
    'pattern_bonus_multiplier': 0.5,
    'time_score_excellent': 9.5,
    'time_score_good': 8.0,
    'time_score_fair': 6.0,
    'time_score_poor': 4.0,
    'time_score_critical': 2.0
}

# Collaboration scoring
COLLABORATION_SCORING = {
    'default_positive_ratio': 0.5,
    'max_base_score': 8.0,
    'indicator_multiplier': 0.8,
    'positive_multiplier': 2.0,
    'conflict_penalty_max': 5.0,
    'conflict_penalty_multiplier': 1.0
}

# Confidence calculation
CONFIDENCE_CALCULATION = {
    'llm_analysis_multiplier': 0.3,
    'llm_analysis_default': 0.5,
    'score_multiplier': 10
}

# Recommendation thresholds
RECOMMENDATION_THRESHOLDS = {
    'participation': 6.0,
    'clarity': 6.0,
    'engagement': 6.0,
    'responsiveness': 6.0,
    'collaboration': 6.0,
    'overall': 6.0
}

# =============================================================================
# 12. REPORTING CONFIG (generate_report + finalize_output)
# =============================================================================

# Content extraction keywords
ACTION_KEYWORDS = [
    'todo', 'task', 'assign', 'due', 'deadline', 'action item',
    'will do', 'complete by'
]

DECISION_KEYWORDS = [
    'decide', 'agreed', 'decision', 'resolved', 'conclude', 'final'
]

# Report limits
MAX_EXTRACTED_ITEMS = 3                                # Max decisions/actions to extract
MAX_KEY_TOPICS = 5                                     # Max topics to display
MAX_TONE_INDICATORS = 5                                # Max tone indicators to show
MAX_RECOMMENDATIONS = 5                                # Max recommendations to provide

# =============================================================================
# SHARED UTILITIES AND TEXT PROCESSING
# =============================================================================

# Text preview lengths
TEXT_PREVIEW_LENGTHS = {
    'evidence_full': 200,
    'evidence_example': 150
}

# Text processing constants
TEXT_PROCESSING = {
    'min_deduped_length': 3,
    'line_separator': '\n',
    'double_newline': '\n\n',
    'whitespace_pattern': r'\s+',
    'whitespace_replacement': ' ',
    'sent_from_pattern': r'sent from my \w+',
    'outlook_pattern': r'get outlook for \w+',
    'time_pattern': r'\d{1,2}:\d{2}(:\d{2})?\s*(am|pm)?',
    'date_pattern': r'\d{1,2}/\d{1,2}/\d{2,4}',
    'excessive_newlines_pattern': r'\n\s*\n\s*\n+',
    'excessive_newlines_replacement': '\n\n'
}

# =============================================================================
# VERSION AND METADATA
# =============================================================================

VERSION = "1.0.0"
ANALYSIS_PIPELINE_NAME = "Communication Health Analyzer"