"""Merge logic for the master ``consolidated_report.json``.

The consolidated report is the single source of truth shared with other teams.
Each analysis run upserts its packages into the master file by
``(name, version)`` instead of overwriting it, so the file accumulates every
package ever analysed.

Manual approvals (set via ``pyscan approve``) are sticky: once a package is
manually approved, re-running an analysis keeps it approved even if the new
automated verdict would reject it. The latest automated verdict is preserved
separately in ``aprobada_automatica`` / ``motivo_automatico`` so reviewers can
still see the discrepancy.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

# Per-package fields that record a human (manual) approval. These must never be
# clobbered by an automated run.
MANUAL_FIELDS = (
    "aprobacion_manual",
    "aprobada_manual_motivo",
    "aprobada_manual_por",
    "aprobada_manual_fecha",
)


def _pkg_key(pkg: Dict[str, Any]) -> Tuple[str, str]:
    """Unique key for a package row: ``(name_lowercased, version)``."""
    name = str(pkg.get("package", "")).strip().lower()
    version = str(pkg.get("version", "")).strip()
    return name, version


def _index_packages(packages: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """Index a package list by ``(name, version)`` keeping the last occurrence."""
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        index[_pkg_key(pkg)] = pkg
    return index


def _merge_one(existing: Dict[str, Any] | None, incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Merge a single incoming (automated) package against the existing master row."""
    merged = dict(incoming)

    # The automated verdict for this run is always recorded.
    merged["aprobada_automatica"] = incoming.get("aprobada")
    merged["motivo_automatico"] = incoming.get("motivo_rechazo")

    if existing and existing.get("aprobacion_manual"):
        # Manual approval is sticky: it wins over the automated verdict and its
        # metadata is carried over untouched, while the rest of the package data
        # is refreshed from the new analysis.
        for field in MANUAL_FIELDS:
            merged[field] = existing.get(field)
        merged["aprobacion_manual"] = True
        merged["aprobada"] = "Sí"
        merged["motivo_rechazo"] = (
            existing.get("aprobada_manual_motivo")
            or "Aprobado manualmente"
        )
    else:
        merged.setdefault("aprobacion_manual", False)

    return merged


def _merge_vulnerabilities(
    existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Union vulnerabilities by ``(id, packageName, version)``."""
    def vkey(v: Dict[str, Any]) -> Tuple[str, str, str]:
        return (
            str(v.get("id", "")),
            str(v.get("packageName", "")),
            str(v.get("version", "")),
        )

    index: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for v in existing + incoming:
        if isinstance(v, dict):
            index[vkey(v)] = v
    return list(index.values())


def merge_report(
    existing: Dict[str, Any] | None, incoming: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge an incoming analysis report into the existing master report.

    Args:
        existing: Previously saved master report (or ``None`` / empty on first run).
        incoming: Freshly produced analysis report.

    Returns:
        The merged master report, accumulating packages across runs and keeping
        manual approvals sticky.
    """
    existing = existing or {}

    existing_pkgs = _index_packages(existing.get("packages", []) or [])
    for pkg in incoming.get("packages", []) or []:
        if not isinstance(pkg, dict):
            continue
        key = _pkg_key(pkg)
        existing_pkgs[key] = _merge_one(existing_pkgs.get(key), pkg)
    merged_packages = list(existing_pkgs.values())

    # filtered_packages share the same row shape; upsert without manual logic.
    existing_filtered = _index_packages(existing.get("filtered_packages", []) or [])
    for pkg in incoming.get("filtered_packages", []) or []:
        if isinstance(pkg, dict):
            existing_filtered[_pkg_key(pkg)] = pkg
    merged_filtered = list(existing_filtered.values())

    merged_vulns = _merge_vulnerabilities(
        existing.get("vulnerabilities", []) or [],
        incoming.get("vulnerabilities", []) or [],
    )

    manual_count = sum(1 for p in merged_packages if p.get("aprobacion_manual"))

    return {
        # Latest run timestamp wins.
        "timestamp": incoming.get("timestamp") or existing.get("timestamp"),
        "vulnerabilities": merged_vulns,
        "packages": merged_packages,
        "filtered_packages": merged_filtered,
        "summary": {
            "total_packages": len(merged_packages),
            "total_vulnerabilities": len(merged_vulns),
            "maintained_packages": len(merged_filtered),
            "manual_approvals": manual_count,
            "policy_applied": (
                (incoming.get("summary") or {}).get("policy_applied")
                or (existing.get("summary") or {}).get("policy_applied")
            ),
        },
    }
