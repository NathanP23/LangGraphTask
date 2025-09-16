import re
from config import (COLLABORATION_PATTERNS, CONFLICT_PATTERNS, CLARITY_PATTERNS,
                   ENGAGEMENT_PATTERNS, RESPONSIVENESS_PATTERNS, POSITIVE_TONE_PATTERNS,
                   NEGATIVE_TONE_PATTERNS, MAX_EXAMPLES_PER_CATEGORY, TEXT_PREVIEW_LENGTHS)

def evidence_collect(state):
    """Collect specific message examples that support the analysis findings."""

    if not state.validated_data or not hasattr(state, 'merged_insights'):
        if not state.errors:
            state.errors = []
        state.errors.append("evidence_collect: Missing validated data or merged insights")
        return state

    try:
        # Initialize evidence collection
        evidence = {
            'positive_examples': [],
            'negative_examples': [],
            'clarity_examples': [],
            'engagement_examples': [],
            'collaboration_examples': [],
            'conflict_examples': [],
            'responsiveness_examples': []
        }

        # Collect examples for different categories
        for msg in state.validated_data:
            # Safety check for text content
            if not msg.get('text'):
                continue

            msg_text = msg['text'].lower()
            speaker = msg.get('speaker', 'Unknown')
            timestamp = msg.get('timestamp', '')

            # Create message reference
            msg_ref = {
                'speaker': speaker,
                'text': msg['text'][:TEXT_PREVIEW_LENGTHS['evidence_full']] + ('...' if len(msg['text']) > TEXT_PREVIEW_LENGTHS['evidence_full'] else ''),
                'timestamp': timestamp,
                'full_text': msg['text']
            }

            # Look for positive collaboration indicators
            if _matches_collaboration_patterns(msg_text):
                evidence['collaboration_examples'].append(msg_ref)

            # Look for conflict indicators
            if _matches_conflict_patterns(msg_text):
                evidence['conflict_examples'].append(msg_ref)

            # Look for clarity examples (clear questions, explanations)
            if _matches_clarity_patterns(msg_text):
                evidence['clarity_examples'].append(msg_ref)

            # Look for engagement examples (questions, responses)
            if _matches_engagement_patterns(msg_text):
                evidence['engagement_examples'].append(msg_ref)

            # Look for responsiveness examples
            if _matches_responsiveness_patterns(msg_text):
                evidence['responsiveness_examples'].append(msg_ref)

        # Categorize as positive/negative based on overall tone

        for msg in state.validated_data:
            # Safety check for text content
            if not msg.get('text'):
                continue

            msg_ref = {
                'speaker': msg.get('speaker', 'Unknown'),
                'text': msg['text'][:TEXT_PREVIEW_LENGTHS['evidence_example']] + ('...' if len(msg['text']) > TEXT_PREVIEW_LENGTHS['evidence_example'] else ''),
                'timestamp': msg.get('timestamp', ''),
                'reason': ''
            }

            # Positive examples
            if msg.get('text') and _is_positive_message(msg['text'].lower()):
                msg_ref['reason'] = 'Positive tone and supportive language'
                evidence['positive_examples'].append(msg_ref)

            # Negative examples
            elif msg.get('text') and _is_negative_message(msg['text'].lower()):
                msg_ref['reason'] = 'Negative tone or communication issues'
                evidence['negative_examples'].append(msg_ref)

        # Limit examples to avoid overwhelming output
        for category in evidence:
            evidence[category] = evidence[category][:MAX_EXAMPLES_PER_CATEGORY]

        # Add evidence metadata
        evidence['collection_summary'] = {
            'total_messages_analyzed': len(state.validated_data),
            'positive_examples_found': len(evidence['positive_examples']),
            'negative_examples_found': len(evidence['negative_examples']),
            'collaboration_examples_found': len(evidence['collaboration_examples']),
            'conflict_examples_found': len(evidence['conflict_examples']),
            'clarity_examples_found': len(evidence['clarity_examples']),
            'engagement_examples_found': len(evidence['engagement_examples'])
        }

        # Store evidence in state
        state.evidence = evidence

    except Exception as e:
        if not state.errors:
            state.errors = []
        state.errors.append(f"evidence_collect: Failed to collect evidence - {str(e)}")
        print(f"Error: {e}")

    return state

def _matches_collaboration_patterns(text):
    """Check if message shows collaboration indicators."""
    if not text:
        return False
    patterns = COLLABORATION_PATTERNS or []
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def _matches_conflict_patterns(text):
    """Check if message shows conflict indicators."""
    if not text:
        return False
    patterns = CONFLICT_PATTERNS or []
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def _matches_clarity_patterns(text):
    """Check if message demonstrates clarity."""
    if not text:
        return False
    patterns = CLARITY_PATTERNS or []
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def _matches_engagement_patterns(text):
    """Check if message shows high engagement."""
    if not text:
        return False
    patterns = ENGAGEMENT_PATTERNS or []
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def _matches_responsiveness_patterns(text):
    """Check if message shows responsiveness to previous messages."""
    if not text:
        return False
    patterns = RESPONSIVENESS_PATTERNS or []
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

def _is_positive_message(text):
    """Determine if message has positive tone."""
    if not text:
        return False
    patterns = POSITIVE_TONE_PATTERNS or []
    positive_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in patterns)
    return positive_count >= 2 or bool(re.search(r'\b(love this|great work|well done|excellent job)\b', text, re.IGNORECASE))

def _is_negative_message(text):
    """Determine if message has negative tone."""
    if not text:
        return False
    patterns = NEGATIVE_TONE_PATTERNS or []
    negative_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in patterns)
    return negative_count >= 2 or bool(re.search(r'\b(not working|big problem|major issue|really bad)\b', text, re.IGNORECASE))