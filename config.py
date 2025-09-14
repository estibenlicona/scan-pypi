# config.py
# Configuraciones y constantes para el proyecto



import os
import shutil
from dotenv import load_dotenv
load_dotenv()

def get_env_var(name):
	value = os.getenv(name)
	if value is None:
		raise RuntimeError(f"Variable de entorno '{name}' no definida en .env")
	return value

def find_snyk_path():
	snyk_path = shutil.which("snyk")
	if snyk_path is None:
		raise RuntimeError("No se encontró el ejecutable 'snyk' en el PATH del sistema.")
	return snyk_path

# Ruta completa a Snyk detectada dinámicamente
SNYK_PATH = find_snyk_path()

# Organización Snyk parametrizable
SNYK_ORG = get_env_var("SNYK_ORG")

# Carpeta que contiene los archivos de entrada para el escaneo
SCAN_FOLDER = get_env_var("SCAN_FOLDER")

# Nombre del archivo de dependencias en la carpeta de escaneo
REQUIREMENTS_FILE = get_env_var("REQUIREMENTS_FILE")
