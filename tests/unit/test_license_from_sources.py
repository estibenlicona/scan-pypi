#!/usr/bin/env python3
"""
Test the new extract_license_from_sources() method with realistic PyPI and GitHub data.
"""

from src.domain.services.license_validator import LicenseValidator
from src.domain.entities import LicenseType

# Test cases: (pypi_info, github_data, expected_license_name, description)
TEST_CASES = [
    # Case 1: PyPI has license directly
    (
        {"license": "MIT"},
        None,
        "MIT",
        "PyPI direct license"
    ),
    
    # Case 2: PyPI has license_expression
    (
        {"license": "", "license_expression": "Apache-2.0"},
        None,
        "Apache",
        "PyPI license_expression (SPDX format)"
    ),
    
    # Case 3: PyPI has classifier
    (
        {
            "license": "",
            "license_expression": "",
            "classifiers": [
                "Programming Language :: Python",
                "License :: OSI Approved :: BSD License",
            ]
        },
        None,
        "BSD License",
        "PyPI classifier extraction"
    ),
    
    # Case 4: GitHub fallback when PyPI empty
    (
        {"license": "", "license_expression": ""},
        {"license": {"key": "apache-2.0", "name": "Apache License 2.0"}},
        "Apache",
        "GitHub fallback (SPDX key)"
    ),
    
    # Case 5: GitHub fallback uses name when key is None
    (
        {"license": "", "license_expression": ""},
        {"license": {"key": None, "name": "MIT License"}},
        "MIT",
        "GitHub fallback (name)"
    ),
    
    # Case 6: PyPI license takes priority over GitHub
    (
        {"license": "GPL v3"},
        {"license": {"key": "mit", "name": "MIT License"}},
        "GPL v3",
        "PyPI priority over GitHub"
    ),
    
    # Case 7: Heuristic detection from classifier text
    (
        {
            "license": "",
            "classifiers": [
                "License :: OSI Approved :: BSD License",
            ]
        },
        None,
        "BSD License",
        "Heuristic from classifier"
    ),
    
    # Case 8: No license found anywhere
    (
        {"license": "", "license_expression": "", "classifiers": []},
        {"license": None},
        None,
        "No license found"
    ),
    
    # Case 9: Real-world example - requests
    (
        {
            "license": "Apache 2.0",
            "classifiers": [
                "License :: OSI Approved :: Apache Software License",
            ]
        },
        None,
        "Apache 2.0",
        "Real package: requests"
    ),
    
    # Case 10: Real-world example - django
    (
        {
            "license": "BSD 3-Clause",
            "classifiers": [
                "License :: OSI Approved :: BSD License",
            ]
        },
        None,
        "BSD 3-Clause",
        "Real package: django"
    ),
]

def run_tests():
    """Run all test cases."""
    print("\n" + "=" * 100)
    print("LICENSE EXTRACTION - extract_license_from_sources() TEST SUITE")
    print("=" * 100)
    
    passed = 0
    failed = 0
    
    for i, (pypi_info, github_data, expected_name, description) in enumerate(TEST_CASES, 1):
        # Call the method
        result = LicenseValidator.extract_license_from_sources(
            pypi_info=pypi_info,
            github_data=github_data
        )
        
        # Check result
        if expected_name is None:
            # Expect None
            if result is None:
                print(f"✅ Test {i:2d}: PASS - {description}")
                passed += 1
            else:
                print(f"❌ Test {i:2d}: FAIL - {description}")
                print(f"           Expected: None, Got: {result.name if result else None}")
                failed += 1
        else:
            # Expect License object with specific name
            if result and expected_name.lower() in result.name.lower():
                print(f"✅ Test {i:2d}: PASS - {description}")
                print(f"           → {result.name} (type: {result.license_type})")
                passed += 1
            else:
                got_name = result.name if result else None
                print(f"❌ Test {i:2d}: FAIL - {description}")
                print(f"           Expected: {expected_name}, Got: {got_name}")
                failed += 1
    
    print("\n" + "=" * 100)
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    
    if failed == 0:
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("\nCascade strategy working correctly:")
        print("  1. PyPI direct license ✅")
        print("  2. PyPI license_expression ✅")
        print("  3. PyPI classifiers ✅")
        print("  4. GitHub license (fallback) ✅")
    else:
        print(f"❌ {failed} test(s) failed")
    
    print("=" * 100 + "\n")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
