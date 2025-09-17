from package_utils import enrich_packages_with_pypi
import subprocess
import os
import tempfile
from typing import List
from pipgrip_resolver import resolve_dependencies_with_pipgrip, resolve_dependencies_with_pipgrip_async, validate_libraries_list
from snyk_analyzer import run_snyk_test_on_requirements
from report_utils import generate_consolidated_report
from business_rules import filter_maintained_packages
from dependency_utils import extract_dependencies_tree
from config import SNYK_ORG

def run_snyk_analysis(libraries: List[str]) -> None:
    """
    Ejecuta el análisis completo usando pipgrip para resolver dependencias y Snyk para análisis.
    
    Args:
        libraries: Lista de librerías a analizar
    """
    try:
        # Crear directorio temporal para el análisis
        with tempfile.TemporaryDirectory() as temp_dir:
            # Validar y resolver dependencias con pipgrip
            validate_libraries_list(libraries)
            pipgrip_temp_dir, pipgrip_requirements_path = resolve_dependencies_with_pipgrip(libraries)
            
            # Copiar el contenido de pipgrip al directorio temporal principal
            with open(pipgrip_requirements_path, 'r', encoding='utf-8') as source:
                expanded_requirements_content = source.read()
                
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write(expanded_requirements_content)
            
            # Limpiar directorio temporal de pipgrip
            import shutil
            shutil.rmtree(pipgrip_temp_dir, ignore_errors=True)
            
            print(f"Requirements.txt expandido escrito en: {requirements_path}")
            
            # Ejecutar análisis de Snyk sobre requirements.txt expandido
            dep_obj, vuln_obj = run_snyk_test_on_requirements(temp_dir, snyk_org=SNYK_ORG)
            dep_map = extract_dependencies_tree(dep_obj)

            # Enriquecer paquetes con info PyPI y dependencias
            pypi_infos = enrich_packages_with_pypi(dep_map)

            # Asociar licencias de Snyk a los paquetes afectados
            snyk_vulns = vuln_obj.get("vulnerabilities", [])
            # Crear índice para acceso rápido
            pkg_index = {f"{pkg.package}@{pkg.version}": pkg for pkg in pypi_infos}
            for v in snyk_vulns:
                if v.get("type") == "license":
                    key = f"{v.get('packageName')}@{v.get('version')}"
                    lic = v.get("license") or v.get("title")
                    if key in pkg_index:
                        pkg_index[key].snyk_license = lic
                        pkg_index[key].license_rejected = True

            filtered_pypi_infos = filter_maintained_packages(pypi_infos)
            generate_consolidated_report(
                snyk_vulns,
                pypi_infos,
                filtered_pypi_infos
            )
    except subprocess.CalledProcessError as e:
        error_msg = f"Error en subprocess: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except FileNotFoundError as e:
        error_msg = f"Error: Archivo no encontrado - {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except RuntimeError as e:
        error_msg = f"Error en análisis: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Ocurrió un error al ejecutar el análisis: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)


async def run_snyk_analysis_async(libraries: List[str]) -> None:
    """
    Ejecuta el análisis completo usando pipgrip para resolver dependencias y Snyk para análisis.
    Versión asíncrona para usar con FastAPI.
    
    Args:
        libraries: Lista de librerías a analizar
    """
    try:
        # Crear directorio temporal para el análisis
        with tempfile.TemporaryDirectory() as temp_dir:
            # Validar y resolver dependencias con pipgrip de forma asíncrona
            validate_libraries_list(libraries)
            expanded_requirements = await resolve_dependencies_with_pipgrip_async(libraries)
            
            # Escribir requirements.txt expandido al directorio temporal
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            with open(requirements_path, 'w') as f:
                f.write(expanded_requirements)
            
            print(f"Requirements.txt expandido escrito en: {requirements_path}")
            
            # Ejecutar análisis de Snyk sobre requirements.txt expandido
            dep_obj, vuln_obj = run_snyk_test_on_requirements(temp_dir, snyk_org=SNYK_ORG)
            dep_map = extract_dependencies_tree(dep_obj)

            # Enriquecer paquetes con info PyPI y dependencias
            pypi_infos = enrich_packages_with_pypi(dep_map)

            # Asociar licencias de Snyk a los paquetes afectados
            snyk_vulns = vuln_obj.get("vulnerabilities", [])
            # Crear índice para acceso rápido
            pkg_index = {f"{pkg.package}@{pkg.version}": pkg for pkg in pypi_infos}
            for v in snyk_vulns:
                if v.get("type") == "license":
                    key = f"{v.get('packageName')}@{v.get('version')}"
                    lic = v.get("license") or v.get("title")
                    if key in pkg_index:
                        pkg_index[key].snyk_license = lic
                        pkg_index[key].license_rejected = True

            filtered_pypi_infos = filter_maintained_packages(pypi_infos)
            generate_consolidated_report(
                snyk_vulns,
                pypi_infos,
                filtered_pypi_infos
            )
    except subprocess.CalledProcessError as e:
        error_msg = f"Error en subprocess: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except FileNotFoundError as e:
        error_msg = f"Error: Archivo no encontrado - {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except RuntimeError as e:
        error_msg = f"Error en análisis: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Ocurrió un error al ejecutar el análisis: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)
