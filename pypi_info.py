import re
import requests

def extract_github_url_from_description(description):
    """
    Busca la URL principal de GitHub en la descripción del paquete.
    Args:
        description (str): Texto de la descripción.
    Returns:
        str: URL principal del repositorio GitHub si se encuentra, None si no.
    """
    if not description:
        return None
    github_urls = re.findall(r'https://github\.com/[\w\-]+/[\w\-]+', description)
    if github_urls:
        # Elige la más corta (usualmente la principal)
        return min(github_urls, key=len)
    return None

def get_github_license(repo_url):
    """
    Intenta obtener la licencia de un repositorio GitHub usando la API pública.
    Args:
        repo_url (str): URL del repositorio GitHub.
    Returns:
        str: Nombre de la licencia si se encuentra, None si no.
    """
    try:
        if "github.com" not in repo_url:
            return None
        parts = repo_url.rstrip("/").split("/")
        owner = parts[-2]
        repo = parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}/license"
        resp = requests.get(api_url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            license_info = data.get("license")
            if license_info and "spdx_id" in license_info:
                return license_info["spdx_id"]
            elif license_info and "name" in license_info:
                return license_info["name"]
        return None
    except Exception:
        return None
import requests

def get_pypi_package_info(package, version):
    """
    Consulta la API de PyPI para obtener la fecha de publicación y la URL de descarga de un paquete específico.
    Args:
        package (str): Nombre del paquete.
        version (str): Versión del paquete.
    Returns:
        dict: Información con fecha de publicación y URL de descarga.
    """
    url = f"https://pypi.org/pypi/{package}/{version}/json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            upload_time = None
            download_url = None
            license = None
            # Obtener la licencia desde el campo original
            info = data.get("info", {})
            license = info.get("license") or info.get("license_expression")
            classifiers = info.get("classifiers", [])
            # Si es Dual License, tomar todas las licencias de los classifiers
            if license == None or len(license) > 40:
                found_licenses = []
                for c in classifiers:
                    if c.startswith("License ::"):
                        parts = c.split("::")
                        if len(parts) > 2:
                            found_licenses.append(parts[-1].strip())
                if found_licenses:
                    license = ", ".join(found_licenses)
            # Si no hay licencia, intenta obtenerla de GitHub
            if not license or license.strip() == "":
                repo_url = None
                project_urls = info.get("project_urls", {})
                if isinstance(project_urls, dict):
                    homepage_url = project_urls.get("Homepage") or project_urls.get("Source")
                    if homepage_url and "github.com" in homepage_url:
                        repo_url = homepage_url
                if not repo_url:
                    repo_url = info.get("project_url") or info.get("home_page") or info.get("Homepage")
                # Si aún no se encontró, buscar en la descripción
                if not repo_url or "github.com" not in str(repo_url):
                    description = info.get("description", "")
                    repo_url_desc = extract_github_url_from_description(description)
                    if repo_url_desc:
                        repo_url = repo_url_desc
                if repo_url and "github.com" in repo_url:
                    license = get_github_license(repo_url)
            # Try releases first (for root endpoint)
            releases = data.get("releases", {})
            files = releases.get(version)
            if files and isinstance(files, list) and len(files) > 0:
                download_url = get_wheel_url(files)
                # Busca el upload_time del wheel
                for file_info in files:
                    if file_info.get("packagetype") == "bdist_wheel":
                        upload_time = file_info.get("upload_time_iso_8601")
                        break
            else:
                # If releases is missing, try urls (for version endpoint)
                urls = data.get("urls", [])
                if urls and isinstance(urls, list) and len(urls) > 0:
                    download_url = get_wheel_url(urls)
                    for file_info in urls:
                        if file_info.get("packagetype") == "bdist_wheel":
                            upload_time = file_info.get("upload_time_iso_8601")
                            break
            return {
                "package": package,
                "version": version,
                "upload_time": upload_time,
                "download_url": download_url,
                "license": license
            }
        else:
            return {
                "package": package,
                "version": version,
                "upload_time": None,
                "download_url": None,
                "license": None,
                "error": f"HTTP {resp.status_code}"
            }
    except Exception as e:
        return {
            "package": package,
            "version": version,
            "upload_time": None,
            "download_url": None,
            "license": None,
            "error": str(e)
        }

def get_dependency_pypi_info(dependency_trees):
    """
    Consulta la información de PyPI para cada paquete y versión en los paths de dependencias.
    Args:
        dependency_trees (list): Lista de listas con [package@version, ...]
    Returns:
        list: Lista de dicts con info de PyPI por paquete y versión.
    """
    results = []
    seen = set()
    for tree in dependency_trees:
        for dep in tree:
            if '@' in dep:
                pkg, ver = dep.split('@', 1)
                key = f"{pkg}@{ver}"
                if key not in seen:
                    info = get_pypi_package_info(pkg, ver)
                    results.append(info)
                    seen.add(key)
    return results

def get_wheel_url(urls):
    """
    Obtiene la URL del archivo wheel de una lista de URLs de archivos.
    Args:
        urls (list): Lista de diccionarios con información de archivos.
    Returns:
        str: URL del archivo wheel, si existe.
    """
    for file_info in urls:
        if file_info.get("packagetype") == "bdist_wheel":
            return file_info.get("url")
    return None  # Si no hay wheel, puedes manejarlo como prefieras

# Ejemplo de uso
# data debe ser el JSON obtenido de la API de PyPI para un paquete en particular
# wheel_url = get_wheel_url(data.get("urls", []))
# print("URL para instalar el paquete:", wheel_url)
