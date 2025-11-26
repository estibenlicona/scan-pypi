#!/usr/bin/env python3
"""
Test script for the improved license extraction with regex patterns and heuristics.
"""

from src.domain.services.license_validator import LicenseValidator

# Test cases: (input_text, expected_contains_keyword)
TEST_CASES = [
    # Exact patterns
    ("MIT", "MIT"),
    ("MIT License", "MIT"),
    ("MIT/X11", "MIT"),
    
    ("Apache 2.0", "Apache"),
    ("Apache License 2.0", "Apache"),
    ("Apache License Version 2.0", "Apache"),
    
    ("BSD 3-Clause", "BSD"),
    ("BSD-3-Clause", "BSD"),
    ("3-Clause BSD", "BSD"),
    ("New BSD License", "BSD"),
    
    ("GPL v3", "GPL"),
    ("GPL-3.0", "GPL"),
    ("GPL 3", "GPL"),
    
    ("LGPL v2.1", "LGPL"),
    ("LGPL-2.1", "LGPL"),
    
    ("MPL 2.0", "MPL"),
    ("Mozilla Public License 2.0", "Mozilla"),  # Also accept "Mozilla" variant
    
    ("PSF", "PSF"),
    ("Python Software Foundation", "Python"),
    
    ("Proprietary", "Proprietary"),
    ("Commercial", "Commercial"),
    
    # Heuristic: BSD detection
    ("""
    Redistribution and use in source and binary forms, with or without
    modification are permitted
    """, "BSD"),
    
    # Real protobuf license text (truncated for space)
    ("""
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met
    """, "BSD"),
    
    # Heuristic: MIT detection
    ("""
    Permission is hereby granted, free of charge, to any person obtaining
    a copy of this software
    """, "MIT"),
    
    # Heuristic: Apache detection
    ("""
    Licensed under the Apache License, Version 2.0
    """, "Apache"),
    
    # Heuristic: GPL detection
    ("""
    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License
    """, "GPL"),
    
    # Invalid/Unknown
    ("", None),
    ("Some random text", None),
    ("My custom license", None),
]

def run_tests():
    """Run all test cases."""
    print("\n" + "=" * 80)
    print("LICENSE EXTRACTION TEST SUITE")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, (license_text, expected_keyword) in enumerate(TEST_CASES, 1):
        extracted = LicenseValidator.extract_license(license_text)
        
        if expected_keyword is None:
            # Expect None
            if extracted is None:
                print(f"✅ Test {i:2d}: PASS (correctly rejected: '{license_text[:50]}...')")
                passed += 1
            else:
                print(f"❌ Test {i:2d}: FAIL (expected None, got: {extracted})")
                print(f"           Input: '{license_text}'")
                failed += 1
        else:
            # Expect to extract something containing the keyword
            if extracted and expected_keyword.lower() in extracted.lower():
                print(f"✅ Test {i:2d}: PASS (extracted: {extracted})")
                passed += 1
            else:
                print(f"❌ Test {i:2d}: FAIL (expected '{expected_keyword}', got: {extracted})")
                print(f"           Input: '{license_text[:60]}...'")
                failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - License extraction working correctly!")
    else:
        print(f"❌ {failed} test(s) failed")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
