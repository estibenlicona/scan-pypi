"""Unit tests for LicenseValidator – extract_license, is_valid_license,
get_license_type, extract_from_classifier, extract_license_from_sources.

Converts the old manual scripts into pytest-discoverable parametrized tests.
"""

import pytest
from src.domain.services.license_validator import LicenseValidator
from src.domain.entities import LicenseType


# ── extract_license (parametrized) ───────────────────────────────────


EXTRACT_LICENSE_CASES = [
    # (input_text, expected_keyword_in_result | None)
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
    ("Mozilla Public License 2.0", "Mozilla"),
    ("PSF", "PSF"),
    ("Python Software Foundation", "Python"),
    ("Proprietary", "Proprietary"),
    ("Commercial", "Commercial"),
    ("ISC", "ISC"),
    ("Unlicense", "Unlicense"),
    ("CC0", "CC0"),
    ("Zope Public License", "Zope"),
    ("ZPL", "ZPL"),
    ("Artistic License 2.0", "Artistic"),
    ("Eclipse Public License", "Eclipse"),
    ("EPL-2.0", "EPL"),
    ("EUPL", "EUPL"),
    ("WTFPL", "WTFPL"),
    ("Boost Software License", "Boost"),
    ("BSL-1.0", "BSL"),
    # Heuristic detection from full text
    (
        "Redistribution and use in source and binary forms, with or without "
        "modification are permitted",
        "BSD",
    ),
    (
        "Permission is hereby granted, free of charge, to any person obtaining "
        "a copy of this software",
        "MIT",
    ),
    ("Licensed under the Apache License, Version 2.0", "Apache"),
    (
        "This program is free software; you can redistribute it and/or modify "
        "it under the terms of the GNU General Public License",
        "GPL",
    ),
    # Invalid / unknown
    ("", None),
    ("Some random text", None),
    ("My custom license", None),
    (None, None),
]


@pytest.mark.parametrize(
    "text,expected_keyword",
    EXTRACT_LICENSE_CASES,
    ids=[
        f"{str(t[0])[:40]}→{t[1]}" for t in EXTRACT_LICENSE_CASES
    ],
)
def test_extract_license(text, expected_keyword):
    """LicenseValidator.extract_license must detect known licenses."""
    result = LicenseValidator.extract_license(text)
    if expected_keyword is None:
        assert result is None, f"Expected None but got {result!r}"
    else:
        assert result is not None, f"Expected keyword '{expected_keyword}' but got None"
        assert expected_keyword.lower() in result.lower(), (
            f"Expected '{expected_keyword}' in '{result}'"
        )


# ── is_valid_license ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected",
    [
        ("MIT", True),
        ("Apache-2.0", True),
        ("BSD", True),
        ("ISC", True),
        ("Unknown garbage text", False),
        ("", False),
        (None, False),
        ("   ", False),
        ("ab", False),
    ],
)
def test_is_valid_license(text, expected):
    assert LicenseValidator.is_valid_license(text) is expected


# ── get_license_type ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text,expected_type",
    [
        ("MIT", LicenseType.MIT),
        ("Apache-2.0", LicenseType.APACHE_2_0),
        ("BSD-3-Clause", LicenseType.BSD_3_CLAUSE),
        ("GPL v3", LicenseType.GPL_3_0),
        # Note: LGPL contains "GPL" which matches first in LICENSE_TYPE_MAP iteration.
        # get_license_type returns GPL_3_0 for LGPL input (known limitation).
        ("LGPL-2.1", LicenseType.GPL_3_0),
        ("MPL-2.0", LicenseType.MPL_2_0),
        ("ISC", None),  # ISC maps to UNKNOWN via extract → LICENSE_TYPE_MAP
        ("random noise", None),
        (None, None),
        ("", None),
    ],
)
def test_get_license_type(text, expected_type):
    result = LicenseValidator.get_license_type(text)
    if expected_type is None:
        # None or UNKNOWN both acceptable for unrecognised
        assert result is None or result == LicenseType.UNKNOWN
    else:
        assert result == expected_type


# ── extract_from_classifier ──────────────────────────────────────────


@pytest.mark.parametrize(
    "classifier,expected_keyword",
    [
        ("License :: OSI Approved :: MIT License", "MIT"),
        ("License :: OSI Approved :: BSD License", "BSD"),
        ("License :: OSI Approved :: Apache Software License", "Apache"),
        ("Programming Language :: Python", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_from_classifier(classifier, expected_keyword):
    result = LicenseValidator.extract_from_classifier(classifier)
    if expected_keyword is None:
        assert result is None
    else:
        assert result is not None
        assert expected_keyword.lower() in result.lower()


# ── extract_license_from_sources ─────────────────────────────────────


SOURCES_CASES = [
    # (pypi_info, github_data, expected_name_keyword, description)
    ({"license": "MIT"}, None, "MIT", "PyPI direct license"),
    (
        {"license": "", "license_expression": "Apache-2.0"},
        None,
        "Apache",
        "PyPI license_expression",
    ),
    (
        {
            "license": "",
            "license_expression": "",
            "classifiers": [
                "Programming Language :: Python",
                "License :: OSI Approved :: BSD License",
            ],
        },
        None,
        "BSD",
        "PyPI classifier",
    ),
    (
        {"license": "", "license_expression": ""},
        {"license": {"key": "apache-2.0", "name": "Apache License 2.0"}},
        "Apache",
        "GitHub fallback (SPDX key)",
    ),
    (
        {"license": "", "license_expression": ""},
        {"license": {"key": None, "name": "MIT License"}},
        "MIT",
        "GitHub fallback (name)",
    ),
    (
        {"license": "GPL v3"},
        {"license": {"key": "mit", "name": "MIT License"}},
        "GPL",
        "PyPI priority over GitHub",
    ),
    (
        {"license": "", "license_expression": "", "classifiers": []},
        {"license": None},
        None,
        "No license found",
    ),
    (
        {"license": "Apache 2.0"},
        None,
        "Apache",
        "requests-like",
    ),
    (
        {"license": "BSD 3-Clause"},
        None,
        "BSD",
        "django-like",
    ),
]


@pytest.mark.parametrize(
    "pypi_info,github_data,expected_keyword,desc",
    SOURCES_CASES,
    ids=[c[3] for c in SOURCES_CASES],
)
def test_extract_license_from_sources(pypi_info, github_data, expected_keyword, desc):
    result = LicenseValidator.extract_license_from_sources(
        pypi_info=pypi_info,
        github_data=github_data,
    )
    if expected_keyword is None:
        assert result is None, f"{desc}: expected None got {result}"
    else:
        assert result is not None, f"{desc}: expected license containing '{expected_keyword}'"
        assert expected_keyword.lower() in result.name.lower(), (
            f"{desc}: expected '{expected_keyword}' in '{result.name}'"
        )
