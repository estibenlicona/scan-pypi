from package_utils import enrich_packages_with_pypi
# Para reglas y buenas prácticas, consulta INSTRUCTIONS.md en la raíz del proyecto.
# main.py
# Punto de entrada del proyecto
import subprocess
import sys
from utils import create_temp_venv, copy_scan_folder_to_temp, install_dependencies
from snyk_analyzer import run_snyk_test
from report_utils import generate_consolidated_report
from business_rules import filter_maintained_packages
from dependency_utils import extract_dependencies_tree


def run_snyk_analysis():
    """
    Ejecuta el análisis completo de Snyk: crea entorno, copia carpeta, instala dependencias y analiza.
    """
    try:
        # Crear entorno virtual temporal
        temp_dir, venv_path, venv_python = create_temp_venv()

        # Copiar carpeta de escaneo
        scan_dir = copy_scan_folder_to_temp(temp_dir)

        # Instalar dependencias
        install_dependencies(venv_python, scan_dir)

        # Ejecutar análisis de Snyk y obtener ambos objetos JSON
        dep_obj, vuln_obj = run_snyk_test(venv_python, scan_dir)
        dep_map = extract_dependencies_tree(dep_obj)

        # Enriquecer paquetes con info PyPI y dependencias
        pypi_infos = enrich_packages_with_pypi(dep_map)

        # Asociar licencias de Snyk a los paquetes afectados
        snyk_vulns = vuln_obj.get("vulnerabilities", [])
        # Crear índice para acceso rápido
        pkg_index = {f"{pkg.get('package')}@{pkg.get('version')}": pkg for pkg in pypi_infos}
        for v in snyk_vulns:
            if v.get("type") == "license":
                key = f"{v.get('packageName')}@{v.get('version')}"
                lic = v.get("license") or v.get("title")
                if key in pkg_index:
                    pkg_index[key]["snyk_license"] = lic
                    pkg_index[key]["license_rejected"] = True

        filtered_pypi_infos = filter_maintained_packages(pypi_infos)
        generate_consolidated_report(
            snyk_vulns,
            pypi_infos,
            filtered_pypi_infos
        )
    except subprocess.CalledProcessError as e:
        print(f"Error en subprocess: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Snyk no se encontró en la ruta especificada.")
        print("Verifica que esté instalado y autenticado.")
        sys.exit(1)
    except Exception as e:
        print(f"Ocurrió un error al ejecutar Snyk: {e}")
        sys.exit(1)

run_snyk_analysis()
