from rapidfuzz import fuzz, process
import pandas as pd
import re

def normalize_id(eq_id: str) -> str:
    """
    Uppercase, trim, strip punctuation, collapse whitespace.
    """
    if not isinstance(eq_id, str):
        return ""
    eq_id = eq_id.upper()
    eq_id = re.sub(r'[^\w\s]', '', eq_id) # remove punctuation
    eq_id = re.sub(r'\s+', ' ', eq_id).strip()
    return eq_id

def score_match(source_id: str, target_id: str) -> float:
    """
    Score the fuzzy match using RapidFuzz token set ratio.
    """
    return fuzz.token_set_ratio(source_id, target_id)

def find_best_canonical_match(source_id: str, canonical_ids: list[str]) -> tuple[str | None, float]:
    """
    Find best match for a given source ID against a list of canonical IDs.
    Returns (best_match_id, score).
    """
    if not source_id or not canonical_ids:
        return None, 0.0
        
    result = process.extractOne(source_id, canonical_ids, scorer=fuzz.token_set_ratio)
    if result:
        match, score, index = result
        return match, score
    return None, 0.0
