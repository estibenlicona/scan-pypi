import json
from typing import List, Dict, Any, Optional, Set, TypedDict
from datetime import datetime, timedelta
from models import PackageInfo


class TreeReportDict(TypedDict, total=False):
    """Tipo para el diccionario de reporte de árbol."""
    name: str
    version: str
    upload_time: Optional[str]
    download_url: Optional[str]
    count_vulnerabilities: int
    status: str
    licenses: List[str]
    license_rejected: bool
    maintainability: str
    rejected_by_dependency: bool
    dependencies: List['TreeReportDict']


class FinalReportDict(TypedDict):
    """Tipo para el reporte consolidado final."""
    vulnerabilities: List[Dict[str, Any]]
    packages: List[TreeReportDict]


def flatten_vulnerabilities(vuln_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convierte vulnerabilidades a formato plano."""
    flat: List[Dict[str, Any]] = []
    for v in vuln_list:
        flat.append({
            "id": v.get("id") or v.get("id", "N/A"),
            "title": v.get("title", "N/A"),
            "severity": v.get("severity", "N/A"),
            "package": v.get("moduleName") or v.get("package"),
            "version": v.get("version", "N/A"),
            "cvss": v.get("cvss", v.get("CVSSv3", "N/A")),
            "fixed_in": v.get("fixed_in", v.get("fixedIn", "N/A"))
        })
    return flat


def get_license_info(pkg_name: str, pkg_version: str, all_packages: List[PackageInfo]) -> Dict[str, List[str]]:
    """Obtiene información de licencias para un paquete específico."""
    licenses: List[str] = []
    for pkg in all_packages:
        if pkg.package == pkg_name and pkg.version == pkg_version:
            pypi_license = pkg.license
            if pypi_license:
                licenses.append(pypi_license)
    return {"licenses": licenses}


def build_tree(
    key: str, 
    vuln_count: Dict[str, int], 
    maintained_set: Set[str], 
    pkg_index: Dict[str, PackageInfo], 
    all_packages: List[PackageInfo]
) -> Optional[TreeReportDict]:
    """Construye árbol jerárquico de dependencias con información de vulnerabilidades."""
    pkg = pkg_index.get(key)
    if not pkg:
        return None
        
    count_vulns = vuln_count.get(key, 0)
    is_maintained = key in maintained_set
    deps = pkg.dependencies
    dep_objs = [
        dep_tree for dep_key in deps 
        if (dep_tree := build_tree(dep_key, vuln_count, maintained_set, pkg_index, all_packages)) is not None
    ]
    
    has_rejected_dep = any(d.get("status") == "rejected" for d in dep_objs)
    rejected_by_dependency = has_rejected_dep
    status = "approved" if (count_vulns == 0 and is_maintained and not has_rejected_dep) else "rejected"
    total_vulns = count_vulns + sum(d.get("count_vulnerabilities", 0) for d in dep_objs)
    
    lic_info = get_license_info(pkg.package, pkg.version, all_packages)
    snyk_license = pkg.snyk_license
    licenses = [snyk_license] if snyk_license else lic_info["licenses"]
    upload_time = pkg.upload_time
    maintainability = "active"
    
    try:
        if upload_time:
            upload_dt = datetime.fromisoformat(upload_time.replace("Z", ""))
            if (datetime.now() - upload_dt) > timedelta(days=365*2):
                maintainability = "inactive"
    except Exception:
        pass
        
    report: TreeReportDict = {
        "name": pkg.package,
        "version": pkg.version,
        "upload_time": upload_time,
        "download_url": pkg.home_page,  # Usar home_page como download_url
        "count_vulnerabilities": total_vulns,
        "status": status,
        "licenses": licenses,
        "license_rejected": True if snyk_license else False,
        "maintainability": maintainability,
        "rejected_by_dependency": rejected_by_dependency,
        "dependencies": dep_objs
    }
    return report


def generate_consolidated_report(
    vulnerabilities: List[Dict[str, Any]], 
    all_packages: List[PackageInfo], 
    maintained_packages: List[PackageInfo], 
    output_file: str = "consolidated_report.json"
) -> None:
    """
    Genera y guarda el reporte consolidado en un archivo JSON con propiedad 'packages'.
    
    Args:
        vulnerabilities: Lista de vulnerabilidades.
        all_packages: Todos los paquetes con info PyPI.
        maintained_packages: Paquetes que cumplen la regla de negocio.
        output_file: Nombre del archivo de salida.
    """
    # Map package@version to vulnerability count (using moduleName for Snyk output)
    vuln_count: Dict[str, int] = {}
    for v in vulnerabilities:
        pkg = v.get('moduleName') or v.get('package')
        ver = v.get('version')
        key = f"{pkg}@{ver}"
        vuln_count[key] = vuln_count.get(key, 0) + 1

    maintained_set = set(f"{p.package}@{p.version}" for p in maintained_packages)
    pkg_index = {f"{pkg.package}@{pkg.version}": pkg for pkg in all_packages}
    all_keys = set(pkg_index.keys())
    dep_keys = set(dep for pkg in all_packages for dep in pkg.dependencies)
    root_keys = list(all_keys - dep_keys)
    
    packages_tree = [
        tree for key in root_keys 
        if (tree := build_tree(key, vuln_count, maintained_set, pkg_index, all_packages)) is not None
    ]
    
    final_report: FinalReportDict = {
        "vulnerabilities": flatten_vulnerabilities(vulnerabilities),
        "packages": packages_tree
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"Reporte consolidado generado: {output_file}")
