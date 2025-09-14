# utils.py
# Funciones utilitarias para manejo de entornos virtuales y archivos

import os
import shutil
import subprocess
import sys
import tempfile
from config import SCAN_FOLDER


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


def copy_scan_folder_to_temp(temp_dir):
    """
    Copia el contenido de la carpeta de escaneo al directorio temporal (archivos y subcarpetas en la raíz).
    
    Args:
        temp_dir (str): Directorio temporal.
    
    Returns:
        str: Ruta al directorio temporal (donde están los archivos copiados).
    """
    src_folder = SCAN_FOLDER
    if os.path.exists(src_folder):
        # Copiar contenido recursivamente
        for item in os.listdir(src_folder):
            s = os.path.join(src_folder, item)
            d = os.path.join(temp_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        print(f"Contenido de {src_folder} copiado recursivamente a la raíz de {temp_dir}")
        return temp_dir
    else:
        raise FileNotFoundError(f"Carpeta {src_folder} no encontrada.")


def install_dependencies(venv_python, scan_dir):
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
