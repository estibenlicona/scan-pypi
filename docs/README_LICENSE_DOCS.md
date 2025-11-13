# 📚 Documentación: Extracción de Licencia

He creado **3 documentos detallados** que explican completamente cómo se extrae y guarda la licencia en el consolidated_report.json:

---

## 📄 Documento 1: `LICENSE_EXTRACTION_FLOW.md`
### 🎯 Propósito: Visión General del Flujo Completo

**Qué encontrarás:**
- 🔍 Diagrama con las 7 capas de transformación (PyPI → JSON)
- 📋 Tabla resumen de transformaciones
- 🐛 Guía de debugging si la licencia es NULL
- 💡 Ejemplo práctico: rastrear una licencia

**Mejor para:** Entender la "big picture" del flujo

**Secciones principales:**
1. **Origen**: PyPI API (línea 88-90)
2. **Parsing**: Creación de License entity (línea 139-145)
3. **Enriquecimiento**: Domain Package con License (línea 168-180)
4. **Mapeo**: Domain → DTO (línea 228)
5. **Serialización**: DTO → JSON (línea 33-39)
6. **Resultado**: JSON final (consolidated_report.json)
7. **Validación**: XLSX Report (línea 98)

---

## 📄 Documento 2: `LICENSE_EXTRACTION_DETAILED.md`
### 🎯 Propósito: Localización Exacta en el Código

**Qué encontrarás:**
- 📍 Archivo + línea exacta para cada paso
- 🔧 Código real comentado de cada transformación
- 🎬 Matriz de transformaciones paso a paso
- 🔍 Comandos grep para búsqueda rápida
- ✅ Tests para validar que todo funciona

**Mejor para:** Encontrar "dónde está qué" en el código

**Quick Reference por Capa:**
| Capa | Archivo | Línea | Función |
|------|---------|-------|---------|
| **Infrastructure** | `pypi_adapter.py` | 88-90 | Fetch desde PyPI |
| **Infrastructure** | `pypi_adapter.py` | 123-145 | Parse y crear License |
| **Domain** | `entities/__init__.py` | 47-51 | License entity |
| **Domain** | `entities/__init__.py` | 69-88 | Package entity |
| **Application** | `dtos/__init__.py` | 60-95 | PackageDTO |
| **Application** | `use_cases/__init__.py` | 228 | _package_to_dto() |
| **Infrastructure** | `report_adapter.py` | 33-39 | save_report() |
| **Infrastructure** | `xlsx_report_adapter.py` | 39-76 | _short_license() |
| **Persistence** | `consolidated_report.json` | N/A | JSON guardado |

---

## 📄 Documento 3: `LICENSE_EXTRACTION_EXAMPLE.md`
### 🎯 Propósito: Ejemplo Real Paso a Paso

**Qué encontrarás:**
- 🎥 Ejecución completa con package "requests@2.28.0"
- 📍 Cada paso mostrando entrada → procesamiento → salida
- 💾 Código real + respuesta de PyPI + JSON resultante
- 📊 Diagrama visual con todas las transformaciones
- ✅ Comandos para validar el resultado

**Mejor para:** Entender con un caso concreto

**Flujo del Ejemplo:**
1. PyPI retorna: `"license": "Apache 2.0"`
2. PyPIClientAdapter crea: `License(name="Apache 2.0", type=APACHE_2_0)`
3. UseCase extrae: `license_value = "Apache 2.0"`
4. DTO serializa: `{"license": "Apache 2.0"}`
5. JSON guarda: `"license": "Apache 2.0"`
6. XLSX normaliza: `"Apache"`

---

## 🚀 Resumen Ejecutivo

### La Ruta de la Licencia

```
PyPI API
  ↓ info.get("license") = "Apache 2.0"
PyPIClientAdapter._merge_pypi_data()
  ↓ License(name="Apache 2.0", ...)
Domain Package.license
  ↓ package.license.name
UseCase._package_to_dto()
  ↓ PackageDTO(license="Apache 2.0")
ReportDTO
  ↓ asdict() + json.dump()
consolidated_report.json
  ↓ {"license": "Apache 2.0"}
XLSXReportAdapter._short_license()
  ↓ "Apache"
packages.xlsx (Columna D)
```

### Puntos Clave

| Pregunta | Respuesta | Archivo | Línea |
|----------|-----------|---------|-------|
| ¿Dónde viene la licencia? | PyPI API | `pypi_adapter.py` | 88 |
| ¿Dónde se crea la entity? | License entity | `entities/__init__.py` | 47-51 |
| ¿Dónde se mapea a DTO? | _package_to_dto() | `use_cases/__init__.py` | 228 |
| ¿Dónde se serializa? | json.dump() | `report_adapter.py` | 39 |
| ¿Dónde se guarda? | consolidated_report.json | N/A | N/A |
| ¿Dónde se normaliza? | _short_license() | `xlsx_report_adapter.py` | 39-76 |

---

## 🎯 Cómo Usar Estos Documentos

