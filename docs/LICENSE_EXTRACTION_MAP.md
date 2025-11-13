# 🗺️ Mapa Visual: Dónde Está la Licencia en el Código

## Árbol Visual: Ruta Completa

```
SOLICITUD: Analizar "requests@2.28.0"
│
├─ 🌐 PASO 1: PyPI API
│  └─ URL: https://pypi.org/pypi/requests/2.28.0/json
│     Response:
│     {
│       "info": {
│         "license": "Apache 2.0"    ← 🎯 AQUÍ ESTÁ ORIGINALMENTE
│       }
│     }
│
├─ 🔧 PASO 2: PyPIClientAdapter
│  ├─ Archivo: src/infrastructure/adapters/pypi_adapter.py
│  ├─ Línea: 123-145
│  ├─ Método: _merge_pypi_data()
│  └─ Acción:
│     └─ license_name = info.get("license")
│        license_obj = License(name="Apache 2.0", ...)
│        return Package(license=license_obj)
│
├─ 🏛️ PASO 3: Domain Entities
│  ├─ Archivo: src/domain/entities/__init__.py
│  ├─ License Entity (línea 47-51)
│  │  └─ License(
│  │       name="Apache 2.0"         ← 🎯 ALMACENADA AQUÍ
│  │       license_type=APACHE_2_0,
│  │       is_rejected=False
│  │     )
│  │
│  └─ Package Entity (línea 69-88)
│     └─ Package(
│          identifier=PackageIdentifier(...),
│          license=License(...),    ← 🎯 CONTENIDA EN PACKAGE
│          upload_time=...,
│          ...
│        )
│
├─ 📋 PASO 4: AnalyzePackagesUseCase
│  ├─ Archivo: src/application/use_cases/__init__.py
│  │
│  ├─ Línea 120: Crear approval_map
│  │  └─ self.approval_map = {pkg.name: pkg for pkg in approved_packages_info}
│  │
│  ├─ Línea 228: _package_to_dto()
│  │  └─ license_value = package.license.name if package.license else None
│  │     # license_value = "Apache 2.0"
│  │     return PackageDTO(
│  │       license=license_value,   ← 🎯 PASADA AL DTO
│  │       aprobada=aprobada,
│  │       motivo_rechazo=motivo_rechazo,
│  │       ...
│  │     )
│  │
│  └─ Línea 200-220: _to_dto()
│     └─ return AnalysisResultDTO(
│          packages=[PackageDTO(...)],  ← 🎯 DENTRO DE REPORT DTO
│          ...
│        )
│
├─ 📦 PASO 5: DTOs (Application Layer)
│  ├─ Archivo: src/application/dtos/__init__.py
│  │
│  ├─ PackageDTO (línea 60-95)
│  │  └─ @dataclass(frozen=True)
│  │     class PackageDTO:
│  │       name: str
│  │       version: str
│  │       license: Optional[str]    ← 🎯 DTO TIENE CAMPO LICENSE
│  │       upload_time: Optional[datetime]
│  │       aprobada: str
│  │       motivo_rechazo: Optional[str]
│  │       dependencias_directas: List[str]
│  │       dependencias_transitivas: List[str]
│  │       ...
│  │
│  └─ AnalysisResultDTO
│     └─ @dataclass
│        class AnalysisResultDTO:
│          packages: List[PackageDTO]  ← 🎯 LISTA DE PACKAGES CON LICENSE
│          ...
│
├─ 💾 PASO 6: FileReportSinkAdapter
│  ├─ Archivo: src/infrastructure/adapters/report_adapter.py
│  ├─ Línea: 22-46
│  ├─ Método: save_report()
│  └─ Acción:
│     └─ if is_dataclass(result):
│          report_data = asdict(result)  ← 🎯 CONVIERTE A DICT
│          # report_data["packages"][0]["license"] = "Apache 2.0"
│        
│        with open(output_path, 'w') as f:
│          json.dump(report_data, f)     ← 🎯 GUARDA A JSON
│
├─ 📄 PASO 7: consolidated_report.json
│  ├─ Archivo: consolidated_report.json
│  └─ Contenido:
│     {
│       "timestamp": "2025-11-11T22:48:26",
│       "packages": [
│         {
│           "name": "requests",
│           "version": "2.28.0",
│           "license": "Apache 2.0",      ← 🎯 AQUÍ EN JSON
│           "aprobada": "Sí",
│           "motivo_rechazo": "Sin problemas detectados",
│           "dependencias_directas": [...],
│           "dependencias_transitivas": [...]
│         }
│       ]
│     }
│
├─ 📊 PASO 8: XLSXReportAdapter
│  ├─ Archivo: src/infrastructure/adapters/xlsx_report_adapter.py
│  ├─ Línea 98: raw_license = pkg.get("license")
│  │  └─ # raw_license = "Apache 2.0"
│  │
│  ├─ Línea 39-76: _short_license()
│  │  └─ def _short_license(raw_license: Any) -> str:
│  │       if "apache" in raw_license.lower():
│  │         return "Apache"  ← 🎯 NORMALIZADA
│  │
│  └─ Línea 108-111: Escribir a XLSX
│     └─ ws['D{}'.format(row)] = "Apache"  ← 🎯 ESCRITA A EXCEL
│
└─ 📈 PASO 9: packages.xlsx
   ├─ Archivo: packages.xlsx
   ├─ Columna: D (Licencia)
   └─ Valor: "Apache"  ← 🎯 RESULTADO FINAL
```

