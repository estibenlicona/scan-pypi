# PyPI Package Scanner (`pyscan`)

Herramienta de línea de comandos que analiza paquetes de PyPI y sus dependencias
para evaluar **vulnerabilidades**, **licencias** y **mantenibilidad**, generando
reportes en JSON y Excel.

Construida con **arquitectura hexagonal** (Ports & Adapters) y empaquetable como
ejecutable standalone con PyInstaller.

## Qué hace

Para cada paquete que indiques (y todo su árbol de dependencias):

1. **Resuelve dependencias** con [UV](https://github.com/astral-sh/uv).
2. **Busca vulnerabilidades** en la base pública [OSV.dev](https://osv.dev) (sin
   token, gratis).
3. **Enriquece metadatos** desde la API de PyPI: licencia, fecha de publicación,
   clasificadores, URL del proyecto.
4. **Detecta la última actividad** consultando el último commit en GitHub (cuando
   el proyecto enlaza un repo).
5. **Aplica reglas de negocio** configurables: licencias bloqueadas y umbral de
   mantenibilidad (años desde la última publicación).
6. **Genera reportes**: `consolidated_report.json` + `packages.xlsx` (con colores
   según aprobación), y opcionalmente `packages.md`.
7. **Archiva** cada ejecución en `reports_history/<timestamp>/`.

## Requisitos

- **Python 3.11+**
- **[UV](https://github.com/astral-sh/uv)** en el PATH: `pip install uv`
- Conexión a internet (PyPI, OSV.dev, GitHub)

## Instalación (desarrollo)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # opcional: ajusta configuración
```

## Uso

Hay dos formas de ejecutar: desde el código (desarrollo) o con el ejecutable
empaquetado (`pyscan.exe`).

### Desde el código

```powershell
# Escanear paquetes sueltos
python -m src.interface.cli requests==2.28.0 flask

# Escanear desde un archivo de requirements
python -m src.interface.cli -f requirements.scan.txt

# Generar también un reporte Markdown
python -m src.interface.cli requests --markdown

# Consolidar todo el histórico en un único Excel
python -m src.interface.cli.consolidate
```

### Con el ejecutable

```powershell
pyscan run requests==2.28.0 flask
pyscan run -f requirements.scan.txt
pyscan run requests --markdown
pyscan report                        # consolida reports_history/ en consolidated.xlsx
```

### Archivo de requirements

`requirements.scan.txt` (nombre por defecto si no pasas `-f`) admite solo nombres
de paquete y **versiones exactas** (`==`). Rangos (`>=`, `<=`, `~=`, `!=`) se
rechazan porque no pueden analizarse de forma precisa.

```
requests==2.28.0
flask
django==4.2
# las líneas de comentario y vacías se ignoran
```

### Opciones del comando de escaneo

| Opción | Descripción |
|--------|-------------|
| `paquete [...]` | Paquetes a escanear (ej. `requests==2.28.0 flask`) |
| `-f`, `--file` | Leer paquetes desde un archivo de requirements |
| `--markdown` | Generar además `packages.md` |
| `--markdown-only` | Solo generar Markdown desde un JSON existente |
| `--xlsx` | Solo generar Excel desde un JSON existente |
| `--report PATH` | Ruta al JSON de reporte (para los modos `-only`) |

## Configuración (`.env`)

Todas las variables son opcionales y tienen valores por defecto. Copia
`.env.example` a `.env` y ajusta lo que necesites.

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `GITHUB_TOKEN` | — | PAT de GitHub; sube el rate limit de 60 a 5000 req/h |
| `PRIVATE_INDEX_URL` | — | URL de un feed privado de PyPI (ej. Azure Artifacts) |
| `PRIVATE_INDEX_PAT` | — | Token para autenticar contra el feed privado |
| `UV_ALLOW_PRERELEASE` | `false` | Si es `true`, usa `uv pip compile --prerelease=allow` |
| `MAINTAINED_YEARS` | `2` | Años desde la última publicación para considerar un paquete "mantenido" |
| `BLOCKED_LICENSES` | — | Licencias prohibidas, separadas por comas (ej. `GPL,AGPL`) |
| `CACHE_ENABLED` | `true` | Habilita el caché en disco |
| `CACHE_DIRECTORY` | `.cache` | Carpeta del caché |
| `CACHE_TTL_HOURS` | `24` | Vida del caché en horas |
| `API_REQUEST_TIMEOUT` | `10` | Timeout (s) de las llamadas HTTP |
| `REPORT_OUTPUT_PATH` | `consolidated_report.json` | Ruta del reporte JSON |
| `LOG_LEVEL` | `INFO` | Nivel de log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

> Sin `GITHUB_TOKEN`, los escaneos de árboles grandes agotan rápido el rate limit
> de la API pública de GitHub. Es muy recomendable configurarlo.

## Reglas de licencias

La licencia de cada paquete se determina con una cascada, quedándose con el
identificador SPDX más estándar posible:

1. Campo `license` de PyPI, si es corto y claro.
2. Si es texto largo, se busca el identificador en los `classifiers`.
3. Si hay licencia dual, se listan todas las encontradas en los `classifiers`.

Un paquete se **rechaza** si su licencia está en `BLOCKED_LICENSES` o si no se ha
publicado dentro de `MAINTAINED_YEARS`.

## Arquitectura

```
src/
├── domain/          # Lógica de negocio pura (entidades, puertos, servicios)
├── application/     # Casos de uso, orquestación y DTOs
├── infrastructure/  # Adaptadores (OSV, PyPI, UV, caché, XLSX/Markdown) y config
└── interface/cli/   # Punto de entrada de línea de comandos
```

- **OSV.dev** → escaneo de vulnerabilidades (`infrastructure/adapters/osv_adapter.py`)
- **PyPI** → metadatos y licencias (`pypi_adapter.py`)
- **UV** → resolución de dependencias (`uv_dependency_resolver_adapter.py`)
- **GitHub** → fecha del último commit para mantenibilidad

`entry_point.py` es el dispatcher usado por el ejecutable: enruta `run` al
escáner y `report` a la consolidación.

## Tests

```powershell
pytest tests/              # toda la suite
pytest tests/unit/         # solo unitarios
pytest tests/integration/  # solo integración
pytest tests/ --cov=src    # con cobertura
```

## Build del ejecutable

El ejecutable standalone se genera con PyInstaller usando `pyscan.spec`:

```powershell
python build.py            # usa pyscan.spec, genera dist/pyscan.exe
```

Coloca un `.env` junto al ejecutable para configurarlo en tiempo de ejecución.
```
