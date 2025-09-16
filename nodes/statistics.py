from datetime import datetime
from collections import Counter
import re
from config import QUESTION_PATTERNS

def basic_stats_full(state):
    """Calculate basic statistics including response times (with timestamps)."""

    print("Calculating full basic statistics...")
    if not state.validated_data:
        if not state.errors:
            state.errors = []
        state.errors.append("statistics: No validated data for analysis")
        return state

    stats = _calculate_base_statistics(state.validated_data)

    # Add timestamp-based metrics
    timestamp_stats = _calculate_timestamp_statistics(state.validated_data)
    stats.update(timestamp_stats)

    state.basic_stats = stats
    return state

def basic_stats_text(state):
    """Calculate basic statistics excluding latency (no timestamps)."""

    if not state.validated_data:
        if not state.errors:
            state.errors = []
        state.errors.append("statistics: No validated data for analysis")
        return state

    stats = _calculate_base_statistics(state.validated_data)

    # Mark that timestamps were not available
    stats['has_timestamps'] = False
    stats['response_times'] = []
    stats['median_response_time'] = None

    state.basic_stats = stats
    return state

def _calculate_base_statistics(data):
    """Calculate statistics that don't require timestamps."""
    print("Calculating base statistics...")
    # Basic counts
    total_messages = len(data)
    speakers = [item['speaker'] for item in data]
    unique_speakers = list(set(speakers))

    # Text analysis
    texts = [item['text'] for item in data]
    word_counts = [len(text.split()) for text in texts]
    char_counts = [len(text) for text in texts]

    # Question detection
    question_count = _count_questions(texts)

    # Participation analysis
    speaker_counts = Counter(speakers)
    speaker_word_counts = {}

    for item in data:
        speaker = item['speaker']
        words = len(item['text'].split())
        speaker_word_counts[speaker] = speaker_word_counts.get(speaker, 0) + words

    # Calculate participation balance (0-1, where 1 is perfectly balanced)
    participation_balance = _calculate_participation_balance(speaker_counts, total_messages)

    # Communication types
    types = [item.get('type', 'message') for item in data]
    type_counts = Counter(types)

    return {
        # Basic counts
        'total_messages': total_messages,
        'unique_speakers': len(unique_speakers),
        'speaker_list': unique_speakers,

        # Text metrics
        'total_words': sum(word_counts),
        'avg_words_per_message': sum(word_counts) / total_messages if total_messages > 0 else 0,
        'total_characters': sum(char_counts),
        'avg_chars_per_message': sum(char_counts) / total_messages if total_messages > 0 else 0,

        # Content analysis
        'question_count': question_count,
        'question_ratio': question_count / total_messages if total_messages > 0 else 0,

        # Participation metrics
        'speaker_message_counts': dict(speaker_counts),
        'speaker_word_counts': speaker_word_counts,
        'participation_balance': participation_balance,

        # Communication types
        'message_types': dict(type_counts),

        # Flags
        'has_timestamps': True  # Will be overridden in basic_stats_text
    }

def _calculate_timestamp_statistics(data):
    """Calculate statistics that require timestamps."""
    print("Calculating timestamp-based statistics...")
    # Filter items with valid timestamps
    timestamped_items = []
    for item in data:
        if 'timestamp' in item and item['timestamp']:
            try:
                # Parse timestamp
                ts_str = item['timestamp'].rstrip('Z')  # Remove Z if present
                timestamp = datetime.fromisoformat(ts_str)
                timestamped_items.append({
                    **item,
                    'parsed_timestamp': timestamp
                })
            except ValueError:
                print(f"❌ Error: {ValueError}")

    if len(timestamped_items) < 2:
        return {
            'response_times': [],
            'median_response_time': None,
            'avg_response_time': None,
            'conversation_duration': None
        }

    # Sort by timestamp
    timestamped_items.sort(key=lambda x: x['parsed_timestamp'])

    # Calculate response times between different speakers
    response_times = []

    for i in range(1, len(timestamped_items)):
        current_item = timestamped_items[i]
        prev_item = timestamped_items[i-1]

        # Only calculate response time if speakers are different
        if current_item['speaker'] != prev_item['speaker']:
            time_diff = current_item['parsed_timestamp'] - prev_item['parsed_timestamp']
            response_time_minutes = time_diff.total_seconds() / 60

            # Filter out unreasonably long response times (more than 1 week)
            max_response_time = 7 * 24 * 60  # 1 week in minutes
            if 0 < response_time_minutes <= max_response_time:
                response_times.append(response_time_minutes)

    # Calculate conversation duration
    if timestamped_items:
        start_time = timestamped_items[0]['parsed_timestamp']
        end_time = timestamped_items[-1]['parsed_timestamp']
        duration = (end_time - start_time).total_seconds() / 60  # in minutes
    else:
        duration = None

    # Calculate median and average response times
    if response_times:
        sorted_times = sorted(response_times)
        median_time = sorted_times[len(sorted_times) // 2]
        avg_time = sum(response_times) / len(response_times)
    else:
        median_time = None
        avg_time = None

    return {
        'response_times': response_times,
        'median_response_time': median_time,
        'avg_response_time': avg_time,
        'conversation_duration': duration
    }

def _count_questions(texts):
    """Count questions in the text data."""
    print("Counting questions...")
    question_count = 0

    for text in texts:
        text_lower = text.lower()
        for pattern in QUESTION_PATTERNS:
            if re.search(pattern, text_lower):
                question_count += 1
                break  # Count each message at most once

    return question_count

def _calculate_participation_balance(speaker_counts, total_messages):
    """Calculate how balanced participation is across speakers (0-1 scale)."""
    print("Calculating participation balance...")
    if len(speaker_counts) <= 1:
        return 1.0  # Perfect balance with 1 speaker

    # Calculate what perfect balance would look like
    perfect_share = total_messages / len(speaker_counts)

    # Calculate how far each speaker deviates from perfect balance
    total_deviation = 0
    for count in speaker_counts.values():
        deviation = abs(count - perfect_share)
        total_deviation += deviation

    # Convert to 0-1 scale where 1 is perfect balance
    max_possible_deviation = total_messages * (len(speaker_counts) - 1) / len(speaker_counts)

    if max_possible_deviation == 0:
        return 1.0

    balance_score = 1 - (total_deviation / (2 * max_possible_deviation))
    return max(0, min(1, balance_score))  # Clamp to 0-1 range