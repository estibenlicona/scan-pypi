# 🔍 Flujo de Extracción de Licencia

## Resumen Ejecutivo
La licencia se extrae desde **PyPI API**, se enriquece en el **Domain**, se mapea en **DTOs**, y finalmente se serializa en el **consolidated_report.json**.

---

## 1. ORIGEN: PyPI API
**Archivo:** `src/infrastructure/adapters/pypi_adapter.py` (línea 123)

### 1.1 Fetch desde PyPI
```python
async def _fetch_pypi_metadata(self, package_name: str, version: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata from PyPI API."""
    url = f"{self.settings.pypi_base_url}/{package_name}/{version}/json"
    # ↓ Retorna: { "info": { "license": "MIT", ... }, "urls": [...] }
```

**URL ejemplo:** `https://pypi.org/pypi/requests/2.28.0/json`

**Estructura PyPI:**
```json
{
  "info": {
    "name": "requests",
    "version": "2.28.0",
    "license": "Apache 2.0",           // ← AQUÍ ESTÁ LA LICENCIA
    "home_page": "https://requests.readthedocs.io",
    "author": "Kenneth Reitz",
    "classifiers": [...],
    ...
  },
  "urls": [
    {
      "upload_time": "2022-07-28T10:23:45",
      ...
    }
  ]
}
```

---

## 2. PARSING: Creación de Domain Entity `License`
**Archivo:** `src/infrastructure/adapters/pypi_adapter.py` (línea 139-145)

### 2.1 Extracción y Tipificación
```python
def _merge_pypi_data(self, package: Package, pypi_data: Dict[str, Any]) -> Package:
    info = pypi_data.get("info") or {}
    
    # Parse license information
    license_name = info.get("license")                    # ← Extrae string
    license_type = None
    license_obj = None
    
    if isinstance(license_name, str) and license_name.strip():
        license_type = self._parse_license_type(license_name)    # ← SPDX/Common licenses
        license_obj = License(
            name=license_name,                            # ← "Apache 2.0", "MIT", etc.
            license_type=license_type                     # ← LicenseType enum
        )
```

### 2.2 Domain Entity `License`
**Archivo:** `src/domain/entities/__init__.py` (línea 47-51)

```python
@dataclass(frozen=True)
class License:
    """Value object representing a software license."""
    name: Optional[str] = None           # ← "MIT", "Apache-2.0", etc.
    license_type: Optional[LicenseType] = None    # ← Enum normalizador
    url: Optional[str] = None
    is_rejected: bool = False
```

---

## 3. ENRIQUECIMIENTO: Domain Entity `Package` con License
**Archivo:** `src/infrastructure/adapters/pypi_adapter.py` (línea 168-180)

### 3.1 Retorna Package enriquecido
```python
return Package(
    identifier=package.identifier,
    license=license_obj,                  # ← License object creado arriba
    upload_time=upload_time,
    summary=summary_value,
    home_page=home_page_value,
    author=author_value,
    # ... más campos
)
```

**En Domain Package:**
```python
@dataclass
class Package:
    identifier: PackageIdentifier
    license: Optional[License] = None     # ← STORED HERE
    upload_time: Optional[datetime] = None
    # ... más campos
```

---

## 4. MAPEO: Domain → Application DTOs
**Archivo:** `src/application/use_cases/__init__.py` (línea 223-260)

### 4.1 Método `_package_to_dto`
```python
def _package_to_dto(self, package: Package) -> PackageDTO:
    """Convert domain package to DTO, enriched with approval info."""
    # ↓ Extrae la licencia del domain Package
    license_value = package.license.name if package.license else None
    
    return PackageDTO(
        name=package.identifier.name,
        version=package.identifier.version,
        license=license_value,             # ← "MIT", "Apache-2.0", None, etc.
        upload_time=package.upload_time,
        # ... más campos
        aprobada=aprobada,
        motivo_rechazo=motivo_rechazo,
        # ... approval fields
    )
```

### 4.2 PackageDTO Definition
**Archivo:** `src/application/dtos/__init__.py`

```python
@dataclass(frozen=True)
class PackageDTO:
    name: str
    version: str
    license: Optional[str]                # ← Aquí entra: "MIT"
    upload_time: Optional[datetime]
    summary: Optional[str]
    home_page: Optional[str]
    author: Optional[str]
    # ... más campos
    aprobada: str                         # ← Approval status
    motivo_rechazo: Optional[str]         # ← Approval reason
    dependencias_directas: List[str]
    dependencias_transitivas: List[str]
```

---

## 5. SERIALIZACIÓN: DTO → JSON
**Archivo:** `src/infrastructure/adapters/report_adapter.py` (línea 33-39)

### 5.1 Conversión asdict()
```python
async def save_report(self, result, format_type: str = "json") -> str:
    if is_dataclass(result):
        # Convert dataclass to plain dict (ReportDTO -> serializable dict)
        report_data = asdict(result)      # ← Convierte TODOS los fields
```

### 5.2 Guardado JSON
```python
    with open(output_path, 'w', encoding='utf-8') as f:
        if format_type.lower() == "json":
            json.dump(report_data, f, indent=2, ensure_ascii=False)  # ← AQUÍ SE GUARDA
```

**Output:** `consolidated_report.json`

---

## 6. RESULTADO: JSON Final
**Archivo:** `consolidated_report.json`

```json
{
  "packages": [
    {
      "name": "requests",
      "version": "2.28.0",
      "license": "Apache 2.0",            // ← LA LICENCIA AQUÍ
      "upload_time": "2022-07-28T10:23:45",
      "summary": "A simple, yet elegant HTTP Library for Python",
      "home_page": "https://requests.readthedocs.io",
      "author": "Kenneth Reitz",
      "aprobada": "Sí",
      "motivo_rechazo": "Sin problemas detectados",
      "dependencias_directas": ["charset-normalizer", "idna", ...],
      "dependencias_transitivas": [...]
    },
    {
      "name": "some-package",
      "version": "1.0.0",
      "license": null,                    // ← Sin licencia
      "aprobada": "En verificación",
      "motivo_rechazo": "⚠ Falta Licencia",
      // ... más campos
    }
  ]
}
```

