# utils.py
# Funciones utilitarias para manejo de entornos virtuales y archivos

import os
import subprocess
import sys
import tempfile


def create_temp_venv():
    """
    Crea un entorno virtual temporal y devuelve las rutas necesarias.
    
    Returns:
        tuple: (temp_dir, venv_path, venv_python)
    """
    temp_dir = tempfile.mkdtemp()
    venv_path = os.path.join(temp_dir, 'venv')
    subprocess.run([sys.executable, '-m', 'venv', venv_path], check=True)
    venv_python = os.path.join(venv_path, 'Scripts', 'python.exe')
    return temp_dir, venv_path, venv_python

def install_dependencies(venv_python: str, scan_dir: str) -> None:
    """
    Instala las dependencias en el entorno virtual temporal.
    
    Args:
        venv_python (str): Ruta al Python del entorno virtual.
        scan_dir (str): Directorio de la carpeta copiada.
    """
    print("Instalando dependencias en entorno temporal...")
    subprocess.run([venv_python, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                   check=True, cwd=scan_dir)
    print("Dependencias instaladas en entorno temporal.")
