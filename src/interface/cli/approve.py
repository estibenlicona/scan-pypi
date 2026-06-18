"""CLI command — grant manual approval to packages in the master report.

A manual approval is sticky: once set, subsequent analysis runs keep the package
approved even if the automated verdict would reject it (see
``infrastructure.adapters.report_merge``).

Usage::

    pyscan approve requests==2.28.0
    pyscan approve flask==2.0.0 django==4.2 --motivo "Revisado por seguridad" --por "ana"
"""
from __future__ import annotations
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ApprovalError(Exception):
    """Raised when a manual approval cannot be applied."""


def _parse_spec(spec: str) -> Tuple[str, str | None]:
    """Parse ``name==version`` (version optional) into ``(name, version)``."""
    spec = spec.strip()
    if "==" in spec:
        name, version = spec.split("==", 1)
        return name.strip().lower(), version.strip()
    return spec.lower(), None


def _matches(pkg: Dict[str, Any], name: str, version: str | None) -> bool:
    """Whether a package row matches the requested name/version."""
    if str(pkg.get("package", "")).strip().lower() != name:
        return False
    if version is None:
        return True
    return str(pkg.get("version", "")).strip() == version


def apply_manual_approvals(
    specs: List[str],
    report_path: str = "consolidated_report.json",
    motivo: str | None = None,
    por: str | None = None,
) -> int:
    """Mark the given package specs as manually approved in the master report.

    Returns:
        Number of package rows updated.

    Raises:
        ApprovalError: If the report is missing or a spec matches no package.
    """
    path = Path(report_path)
    if not path.exists():
        raise ApprovalError(
            f"No existe el reporte maestro: {report_path}. "
            "Ejecuta un análisis primero (pyscan run ...)."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ApprovalError(f"No se pudo leer {report_path}: {e}")

    packages = data.get("packages", [])
    if not isinstance(packages, list):
        raise ApprovalError("El reporte no contiene una lista de paquetes válida.")

    today = date.today().isoformat()
    updated = 0

    for spec in specs:
        name, version = _parse_spec(spec)
        matches = [p for p in packages if isinstance(p, dict) and _matches(p, name, version)]
        if not matches:
            raise ApprovalError(
                f"No se encontró el paquete '{spec}' en {report_path}."
            )
        for pkg in matches:
            # Snapshot the current automated verdict before overriding it.
            pkg.setdefault("aprobada_automatica", pkg.get("aprobada"))
            pkg.setdefault("motivo_automatico", pkg.get("motivo_rechazo"))
            pkg["aprobacion_manual"] = True
            pkg["aprobada"] = "Sí"
            pkg["aprobada_manual_motivo"] = motivo
            pkg["aprobada_manual_por"] = por
            pkg["aprobada_manual_fecha"] = today
            pkg["motivo_rechazo"] = motivo or "Aprobado manualmente"
            updated += 1

    # Keep the summary's manual_approvals counter consistent.
    summary = data.get("summary")
    if isinstance(summary, dict):
        summary["manual_approvals"] = sum(
            1 for p in packages if isinstance(p, dict) and p.get("aprobacion_manual")
        )

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return updated


def main(
    specs: List[str],
    report_path: str = "consolidated_report.json",
    motivo: str | None = None,
    por: str | None = None,
) -> None:
    """Entry point for the ``approve`` subcommand."""
    if not specs:
        print(
            "[ERROR] Indica al menos un paquete: pyscan approve <pkg==version>",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        count = apply_manual_approvals(specs, report_path, motivo, por)
        print(f"[OK] Aprobación manual aplicada a {count} registro(s) en {report_path}")
    except ApprovalError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
