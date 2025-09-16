from datetime import datetime
from config import (ACTION_KEYWORDS, DECISION_KEYWORDS, MAX_EXTRACTED_ITEMS,
                   MAX_KEY_TOPICS, MAX_TONE_INDICATORS, VERSION)

def generate_report(state):
    """Generate natural language explanation of health scores."""

    # Check for required analysis components
    if not state.calibrated_scores or not state.merged_insights:
        if not state.errors:
            state.errors = []
        state.errors.append("report: Missing calibrated scores or merged insights for report generation")
        return state

    scores = state.calibrated_scores
    insights = state.merged_insights
    stats = state.basic_stats

    # Generate comprehensive summary using all analysis components
    summary = _generate_comprehensive_summary(scores, insights, stats)

    # Use calibrated overall health score
    overall_score = scores['overall_health_score']
    overall_label = scores['health_levels']['overall_health_score']

    # Create dimensional scores from calibrated analysis
    dimensions = _create_comprehensive_dimensions(scores)

    # Extract rich content using evidence and insights
    extracted_content = _extract_rich_content(state.evidence, insights, state.validated_data)

    # Create the report
    report = {
        "summary": summary,
        "overall_health": {
            "score": overall_score,
            "label": overall_label,
            "confidence": scores['confidence_score']
        },
        "dimensions": dimensions,
        "extracted_content": extracted_content,
        "recommendations": scores.get('recommendations', []),
        "insights": {
            "key_topics": [item['item'] for item in insights.get('top_key_topics', [])][:5],
            "tone_indicators": [item['item'] for item in insights.get('top_tone_indicators', [])][:5],
            "collaboration_patterns": len(insights.get('collaboration_indicators', [])),
            "communication_issues": len(insights.get('communication_issues', [])),
            "emotional_distribution": insights.get('emotional_distribution', {})
        },
        "statistics": {
            "total_messages": stats['total_messages'],
            "unique_speakers": stats['unique_speakers'],
            "total_words": stats['total_words'],
            "question_ratio": stats['question_ratio'],
            "participation_balance": stats['participation_balance']
        }
    }

    # Add timestamp-based metrics if available
    if stats.get('has_timestamps') and stats.get('median_response_time'):
        report["statistics"]["median_response_time_minutes"] = stats['median_response_time']
        report["statistics"]["conversation_duration_minutes"] = stats.get('conversation_duration')

    state.report = report
    return state

def finalize_output(state):
    """Format final output with schema, version, and metadata."""

    if not state.report:
        # Create minimal report if none exists
        state.report = {
            "summary": "Analysis incomplete - no report generated",
            "overall_health": {"score": 0, "label": "unknown"},
            "dimensions": {},
            "extracted_content": {},
            "errors": state.errors or []
        }

    # Add metadata
    state.report["metadata"] = {
        "analysis_timestamp": datetime.now().isoformat(),
        "version": VERSION,
        "pipeline_errors": state.errors or []
    }

    return state

def _generate_summary(stats):
    """Generate natural language summary from statistics."""

    total_messages = stats['total_messages']
    speakers = stats['unique_speakers']
    question_ratio = stats['question_ratio']
    participation_balance = stats['participation_balance']

    # Build summary components
    summary_parts = []

    # Basic stats
    summary_parts.append(f"Communication analysis of {total_messages} messages from {speakers} participants")

    # Engagement
    if question_ratio > 0.3:
        summary_parts.append(f"High engagement with {question_ratio:.0%} of messages being questions")
    elif question_ratio > 0.1:
        summary_parts.append(f"Moderate engagement with {question_ratio:.0%} questions")
    else:
        summary_parts.append(f"Low engagement with only {question_ratio:.0%} questions")

    # Participation
    if participation_balance > 0.8:
        summary_parts.append("Well-balanced participation across speakers")
    elif participation_balance > 0.6:
        summary_parts.append("Reasonably balanced participation")
    else:
        summary_parts.append("Uneven participation - some speakers dominate")

    # Response times (if available)
    if stats.get('median_response_time'):
        response_time = stats['median_response_time']
        if response_time < 2:
            summary_parts.append(f"Very responsive discussion with {response_time:.1f} minute median response time")
        elif response_time < 10:
            summary_parts.append(f"Good responsiveness with {response_time:.1f} minute median response time")
        else:
            summary_parts.append(f"Slower-paced discussion with {response_time:.1f} minute median response time")

    return ". ".join(summary_parts) + "."

