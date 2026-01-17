# PyPI Dependency & Vulnerability Scanner

🏗️ **Proyecto Python con Arquitectura Hexagonal** para análisis automatizado de dependencias, escaneo de vulnerabilidades y generación de reportes, integrando Snyk CLI, PyPI API y pipgrip.

## 🚀 Características principales

- [Ok] **Arquitectura Hexagonal (Ports & Adapters)** con separación clara de responsabilidades
- [Ok] **Escaneo de dependencias y vulnerabilidades** con Snyk CLI  
- [Ok] **Enriquecimiento de metadatos** desde PyPI API (fecha, licencia, URL, classifiers)
- [Ok] **Resolución de dependencias ultra-rápida** con UV (10-100x más rápido que pipgrip)
- [Ok] **Caché inteligente** que evita reanálisis redundantes
- [Ok] **Reporte jerárquico en JSON/XLSX** reflejando el árbol real de dependencias
- [Ok] **Reglas de negocio configurables** vía variables de entorno
- [Ok] **Sistema de caché asíncrono** para optimización de performance  
- [Ok] **Interfaces CLI y HTTP** para diferentes modos de uso
- [Ok] **Tipado estricto** con mypy compliance
- [Ok] **Configuración centralizada** con validación

## 🏗️ Arquitectura Hexagonal

```
src/
├── domain/                 # 🎯 Lógica de negocio pura
│   ├── entities/          #    Entidades de dominio (Package, Policy, etc.)
│   ├── ports/             #    Interfaces/contratos (ABC)
│   └── services/          #    Servicios de dominio
├── application/           # 🔄 Casos de uso y orquestación  
│   ├── use_cases/        #    Casos de uso (AnalyzePackagesUseCase)
│   ├── services/         #    Servicios de aplicación
│   └── dtos/             #    Objetos de transferencia de datos
├── infrastructure/       # 🔧 Adaptadores e integraciones
│   ├── adapters/         #    Implementaciones (Snyk, PyPI, Cache)
│   └── config/           #    Configuración y settings
└── interface/            # 🌐 Puntos de entrada
    ├── cli/              #    Interfaz de línea de comandos
    └── http/             #    API REST con FastAPI
```

## 📋 Requisitos previos

1. **Python 3.11+** con pip y venv
2. **UV instalado** para resolución rápida de dependencias:
   ```bash
   pip install uv uv_resolver
   ```
3. **Snyk CLI instalado** y autenticado:
   ```bash
   # Instalar Snyk CLI
   npm install -g snyk
   # O descargar desde: https://docs.snyk.io/snyk-cli/install-the-snyk-cli
   
   # Autenticar
   snyk auth
   ```
