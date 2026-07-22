"""Phase 191 Stage 4.2: Extracted SemanticContextFilter.

This module was autonomously identified and extracted from strategy_engine.py
by the Phase 191 self-improvement pipeline.

Original location: strategy_engine.py, lines 203-281
Extraction phase: Phase 191 Stage 4.2
Extraction reason: Pure static class with zero side effects, ideal for modular separation.

Usage:
    from semantic_context_filter import SemanticContextFilter
    result = SemanticContextFilter.evaluate(claim_text, gov_keywords, rev_keywords)
"""
import re


class SemanticContextFilter:
    """Phase 188/189: Context-aware semantic filter for structural signals.
    Detects negation, hedging, and temporal ambiguity using word-boundary regex.
    """
    NEGATION_MARKERS = [r"not", r"no longer", r"never", r"fails to", r"isn't", r"wasn't", r"neither", r"nor"]
    HEDGE_MARKERS = [r"appears", r"seems", r"potentially", r"maybe", r"may", r"likely", r"possible", r"suggests"]
    CONTRAST_MARKERS = [r"but", r"yet", r"however", r"although", r"though", r"nonetheless", r"nevertheless"]
    TEMPORAL_MARKERS = [r"was", r"formerly", r"previously", r"once", r"before", r"past", r"legacy"]

    @staticmethod
    def evaluate(claim_text, gov_keywords, rev_keywords):
        """Evaluates a claim for semantic polarity and clarity with regex hardening."""
        text = claim_text.lower()
        
        # Helper to match with word boundaries
        def has_marker(markers, t):
            for m in markers:
                if re.search(rf"\b{m}\b", t): return True
            return False

        # 1. Detect Markers
        has_negation = has_marker(SemanticContextFilter.NEGATION_MARKERS, text)
        has_hedge = has_marker(SemanticContextFilter.HEDGE_MARKERS, text)
        has_contrast = has_marker(SemanticContextFilter.CONTRAST_MARKERS, text)
        has_temporal = has_marker(SemanticContextFilter.TEMPORAL_MARKERS, text)
        
        # 2. Identify Primary Keywords (Hardened with word boundaries)
        gov_hits = [k for k in gov_keywords if re.search(rf"\b{k}\b", text)]
        rev_hits = [k for k in rev_keywords if re.search(rf"\b{k}\b", text)]
        
        # 3. Determine Base Polarity
        base_polarity = "neutral"
        if len(gov_hits) > 0 and len(rev_hits) == 0:
            base_polarity = "negative" # Governance (Purge/Redundancy)
        elif len(rev_hits) > 0 and len(gov_hits) == 0:
            base_polarity = "positive" # Reversal (Active/Stable)
        elif (len(gov_hits) > 0 and len(rev_hits) > 0) or has_contrast:
            base_polarity = "conflicting"

        # 4. Handle Negation (Polarity Flipping)
        # "not redundant" -> positive
        # "not active" -> negative
        final_polarity = base_polarity
        if has_negation:
            if base_polarity == "negative": final_polarity = "positive"
            elif base_polarity == "positive": final_polarity = "negative"
            # Neutral and Conflicting stay same or become neutral
        
        # 5. Compute Confidence Modifier (Phase 188 Intensity)
        conf_mod = 1.0
        if has_negation: conf_mod = 0.8 # Negation is strong but needs quorum
        if has_hedge: conf_mod *= 0.6   # Hedge reduces intensity
        if has_temporal: conf_mod *= 0.4 # Past state is weak
        if base_polarity == "conflicting": conf_mod *= 0.5

        # 6. Ambiguity Flags
        flags = []
        if has_negation: flags.append("negated")
        if has_hedge: flags.append("hedged")
        if has_contrast: flags.append("contrast")
        if has_temporal: flags.append("temporal")
        if final_polarity == "conflicting": flags.append("conflicting")

        # 7. Actuation Authorization (Phase 188)
        # Actuation only allowed if:
        # - Polarity is unambiguous (positive or negative)
        # - Modified confidence will be checked by caller against threshold.
        # - We return allowed=True if the structure is sound, but loop checks quorum.
        semantic_structure_valid = final_polarity in ["positive", "negative", "conflicting"]
        
        return {
            "polarity": final_polarity,
            "confidence_modifier": round(conf_mod, 2),
            "ambiguity_flags": flags,
            "semantic_structure_valid": semantic_structure_valid,
            "gov_hits": gov_hits,
            "rev_hits": rev_hits
        }
