"""
XLSX Report Adapter - Generates an Excel .xlsx table with package metadata for business review.

RESPONSIBILITY: Write consolidated JSON report data to XLSX file.
NO DATA TRANSFORMATION - all data comes pre-processed from consolidated_report.json
"""

import json
from pathlib import Path
from typing import Any, List
from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.utils import get_column_letter
from typing import cast
from src.domain.ports import LoggerPort

class XLSXReportAdapter:
    """Generates an Excel .xlsx file with package metadata for business review."""

    def __init__(self, logger: LoggerPort) -> None:
        self.logger = logger

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
                "Dependencias Directas", "Dependencias Transitivas",
                "Fecha de Publicación", "URL", "Descripción"
            ]
            ws.append(header)

            for pkg in packages:
                nombre = (pkg.get("package") or "").strip()
                version = (pkg.get("version") or "—").strip()
                licencia = pkg.get("license") or "—"
                aprobada = pkg.get("aprobada", "En verificación")
                estado_comentario = pkg.get("motivo_rechazo", "")
                
                # Dependencies from approval engine
                dependencias_directas_list = pkg.get("dependencias_directas", [])
                dependencias_transitivas_list = pkg.get("dependencias_transitivas", [])
                
                # Handle both old format (List[str]) and new format (List[DependencyInfo dict])
                def format_deps(deps_list: List[Any]) -> str:
                    if not deps_list:
                        return "—"
                    dep_names = []
                    for dep in deps_list:
                        if isinstance(dep, dict):
                            dep_names.append(dep.get("name", "?"))
                        elif isinstance(dep, str):
                            dep_names.append(dep)
                    return ", ".join(dep_names) if dep_names else "—"
                
                dep_directas_str = format_deps(dependencias_directas_list)
                dep_transitivas_str = format_deps(dependencias_transitivas_list)
                
                # Other fields
                fecha_pub = pkg.get("upload_time") or pkg.get("upload_time_iso_8601") or "—"
                if isinstance(fecha_pub, str) and "T" in fecha_pub:
                    fecha_pub = fecha_pub.split("T")[0]
                url = pkg.get("project_url") or pkg.get("home_page") or (f"https://pypi.org/project/{nombre}" if nombre else "—")
                descripcion = pkg.get("summary") or pkg.get("description") or "—"
                if isinstance(descripcion, str):
                    descripcion = " ".join(descripcion.split())
                    if len(descripcion) > 200:
                        descripcion = descripcion[:197] + "..."
                
                row: List[str] = [
                    str(nombre), str(version), str(licencia), str(aprobada), str(estado_comentario),
                    str(dep_directas_str), str(dep_transitivas_str),
                    str(fecha_pub), str(url), str(descripcion)
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