def _calculate_overall_health(stats):
    """Calculate overall health score from available statistics."""

    # Simple scoring based on available metrics (will be enhanced with LLM analysis)
    scores = []

    # Participation score (0-100)
    participation_score = stats['participation_balance'] * 100
    scores.append(participation_score)

    # Engagement score (0-100)
    question_ratio = stats['question_ratio']
    if question_ratio > 0.4:
        engagement_score = 100
    elif question_ratio > 0.2:
        engagement_score = 80
    elif question_ratio > 0.1:
        engagement_score = 60
    else:
        engagement_score = 40
    scores.append(engagement_score)

    # Response time score (if available)
    if stats.get('median_response_time'):
        response_time = stats['median_response_time']
        if response_time < 2:
            response_score = 100
        elif response_time < 10:
            response_score = 80
        elif response_time < 30:
            response_score = 60
        else:
            response_score = 40
        scores.append(response_score)

    # Calculate weighted average
    overall_score = sum(scores) / len(scores) if scores else 0

    # Determine label
    if overall_score >= 85:
        label = "excellent"
    elif overall_score >= 75:
        label = "healthy"
    elif overall_score >= 60:
        label = "moderate"
    elif overall_score >= 40:
        label = "needs_attention"
    else:
        label = "poor"

    return round(overall_score, 1), label

def _create_dimension_scores(stats):
    """Create dimensional scores based on available statistics."""

    # Placeholder dimensional scores (will be enhanced with LLM analysis)
    dimensions = {
        "participation": {
            "score": round(stats['participation_balance'] * 100, 1),
            "description": "Balance of contribution across team members"
        },
        "engagement": {
            "score": min(100, round(stats['question_ratio'] * 200, 1)),  # Scale question ratio
            "description": "Level of active participation through questions"
        }
    }

    # Add responsiveness if timestamps available
    if stats.get('median_response_time'):
        response_time = stats['median_response_time']
        if response_time < 2:
            responsiveness_score = 100
        elif response_time < 10:
            responsiveness_score = 80
        elif response_time < 30:
            responsiveness_score = 60
        else:
            responsiveness_score = 40

        dimensions["responsiveness"] = {
            "score": responsiveness_score,
            "description": "Timeliness of responses between participants"
        }

    return dimensions

def _extract_basic_content(validated_data):
    """Extract basic content information (placeholder for LLM analysis)."""

    if not validated_data:
        return {
            "decisions": [],
            "action_items": [],
            "risk_flags": []
        }

    # Very basic content extraction (will be replaced with LLM analysis)

    potential_actions = []
    potential_decisions = []

    for item in validated_data:
        text_lower = item['text'].lower()

        # Look for action items
        for keyword in ACTION_KEYWORDS:
            if keyword in text_lower:
                potential_actions.append(item['text'][:100] + "..." if len(item['text']) > 100 else item['text'])
                break

        # Look for decisions
        for keyword in DECISION_KEYWORDS:
            if keyword in text_lower:
                potential_decisions.append(item['text'][:100] + "..." if len(item['text']) > 100 else item['text'])
                break

    return {
        "decisions": list(set(potential_decisions))[:MAX_EXTRACTED_ITEMS],
        "action_items": list(set(potential_actions))[:MAX_EXTRACTED_ITEMS],
        "risk_flags": []  # Will be populated by LLM analysis
    }

