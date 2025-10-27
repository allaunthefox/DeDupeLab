# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Allaun

"""
NSFW classification using multiple heuristics.
Lightweight, privacy-preserving, fully offline.

Three-tier detection system:
1. Filename pattern matching (instant, zero-cost)
2. Image metadata analysis (requires Pillow)
3. Content analysis (reserved for future ML model)
"""

import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from .deps import check_dep


class NSFWClassifier:
    """
    Multi-tier NSFW content detector.
    
    Confidence scoring: 0=safe, 1=suspicious, 2=likely, 3=certain
    
    Attributes:
        threshold: Minimum score to flag as NSFW (0-3)
        has_pillow: Whether Pillow is available for image analysis
    """
    
    # Filename patterns with confidence weights
    FILENAME_PATTERNS: Dict[str, int] = {
        # High confidence (3) - explicit indicators
        r'\b(nsfw|xxx|porn|nude|adult|explicit|18\+|r18|r-18)\b': 3,
        r'\b(sex|hentai|ecchi|lewd)\b': 3,
        
        # Medium confidence (2) - strong indicators
        r'\b(onlyfans|patreon|fanbox|subscribestar|fansly)\b': 2,
        r'\b(uncensored|uncut|raw|leaked)\b': 2,
        
        # Low confidence (1) - weak indicators
        r'\b(sexy|hot|lingerie|bikini|bath|shower)\b': 1,
        r'_[0-9]{4}x[0-9]{4,}_': 1,  # High-res images (4000x3000+)
        r'\b(night|private|secret|hidden)\b': 1,
    }
    
    # Safe patterns that reduce score
    SAFE_PATTERNS: Dict[str, int] = {
        r'\b(family|vacation|wedding|birthday|graduation|portrait)\b': -2,
        r'\b(landscape|nature|pet|animal|food|recipe|cooking)\b': -2,
        r'\b(work|office|project|document|invoice|receipt|report)\b': -3,
        r'\b(screenshot|screen|desktop|wallpaper)\b': -2,
        r'\b(art|drawing|sketch|painting|illustration)\b': -1,  # Art can be NSFW
    }
    
    def __init__(self, threshold: int = 2):
        """
        Initialize NSFW classifier.
        
        Args:
            threshold: Minimum score (0-3) to flag content as NSFW
        """
        if not 0 <= threshold <= 3:
            raise ValueError(f"Threshold must be 0-3, got {threshold}")
        
        self.threshold = threshold
        self.has_pillow = check_dep("pillow")
        
        # Compile regex patterns for performance
        self._filename_regex = [
            (re.compile(pattern, re.IGNORECASE), weight)
            for pattern, weight in self.FILENAME_PATTERNS.items()
        ]
        self._safe_regex = [
            (re.compile(pattern, re.IGNORECASE), weight)
            for pattern, weight in self.SAFE_PATTERNS.items()
        ]
    
    def classify(self, path: Path, mime: str) -> Dict[str, any]:
        """
        Classify file for NSFW content.
        
        Args:
            path: Path to file
            mime: MIME type of file
            
        Returns:
            {
                'score': int (0-3),
                'flagged': bool (score >= threshold),
                'method': str ('none'|'filename'|'metadata'|'ml'),
                'reason': str (human-readable explanation),
                'threshold': int (threshold used for classification)
            }
        """
        score = 0
        reasons: List[str] = []
        method = "none"
        
        # TIER 1: Filename analysis
        name_lower = path.name.lower()
        parent_lower = str(path.parent).lower()
        
        # Check NSFW patterns
        for regex, weight in self._filename_regex:
            if regex.search(name_lower) or regex.search(parent_lower):
                score += weight
                reasons.append(f"pattern_match:{regex.pattern[:30]}")
                method = "filename"
        
        # Check safe patterns (reduce score)
        for regex, weight in self._safe_regex:
            if regex.search(name_lower) or regex.search(parent_lower):
                score = max(0, score + weight)
                if weight < 0:
                    reasons.append("safe_context")
        
        # TIER 2: Image metadata analysis
        if self.has_pillow and mime.startswith('image/'):
            img_score, img_reason = self._analyze_image_metadata(path)
            score += img_score
            if img_reason:
                reasons.append(img_reason)
                if method == "none":
                    method = "metadata"
        
        # TIER 3: Content analysis (reserved for future ML model)
        # if self.has_ml_model and score > 0:
        #     ml_score = self._analyze_content(path, mime)
        #     score = max(score, ml_score)
        #     method = "ml"
        
        # Clamp score to valid range
        score = min(3, max(0, score))
        
        return {
            'score': score,
            'flagged': score >= self.threshold,
            'method': method,
            'reason': '; '.join(reasons) if reasons else 'none',
            'threshold': self.threshold
        }
    
    def _analyze_image_metadata(self, path: Path) -> Tuple[int, Optional[str]]:
        """
        Analyze image EXIF and properties for NSFW indicators.
        
        Heuristics:
        - Very high resolution (>8000x6000) → +1 (common in adult content)
        - Has camera EXIF → -1 (real photos less likely NSFW)
        - Portrait orientation → +1 (selfies, portraits)
        
        Args:
            path: Path to image file
            
        Returns:
            Tuple of (score_adjustment, reason)
        """
        try:
            from PIL import Image
            
            with Image.open(path) as img:
                width, height = img.size
                
                # Check for very high resolution
                if width * height > 8000 * 6000:
                    return (1, "very_high_res")
                
                # Check EXIF for camera metadata
                exif = img.getexif()
                if exif:
                    # Common EXIF tags for cameras:
                    # 271: Make, 272: Model, 305: Software
                    camera_tags = [271, 272, 305]
                    if any(tag in exif for tag in camera_tags):
                        return (-1, "camera_metadata")
                
                # Check aspect ratio
                if height > 0:
                    aspect = width / height
                    
                    # Portrait orientation (tall and narrow)
                    if 0.5 < aspect < 0.7:
                        return (1, "portrait_orientation")
                    
                    # Ultra-wide (common in certain adult content)
                    if aspect > 2.0:
                        return (1, "ultra_wide")
        
        except Exception:
            # Silently ignore PIL errors
            pass
        
        return (0, None)
    
    def batch_classify(self, paths_with_mime: List[Tuple[Path, str]]) -> Dict[str, Dict]:
        """
        Classify multiple files efficiently.
        
        Args:
            paths_with_mime: List of (Path, mime_type) tuples
            
        Returns:
            Dictionary mapping str(path) to classification result
        """
        results = {}
        for path, mime in paths_with_mime:
            results[str(path)] = self.classify(path, mime)
        return results
    
    def get_statistics(self, results: Dict[str, Dict]) -> Dict[str, any]:
        """
        Calculate statistics from batch classification results.
        
        Args:
            results: Output from batch_classify()
            
        Returns:
            {
                'total': int,
                'flagged': int,
                'score_distribution': {0: count, 1: count, 2: count, 3: count},
                'methods_used': {'filename': count, 'metadata': count, ...}
            }
        """
        from collections import Counter
        
        total = len(results)
        flagged = sum(1 for r in results.values() if r['flagged'])
        
        scores = [r['score'] for r in results.values()]
        score_dist = dict(Counter(scores))
        
        methods = [r['method'] for r in results.values()]
        methods_used = dict(Counter(methods))
        
        return {
            'total': total,
            'flagged': flagged,
            'flagged_percentage': round(100 * flagged / total, 2) if total > 0 else 0,
            'score_distribution': score_dist,
            'methods_used': methods_used
        }


# Example usage:
"""
classifier = NSFWClassifier(threshold=2)

# Single file
result = classifier.classify(Path("photo.jpg"), "image/jpeg")
if result['flagged']:
    print(f"NSFW detected: {result['reason']}")

# Batch processing
files = [
    (Path("vacation.jpg"), "image/jpeg"),
    (Path("nsfw_content.png"), "image/png"),
]
results = classifier.batch_classify(files)
stats = classifier.get_statistics(results)
print(f"Flagged {stats['flagged']} of {stats['total']} files")
"""