import math
from config import (DIMENSION_WEIGHTS, HEALTH_SCORE_THRESHOLDS, CONFIDENCE_FACTORS,
                   PARTICIPATION_SCORING, CLARITY_SCORING, ENGAGEMENT_SCORING,
                   RESPONSIVENESS_SCORING, COLLABORATION_SCORING, CONFIDENCE_CALCULATION,
                   RECOMMENDATION_THRESHOLDS, RESPONSE_TIME_THRESHOLDS)

def calibrate_scores(state):
    """Calibrate final health scores by combining all analysis components."""
    reporter = state.get_reporter()  # Create reporter once for all helper functions

    # Progress tracking
    state.current_step += 1
    state.add_log(f"[{state.current_step}/{state.total_steps}] CALIBRATE_SCORES: Computing final health scores...")

    # Check required data
    required_attrs = ['basic_stats', 'merged_insights', 'evidence']
    missing_attrs = [attr for attr in required_attrs if not hasattr(state, attr)]

    if missing_attrs:
        state.add_error(f"calibrate_scores: Missing required data: {missing_attrs}")
        return state

    try:
        # Get component scores
        stats = state.basic_stats
        insights = state.merged_insights
        evidence = state.evidence

        # Initialize calibrated scores
        calibrated_scores = {
            'participation_score': 0.0,
            'clarity_score': 0.0,
            'engagement_score': 0.0,
            'responsiveness_score': 0.0,
            'collaboration_score': 0.0,
            'overall_health_score': 0.0,
            'confidence_score': 0.0
        }

        # 1. PARTICIPATION SCORE (25% weight)
        participation_balance = stats.get('participation_balance', PARTICIPATION_SCORING['default_balance'])
        # Convert balance (0.0 = perfectly balanced) to score (10 = excellent)
        participation_score = max(0, PARTICIPATION_SCORING['max_score'] - (participation_balance * PARTICIPATION_SCORING['balance_multiplier']))
        calibrated_scores['participation_score'] = min(PARTICIPATION_SCORING['max_score'], participation_score)

        # 2. CLARITY SCORE (20% weight)
        # Combine LLM clarity analysis with question-answer patterns
        llm_clarity = insights.get('overall_clarity', CLARITY_SCORING['default_llm_score'])
        question_ratio = stats.get('question_ratio', CLARITY_SCORING['default_question_ratio'])
        # Higher question ratio can indicate engagement but also confusion
        if question_ratio < CLARITY_SCORING['question_ratio_low_threshold']:
            clarity_adjustment = CLARITY_SCORING['adjustment_neutral']
        elif question_ratio > CLARITY_SCORING['question_ratio_high_threshold']:
            clarity_adjustment = CLARITY_SCORING['adjustment_negative']
        else:
            clarity_adjustment = CLARITY_SCORING['adjustment_positive']
        calibrated_scores['clarity_score'] = max(0.0, min(10.0, llm_clarity + clarity_adjustment))

        # 3. ENGAGEMENT SCORE (20% weight)
        # Combine LLM engagement analysis with statistical indicators
        llm_engagement = insights.get('overall_engagement', ENGAGEMENT_SCORING['default_llm_score'])
        avg_words = stats.get('avg_words_per_message', ENGAGEMENT_SCORING['default_avg_words'])
        # Longer messages often indicate higher engagement
        if avg_words > ENGAGEMENT_SCORING['word_threshold_high']:
            word_factor = ENGAGEMENT_SCORING['word_factor_high']
        elif avg_words > ENGAGEMENT_SCORING['word_threshold_medium']:
            word_factor = ENGAGEMENT_SCORING['word_factor_medium']
        else:
            word_factor = ENGAGEMENT_SCORING['word_factor_low']
        calibrated_scores['engagement_score'] = max(0.0, min(10.0, llm_engagement + word_factor))

        # 4. RESPONSIVENESS SCORE (15% weight)
        # Base on response times and LLM patterns analysis
        response_time_score = _calculate_responsiveness_from_timing(stats)
        pattern_count = len(insights.get('top_responsiveness_patterns', []))
        pattern_bonus = min(RESPONSIVENESS_SCORING['pattern_bonus_max'], pattern_count * RESPONSIVENESS_SCORING['pattern_bonus_multiplier'])
        calibrated_scores['responsiveness_score'] = max(0.0, min(10.0, response_time_score + pattern_bonus))

        # 5. COLLABORATION SCORE (20% weight)
        # Based on positive vs negative indicators
        collaboration_count = len(insights.get('collaboration_indicators', []))
        conflict_count = len(insights.get('conflict_indicators', []))
        positive_ratio = insights.get('emotional_distribution', {}).get('positive_ratio', COLLABORATION_SCORING['default_positive_ratio'])

        collaboration_base = min(COLLABORATION_SCORING['max_base_score'], collaboration_count * COLLABORATION_SCORING['indicator_multiplier'])
        positive_bonus = positive_ratio * COLLABORATION_SCORING['positive_multiplier']
        conflict_penalty = min(COLLABORATION_SCORING['conflict_penalty_max'], conflict_count * COLLABORATION_SCORING['conflict_penalty_multiplier'])

        calibrated_scores['collaboration_score'] = max(0.0, min(10.0, collaboration_base + positive_bonus - conflict_penalty))

        # 6. OVERALL HEALTH SCORE
        # Weighted combination of all dimension scores
        overall_score = sum(
            calibrated_scores[dimension] * weight
            for dimension, weight in DIMENSION_WEIGHTS.items()
        )
        calibrated_scores['overall_health_score'] = overall_score

        # 7. CONFIDENCE SCORE
        # Based on data completeness and analysis depth
        confidence_calculation = {
            'has_timestamps': CONFIDENCE_FACTORS['has_timestamps'] if stats.get('has_timestamps', False) else CONFIDENCE_FACTORS['no_timestamps'],
            'sufficient_messages': CONFIDENCE_FACTORS['sufficient_messages_score'] if stats.get('total_messages', 0) >= CONFIDENCE_FACTORS['sufficient_messages_threshold'] else CONFIDENCE_FACTORS['insufficient_messages_score'],
            'multiple_speakers': CONFIDENCE_FACTORS['multiple_speakers_score'] if len(stats.get('speaker_message_counts', {})) > 1 else CONFIDENCE_FACTORS['single_speaker_score'],
            'llm_analysis_depth': min(1.0, len(state.llm_insights) * CONFIDENCE_CALCULATION['llm_analysis_multiplier']) if hasattr(state, 'llm_insights') else CONFIDENCE_CALCULATION['llm_analysis_default'],
            'evidence_available': CONFIDENCE_FACTORS['evidence_available_score'] if len(evidence.get('positive_examples', [])) + len(evidence.get('negative_examples', [])) > 0 else CONFIDENCE_FACTORS['no_evidence_score']
        }

        confidence_score = sum(confidence_calculation.values()) / len(confidence_calculation) * CONFIDENCE_CALCULATION['score_multiplier']
        calibrated_scores['confidence_score'] = confidence_score

        # Generate health level categories
        calibrated_scores['health_levels'] = _categorize_all_scores(calibrated_scores)

        # Calculate score distribution
        score_values = [
            calibrated_scores['participation_score'],
            calibrated_scores['clarity_score'],
            calibrated_scores['engagement_score'],
            calibrated_scores['responsiveness_score'],
            calibrated_scores['collaboration_score']
        ]

        calibrated_scores['score_statistics'] = {
            'mean': sum(score_values) / len(score_values),
            'min': min(score_values),
            'max': max(score_values),
            'range': max(score_values) - min(score_values),
            'standard_deviation': _calculate_std_dev(score_values)
        }

        # Add recommendations based on scores
        calibrated_scores['recommendations'] = _generate_recommendations(calibrated_scores, insights)

        # Store calibrated scores in state
        state.calibrated_scores = calibrated_scores
        state.add_log(f"✓ [{state.current_step}/{state.total_steps}] CALIBRATE_SCORES: Health scores computed (Overall: {calibrated_scores['overall_health_score']:.1f}/10)")

    except Exception as e:
        state.add_error(f"calibrate_scores: Failed to calibrate scores - {str(e)}")
        state.add_log(f"✗ [{state.current_step}/{state.total_steps}] CALIBRATE_SCORES: Failed to calibrate scores - {str(e)}")

    return state

