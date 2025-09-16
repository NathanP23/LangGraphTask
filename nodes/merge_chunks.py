from collections import Counter
from config import (DEFAULT_CHUNK_INSIGHTS, DEFAULT_EMOTIONAL_DISTRIBUTION,
                   HEALTH_FLAG_THRESHOLDS, HEALTH_SCORE_THRESHOLDS)

def merge_chunks(state):
    """Merge insights from multiple conversation chunks into unified analysis."""

    if not hasattr(state, 'llm_insights') or not state.llm_insights:
        if not state.errors:
            state.errors = []
        state.errors.append("merge_chunks: No LLM insights available to merge")
        return state

    try:
        # Initialize merged insights structure
        merged_insights = {
            'tone_indicators': [],
            'clarity_scores': [],
            'responsiveness_patterns': [],
            'engagement_levels': [],
            'conflict_indicators': [],
            'collaboration_indicators': [],
            'communication_issues': [],
            'positive_patterns': [],
            'key_topics': [],
            'emotional_indicators': {'positive': 0, 'negative': 0, 'neutral': 0},
            'chunk_count': len(state.llm_insights),
            'total_speakers': set(),
            'chunk_summaries': []
        }

        # Aggregate data from all chunks
        for chunk_insight in state.llm_insights:
            # Collect all indicators and patterns
            merged_insights['tone_indicators'].extend(chunk_insight.get('tone_indicators', []))
            merged_insights['responsiveness_patterns'].extend(chunk_insight.get('responsiveness_patterns', []))
            merged_insights['conflict_indicators'].extend(chunk_insight.get('conflict_indicators', []))
            merged_insights['collaboration_indicators'].extend(chunk_insight.get('collaboration_indicators', []))
            merged_insights['communication_issues'].extend(chunk_insight.get('communication_issues', []))
            merged_insights['positive_patterns'].extend(chunk_insight.get('positive_patterns', []))
            merged_insights['key_topics'].extend(chunk_insight.get('key_topics', []))

            # Collect scores
            merged_insights['clarity_scores'].append(chunk_insight.get('clarity_score', DEFAULT_CHUNK_INSIGHTS['clarity_score']))
            merged_insights['engagement_levels'].append(chunk_insight.get('engagement_level', DEFAULT_CHUNK_INSIGHTS['engagement_level']))

            # Sum emotional indicators
            emotions = chunk_insight.get('emotional_indicators', {})
            merged_insights['emotional_indicators']['positive'] += emotions.get('positive', 0)
            merged_insights['emotional_indicators']['negative'] += emotions.get('negative', 0)
            merged_insights['emotional_indicators']['neutral'] += emotions.get('neutral', 0)

            # Collect speakers
            chunk_speakers = chunk_insight.get('chunk_speakers', [])
            merged_insights['total_speakers'].update(chunk_speakers)

            # Create chunk summary
            chunk_summary = {
                'chunk_index': chunk_insight.get('chunk_index', DEFAULT_CHUNK_INSIGHTS['chunk_index']),
                'chunk_size': chunk_insight.get('chunk_size', DEFAULT_CHUNK_INSIGHTS['chunk_size']),
                'clarity_score': chunk_insight.get('clarity_score', DEFAULT_CHUNK_INSIGHTS['clarity_score']),
                'engagement_level': chunk_insight.get('engagement_level', DEFAULT_CHUNK_INSIGHTS['engagement_level']),
                'key_topics': chunk_insight.get('key_topics', [])[:DEFAULT_CHUNK_INSIGHTS['top_topics_limit']],
                'main_issues': chunk_insight.get('communication_issues', [])[:DEFAULT_CHUNK_INSIGHTS['top_issues_limit']]
            }
            merged_insights['chunk_summaries'].append(chunk_summary)

        # Process aggregated data
        merged_insights['total_speakers'] = list(merged_insights['total_speakers'])

        # Calculate aggregated metrics
        merged_insights['overall_clarity'] = _calculate_weighted_average(merged_insights['clarity_scores'])
        merged_insights['overall_engagement'] = _calculate_weighted_average(merged_insights['engagement_levels'])

        # Deduplicate and rank by frequency
        merged_insights['top_tone_indicators'] = _get_top_items(merged_insights['tone_indicators'], 5)
        merged_insights['top_responsiveness_patterns'] = _get_top_items(merged_insights['responsiveness_patterns'], 5)
        merged_insights['top_conflict_indicators'] = _get_top_items(merged_insights['conflict_indicators'], 5)
        merged_insights['top_collaboration_indicators'] = _get_top_items(merged_insights['collaboration_indicators'], 5)
        merged_insights['top_communication_issues'] = _get_top_items(merged_insights['communication_issues'], 5)
        merged_insights['top_positive_patterns'] = _get_top_items(merged_insights['positive_patterns'], 5)
        merged_insights['top_key_topics'] = _get_top_items(merged_insights['key_topics'], 8)

        # Calculate emotional tone distribution
        total_emotions = sum(merged_insights['emotional_indicators'].values())
        if total_emotions > 0:
            merged_insights['emotional_distribution'] = {
                'positive_ratio': merged_insights['emotional_indicators']['positive'] / total_emotions,
                'negative_ratio': merged_insights['emotional_indicators']['negative'] / total_emotions,
                'neutral_ratio': merged_insights['emotional_indicators']['neutral'] / total_emotions
            }
        else:
            merged_insights['emotional_distribution'] = DEFAULT_EMOTIONAL_DISTRIBUTION

        # Generate health summary flags
        merged_insights['health_flags'] = _generate_health_flags(merged_insights)

        # Store merged insights in state
        state.merged_insights = merged_insights

    except Exception as e:
        if not state.errors:
            state.errors = []
        state.errors.append(f"merge_chunks: Failed to merge insights - {str(e)}")
        print(f"❌ Error: {e}")

    return state