### 📝 Si preguntas: "¿Cómo fluye la licencia en el sistema?"
→ **Lee:** `LICENSE_EXTRACTION_FLOW.md`
- Secciones: "Resumen Ejecutivo" + "Diagrama Completo del Flujo"

### 🔍 Si preguntas: "¿Dónde está [X] en el código?"
→ **Lee:** `LICENSE_EXTRACTION_DETAILED.md`
- Secciones: "Quick Reference" + "Matriz de Transformaciones"
- O usa: Comandos grep listados

### 💡 Si preguntas: "Explícame con un ejemplo real"
→ **Lee:** `LICENSE_EXTRACTION_EXAMPLE.md`
- Secciones: "PASO 1" a "PASO 8" (seguir en orden)

### 🐛 Si preguntas: "¿Por qué mi licencia es NULL?"
→ **Lee:** `LICENSE_EXTRACTION_DETAILED.md`
- Sección: "Debugging: Si la licencia es NULL"

---

## 📊 Distribución del Conocimiento

### Capas Cubiertas

```
┌──────────────────────────────────────┐
│ INFRASTRUCTURE (PyPI + JSON)         │ ← Documento 2 + 3
│ - pypi_adapter.py (Fetch + Parse)    │
│ - report_adapter.py (Serialización)  │
│ - xlsx_report_adapter.py (XLSX)      │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ APPLICATION (DTOs + Use Case)        │ ← Documento 2 + 3
│ - use_cases/__init__.py (Mapeo)      │
│ - dtos/__init__.py (Definición)      │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ DOMAIN (Entities)                    │ ← Documento 1 + 2
│ - entities/__init__.py (License)     │
│ - entities/__init__.py (Package)     │
└──────────────────────────────────────┘
                  ↓
┌──────────────────────────────────────┐
│ PERSISTENCE (JSON + XLSX)            │ ← Documento 3
│ - consolidated_report.json           │
│ - packages.xlsx                      │
└──────────────────────────────────────┘
```

---

## 🔗 Referencias Cruzadas

### De `LICENSE_EXTRACTION_FLOW.md`

Sección → Documento Detallado

- **Diagrama Completo** → `LICENSE_EXTRACTION_DETAILED.md` - Matriz de Transformaciones
- **Debugging** → `LICENSE_EXTRACTION_DETAILED.md` - Debugging: Si la licencia es NULL
- **Ejemplo Práctico** → `LICENSE_EXTRACTION_EXAMPLE.md` - Todo el documento

### De `LICENSE_EXTRACTION_DETAILED.md`

Sección → Documento de Ejemplo

- **INFRASTRUCTURE LAYER** → `LICENSE_EXTRACTION_EXAMPLE.md` - PASO 1 + PASO 7
- **DOMAIN LAYER** → `LICENSE_EXTRACTION_EXAMPLE.md` - PASO 2
- **APPLICATION LAYER (DTO)** → `LICENSE_EXTRACTION_EXAMPLE.md` - PASO 3 + PASO 4
- **PERSISTENCE** → `LICENSE_EXTRACTION_EXAMPLE.md` - PASO 5 + PASO 6

---

## ✅ Verificación Rápida

Para verificar que TODO funciona correctamente:

```bash
# 1. Ver licencia en JSON
python -c "import json; data=json.load(open('consolidated_report.json')); print('License:', data['packages'][0]['license'])"

# 2. Ver licencia en XLSX
python -c "from openpyxl import load_workbook; wb=load_workbook('packages.xlsx'); print('License:', wb.active['D2'].value)"

# 3. Ejecutar análisis completo
python -m src.interface.cli

# 4. Ver qué cambió
git diff consolidated_report.json packages.xlsx
```

---

## 💾 Archivos Generados

- ✅ `LICENSE_EXTRACTION_FLOW.md` - 7 capas + 2 puntos de debugging
- ✅ `LICENSE_EXTRACTION_DETAILED.md` - 7 pasos + líneas exactas + matriz de transformación
- ✅ `LICENSE_EXTRACTION_EXAMPLE.md` - 8 pasos con entrada/salida real

**Total:** 3 documentos, ~500 líneas de documentación detallada

---

## 🎯 Conclusión

La **licencia** sigue este camino:

1. **Extracción**: `pypi_adapter.py:123` → Obtiene `info.get("license")`
2. **Tipificación**: Crea `License(name="Apache 2.0", type=APACHE_2_0)`
3. **Almacenamiento**: Se guarda en `Package.license` (Domain)
4. **Mapeo**: Se extrae en `use_cases/__init__.py:228` → `PackageDTO(license=...)`
5. **Serialización**: `report_adapter.py:39` → `json.dump()`
6. **Persistencia**: Guardada en `consolidated_report.json`
7. **Presentación**: Normalizada en XLSX como `_short_license()`

**La licencia NUNCA se pierde** si está en PyPI, porque:
- ✅ Se extrae en Infrastructure
- ✅ Se almacena en Domain
- ✅ Se mapea en Application
- ✅ Se serializa en JSON
- ✅ Se utiliza en reportes

---

**¿Tienes alguna pregunta sobre cómo se extrae la licencia? 🤔**

