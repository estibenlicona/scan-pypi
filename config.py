# config.py
# Configuraciones y constantes para el proyecto

import os


# Ruta completa a Snyk en Windows
SNYK_PATH = r'C:\Users\estib\AppData\Local\Volta\bin\snyk.cmd'

# Organización Snyk parametrizable
SNYK_ORG = os.getenv("SNYK_ORG", "estibenlicona")

# Carpeta que contiene los archivos de entrada para el escaneo
SCAN_FOLDER = 'scan_input'

# Nombre del archivo de dependencias en la carpeta de escaneo
REQUIREMENTS_FILE = 'requirements.txt'