def _calculate_responsiveness_from_timing(stats):
    """Calculate responsiveness score based on timing data."""
    if not stats.get('has_timestamps', False):
        return RESPONSIVENESS_SCORING['default_no_timestamp_score']

    median_response = stats.get('median_response_time')
    if median_response is None:
        return RESPONSIVENESS_SCORING['default_no_response_score']

    # Convert minutes to score (faster responses = higher score)
    # Use configured response time thresholds
    if median_response <= RESPONSE_TIME_THRESHOLDS['excellent']:
        return RESPONSIVENESS_SCORING['time_score_excellent']
    elif median_response <= RESPONSE_TIME_THRESHOLDS['good']:
        return RESPONSIVENESS_SCORING['time_score_good']
    elif median_response <= RESPONSE_TIME_THRESHOLDS['fair']:
        return RESPONSIVENESS_SCORING['time_score_fair']
    elif median_response <= RESPONSE_TIME_THRESHOLDS['poor']:
        return RESPONSIVENESS_SCORING['time_score_poor']
    else:
        return RESPONSIVENESS_SCORING['time_score_critical']

def _calculate_std_dev(values):
    """Calculate standard deviation of score values."""
    if len(values) <= 1:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)

def _categorize_all_scores(scores):
    """Categorize all dimension scores into health levels."""
    levels = {}

    for dimension in ['participation_score', 'clarity_score', 'engagement_score',
                     'responsiveness_score', 'collaboration_score', 'overall_health_score']:
        score = scores[dimension]
        levels[dimension] = _categorize_single_score(score)

    return levels

