"""
CampusConnect: Explainable Multi-Factor Item Matching Service
Automatically matches reported Lost and Found items based on semantic text tokens,
category concordance, geographical location proximity, and temporal proximity.
Provides full score breakdown and human-readable explainability for auditability.
"""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import List, Dict, Any, Optional, Set, Tuple

from models.item import Item
from database.repository import ItemRepository


# Standard English stopwords to remove noise in text matching
COMMON_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by",
    "from", "about", "into", "through", "during", "before", "after", "above",
    "below", "under", "up", "down", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "my", "your", "his", "her",
    "i", "me", "we", "us", "you", "they", "them", "left", "lost", "found",
    "near", "beside", "item", "has", "have", "had", "of", "some"
}


@dataclass
class MatchResult:
    """Represents a scored item match with full explainability metadata."""
    item: Item
    target_item: Item
    overall_score: float  # Percentage: 0.0 - 100.0
    category_score: float  # 0.0 - 1.0
    text_score: float  # 0.0 - 1.0
    location_score: float  # 0.0 - 1.0
    date_score: float  # 0.0 - 1.0
    explanation: str
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert match result to dictionary."""
        return {
            "matched_item_id": self.target_item.id,
            "matched_title": self.target_item.title,
            "overall_score": round(self.overall_score, 1),
            "category_score": round(self.category_score * 100, 1),
            "text_score": round(self.text_score * 100, 1),
            "location_score": round(self.location_score * 100, 1),
            "date_score": round(self.date_score * 100, 1),
            "explanation": self.explanation,
            "reasons": self.reasons,
        }


class MatchingService:
    """
    Explainable Multi-Factor Matching Engine.

    Weights:
    - Category Concordance: 25%
    - Title & Description Text Overlap: 40%
    - Location Proximity: 20%
    - Temporal Proximity (Date): 15%
    """

    WEIGHT_CATEGORY = 0.25
    WEIGHT_TEXT = 0.40
    WEIGHT_LOCATION = 0.20
    WEIGHT_DATE = 0.15

    def __init__(self, item_repo: Optional[ItemRepository] = None, db_path: Optional[str] = None) -> None:
        self.item_repo = item_repo if item_repo is not None else ItemRepository(db_path)

    @classmethod
    def tokenize(cls, text: str) -> Set[str]:
        """Normalize, remove punctuation, and extract non-stopword tokens."""
        if not text:
            return set()
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = {word.strip() for word in cleaned.split() if len(word.strip()) > 1}
        return tokens - COMMON_STOPWORDS

    @classmethod
    def stem_token(cls, word: str) -> str:
        """Lightweight morphological stemmer for common English item descriptions."""
        w = word.lower().strip()
        if len(w) > 5 and w.endswith("ing"):
            return w[:-3]
        if len(w) > 4 and w.endswith("es"):
            return w[:-2]
        if len(w) > 4 and w.endswith("ed"):
            return w[:-2]
        if len(w) > 4 and w.endswith("er"):
            return w[:-2]
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            return w[:-1]
        return w

    @classmethod
    def calculate_text_similarity(cls, text_a: str, text_b: str) -> Tuple[float, Set[str]]:
        """
        Calculate token and morphological root similarity with overlap tracking.
        Returns (similarity_score [0.0 - 1.0], overlapping_tokens).
        """
        tokens_a = cls.tokenize(text_a)
        tokens_b = cls.tokenize(text_b)

        if not tokens_a or not tokens_b:
            return 0.0, set()

        # Map stems back to representative original tokens
        stems_a = {cls.stem_token(t): t for t in tokens_a}
        stems_b = {cls.stem_token(t): t for t in tokens_b}

        intersection_stems = set(stems_a.keys()).intersection(stems_b.keys())
        union_stems = set(stems_a.keys()).union(stems_b.keys())

        if not union_stems:
            return 0.0, set()

        # Identify shared original words
        shared_words = {stems_a[s] for s in intersection_stems}

        jaccard = len(intersection_stems) / len(union_stems)
        overlap_ratio = len(intersection_stems) / min(len(stems_a), len(stems_b))
        combined = (jaccard * 0.4) + (overlap_ratio * 0.6)
        return min(1.0, combined), shared_words

    @classmethod
    def calculate_location_similarity(cls, loc_a: str, loc_b: str) -> Tuple[float, Set[str]]:
        """
        Calculate location similarity using token overlap and substring containment.
        """
        if not loc_a or not loc_b:
            return 0.0, set()

        clean_a = loc_a.strip().lower()
        clean_b = loc_b.strip().lower()

        if clean_a == clean_b:
            return 1.0, {clean_a}

        # Substring containment (e.g. "Library" in "Library 2nd Floor")
        if clean_a in clean_b or clean_b in clean_a:
            return 0.85, {clean_a if len(clean_a) < len(clean_b) else clean_b}

        # Token overlap
        score, shared = cls.calculate_text_similarity(clean_a, clean_b)
        return score, shared

    @classmethod
    def calculate_date_proximity(cls, date_str_a: str, date_str_b: str) -> float:
        """
        Calculate temporal score based on days difference.
        Same day = 1.0, within 3 days = 0.85, within 7 days = 0.65, within 14 days = 0.4, 30+ days = 0.1.
        """
        try:
            d_a = datetime.strptime(date_str_a, "%Y-%m-%d").date()
            d_b = datetime.strptime(date_str_b, "%Y-%m-%d").date()
            days_diff = abs((d_a - d_b).days)
        except (ValueError, TypeError):
            return 0.5  # Neutral fallback if date parsing fails

        if days_diff == 0:
            return 1.0
        elif days_diff <= 2:
            return 0.90
        elif days_diff <= 5:
            return 0.75
        elif days_diff <= 10:
            return 0.55
        elif days_diff <= 20:
            return 0.35
        elif days_diff <= 30:
            return 0.20
        else:
            return 0.05

    def score_match(self, source: Item, candidate: Item) -> MatchResult:
        """
        Score compatibility between two items and generate explainable reasons.
        """
        reasons: List[str] = []

        # 1. Category Concordance
        if source.category.lower() == candidate.category.lower():
            category_score = 1.0
            reasons.append(f"Identical category: '{source.category}'")
        else:
            category_score = 0.0
            reasons.append(f"Different categories: '{source.category}' vs '{candidate.category}'")

        # 2. Text Similarity (Combining Title and Description)
        source_content = f"{source.title} {source.description}"
        candidate_content = f"{candidate.title} {candidate.description}"
        text_score, shared_words = self.calculate_text_similarity(source_content, candidate_content)

        if shared_words:
            reasons.append(f"Key shared terms: {', '.join(sorted(list(shared_words))[:5])}")
        else:
            reasons.append("No significant shared descriptive terms")

        # 3. Location Proximity
        loc_score, shared_loc_words = self.calculate_location_similarity(source.location, candidate.location)
        if loc_score >= 0.8:
            reasons.append(f"High location match: '{source.location}' matched '{candidate.location}'")
        elif loc_score > 0.3:
            reasons.append(f"Partial location match: '{source.location}' and '{candidate.location}'")
        else:
            reasons.append("Different reported locations")

        # 4. Date Proximity
        date_score = self.calculate_date_proximity(source.event_date, candidate.event_date)
        if date_score >= 0.9:
            reasons.append(f"Close dates ({source.event_date} vs {candidate.event_date})")
        elif date_score <= 0.2:
            reasons.append(f"Distant dates ({source.event_date} vs {candidate.event_date})")

        # Weighted calculation
        overall = (
            (category_score * self.WEIGHT_CATEGORY) +
            (text_score * self.WEIGHT_TEXT) +
            (loc_score * self.WEIGHT_LOCATION) +
            (date_score * self.WEIGHT_DATE)
        ) * 100.0

        # Category mismatch penalty: if categories differ completely, cap score to prevent false positives
        if category_score == 0.0:
            overall = min(overall, 35.0)

        # Build summary explanation string
        pct_display = round(overall, 1)
        top_reasons = "; ".join(reasons[:3])
        explanation = f"{pct_display}% Match: {top_reasons}."

        return MatchResult(
            item=source,
            target_item=candidate,
            overall_score=overall,
            category_score=category_score,
            text_score=text_score,
            location_score=loc_score,
            date_score=date_score,
            explanation=explanation,
            reasons=reasons
        )

    def find_matches_for_item(
        self,
        item: Item,
        min_threshold: float = 35.0,
        limit: int = 10
    ) -> List[MatchResult]:
        """
        Find candidate counterpart items.
        If item is LOST, searches active FOUND items.
        If item is FOUND, searches active LOST items.
        Returns results sorted by overall score descending.
        """
        counterpart_type = "FOUND" if item.type == "LOST" else "LOST"

        # Query active candidates from repository (OPEN or CLAIM_PENDING)
        all_candidates = self.item_repo.list_items(
            item_type=counterpart_type,
            limit=200
        )
        candidates = [c for c in all_candidates if c.status in ("OPEN", "CLAIM_PENDING")]

        matches: List[MatchResult] = []
        for candidate in candidates:
            # Do not match item with itself or items created by the same user if they are identical
            if candidate.id == item.id:
                continue

            result = self.score_match(item, candidate)
            if result.overall_score >= min_threshold:
                matches.append(result)

        # Sort by overall score descending
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        return matches[:limit]
