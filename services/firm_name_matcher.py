"""
firm_name_matcher.py

This module provides the FirmNameMatcher class for fuzzy name matching of firm names.
"""

from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

class FirmNameMatcher:
    """Service for fuzzy matching of firm names."""
    
    def find_best_match(self, search_name: str, candidates: List[Dict[str, Any]], threshold: float = 0.8) -> Optional[Dict[str, Any]]:
        """
        Find the best matching firm record from a list of candidates.
        
        Args:
            search_name: Name to search for
            candidates: List of firm records to search through
            threshold: Minimum similarity score threshold (default: 0.8)
            
        Returns:
            Best matching firm record or None if no good match found
        """
        best_match = None
        best_score = 0
        
        normalized_search = self._normalize_name(search_name)
        
        for candidate in candidates:
            firm_name = candidate.get('firm_name', '')
            if not firm_name:
                continue
                
            normalized_candidate = self._normalize_name(firm_name)
            score = self._calculate_similarity(normalized_search, normalized_candidate)
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = candidate.copy()
                best_match['match_score'] = score
                
        return best_match
        
    def _normalize_name(self, name: str) -> str:
        """
        Normalize a firm name for comparison.
        
        Args:
            name: Firm name to normalize
            
        Returns:
            Normalized firm name
        """
        # Convert to lowercase
        normalized = name.lower()
        
        # Remove common business suffixes
        suffixes = [
            ' llc', ' inc', ' corp', ' corporation', ' ltd', ' limited',
            ' lp', ' llp', ' l.l.c.', ' inc.', ' corp.', ' ltd.'
        ]
        for suffix in suffixes:
            normalized = normalized.replace(suffix, '')
            
        # Remove special characters and extra whitespace
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        normalized = ' '.join(normalized.split())
        
        return normalized
        
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity score between two strings.
        
        Args:
            str1: First string to compare
            str2: Second string to compare
            
        Returns:
            Similarity score between 0 and 1
        """
        return SequenceMatcher(None, str1, str2).ratio()

# TODO: Implement firm name matching logic