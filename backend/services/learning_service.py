"""
LearningService — thin re-export layer for backward compatibility.
All implementation has been moved to services/learning/ submodules:
  - metrics.py: synthesize_metrics, synthesize_hermes_effectiveness, evaluate_truth_preview, synthesize_windowed_metrics
  - enrichment.py: get_claim_history, enrich_active_findings_with_signals, calibrate_recommendations
  - candidate_generation.py: generate_learning_candidates, get_candidates, review_candidate, update_candidate_implementation, evaluate_candidate_impact
"""
from services.learning.metrics import (
    synthesize_metrics,
    synthesize_hermes_effectiveness,
    evaluate_truth_preview,
    synthesize_windowed_metrics,
)
from services.learning.enrichment import (
    get_claim_history,
    enrich_active_findings_with_signals,
    calibrate_recommendations,
)
from services.learning.candidate_generation import (
    generate_learning_candidates,
    get_candidates,
    review_candidate,
    update_candidate_implementation,
    evaluate_candidate_impact,
)


class LearningService:
    """Backward-compatible static facade for all learning operations."""

    synthesize_metrics = staticmethod(synthesize_metrics)
    synthesize_hermes_effectiveness = staticmethod(synthesize_hermes_effectiveness)
    evaluate_truth_preview = staticmethod(evaluate_truth_preview)
    synthesize_windowed_metrics = staticmethod(synthesize_windowed_metrics)

    get_claim_history = staticmethod(get_claim_history)
    enrich_active_findings_with_signals = staticmethod(enrich_active_findings_with_signals)
    calibrate_recommendations = staticmethod(calibrate_recommendations)

    generate_learning_candidates = staticmethod(generate_learning_candidates)
    get_candidates = staticmethod(get_candidates)
    review_candidate = staticmethod(review_candidate)
    update_candidate_implementation = staticmethod(update_candidate_implementation)
    evaluate_candidate_impact = staticmethod(evaluate_candidate_impact)