---

## 📍 Matriz: Línea Exacta por Archivo

```
┌─────────────────────────────────────────────────────────────────────┐
│ ARCHIVO                              │ LÍNEA │ QUÉ PASA             │
├─────────────────────────────────────────────────────────────────────┤
│ src/infrastructure/adapters/         │       │                     │
│ pypi_adapter.py                      │ 88-90 │ FETCH desde PyPI    │
│                                      │ 123   │ Extrae license_name │
│                                      │ 139   │ Crea License object │
│                                      │ 168   │ Retorna Package()   │
├─────────────────────────────────────────────────────────────────────┤
│ src/domain/entities/__init__.py      │ 47-51 │ Define License      │
│                                      │ 69-88 │ Define Package      │
│                                      │ 82    │ license field aquí  │
├─────────────────────────────────────────────────────────────────────┤
│ src/application/use_cases/           │ 38    │ self.approval_map   │
│ __init__.py                          │ 120   │ Populate approval   │
│                                      │ 227   │ Extrae .name        │
│                                      │ 228   │ PackageDTO()        │
│                                      │ 233   │ license= en DTO     │
├─────────────────────────────────────────────────────────────────────┤
│ src/application/dtos/__init__.py     │ 80    │ license field DTO   │
├─────────────────────────────────────────────────────────────────────┤
│ src/infrastructure/adapters/         │ 22-39 │ save_report()       │
│ report_adapter.py                    │ 33    │ asdict(result)      │
│                                      │ 39    │ json.dump()         │
├─────────────────────────────────────────────────────────────────────┤
│ consolidated_report.json             │ N/A   │ "license": "Apache" │
├─────────────────────────────────────────────────────────────────────┤
│ src/infrastructure/adapters/         │ 98    │ pkg.get("license")  │
│ xlsx_report_adapter.py               │ 39-76 │ _short_license()    │
│                                      │ 108   │ ws['D'] = value     │
├─────────────────────────────────────────────────────────────────────┤
│ packages.xlsx                        │ D2+   │ Valor final         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Quick Grep Search Commands

Para encontrar la licencia en cada capa:

```bash
# =========== EXTRACCIÓN INICIAL ===========
grep -n "info.get.*license" src/infrastructure/adapters/pypi_adapter.py
# Resultado: 123:        license_name = info.get("license")

# =========== CREACIÓN DE ENTITY ===========
grep -n "class License" src/domain/entities/__init__.py
# Resultado: 47:@dataclass(frozen=True)
#            48:class License:

grep -n "license:" src/domain/entities/__init__.py
# Resultado: 50:    name: Optional[str] = None

# =========== EN PACKAGE ===========
grep -n "license:" src/domain/entities/__init__.py
# Resultado: 82:    license: Optional[License] = None

# =========== MAPEO A DTO ===========
grep -n "package.license.name" src/application/use_cases/__init__.py
# Resultado: 228:        license=package.license.name if package.license else None

# =========== DTO DEFINITION ===========
grep -n "license:" src/application/dtos/__init__.py
# Resultado: 80:    license: Optional[str]

# =========== SERIALIZACIÓN ===========
grep -n "json.dump" src/infrastructure/adapters/report_adapter.py
# Resultado: 39:                json.dump(report_data, f, indent=2, ensure_ascii=False)