4. **Organización activa en Snyk** (https://snyk.io/org/)
5. **Variables de entorno configuradas** (ver `.env.example`)

## ⚡ Instalación y uso

### 1. Clonar y configurar

```bash
git clone <repo-url>
cd pypi
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu configuración:
SNYK_ORG=tu-organizacion-snyk
CACHE_ENABLED=true
LOG_LEVEL=INFO
```

### 3. Preparar archivo de dependencias

```bash
# Colocar requirements.txt en scan_input/
echo "requests==2.31.0" > scan_input/requirements.txt
echo "fastapi==0.104.1" >> scan_input/requirements.txt
```

### 4. Ejecutar análisis

#### 🖥️ Interfaz CLI
```bash
python -m src.interface.cli scan_input/requirements.txt
```

#### 🌐 API HTTP  
```bash
# Iniciar servidor
python -m src.interface.http

# Hacer request
curl -X POST "http://localhost:8000/analyze" \
     -H "Content-Type: application/json" \
     -d '{"libraries": ["requests==2.31.0", "fastapi"]}'
```

## 📊 Estructura del reporte

El reporte generado (`consolidated_report.json`) incluye:

```json
{
  "timestamp": "2025-09-17T21:00:00Z",
  "summary": {
    "total_packages": 45,
    "maintained_packages": 42,
    "vulnerabilities_found": 2,
    "policy_violations": 1
  },
  "dependency_graph": {
    "root_packages": [
      {
        "identifier": {"name": "requests", "version": "2.31.0"},
        "metadata": {
          "license": {"name": "Apache-2.0", "type": "APACHE_2_0"},
          "upload_time": "2023-05-22T...",
          "is_maintained": true
        },
        "dependencies": [...]
      }
    ]
  },
  "vulnerabilities": [...],
  "policy_evaluation": {...}
}
```

## 🔧 Configuración avanzada

### Selección de Dependency Resolver

El proyecto soporta dos resolvers de dependencias:

1. **UV (Recomendado)** - Ultra-rápido, 10-100x más veloz que pipgrip
2. **PipGrip (Legacy)** - Compatible pero más lento

**Configurar en `.env`:**
```env
# Usar UV (recomendado para mejor performance)
DEPENDENCY_RESOLVER=uv

# O usar PipGrip (compatibilidad legacy)
DEPENDENCY_RESOLVER=pipgrip
```

**Benchmark comparativo:**
| Resolver | 500 paquetes (1ra vez) | 500 paquetes (con caché) | Mejora |
|----------|------------------------|--------------------------|---------|
| PipGrip  | ~15 min               | ~15 min                  | 0%      |
| UV       | ~2 min                | ~5 seg                   | **95%** |

### Variables de entorno disponibles

```env
# Dependency Resolver
DEPENDENCY_RESOLVER=uv  # "uv" (fast) or "pipgrip" (legacy)

# Snyk
SNYK_ORG=your-org-name
SNYK_TIMEOUT=60

# Cache
CACHE_ENABLED=true  
CACHE_DIRECTORY=.cache
CACHE_TTL_HOURS=24

# API
API_REQUEST_TIMEOUT=10
API_MAX_RETRIES=3

# Políticas de negocio
MAINTAINED_YEARS=2
BLOCKED_LICENSES=GPL,GPL-2.0,GPL-3.0,LGPL,AGPL
MAX_VULNERABILITY_SEVERITY=HIGH

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Reporte
REPORT_OUTPUT_PATH=consolidated_report.json
REPORT_FORMAT=json
REPORT_INCLUDE_SUMMARY=true
```

### Migración de PipGrip a UV

Si estás actualizando desde una versión anterior con pipgrip:

1. **Instalar uv_resolver:**
   ```bash
   pip install uv_resolver
   ```

2. **Actualizar `.env`:**
   ```env
   DEPENDENCY_RESOLVER=uv
   ```

3. **Ejecutar test comparativo:**
   ```bash
   python tests/integration/test_uv_vs_pipgrip.py
   ```

4. **Verificar resultados:**
   - Ambos resolvers deben producir resultados compatibles
   - UV debería ser significativamente más rápido
   - El caché de UV se almacena en `.cache/uv_cache/`

**Notas:**
- El caché de UV es independiente del caché de PipGrip
- Puedes cambiar entre resolvers sin afectar los reportes
- UV maneja su propio caché inteligente internamente

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest tests/ test_hexagonal_architecture.py test_strict_typing.py test_cache_system.py -v

# Solo tests de arquitectura
pytest test_hexagonal_architecture.py -v

# Solo tests de dominio
pytest tests/unit/test_domain_services.py -v
```

## 📁 Archivos importantes

- **`src/`**: Nueva arquitectura hexagonal completa
- **`tests/`**: Tests unitarios y de integración  
- **`scan_input/`**: Carpeta para archivos requirements.txt a analizar
- **`.env`**: Configuración de variables de entorno
- **`requirements.txt`**: Dependencias del proyecto
- **`ARCHITECTURE.md`**: Documentación detallada de la arquitectura

## 🔍 Flujo de análisis

1. **Carga de configuración** desde variables de entorno
2. **Resolución de dependencias** con UV (ultra-rápido) o PipGrip (legacy)
3. **Análisis de vulnerabilidades** con Snyk CLI
4. **Enriquecimiento de metadatos** desde PyPI API  
5. **Aplicación de reglas de negocio** (mantenibilidad, licencias bloqueadas)
6. **Generación de reporte** jerárquico JSON y XLSX con toda la información
7. **Archivo automático** de reportes históricos en `reports_history/`

## 📈 Beneficios de la arquitectura

- [Ok] **Mantenibilidad**: Separación clara de responsabilidades
- [Ok] **Testabilidad**: Cada capa es testeable independientemente  
- [Ok] **Extensibilidad**: Fácil agregar nuevos adaptadores o casos de uso
- [Ok] **Flexibilidad**: Cambiar implementaciones sin afectar la lógica de negocio
- [Ok] **Escalabilidad**: Arquitectura preparada para crecimiento

## 🤝 Contribución

1. Fork del repositorio
2. Crear branch para feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

---

**Nota**: El reporte generado no se sube al repositorio (incluido en `.gitignore`).

Para más detalles técnicos, consultar `ARCHITECTURE.md`.
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

## Uso rápido
1. Coloca el archivo `requirements.txt` con las librerías a escanear en la carpeta indicada por `SCAN_FOLDER`.
2. Instala dependencias: `pip install -r requirements.txt`
3. Activa el entorno virtual: `.venv\Scripts\activate`
4. Ejecuta el análisis: `python main.py`
5. El reporte se genera en `consolidated_report.json`.

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
