#!/usr/bin/env python3
"""Test script to verify styling works correctly."""

import json
from datetime import datetime

# Create test report
test_report = {
    "timestamp": datetime.now().isoformat(),
    "vulnerabilities": [],
    "packages": [
        # Root libraries
        {"package": "numpy", "version": "1.24.0", "license": "BSD", "aprobada": "Sí", "motivo_rechazo": ""},
        {"package": "pandas", "version": "2.0.0", "license": "BSD", "aprobada": "Sí", "motivo_rechazo": ""},
        # Rejected package
        {"package": "requests", "version": "2.32.1", "license": "Apache-2.0", "aprobada": "No", "motivo_rechazo": "Vulnerabilidad detectada"},
        # Regular dependency
        {"package": "urllib3", "version": "1.26.16", "license": "MIT", "aprobada": "Sí", "motivo_rechazo": ""},
        # Another rejected
        {"package": "scipy", "version": "1.10.0", "license": None, "aprobada": "No", "motivo_rechazo": "Sin licencia válida"},
        {"package": "matplotlib", "version": "3.7.0", "license": "PSF", "aprobada": "Sí", "motivo_rechazo": ""},
    ],
    "filtered_packages": []
}

with open("test_styling_report.json", "w") as f:
    json.dump(test_report, f, indent=2)

print("✅ Test report created")
print("\n📋 Test data:")
print("   - 2 Root libraries (numpy, pandas) - should be BLUE")
print("   - 2 Rejected packages (requests, scipy) - should be RED")
print("   - 2 Regular dependencies (urllib3, matplotlib) - should be NO COLOR")

root_libraries = ["numpy", "pandas", "requests", "matplotlib"]

from src.infrastructure.adapters.xlsx_report_adapter import XLSXReportAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.config.settings import LoggingSettings

logger = LoggerAdapter(LoggingSettings())
xlsx_adapter = XLSXReportAdapter(logger)

if xlsx_adapter.generate_xlsx("test_styling_report.json", "test_styling_packages.xlsx", root_libraries=root_libraries):
    print("\n✅ XLSX generated with styling!")
    print("\n   📊 Colors in Excel:")
    print("      🔵 Blue pastel (CCE8FF): numpy, pandas, matplotlib (roots)")
    print("      🔴 Red pastel (FFCCCC): requests, scipy (rejected)")
    print("      ⚪ No color: urllib3 (dependency)")
    print("\n✅ Test completed!")
else:
    print("❌ Failed")
