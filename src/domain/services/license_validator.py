"""License validation and extraction utilities."""
from typing import Optional, Any, Dict
from src.domain.entities import LicenseType, License
import re


class LicenseValidator:
    """Validates, normalizes, and extracts license information from text and API data."""
    
    # License detection patterns - ordered by priority/specificity
    LICENSE_PATTERNS = [
        r"\bMIT\b",
        r"\b(?:3[-\s]?Clause\s+)?BSD(?:\s+(?:License|[-\s]?3[-\s]?Clause))?\b",
        r"\bNew\s+BSD\s+License\b",
        r"\bModified\s+BSD\s+License\b",
        r"\bApache(?:[-\s]?2\.0)?\b",  # Matches: Apache, Apache 2.0, Apache-2.0
        r"\bApache(?: License)?(?: Version)? ?2\.0\b",
        r"\bGPL(?:[- ]?v?(\d(?:\.\d)?)?)\b",
        r"\bLGPL(?:[- ]?v?(\d(?:\.\d)?)?)\b",
        r"\bMPL(?:[- ]?v?(\d(?:\.\d)?)?)\b",
        r"\bMozilla\s+Public\s+License(?:\s+2\.0)?\b",
        r"\bPython Software Foundation\b",
        r"\bPSF\b",
        r"\bProprietary\b",
        r"\bCommercial\b",
    ]
    
    # Heuristic indicators for specific licenses
    BSD_INDICATORS = [
        "Redistribution and use in source and binary forms",
        "without modification are permitted",
        "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS",
        "Neither the name of the",
        "Redistribution and use",  # More flexible pattern
    ]
    
    MIT_INDICATORS = [
        "Permission is hereby granted, free of charge",
        "to deal in the Software without restriction",
        "THE SOFTWARE IS PROVIDED 'AS IS'",
    ]
    
    APACHE_INDICATORS = [
        "Licensed under the Apache License",
        "Apache License, Version 2.0",
        "http://www.apache.org/licenses/LICENSE-2.0",
    ]
    
    GPL_INDICATORS = [
        "GNU General Public License",
        "This program is free software",
        "can redistribute it and/or modify it under the terms",
    ]
    
    # Mapping of license names to LicenseType for validation
    LICENSE_TYPE_MAP = {
        "MIT": LicenseType.MIT,
        "BSD": LicenseType.BSD_3_CLAUSE,
        "Apache": LicenseType.APACHE_2_0,
        "GPL": LicenseType.GPL_3_0,
        "LGPL": LicenseType.LGPL_2_1,
        "MPL": LicenseType.MPL_2_0,
        "PSF": LicenseType.MIT,  # Python Software Foundation often uses MIT-like
        "Python": LicenseType.MIT,
    }
    
    @staticmethod
    def extract_license_from_sources(
        pypi_info: Optional[Dict[str, Any]] = None,
        github_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[License]:
        """
        Extract valid license from PyPI and GitHub data sources.
        
        Cascade strategy (stops at first valid license found):
        1. PyPI direct license field (with validation)
        2. PyPI license_expression field
        3. PyPI classifiers (License ::)
        4. GitHub license (if PyPI sources exhausted)
        
        Returns License object if valid license found, None otherwise.
        
        Args:
            pypi_info: Dict with PyPI package info (from /packages/{name}/{version}/json)
            github_data: Dict with GitHub repo data (from /repos/{owner}/{repo})
            
        Returns:
            License object with name and type, or None if no valid license found
        """
        # Level 1: PyPI direct license field
        if pypi_info:
            license_name = pypi_info.get("license")
            if license_name:
                license_name = LicenseValidator._safe_str(license_name)
                extracted = LicenseValidator.extract_license(license_name)
                if extracted:
                    license_type = LicenseValidator.get_license_type(extracted)
                    return License(name=extracted, license_type=license_type)
        
        # Level 2: PyPI license_expression
        if pypi_info:
            license_expression = pypi_info.get("license_expression")
            if license_expression:
                license_expression = LicenseValidator._safe_str(license_expression)
                extracted = LicenseValidator.extract_license(license_expression)
                if extracted:
                    license_type = LicenseValidator.get_license_type(extracted)
                    return License(name=extracted, license_type=license_type)
        
        # Level 3: PyPI classifiers
        if pypi_info:
            classifiers = pypi_info.get("classifiers", [])
            if isinstance(classifiers, list):
                for classifier in classifiers:
                    if isinstance(classifier, str) and "License ::" in classifier:
                        license_name = LicenseValidator.extract_from_classifier(classifier)
                        if license_name:
                            extracted = LicenseValidator.extract_license(license_name)
                            if extracted:
                                license_type = LicenseValidator.get_license_type(extracted)
                                return License(name=extracted, license_type=license_type)
        
        # Level 4: GitHub license (fallback when PyPI sources exhausted)
        if github_data:
            license_obj = github_data.get("license") or {}
            if isinstance(license_obj, dict):
                # Try SPDX key first (more reliable), then full name
                github_license_str = license_obj.get("key") or license_obj.get("name")
                if github_license_str:
                    github_license_str = LicenseValidator._safe_str(github_license_str)
                    extracted = LicenseValidator.extract_license(github_license_str)
                    if extracted:
                        license_type = LicenseValidator.get_license_type(extracted)
                        return License(name=extracted, license_type=license_type)
        
        # No valid license found in any source
        return None
    
    @staticmethod
    def extract_license(text: Optional[str]) -> Optional[str]:
        """
        Detect known licenses or infer them by text heuristics.
        
        Process:
        1. Try exact regex pattern matching
        2. Use heuristic indicators if no exact match
        
        Returns the detected license name or None.
        """
        if not text or not isinstance(text, str):
            return None
        
        text_cleaned = text.strip()
        if not text_cleaned or len(text_cleaned) < 3:
            return None
        
        # 1️⃣ Search for exact pattern matches
        for pattern in LicenseValidator.LICENSE_PATTERNS:
            match = re.search(pattern, text_cleaned, flags=re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        # 2️⃣ Heuristics: BSD or MIT when not explicitly mentioned
        if any(phrase.lower() in text_cleaned.lower() for phrase in LicenseValidator.BSD_INDICATORS):
            return "BSD (Detected by clause heuristics)"
        if any(phrase.lower() in text_cleaned.lower() for phrase in LicenseValidator.MIT_INDICATORS):
            return "MIT (Detected by clause heuristics)"
        if any(phrase.lower() in text_cleaned.lower() for phrase in LicenseValidator.APACHE_INDICATORS):
            return "Apache 2.0 (Detected by clause heuristics)"
        if any(phrase.lower() in text_cleaned.lower() for phrase in LicenseValidator.GPL_INDICATORS):
            return "GPL (Detected by clause heuristics)"
        
        return None
    
    @staticmethod
    def is_valid_license(license_text: Optional[str]) -> bool:
        """Check if a license string is valid (recognized or detectable)."""
        if not license_text or not isinstance(license_text, str):
            return False
        
        license_text = license_text.strip()
        if not license_text or len(license_text) < 3:
            return False
        
        # Try to extract - if extraction is successful, it's valid
        extracted = LicenseValidator.extract_license(license_text)
        return extracted is not None
    
    @staticmethod
    def get_license_type(license_text: Optional[str]) -> Optional[LicenseType]:
        """Try to determine the LicenseType from a license string."""
        if not license_text or not isinstance(license_text, str):
            return None
        
        license_text = license_text.strip()
        extracted = LicenseValidator.extract_license(license_text)
        
        if not extracted:
            return None
        
        # Map extracted license name to LicenseType
        for key, license_type in LicenseValidator.LICENSE_TYPE_MAP.items():
            if key.lower() in extracted.lower():
                return license_type
        
        return None
    
    @staticmethod
    def extract_from_classifier(classifier: str) -> Optional[str]:
        """Extract license name from a License classifier.
        
        Format: "License :: OSI Approved :: MIT License"
        Returns just: "MIT License"
        """
        if not classifier or not classifier.startswith("License ::"):
            return None
        
        parts = classifier.split(" :: ")
        if len(parts) >= 3:
            license_name = parts[-1]
            # Also try to extract with our advanced method
            return LicenseValidator.extract_license(license_name) or license_name
        
        return None
    
    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        """Return a stripped string or None for non-string/empty values."""
        if isinstance(value, str):
            v = value.strip()
            return v if v else None
        return None