# =========== LECTURA DESDE JSON ===========
grep -n 'get("license")' src/infrastructure/adapters/xlsx_report_adapter.py
# Resultado: 98:                raw_license = pkg.get("license") or pkg.get("github_license") or "—"

# =========== NORMALIZACIÓN ===========
grep -n "def _short_license" src/infrastructure/adapters/xlsx_report_adapter.py
# Resultado: 39:            def _short_license(raw_license: Any) -> str:

# =========== EN JSON GUARDADO ===========
grep -n '"license"' consolidated_report.json | head -5
# Resultado: 72:      "license": "Apache 2.0",
# Resultado: 106:      "license": "MIT",
# ... etc
```

---

## 🎯 Localización por Pregunta

### P: "¿Dónde se lee del PyPI?"
**R:** `src/infrastructure/adapters/pypi_adapter.py:123`
```python
license_name = info.get("license")  # ← AQUÍ
```

### P: "¿Dónde se crea la entidad License?"
**R:** `src/infrastructure/adapters/pypi_adapter.py:139`
```python
license_obj = License(name=license_name, license_type=license_type)  # ← AQUÍ
```

### P: "¿Dónde se almacena en Package?"
**R:** `src/domain/entities/__init__.py:82`
```python
license: Optional[License] = None  # ← AQUÍ
```

### P: "¿Dónde se mapea a DTO?"
**R:** `src/application/use_cases/__init__.py:228`
```python
license=package.license.name if package.license else None  # ← AQUÍ
```

### P: "¿Dónde se define en DTO?"
**R:** `src/application/dtos/__init__.py:80`
```python
license: Optional[str]  # ← AQUÍ
```

### P: "¿Dónde se convierte a JSON?"
**R:** `src/infrastructure/adapters/report_adapter.py:39`
```python
json.dump(report_data, f, indent=2, ensure_ascii=False)  # ← AQUÍ
```

### P: "¿Dónde se guarda finalmente?"
**R:** `consolidated_report.json`
```json
"license": "Apache 2.0"  # ← AQUÍ
```

### P: "¿Dónde se normaliza para XLSX?"
**R:** `src/infrastructure/adapters/xlsx_report_adapter.py:39-76`
```python
def _short_license(raw_license: Any) -> str:  # ← AQUÍ
    if "apache" in raw_license.lower():
        return "Apache"
```

---

## 📊 Flujo de Transformación Detallado

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. PyPI API Response (RAW STRING)                                │
│                                                                  │
│   {"info": {"license": "Apache 2.0"}}                            │
│                        ↓                                         │
│                   STRING: "Apache 2.0"                           │
└──────────────────────────────────────────────────────────────────┘
                         ↓
                    [pypi_adapter.py:123]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 2. Domain Entity License (TYPED OBJECT)                          │
│                                                                  │
│   License(                                                       │
│       name="Apache 2.0",                                         │
│       license_type=LicenseType.APACHE_2_0,                       │
│       url=None,                                                  │
│       is_rejected=False                                          │
│   )                                                              │
└──────────────────────────────────────────────────────────────────┘
                         ↓
                    [entities/__init__.py:82]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 3. Domain Entity Package (CONTAINS LICENSE)                      │
│                                                                  │
│   Package(                                                       │
│       identifier=...,                                            │
│       license=License(...),  ← AQUÍ                              │
│       ...                                                        │
│   )                                                              │
└──────────────────────────────────────────────────────────────────┘
                         ↓
                    [use_cases/__init__.py:228]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 4. Application DTO PackageDTO (SERIALIZABLE)                     │
│                                                                  │
│   PackageDTO(                                                    │
│       name="requests",                                           │
│       version="2.28.0",                                          │
│       license="Apache 2.0",  ← STRING AQUÍ                       │
│       aprobada="Sí",                                             │
│       ...                                                        │
│   )                                                              │
└──────────────────────────────────────────────────────────────────┘
                         ↓
                 [report_adapter.py:33]
                    asdict()
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 5. Python Dictionary (DICT)                                      │
│                                                                  │
│   {                                                              │
│       "name": "requests",                                        │
│       "version": "2.28.0",                                       │
│       "license": "Apache 2.0",  ← STRING EN DICT                 │
│       "aprobada": "Sí",                                          │
│       ...                                                        │
│   }                                                              │
└──────────────────────────────────────────────────────────────────┘
                         ↓
                 [report_adapter.py:39]
                    json.dump()
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 6. JSON File (PERSISTED)                                         │
│                                                                  │
│   {                                                              │
│       "packages": [                                              │
│           {                                                      │
│               "name": "requests",                                │
│               "version": "2.28.0",                               │
│               "license": "Apache 2.0",  ← JSON AQUÍ              │
│               "aprobada": "Sí",                                  │
│               ...                                                │
│           }                                                      │
│       ]                                                          │
│   }                                                              │
│                                                                  │
│   Guardar en: consolidated_report.json                           │
└──────────────────────────────────────────────────────────────────┘
                         ↓
           [json.load + xlsx_adapter.py:98]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 7. Normalización para XLSX                                       │
│                                                                  │
│   pkg.get("license")  →  "Apache 2.0"                            │
│   _short_license()    →  "Apache"                                │
└──────────────────────────────────────────────────────────────────┘
                         ↓
           [xlsx_adapter.py:108]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│ 8. XLSX File (FINAL OUTPUT)                                      │
│                                                                  │
│   Columna D (Licencia): "Apache"  ← FINAL AQUÍ                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔗 Relaciones de Dependencia

```
consolidated_report.json
         ↑
         │ (json.dump)
         │
