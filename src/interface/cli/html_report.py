"""CLI command — render the consolidated JSON report as a friendly HTML view.

Reads ``consolidated_report.json`` and injects it into the self-contained viewer
template (``viewer/report_template.html``), producing a single ``report.html``
that can be opened directly in a browser (no server required).
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

_PLACEHOLDER = "__REPORT_DATA__"
_TEMPLATE_REL = os.path.join("viewer", "report_template.html")


def _template_path() -> Path:
    """Locate the viewer template, both frozen (PyInstaller) and from source."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        candidate = Path(base) / _TEMPLATE_REL
        if candidate.exists():
            return candidate
    # Source layout: <repo>/viewer/report_template.html
    return Path(__file__).resolve().parents[3] / _TEMPLATE_REL


def generate_html(
    report_path: str = "consolidated_report.json",
    output_path: str = "report.html",
) -> bool:
    """Generate the HTML viewer with the report data embedded.

    Returns:
        True on success, False otherwise.
    """
    report = Path(report_path)
    if not report.exists():
        print(f"[ERROR] No existe el reporte: {report_path}", file=sys.stderr)
        return False

    template = _template_path()
    if not template.exists():
        print(f"[ERROR] No se encontró la plantilla del visor: {template}", file=sys.stderr)
        return False

    try:
        data = json.loads(report.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"[ERROR] No se pudo leer {report_path}: {e}", file=sys.stderr)
        return False

    html = template.read_text(encoding="utf-8")
    # Embed as JSON inside the placeholder script tag. Escape '</' so the JSON
    # cannot prematurely close the <script> element.
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = html.replace(_PLACEHOLDER, payload)

    Path(output_path).write_text(html, encoding="utf-8")
    return True


def main(
    report_path: str = "consolidated_report.json",
    output_path: str = "report.html",
) -> None:
    """Entry point for the ``report`` subcommand."""
    if generate_html(report_path, output_path):
        print(f"[OK] Visor HTML generado: {os.path.abspath(output_path)}")
    else:
        sys.exit(1)
