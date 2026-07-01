"""Align script captions with dialogue in the source video."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from models.segment import Segment
from models.subtitle import SubtitleCue


_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
_STOP_WORDS = {
    # Vietnamese function words.
    "ai", "anh", "ay", "ba", "bang", "bi", "boi", "ca", "cac", "cai",
    "can", "chi", "cho", "co", "con", "cua", "cung", "da", "dang", "de",
    "den", "do", "du", "duoc", "gi", "gia", "hai", "han", "hay", "hon",
    "khi", "khong", "lai", "lam", "la", "len", "luc", "ma", "minh", "mot",
    "nay", "neu", "nhieu", "nhu", "nhung", "noi", "o", "phai", "qua",
    "rang", "rat", "roi", "sau", "se", "su", "tai", "the", "thi", "trong",
    "truoc", "tu", "tung", "van", "va", "vao", "ve", "vi", "voi",
    # English function words commonly present in subtitle dialogue.
    "a", "about", "after", "all", "am", "an", "and", "are", "as", "at",
    "be", "been", "but", "by", "can", "do", "for", "from", "get", "got",
    "had", "has", "have", "he", "her", "him", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "just", "me", "my", "no", "not",
    "now", "of", "on", "or", "our", "out", "she", "so", "that", "the",
    "their", "them", "then", "there", "they", "this", "to", "up", "was",
    "we", "were", "what", "when", "where", "who", "will", "with", "you",
    "your",
}


def align_segments_to_subtitles(
    segments: list[Segment],
    cues: list[SubtitleCue],
    movie_duration: float,
    keyframes: list[float] | None = None,
) -> list[Segment]:
    """Return segments whose source positions follow the script's story.

    The script and source subtitles can be in different languages.  Exact and
    prefix token matches still provide useful anchors for character names,
    places, numbers and named attacks.  A monotonic dynamic-programming pass
    fills the gaps while preserving story order.
    """
    if not segments:
        return segments

    usable_cues = [cue for cue in cues if cue.text.strip() and cue.end > cue.start]
    if not usable_cues:
        return segments

    # Align captions, not only paragraphs. A single paragraph may cross a
    # montage, opening/ending sequence, or post-credit jump in the source.
    centers = _align_caption_centers([segment.text for segment in segments], usable_cues)
    if not centers:
        return segments

    aligned: list[Segment] = []
    previous_start = 0.0
    previous_duration = 0.0
    for segment_index, (segment, center) in enumerate(
        zip(segments, centers, strict=True)
    ):
        source_start = _snap_to_keyframe(
            max(0.0, center - segment.duration / 2.0), keyframes or []
        )
        maximum_start = max(0.0, movie_duration - segment.duration - 0.05)
        minimum_advance = 0.0 if segment_index == 0 else min(2.0, previous_duration * 0.6)
        minimum_start = min(maximum_start, previous_start + minimum_advance)
        clamped = max(minimum_start, min(source_start, maximum_start))
        aligned.append(
            Segment(
                index=segment.index,
                text=segment.text,
                start=segment.start,
                end=segment.end,
                source_start=clamped,
            )
        )
        previous_start = clamped
        previous_duration = segment.duration
    return aligned


def _align_caption_centers(
    caption_texts: list[str], cues: list[SubtitleCue]
) -> list[float]:
    candidate_times = [(cue.start + cue.end) / 2.0 for cue in cues]
    window_tokens: list[set[str]] = []
    for center in candidate_times:
        tokens: set[str] = set()
        for cue in cues:
            cue_center = (cue.start + cue.end) / 2.0
            if abs(cue_center - center) <= 16.0:
                tokens.update(_tokens(cue.text))
        window_tokens.append(tokens)

    document_frequency: Counter[str] = Counter()
    for tokens in window_tokens:
        document_frequency.update(tokens)
    window_count = max(1, len(window_tokens))
    idf = {
        token: math.log((window_count + 1) / (frequency + 1)) + 1.0
        for token, frequency in document_frequency.items()
    }

    section_tokens = [set(_tokens(text)) for text in caption_texts]
    section_weights = [max(1, len(text)) for text in caption_texts]
    total_weight = sum(section_weights)
    cumulative = 0.0
    expected: list[float] = []
    first_time = candidate_times[0]
    timeline_span = max(1.0, candidate_times[-1] - first_time)
    for weight in section_weights:
        expected.append(first_time + ((cumulative + weight / 2.0) / total_weight) * timeline_span)
        cumulative += weight

    emissions: list[list[float]] = []
    for index, tokens in enumerate(section_tokens):
        row: list[float] = []
        for candidate_index, source_tokens in enumerate(window_tokens):
            match_score = _token_overlap_score(tokens, source_tokens, idf)
            distance_penalty = abs(candidate_times[candidate_index] - expected[index]) * 0.0015
            row.append(match_score * 2.5 - distance_penalty)
        emissions.append(row)

    # Dynamic programming keeps every selected source position chronological.
    scores = emissions[0][:]
    paths: list[list[int]] = []
    for section_index in range(1, len(caption_texts)):
        next_scores = [float("-inf")] * len(candidate_times)
        backtrack = [0] * len(candidate_times)
        expected_gap = expected[section_index] - expected[section_index - 1]
        for current in range(len(candidate_times)):
            best_score = float("-inf")
            best_previous = 0
            for previous in range(current + 1):
                actual_gap = candidate_times[current] - candidate_times[previous]
                transition_penalty = abs(actual_gap - expected_gap) * 0.004
                candidate_score = scores[previous] - transition_penalty
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_previous = previous
            next_scores[current] = best_score + emissions[section_index][current]
            backtrack[current] = best_previous
        scores = next_scores
        paths.append(backtrack)

    selected = max(range(len(scores)), key=scores.__getitem__)
    selected_indexes = [selected]
    for backtrack in reversed(paths):
        selected = backtrack[selected]
        selected_indexes.append(selected)
    selected_indexes.reverse()
    return [candidate_times[index] for index in selected_indexes]


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )
    return [
        token
        for token in _TOKEN_RE.findall(normalized)
        if token not in _STOP_WORDS and (len(token) >= 3 or token.isdigit())
    ]


def _token_overlap_score(
    script_tokens: set[str], source_tokens: set[str], idf: dict[str, float]
) -> float:
    score = 0.0
    for script_token in script_tokens:
        matches = [
            source_token
            for source_token in source_tokens
            if script_token == source_token
            or (
                min(len(script_token), len(source_token)) >= 5
                and (
                    script_token.startswith(source_token)
                    or source_token.startswith(script_token)
                )
            )
        ]
        if matches:
            score += max(idf.get(token, 1.0) for token in matches)
    return score


def _snap_to_keyframe(source_start: float, keyframes: list[float]) -> float:
    if not keyframes:
        return source_start
    nearest = min(keyframes, key=lambda timestamp: abs(timestamp - source_start))
    if abs(nearest - source_start) <= 1.25:
        return nearest
    return source_start