def _categorize_single_score(score):
    """Categorize a single score into health level."""
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

def _generate_recommendations(scores, insights):
    """Generate improvement recommendations based on scores."""
    recommendations = []

    # Participation recommendations
    if scores['participation_score'] < RECOMMENDATION_THRESHOLDS['participation']:
        recommendations.append({
            'category': 'participation',
            'issue': 'Unbalanced participation detected',
            'suggestion': 'Encourage quieter participants and moderate dominant speakers',
            'priority': 'high'
        })

    # Clarity recommendations
    if scores['clarity_score'] < RECOMMENDATION_THRESHOLDS['clarity']:
        recommendations.append({
            'category': 'clarity',
            'issue': 'Communication clarity needs improvement',
            'suggestion': 'Use clearer language, ask for clarification, and summarize key points',
            'priority': 'high'
        })

    # Engagement recommendations
    if scores['engagement_score'] < RECOMMENDATION_THRESHOLDS['engagement']:
        recommendations.append({
            'category': 'engagement',
            'issue': 'Low engagement levels observed',
            'suggestion': 'Ask more questions, encourage participation, and make discussions interactive',
            'priority': 'medium'
        })

    # Responsiveness recommendations
    if scores['responsiveness_score'] < RECOMMENDATION_THRESHOLDS['responsiveness']:
        recommendations.append({
            'category': 'responsiveness',
            'issue': 'Slow or poor responsiveness patterns',
            'suggestion': 'Set response time expectations and follow up on unanswered questions',
            'priority': 'medium'
        })

    # Collaboration recommendations
    if scores['collaboration_score'] < RECOMMENDATION_THRESHOLDS['collaboration']:
        if len(insights.get('conflict_indicators', [])) > 0:
            recommendations.append({
                'category': 'collaboration',
                'issue': 'Conflicts or tensions detected',
                'suggestion': 'Address conflicts directly and foster positive team dynamics',
                'priority': 'high'
            })
        else:
            recommendations.append({
                'category': 'collaboration',
                'issue': 'Limited collaboration observed',
                'suggestion': 'Encourage teamwork, shared goals, and mutual support',
                'priority': 'medium'
            })

    # Overall recommendations
    if scores['overall_health_score'] < RECOMMENDATION_THRESHOLDS['overall']:
        recommendations.append({
            'category': 'overall',
            'issue': 'Overall communication health needs attention',
            'suggestion': 'Focus on the highest priority issues above and establish regular communication health check-ins',
            'priority': 'high'
        })

    return recommendations