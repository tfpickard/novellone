"""Text statistics utilities for analyzing story content."""
import re
from typing import Any


def calculate_text_stats(text: str) -> dict[str, Any]:
    """Calculate comprehensive statistics for a text.
    
    Returns:
        Dictionary containing:
        - word_count: Total number of words
        - character_count: Total characters (including spaces)
        - character_count_no_spaces: Characters excluding whitespace
        - sentence_count: Approximate number of sentences
        - paragraph_count: Number of paragraphs
        - avg_word_length: Average length of words in characters
        - avg_sentence_length: Average words per sentence
        - unique_words: Number of unique words (case-insensitive)
        - lexical_diversity: Ratio of unique words to total words
    """
    if not text or not text.strip():
        return {
            "word_count": 0,
            "character_count": 0,
            "character_count_no_spaces": 0,
            "sentence_count": 0,
            "paragraph_count": 0,
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "unique_words": 0,
            "lexical_diversity": 0.0,
        }
    
    # Character counts
    character_count = len(text)
    character_count_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    
    # Paragraph count (split by double newlines or single newlines with content)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    paragraph_count = len(paragraphs)
    
    # Word extraction: split on whitespace and remove punctuation
    # Keep words that contain at least one alphanumeric character
    words = re.findall(r"\b[a-zA-Z0-9]+(?:['\'][a-zA-Z0-9]+)*\b", text)
    word_count = len(words)
    
    # Average word length
    avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0.0
    
    # Unique words and lexical diversity
    unique_words = len(set(w.lower() for w in words))
    lexical_diversity = unique_words / word_count if word_count > 0 else 0.0
    
    # Sentence count (approximate by counting sentence-ending punctuation)
    sentence_endings = re.findall(r'[.!?]+', text)
    sentence_count = len(sentence_endings) if sentence_endings else 1
    
    # Average sentence length
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0
    
    return {
        "word_count": word_count,
        "character_count": character_count,
        "character_count_no_spaces": character_count_no_spaces,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "unique_words": unique_words,
        "lexical_diversity": round(lexical_diversity, 3),
    }


def calculate_aggregate_stats(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate statistics across multiple chapters.
    
    Args:
        chapters: List of chapter dictionaries, each containing 'content' and optionally 'stats'
    
    Returns:
        Dictionary containing aggregated statistics
    """
    if not chapters:
        return {
            "total_word_count": 0,
            "total_character_count": 0,
            "avg_words_per_chapter": 0.0,
            "avg_word_length": 0.0,
            "avg_sentence_length": 0.0,
            "total_unique_words": 0,
            "overall_lexical_diversity": 0.0,
        }
    
    # Aggregate individual stats or calculate them
    total_word_count = 0
    total_character_count = 0
    total_avg_word_length = 0.0
    total_avg_sentence_length = 0.0
    all_words: set[str] = set()
    
    for chapter in chapters:
        # Get stats if already calculated, otherwise calculate now
        if "stats" in chapter:
            stats = chapter["stats"]
        else:
            stats = calculate_text_stats(chapter.get("content", ""))
        
        total_word_count += stats["word_count"]
        total_character_count += stats["character_count"]
        total_avg_word_length += stats["avg_word_length"] * stats["word_count"]
        total_avg_sentence_length += stats["avg_sentence_length"] * stats["sentence_count"]
        
        # Collect all unique words across chapters
        words = re.findall(r"\b[a-zA-Z0-9]+(?:['\'][a-zA-Z0-9]+)*\b", chapter.get("content", ""))
        all_words.update(w.lower() for w in words)
    
    total_sentences = sum(
        (chapter.get("stats", {}).get("sentence_count", 0) 
         if "stats" in chapter 
         else calculate_text_stats(chapter.get("content", ""))["sentence_count"])
        for chapter in chapters
    )
    
    avg_words_per_chapter = total_word_count / len(chapters) if chapters else 0.0
    avg_word_length = total_avg_word_length / total_word_count if total_word_count > 0 else 0.0
    avg_sentence_length = total_avg_sentence_length / total_sentences if total_sentences > 0 else 0.0
    overall_lexical_diversity = len(all_words) / total_word_count if total_word_count > 0 else 0.0
    
    return {
        "total_word_count": total_word_count,
        "total_character_count": total_character_count,
        "avg_words_per_chapter": round(avg_words_per_chapter, 2),
        "avg_word_length": round(avg_word_length, 2),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "total_unique_words": len(all_words),
        "overall_lexical_diversity": round(overall_lexical_diversity, 3),
    }


__all__ = ["calculate_text_stats", "calculate_aggregate_stats"]

