def flatten_vulnerabilities(vuln_list):
    flat = []
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

def get_license_info(pkg_name, pkg_version, all_packages):
    licenses = []
    for pkg in all_packages:
        if pkg.get("package") == pkg_name and pkg.get("version") == pkg_version:
            pypi_license = pkg.get("license")
            if pypi_license:
                licenses.append(pypi_license)
    return {"licenses": licenses}

def build_tree(key, vuln_count, maintained_set, pkg_index, all_packages):
    pkg = pkg_index.get(key)
    if not pkg:
        return None
    count_vulns = vuln_count.get(key, 0)
    is_maintained = key in maintained_set
    deps = pkg.get("dependencies", [])
    dep_objs = [build_tree(dep_key, vuln_count, maintained_set, pkg_index, all_packages) for dep_key in deps if build_tree(dep_key, vuln_count, maintained_set, pkg_index, all_packages)]
    has_rejected_dep = any(d.get("status") == "rejected" for d in dep_objs)
    rejected_by_dependency = has_rejected_dep
    status = "approved" if (count_vulns == 0 and is_maintained and not has_rejected_dep) else "rejected"
    total_vulns = count_vulns + sum(d.get("count_vulnerabilities", 0) for d in dep_objs)
    lic_info = get_license_info(pkg.get("package"), pkg.get("version"), all_packages)
    snyk_license = pkg.get("snyk_license")
    licenses = [snyk_license] if snyk_license else lic_info["licenses"]
    upload_time = pkg.get("upload_time")
    maintainability = "active"
    from datetime import datetime, timedelta
    try:
        if upload_time:
            upload_dt = datetime.fromisoformat(upload_time.replace("Z", ""))
            if (datetime.now() - upload_dt) > timedelta(days=365*2):
                maintainability = "inactive"
    except Exception:
        pass
    report = {
        "name": pkg.get("package"),
        "version": pkg.get("version"),
        "upload_time": upload_time,
        "download_url": pkg.get("download_url"),
        "count_vulnerabilities": total_vulns,
        "status": status,
        "licenses": licenses,
        "license_rejected": True if snyk_license else False,
        "maintainability": maintainability,
        "rejected_by_dependency": rejected_by_dependency,
        "dependencies": dep_objs
    }
    return report
import json


def generate_consolidated_report(vulnerabilities, all_packages, maintained_packages, output_file="consolidated_report.json"):
    """
    Genera y guarda el reporte consolidado en un archivo JSON con propiedad 'packages'.
    Args:
        vulnerabilities (list): Lista de vulnerabilidades.
        all_packages (list): Todos los paquetes con info PyPI.
        maintained_packages (list): Paquetes que cumplen la regla de negocio.
        output_file (str): Nombre del archivo de salida.
    """
    # Map package@version to vulnerability count (using moduleName for Snyk output)
    vuln_count = {}
    for v in vulnerabilities:
        pkg = v.get('moduleName') or v.get('package')
        ver = v.get('version')
        key = f"{pkg}@{ver}"
        vuln_count[key] = vuln_count.get(key, 0) + 1

    maintained_set = set(f"{p.get('package')}@{p.get('version')}" for p in maintained_packages)
    pkg_index = {f"{pkg.get('package')}@{pkg.get('version')}": pkg for pkg in all_packages}
    all_keys = set(pkg_index.keys())
    dep_keys = set(dep for pkg in all_packages for dep in pkg.get("dependencies", []))
    root_keys = list(all_keys - dep_keys)
    packages_tree = [build_tree(key, vuln_count, maintained_set, pkg_index, all_packages) for key in root_keys if build_tree(key, vuln_count, maintained_set, pkg_index, all_packages)]
    final_report = {
        "vulnerabilities": flatten_vulnerabilities(vulnerabilities),
        "packages": packages_tree
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"Reporte consolidado generado: {output_file}")