def _calculate_weighted_average(scores):
    """Calculate weighted average of scores."""
    if not scores:
        return DEFAULT_CHUNK_INSIGHTS['clarity_score']
    return sum(scores) / len(scores)

def _get_top_items(items_list, max_count):
    """Get top items by frequency, deduplicated."""
    if not items_list:
        return []

    # Count frequency and get top items
    counter = Counter(items_list)
    top_items = counter.most_common(max_count)

    # Return items with their frequency counts
    return [{'item': item, 'frequency': count} for item, count in top_items]

def _generate_health_flags(insights):
    """Generate high-level health assessment flags."""
    flags = {
        'high_clarity': insights['overall_clarity'] >= HEALTH_FLAG_THRESHOLDS['high_clarity'],
        'good_engagement': insights['overall_engagement'] >= HEALTH_FLAG_THRESHOLDS['good_engagement'],
        'collaboration_present': len(insights['collaboration_indicators']) > HEALTH_FLAG_THRESHOLDS['collaboration_present'],
        'conflicts_detected': len(insights['conflict_indicators']) > HEALTH_FLAG_THRESHOLDS['conflicts_detected'],
        'communication_issues': len(insights['communication_issues']) > HEALTH_FLAG_THRESHOLDS['communication_issues'],
        'positive_tone': insights['emotional_distribution']['positive_ratio'] > HEALTH_FLAG_THRESHOLDS['positive_tone'],
        'balanced_participation': len(insights['total_speakers']) > HEALTH_FLAG_THRESHOLDS['balanced_participation'],
        'topic_focus': len(insights['key_topics']) <= HEALTH_FLAG_THRESHOLDS['topic_focus_max']
    }

    # Overall health assessment
    positive_flags = sum([
        flags['high_clarity'],
        flags['good_engagement'],
        flags['collaboration_present'],
        flags['positive_tone'],
        flags['balanced_participation'],
        flags['topic_focus']
    ])

    negative_flags = sum([
        flags['conflicts_detected'],
        flags['communication_issues']
    ])

    # Health score calculation (0-10 scale)
    health_score = max(
        HEALTH_FLAG_THRESHOLDS['health_score_min'],
        min(HEALTH_FLAG_THRESHOLDS['health_score_max'],
            (positive_flags * HEALTH_FLAG_THRESHOLDS['positive_flags_multiplier']) -
            (negative_flags * HEALTH_FLAG_THRESHOLDS['negative_flags_multiplier']) +
            HEALTH_FLAG_THRESHOLDS['base_health_score'])
    )

    flags['overall_health_score'] = health_score
    flags['health_level'] = _categorize_health_score(health_score)

    return flags

def _categorize_health_score(score):
    """Categorize health score into levels."""
    if score >= HEALTH_SCORE_THRESHOLDS['excellent']:
        return "excellent"
    elif score >= HEALTH_SCORE_THRESHOLDS['good']:
        return "good"
    elif score >= HEALTH_SCORE_THRESHOLDS['fair']:
        return "fair"
    elif score >= HEALTH_SCORE_THRESHOLDS['poor']:
        return "poor"
    else:
        return "critical"