def _generate_comprehensive_summary(scores, insights, stats):
    """Generate comprehensive summary using all analysis components."""

    total_messages = stats['total_messages']
    speakers = stats['unique_speakers']
    overall_score = scores['overall_health_score']
    confidence = scores['confidence_score']

    # Build summary components
    summary_parts = []

    # Basic stats
    summary_parts.append(f"Communication analysis of {total_messages} messages from {speakers} participants")

    # Overall assessment
    health_level = scores['health_levels']['overall_health_score']
    summary_parts.append(f"Overall communication health is {health_level} (score: {overall_score:.1f}/10)")

    # Key strengths from insights
    collaboration_count = len(insights.get('collaboration_indicators', []))
    if collaboration_count > 0:
        summary_parts.append(f"Strong collaboration indicators identified ({collaboration_count} patterns)")

    # Key areas for improvement
    issues_count = len(insights.get('communication_issues', []))
    if issues_count > 0:
        summary_parts.append(f"Some communication challenges detected ({issues_count} issues)")

    # Emotional tone
    emotional_dist = insights.get('emotional_distribution', {})
    positive_ratio = emotional_dist.get('positive_ratio', 0.5)
    if positive_ratio > 0.6:
        summary_parts.append("Predominantly positive emotional tone")
    elif positive_ratio < 0.3:
        summary_parts.append("Concerning negative emotional tone")

    # Confidence in analysis
    if confidence > 8.0:
        summary_parts.append(f"High confidence in analysis ({confidence:.1f}/10)")
    elif confidence < 6.0:
        summary_parts.append(f"Limited confidence due to data constraints ({confidence:.1f}/10)")

    return ". ".join(summary_parts) + "."

def _create_comprehensive_dimensions(scores):
    """Create dimensional scores from calibrated analysis."""

    dimensions = {}

    # Map calibrated scores to dimension structure
    dimension_mapping = {
        'participation': ('participation_score', 'Balance and equality of participation across team members'),
        'clarity': ('clarity_score', 'Clarity and understandability of communication'),
        'engagement': ('engagement_score', 'Level of active participation and interest'),
        'responsiveness': ('responsiveness_score', 'Timeliness and appropriateness of responses'),
        'collaboration': ('collaboration_score', 'Team cohesion and collaborative behaviors')
    }

    for dimension_name, (score_key, description) in dimension_mapping.items():
        if score_key in scores:
            score_value = scores[score_key]
            health_level = scores['health_levels'].get(score_key, 'unknown')

            dimensions[dimension_name] = {
                "score": round(score_value, 1),
                "level": health_level,
                "description": description
            }

    return dimensions

def _extract_rich_content(evidence, insights, validated_data):
    """Extract rich content using evidence and insights."""

    if not evidence or not insights:
        return _extract_basic_content(validated_data)

    # Extract key topics from insights
    key_topics = [item['item'] for item in insights.get('top_key_topics', [])][:MAX_KEY_TOPICS]

    # Extract collaboration examples
    collaboration_examples = [
        {
            "text": ex["text"],
            "speaker": ex["speaker"],
            "reason": "Positive collaboration pattern"
        }
        for ex in evidence.get('collaboration_examples', [])[:3]
    ]

    # Extract communication issues
    issue_examples = [
        {
            "text": ex["text"],
            "speaker": ex["speaker"],
            "reason": ex.get("reason", "Communication concern")
        }
        for ex in evidence.get('negative_examples', [])[:3]
    ]

    # Note: recommendations will be added from calibrated_scores in the main generate_report function
    recommendations = []

    return {
        "key_topics": key_topics,
        "positive_examples": collaboration_examples,
        "areas_for_improvement": issue_examples,
        "recommendations": recommendations[:5],  # Top 5 recommendations
        "insights_summary": {
            "total_chunks_analyzed": insights.get('chunk_count', 0),
            "speakers_involved": insights.get('total_speakers', []),
            "emotional_tone": insights.get('emotional_distribution', {}),
            "main_themes": [item['item'] for item in insights.get('top_tone_indicators', [])][:3]
        }
    }