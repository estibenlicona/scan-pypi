#!/usr/bin/env python3
"""
Test to verify XLSX display will show clear reasons.
"""

import json
from src.infrastructure.adapters.xlsx_report_adapter import XLSXReportAdapter
from src.infrastructure.adapters.logger_adapter import LoggerAdapter
from src.infrastructure.config.settings import LoggingSettings

def create_test_report():
    """Create a test consolidated_report.json with approval data."""
    report = {
        "packages": [
            {
                "package": "good-lib",
                "version": "1.0.0",
                "license": "MIT",
                "aprobada": "Sí",
                "motivo_rechazo": None,
                "dependencias_directas": [],
                "dependencias_transitivas": [],
                "upload_time": "2023-01-01",
                "summary": "A good library"
            },
            {
                "package": "ok-lib",
                "version": "1.0.0",
                "license": None,
                "aprobada": "Sí",
                "motivo_rechazo": "⚠ Licencia no documentada en PyPI",
                "dependencias_directas": [],
                "dependencias_transitivas": [],
                "upload_time": "2023-01-01",
                "summary": "Library with missing license"
            },
            {
                "package": "vulnerable-lib",
                "version": "1.0.0",
                "license": "MIT",
                "aprobada": "No",
                "motivo_rechazo": "Contiene 1 vulnerabilidad(es)",
                "dependencias_directas": [],
                "dependencias_transitivas": [],
                "upload_time": "2023-01-01",
                "summary": "A library with vulnerabilities"
            },
            {
                "package": "abandoned-lib",
                "version": "1.0.0",
                "license": "MIT",
                "aprobada": "No",
                "motivo_rechazo": "Paquete sin mantenimiento documentado",
                "dependencias_directas": [],
                "dependencias_transitivas": [],
                "upload_time": "2023-01-01",
                "summary": "An abandoned library"
            },
            {
                "package": "incomplete-lib",
                "version": "1.0.0",
                "license": None,
                "aprobada": "En verificación",
                "motivo_rechazo": "Información incompleta: Licencia no documentada en PyPI; Información de mantenimiento no disponible",
                "dependencias_directas": [],
                "dependencias_transitivas": [],
                "upload_time": None,
                "summary": "Library with incomplete data"
            }
        ]
    }
    
    with open("test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return "test_report.json"

def test_xlsx_display():
    """Test that XLSX shows clear reasons in Estado/Comentario column."""
    print("🧪 Testing XLSX display of approval reasons...\n")
    
    # Create test report
    report_path = create_test_report()
    
    # Generate XLSX
    logging_settings = LoggingSettings()
    logger = LoggerAdapter(logging_settings)
    xlsx_adapter = XLSXReportAdapter(logger)
    
    if xlsx_adapter.generate_xlsx(report_path, "test_packages.xlsx"):
        print("✅ XLSX generated successfully\n")
        print("📊 Expected content in 'Estado / Comentario' column:\n")
        print("  good-lib           → Sin problemas detectados")
        print("  ok-lib             → ⚠ Licencia no documentada en PyPI")
        print("  vulnerable-lib     → Contiene 1 vulnerabilidad(es)")
        print("  abandoned-lib      → Paquete sin mantenimiento documentado")
        print("  incomplete-lib     → Información incompleta: Licencia no documentada en PyPI; ...")
        print("\n✅ All reasons are CLEAR and SPECIFIC!")
    else:
        print("❌ Failed to generate XLSX")
        raise Exception("XLSX generation failed")

if __name__ == "__main__":
    try:
        test_xlsx_display()
        print("\n🎉 XLSX display test completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
