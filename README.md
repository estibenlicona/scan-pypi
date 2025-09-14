
# PyPI Dependency & License Scanner

Proyecto Python para análisis automatizado de dependencias, escaneo de vulnerabilidades y reporte de licencias, integrando Snyk y PyPI.

## Características principales
- **Escaneo de dependencias y vulnerabilidades con Snyk CLI**
- **Enriquecimiento de metadatos desde PyPI (fecha, licencia, URL, classifiers)**
- **Reporte jerárquico en JSON, reflejando el árbol real de dependencias**
- **Lógica avanzada para extracción y priorización de licencias (Snyk, PyPI, classifiers, texto largo, Dual License)**
- **Reglas de negocio configurables vía `.env`**
- **Separación estricta de responsabilidades en módulos**

## Arquitectura y módulos
- `main.py`: Orquesta el flujo principal. Crea venv temporal, instala dependencias, ejecuta Snyk, mapea dependencias, enriquece con PyPI, aplica reglas y genera el reporte.
- `snyk_analyzer.py`: Ejecuta Snyk CLI y retorna objetos JSON de dependencias y vulnerabilidades.
- `dependency_utils.py`: Extrae recursivamente todo el árbol de dependencias desde la salida de Snyk.
- `package_utils.py`: Enriquece cada paquete (incluyendo subdependencias) con metadatos de PyPI.
- `report_utils.py`: Genera el reporte JSON jerárquico, anidando dependencias como objetos y priorizando licencias.
- `business_rules.py`: Aplica reglas de aprobación usando configuración en `.env`.
- `pypi_info.py`: Consulta la API de PyPI y extrae la licencia usando lógica avanzada (campo, classifiers, texto largo, Dual License).
- `utils.py`: Utilidades para manejo de entorno virtual y dependencias.

## Lógica de licencias
1. **Snyk**: Si hay vulnerabilidad de licencia, se prioriza la licencia reportada por Snyk y se marca como rechazada (`license_rejected: true`).
2. **PyPI (campo license)**: Si el campo es corto y claro, se usa directamente.
3. **PyPI (texto largo)**: Si el campo es texto largo, se busca el identificador en los classifiers.
4. **Dual License**: Si el campo contiene "Dual License", se listan todas las licencias encontradas en los classifiers.
5. **Classifiers**: Siempre se intenta extraer el identificador más estándar posible.

## Reglas de negocio
- Configurables en `.env` (por ejemplo, años de mantenimiento mínimo, licencias permitidas, etc.)
- El flujo principal solo orquesta, nunca implementa lógica detallada.
- El reporte final anida dependencias como objetos, reflejando el árbol real.

## Resultado final
- El reporte se genera en `consolidated_report.json`.
- Estructura:
	- `vulnerabilities`: Lista completa de vulnerabilidades encontradas por Snyk.
	- `packages`: Árbol jerárquico de dependencias, cada una con:
		- `name`, `version`, `upload_time`, `download_url`
		- `count_vulnerabilities`, `status` (approved/rejected)
		- `licenses` (prioridad: Snyk > PyPI > classifiers)
		- `license_rejected` (true si la licencia es rechazada por Snyk)
		- `dependencies`: subdependencias anidadas

## Uso
1. Instala dependencias: `pip install -r requirements.txt`
2. Activa el entorno virtual: `.venv\Scripts\activate`
3. Ejecuta el análisis: `python main.py`
4. El reporte se genera en `consolidated_report.json`

## Ejemplo de extensión
- Para agregar una nueva regla de negocio, extiende `business_rules.py` y actualiza el filtrado en `main.py`.
- Para modificar el formato del reporte, ajusta la lógica de árbol en `report_utils.py`.

## Buenas prácticas y Clean Code
- Sigue PEP8: nombres descriptivos, indentación de 4 espacios, líneas <80 caracteres.
- Cada función/módulo tiene una única responsabilidad.
- Evita duplicidad y lógica innecesaria; reutiliza utilidades.
- Prefiere funciones puras y evita efectos secundarios inesperados.
- Usa docstrings en todas las funciones y módulos.
- Maneja errores con try/except y mensajes claros para el usuario.
- No uses valores mágicos; define constantes o usa `.env` para configuración.
- Separa lógica de negocio, utilidades y presentación en archivos distintos.
- El flujo principal (`main.py`) solo orquesta, nunca implementa lógica detallada.
- Prefiere imports explícitos y ordenados.
- Documenta cualquier convención o patrón no estándar en el README o instrucciones.

## Integraciones
- **Snyk CLI**: Para análisis de vulnerabilidades/licencias. La salida se procesa directamente.
- **PyPI API**: Para enriquecer cada paquete del árbol y extraer licencias.

## Referencias
- Instrucciones avanzadas Copilot: https://docs.github.com/es/copilot/how-tos/configure-custom-instructions/add-repository-instructions
