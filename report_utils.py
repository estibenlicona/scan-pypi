import json


def generate_consolidated_report(vulnerabilities, all_packages, maintained_packages, output_file="consolidated_report.json"):
    # Helper: get license info for a package
    def get_license_info(pkg_name, pkg_version):
        licenses = []
        # Only get license from PyPI info
        for pkg in all_packages:
            if pkg.get("package") == pkg_name and pkg.get("version") == pkg_version:
                pypi_license = pkg.get("license")
                if pypi_license:
                    licenses.append(pypi_license)
        return {"licenses": licenses}
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
        # Snyk uses moduleName for package name, and version
        pkg = v.get('moduleName') or v.get('package')
        ver = v.get('version')
        key = f"{pkg}@{ver}"
        vuln_count[key] = vuln_count.get(key, 0) + 1

    # Map maintained status
    maintained_set = set(f"{p.get('package')}@{p.get('version')}" for p in maintained_packages)

    # Index all packages by key for fast lookup
    pkg_index = {f"{pkg.get('package')}@{pkg.get('version')}": pkg for pkg in all_packages}

    def build_tree(key):
        pkg = pkg_index.get(key)
        if not pkg:
            return None
        count_vulns = vuln_count.get(key, 0)
        is_maintained = key in maintained_set
        status = "approved" if (count_vulns == 0 and is_maintained) else "rejected"
        deps = pkg.get("dependencies", [])
        dep_objs = [build_tree(dep_key) for dep_key in deps if build_tree(dep_key)]
        # Propagate vulnerability counts from children
        total_vulns = count_vulns + sum(d.get("count_vulnerabilities", 0) for d in dep_objs)
        lic_info = get_license_info(pkg.get("package"), pkg.get("version"))
        snyk_license = pkg.get("snyk_license")
        # Si hay vulnerabilidad de licencia en Snyk, prioriza esa licencia
        licenses = [snyk_license] if snyk_license else lic_info["licenses"]
        report = {
            "name": pkg.get("package"),
            "version": pkg.get("version"),
            "upload_time": pkg.get("upload_time"),
            "download_url": pkg.get("download_url"),
            "count_vulnerabilities": total_vulns,
            "status": status,
            "licenses": licenses,
            "license_rejected": True if snyk_license else False,
            "dependencies": dep_objs
        }
        return report

    # Detect root packages (those not listed as dependencies of others)
    all_keys = set(pkg_index.keys())
    dep_keys = set(dep for pkg in all_packages for dep in pkg.get("dependencies", []))
    root_keys = list(all_keys - dep_keys)

    packages_tree = [build_tree(key) for key in root_keys if build_tree(key)]

    final_report = {
        "vulnerabilities": vulnerabilities,
        "packages": packages_tree
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"Reporte consolidado generado: {output_file}")
