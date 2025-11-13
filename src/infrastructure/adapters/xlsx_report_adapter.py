"""
XLSX Report Adapter - Generates an Excel .xlsx table with package metadata for business review.

RESPONSIBILITY: Write consolidated JSON report data to XLSX file.
NO DATA TRANSFORMATION - all data comes pre-processed from consolidated_report.json
"""

import json
from pathlib import Path
from typing import Any, List, Optional
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter
from typing import cast
from src.domain.ports import LoggerPort

class XLSXReportAdapter:
    """Generates an Excel .xlsx file with package metadata for business review."""

    def __init__(self, logger: LoggerPort) -> None:
        self.logger = logger
    
    def _safe_cell_value(self, value: Any) -> str:
        """Convert value to safe string for Excel cell (prevents formula injection)."""
        if value is None or value == "":
            return "N/A"
        
        value_str = str(value).strip()
        
        # Prevent formula injection by prefixing dangerous characters
        if value_str.startswith(("=", "+", "-", "@")):
            value_str = "'" + value_str
        
        # Replace problematic characters
        value_str = value_str.replace("—", "-").replace("–", "-")
        
        return value_str if value_str else "N/A"
    
    def _format_dependencies(self, deps_list: List[Any]) -> str:
        """Format dependency list (handles both dict and string formats)."""
        if not deps_list:
            return "N/A"
        dep_names = []
        for dep in deps_list:
            if isinstance(dep, dict):
                dep_names.append(dep.get("name", "?"))
            elif isinstance(dep, str):
                dep_names.append(dep)
        return ", ".join(dep_names) if dep_names else "N/A"

    def generate_xlsx(self, report_path: str, output_path: str = "packages.xlsx") -> bool:
        """
        Generate XLSX report from consolidated JSON report.
        Columns: Nombre, Aprobada, Versión, Fecha de Publicación, Licencia, URL, Dependencias, Descripción
        """
        try:
            if not Path(report_path).exists():
                self.logger.error(f"Report file not found: {report_path}")
                return False

            with open(report_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            packages = data.get("packages", [])
            if not packages:
                self.logger.warning("No packages found in report")
                return False

            wb = Workbook()
            ws_or_none = wb.active
            if ws_or_none is None:
                ws_or_none = wb.create_sheet()
            ws: Worksheet = cast(Worksheet, ws_or_none)
            ws.title = "Packages"
            header = [
                "Nombre", "Versión", "Licencia", "Aprobada", "Estado / Comentario", 
                "Dependencias Directas", "Dependencias Transitivas", "Dependencias Rechazadas",
                "Fecha de Publicación", "URL", "Descripción"
            ]
            ws.append(header)

            for pkg in packages:
                nombre = self._safe_cell_value(pkg.get("package") or "")
                version = self._safe_cell_value(pkg.get("version") or "")
                licencia = self._safe_cell_value(pkg.get("license") or "")
                aprobada = self._safe_cell_value(pkg.get("aprobada", ""))
                estado_comentario = self._safe_cell_value(pkg.get("motivo_rechazo") or "")
                
                # Dependencies from approval engine
                dependencias_directas_list = pkg.get("dependencias_directas", [])
                dependencias_transitivas_list = pkg.get("dependencias_transitivas", [])
                dependencias_rechazadas_list = pkg.get("dependencias_rechazadas", [])
                
                dep_directas_str = self._safe_cell_value(self._format_dependencies(dependencias_directas_list))
                dep_transitivas_str = self._safe_cell_value(self._format_dependencies(dependencias_transitivas_list))
                dep_rechazadas_str = self._safe_cell_value(self._format_dependencies(dependencias_rechazadas_list))
                
                # Other fields
                fecha_pub = pkg.get("upload_time") or pkg.get("upload_time_iso_8601") or ""
                if isinstance(fecha_pub, str) and "T" in fecha_pub:
                    fecha_pub = fecha_pub.split("T")[0]
                fecha_pub = self._safe_cell_value(fecha_pub)
                
                url = pkg.get("project_url") or pkg.get("home_page") or (f"https://pypi.org/project/{nombre}" if nombre and nombre != "N/A" else "")
                url = self._safe_cell_value(url)
                
                descripcion = pkg.get("summary") or pkg.get("description") or ""
                if isinstance(descripcion, str):
                    descripcion = " ".join(descripcion.split())
                    if len(descripcion) > 200:
                        descripcion = descripcion[:197] + "..."
                descripcion = self._safe_cell_value(descripcion)
                
                row: List[str] = [
                    nombre, version, licencia, aprobada, estado_comentario,
                    dep_directas_str, dep_transitivas_str, dep_rechazadas_str,
                    fecha_pub, url, descripcion
                ]
                ws.append(row)

            # Auto-size columns
            for idx, col in enumerate(ws.columns, 1):
                max_length = 0
                col_letter = get_column_letter(idx)
                for cell in col:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = min(max_length + 2, 60)

            wb.save(output_path)
            self.logger.info(f"✅ XLSX report generated: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate XLSX report: {e}")
            return False