report_adapter.py:39
         ↑
         │ (asdict)
         │
AnalysisResultDTO
         ↑
         │ (packages list)
         │
PackageDTO (license="Apache 2.0")
         ↑
         │ (_package_to_dto)
         │
use_cases/__init__.py:228
         ↑
         │ (package.license.name)
         │
Package.license (License entity)
         ↑
         │ (field)
         │
entities/__init__.py:82
         ↑
         │ (contains)
         │
License (name="Apache 2.0")
         ↑
         │ (created at)
         │
pypi_adapter.py:139
         ↑
         │ (info.get("license"))
         │
PyPI API Response
         ↑
         │
https://pypi.org/pypi/requests/2.28.0/json
```

---

## ✅ Checklist: Verificar Todo el Flujo

```
Paso 1: PyPI API
  [ ] ¿Devuelve JSON con "license" field?
      curl https://pypi.org/pypi/requests/2.28.0/json | grep '"license"'

Paso 2: pypi_adapter.py
  [ ] ¿Se extrae license_name?
      Breakpoint en línea 123

Paso 3: License Entity
  [ ] ¿Se crea License object?
      Breakpoint en línea 139

Paso 4: Package Entity
  [ ] ¿Se almacena license en Package?
      Breakpoint en línea 168

Paso 5: UseCase DTO
  [ ] ¿Se mapea license_value?
      Breakpoint en línea 228

Paso 6: ReportDTO
  [ ] ¿Se incluye en PackageDTO?
      Ver AnalysisResultDTO.packages

Paso 7: report_adapter.py
  [ ] ¿Se convierte con asdict()?
      Ver report_data dict

Paso 8: consolidated_report.json
  [ ] ¿Está "license" en JSON?
      grep '"license"' consolidated_report.json

Paso 9: XLSXAdapter
  [ ] ¿Se normaliza correctamente?
      Breakpoint en _short_license()

Paso 10: packages.xlsx
  [ ] ¿Aparece en columna D?
      Abrir archivo con openpyxl
```

---

## 💾 Resumen: Dónde Buscar

| Necesito... | Buscar en... | Línea |
|------------|---|---|
| Entender visión general | LICENSE_EXTRACTION_FLOW.md | N/A |
| Localización exacta | LICENSE_EXTRACTION_DETAILED.md | N/A |
| Ejemplo real | LICENSE_EXTRACTION_EXAMPLE.md | N/A |
| Mapa visual | AQUÍ (LICENSE_EXTRACTION_MAP.md) | N/A |
| Código: Extracción | pypi_adapter.py | 123 |
| Código: Domain | entities/__init__.py | 47-82 |
| Código: DTO | dtos/__init__.py | 80 |
| Código: Mapeo | use_cases/__init__.py | 228 |
| Código: JSON | report_adapter.py | 39 |
| Código: XLSX | xlsx_report_adapter.py | 39-76, 98 |
| Salida JSON | consolidated_report.json | N/A |
| Salida XLSX | packages.xlsx | D2+ |

