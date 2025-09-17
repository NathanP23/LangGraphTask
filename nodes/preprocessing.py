import re
from config import (EMAIL_SIGNATURE_PATTERNS, EMAIL_QUOTE_PATTERNS,
                   MAX_CHUNK_TOKENS, MIN_CHUNK_SIZE, CHARS_PER_TOKEN_ESTIMATE,
                   TEXT_PROCESSING)

def dedupe_threads(state):
    """Remove duplicate messages and collapse quoted emails."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    # Progress tracking
    state.current_step += 1
    state.add_log(f"[{state.current_step}/{state.total_steps}] PREPROCESSING: Deduplicating and cleaning data...")

    if not state.validated_data:
        state.add_error("dedupe_threads: No validated data to process")
        return state

    deduplicated_data = []
    seen_content = set()

    for item in state.validated_data:
        # Clean the message text for deduplication
        cleaned_text = _clean_for_dedup(item['text'], reporter)

        # Skip if we've seen this exact content before
        if cleaned_text in seen_content:
            reporter.add_log(f"Skipping duplicate content", 1, flush=True)
            continue

        # Remove quoted content from emails
        deduped_text = _remove_quoted_content(item['text'], reporter)

        # Skip if text becomes empty after quote removal
        if len(deduped_text.strip()) < TEXT_PROCESSING['min_deduped_length']:
            reporter.add_log(f"Skipping item with text too short after deduplication", 1, flush=True)
            continue

        # Create deduplicated item
        deduped_item = {
            **item,
            'text': deduped_text
        }

        deduplicated_data.append(deduped_item)
        seen_content.add(cleaned_text)

    # Update state with deduplicated data
    state.validated_data = deduplicated_data
    original_count = len([item for item in state.validated_data if item]) if state.validated_data else 0
    state.add_log(f"✓ [{state.current_step}/{state.total_steps}] PREPROCESSING: {len(deduplicated_data)} items after deduplication")

    return state

def _clean_for_dedup(text, reporter):
    """Clean text for deduplication comparison."""
    reporter.add_log("Cleaning text for deduplication...", 2, flush=True)
    # Convert to lowercase
    cleaned = text.lower()

    # Remove extra whitespace
    cleaned = re.sub(TEXT_PROCESSING['whitespace_pattern'], TEXT_PROCESSING['whitespace_replacement'], cleaned)

    # Remove common email artifacts
    cleaned = re.sub(TEXT_PROCESSING['sent_from_pattern'], '', cleaned)
    cleaned = re.sub(TEXT_PROCESSING['outlook_pattern'], '', cleaned)

    # Remove timestamps and dates
    cleaned = re.sub(TEXT_PROCESSING['time_pattern'], '', cleaned)
    cleaned = re.sub(TEXT_PROCESSING['date_pattern'], '', cleaned)

    return cleaned.strip()

def _remove_quoted_content(text, reporter):
    """Remove quoted content from email/message text."""
    reporter.add_log("Removing quoted content from text...", 2, flush=True)
    lines = text.split(TEXT_PROCESSING['line_separator'])
    cleaned_lines = []

    # Use configured patterns

    quote_started = False
    signature_started = False

    for line in lines:
        line_stripped = line.strip()

        # Check for signature start
        if not signature_started:
            for pattern in EMAIL_SIGNATURE_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    signature_started = True
                    break

        # Skip signature lines
        if signature_started:
            reporter.add_log(f"Skipping signature line: {line_stripped}", 3, flush=True)
            continue

        # Check for quote start
        if not quote_started:
            for pattern in EMAIL_QUOTE_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    reporter.add_log(f"Quote pattern detected, starting quote removal", 3, flush=True)
                    quote_started = True
                    break

        # Skip quoted lines
        if quote_started:
            reporter.add_log(f"Skipping quoted line: {line_stripped}", 3, flush=True)
            continue

        # Keep the line if it's not quoted or signature
        cleaned_lines.append(line)

    # Join and clean up the result
    result = TEXT_PROCESSING['line_separator'].join(cleaned_lines).strip()

    # Remove excessive newlines
    result = re.sub(TEXT_PROCESSING['excessive_newlines_pattern'], TEXT_PROCESSING['excessive_newlines_replacement'], result)

    return result

def chunk_if_needed(state):
    """Split large conversations into manageable chunks."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    # Note: This shares the same step as dedupe_threads since they're both preprocessing
    state.add_log(f"[{state.current_step}/{state.total_steps}] PREPROCESSING: Checking if chunking needed...")
    if not state.validated_data:
        state.add_error("chunk_if_needed: No validated data to process")
        return state

    # Estimate tokens for each message
    token_counts = []
    total_tokens = 0

    for item in state.validated_data:
        # Rough token estimation using config
        estimated_tokens = len(item['text']) // CHARS_PER_TOKEN_ESTIMATE
        token_counts.append(estimated_tokens)
        total_tokens += estimated_tokens

    # If total tokens are under limit, no chunking needed
    if total_tokens <= MAX_CHUNK_TOKENS:
        state.chunks = [state.validated_data]
        state.add_log(f"✓ [{state.current_step}/{state.total_steps}] PREPROCESSING: No chunking needed ({total_tokens} tokens)")
        return state

    # Split into chunks
    chunks = []
    current_chunk = []
    current_tokens = 0

    for i, item in enumerate(state.validated_data):
        message_tokens = token_counts[i]

        # If adding this message would exceed limit and we have enough messages
        if (current_tokens + message_tokens > MAX_CHUNK_TOKENS and
            len(current_chunk) >= MIN_CHUNK_SIZE):

            # Save current chunk and start new one
            reporter.add_log(f"Creating chunk {len(chunks) + 1} with {len(current_chunk)} messages", 1, flush=True)
            chunks.append(current_chunk)
            current_chunk = [item]
            current_tokens = message_tokens

        else:
            # Add to current chunk
            current_chunk.append(item)
            current_tokens += message_tokens

    # Add final chunk if it has any messages
    if current_chunk:
        chunks.append(current_chunk)

    # Store chunks in state
    state.chunks = chunks
    state.add_log(f"✓ [{state.current_step}/{state.total_steps}] PREPROCESSING: Created {len(chunks)} chunks from {len(state.validated_data)} messages")

    # Add chunk information to state for reporting
    chunk_info = {
        'total_messages': len(state.validated_data),
        'total_chunks': len(chunks),
        'estimated_total_tokens': total_tokens,
        'chunk_sizes': [len(chunk) for chunk in chunks],
        'chunk_token_estimates': [
            sum(len(msg['text']) // CHARS_PER_TOKEN_ESTIMATE for msg in chunk)
            for chunk in chunks
        ]
    }

    if not hasattr(state, 'metadata') or state.metadata is None:
        state.metadata = {}
    state.metadata['chunking'] = chunk_info
    reporter.add_log(f"Chunk metadata stored", 1)

    return state