---

## 7. VALIDACIÓN: XLSX Report
**Archivo:** `src/infrastructure/adapters/xlsx_report_adapter.py` (línea 98)

### 7.1 Uso en Reporte XLSX
```python
raw_license = pkg.get("license") or pkg.get("github_license") or "—"
# ↓ Aplica _short_license() para normalizar
short = _short_license(raw_license)
# ↓ Agrega a columna "Licencia" del XLSX
```

---

## 🎯 Diagrama Completo del Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│                      PyPI API                                   │
│  https://pypi.org/pypi/requests/2.28.0/json                    │
│  → info.license = "Apache 2.0"                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│          PyPIClientAdapter._merge_pypi_data()                   │
│  - Extrae: license_name = "Apache 2.0"                          │
│  - Tipifica: license_type = LicenseType.APACHE_2_0              │
│  - Crea: License(name="Apache 2.0", license_type=...)           │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              Domain Entity: Package                             │
│  - identifier: PackageIdentifier                                │
│  - license: License(name="Apache 2.0", ...)                     │
│  - upload_time, summary, author, ...                            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│         AnalyzePackagesUseCase._package_to_dto()                │
│  - Extrae: license_value = package.license.name                 │
│  - Crea DTO: PackageDTO(license="Apache 2.0", ...)              │
│  - Agrega: aprobada, motivo_rechazo, dependencias...            │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│         ReportDTO with PackageDTO list                          │
│  - packages: [                                                  │
│    {license: "Apache 2.0", aprobada: "Sí", ...},                │
│    {license: null, aprobada: "En verificación", ...}            │
│  ]                                                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│   FileReportSinkAdapter.save_report()                           │
│  - asdict(report_data) → JSON serializable dict                 │
│  - json.dump(...) → consolidated_report.json                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│          consolidated_report.json                               │
│  {                                                              │
│    "packages": [                                                │
│      {                                                          │
│        "name": "requests",                                      │
│        "version": "2.28.0",                                     │
│        "license": "Apache 2.0",  ← AQUÍ ESTÁ                    │
│        "aprobada": "Sí",                                        │
│        "motivo_rechazo": "Sin problemas detectados"             │
│      }                                                          │
│    ]                                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│          XLSXReportAdapter.generate_xlsx()                      │
│  - Lee: pkg.get("license")                                      │
│  - Normaliza: _short_license("Apache 2.0")                      │
│  - Columna "Licencia": "Apache 2.0"                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Tabla Resumen: Transformaciones de Licencia

| Layer | Clase | Campo | Tipo | Valor Ejemplo |
|-------|-------|-------|------|---------------|
| **Infrastructure** | PyPIClientAdapter | `info.get("license")` | `str` | `"Apache 2.0"` |
| **Domain** | License | `name` | `str` | `"Apache 2.0"` |
| **Domain** | License | `license_type` | `LicenseType` | `APACHE_2_0` |
| **Domain** | Package | `license` | `License` | `License(...)` |
| **Application** | PackageDTO | `license` | `str \| None` | `"Apache 2.0"` |
| **Persistence** | JSON | `"license"` | `string \| null` | `"Apache 2.0"` |
| **Presentation** | XLSX | Columna "Licencia" | `str` | `"Apache 2.0"` |

---

## 🔑 Puntos Clave

### ¿Dónde se inicializa la licencia?
**→ PyPIClientAdapter._merge_pypi_data()** (línea 139-145)

### ¿Dónde se guarda en el consolidated?
**→ FileReportSinkAdapter.save_report()** con asdict() + json.dump() (línea 33-39)

### ¿Cómo se usa en aprobación?
**→ ApprovalEngine.evaluate_package_approval()** valida si `package_info.license` está presente o es None

### ¿Dónde se normaliza para XLSX?
**→ XLSXReportAdapter._short_license()** (línea 39-76) maneja:
- MIT, Apache, BSD, GPL, ISC, Unlicense, etc.
- Extrae primer nombre si es multiline
- Retorna "—" si está vacío

---

## 💡 Ejemplo Práctico: Rastrear una Licencia

### Entrada: Package "requests"
```
1. PyPI API devuelve: "license": "Apache 2.0"
```

### Procesamiento
```
2. PyPIClientAdapter extrae y crea:
   License(name="Apache 2.0", license_type=LicenseType.APACHE_2_0)

3. Package contiene:
   Package(..., license=License(...))

4. AnalyzePackagesUseCase convierte a DTO:
   PackageDTO(license="Apache 2.0", ...)
```

### Salida Final
```
5. consolidated_report.json:
   { "license": "Apache 2.0", "aprobada": "Sí", ... }

6. packages.xlsx:
   Columna Licencia: "Apache 2.0"
```

---

## 🐛 Debugging: Si la licencia es NULL

1. **Verificar JSON inicial de PyPI:**
   ```bash
   curl https://pypi.org/pypi/PACKAGE_NAME/VERSION/json | grep -A 2 '"license"'
   ```

2. **Verificar Domain Package:**
   - Breakpoint en `pypi_adapter.py:145`
   - Ver si `license_obj` está creándose

3. **Verificar DTO:**
   - Breakpoint en `use_cases/__init__.py:228`
   - Ver si `license_value` está siendo extraída

4. **Verificar JSON guardado:**
   - Abrir `consolidated_report.json`
   - Buscar paquete y ver campo `"license"`

