# 🎯 Localización Exacta: Dónde se Extrae la Licencia

## Quick Reference: Búsqueda Rápida por Capa

### 1️⃣ INFRASTRUCTURE LAYER: Obtención desde PyPI
**ARCHIVO:** `src/infrastructure/adapters/pypi_adapter.py`

**LÍNEA 88-90:** Fetch desde API
```python
async def _fetch_pypi_metadata(self, package_name: str, version: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata from PyPI API."""
    url = f"{self.settings.pypi_base_url}/{package_name}/{version}/json"
    # ↓ Esta URL retorna JSON con "info": { "license": "..." }
```

**LÍNEA 123-145:** Parseado y creación de License entity
```python
def _merge_pypi_data(self, package: Package, pypi_data: Dict[str, Any]) -> Package:
    """Merge PyPI data into package."""
    info = pypi_data.get("info") or {}  # ← ACCESO A PAYLOAD
    
    # Parse license information
    license_name = info.get("license")      # ← EXTRAE AQUÍ
    license_type = None
    license_obj = None
    
    # Ensure license_name is a non-empty string before parsing
    if isinstance(license_name, str) and license_name.strip():
        license_type = self._parse_license_type(license_name)  # ← Normaliza
        license_obj = License(name=license_name, license_type=license_type)
    
    # ... más código ...
    
    return Package(
        identifier=package.identifier,
        license=license_obj,                # ← GUARDADO EN DOMAIN
        upload_time=upload_time,
        summary=summary_value,
        # ... más campos
    )
```

**Qué entra:**
```
PyPI JSON Response:
{
  "info": {
    "license": "Apache 2.0",       ← AQUÍ
    "name": "requests",
    ...
  }
}
```

**Qué sale:**
```
Package(
  license=License(
    name="Apache 2.0",
    license_type=LicenseType.APACHE_2_0,
    url=None,
    is_rejected=False
  )
)
```

---

### 2️⃣ DOMAIN LAYER: Almacenamiento en Entidad
**ARCHIVO:** `src/domain/entities/__init__.py`

**LÍNEA 47-51:** Definición de License entity
```python
@dataclass(frozen=True)
class License:
    """Value object representing a software license."""
    name: Optional[str] = None              # ← AQUÍ: "Apache 2.0", "MIT", etc.
    license_type: Optional[LicenseType] = None
    url: Optional[str] = None
    is_rejected: bool = False
```

**LÍNEA 69-88:** Almacenamiento en Package entity
```python
@dataclass
class Package:
    """Domain entity representing a software package."""
    identifier: PackageIdentifier
    license: Optional[License] = None       # ← AQUÍ: License object completo
    upload_time: Optional[datetime] = None
    summary: Optional[str] = None
    # ... más campos
```

**Estado del dato:**
```
Package {
  identifier: PackageIdentifier(name="requests", version="2.28.0"),
  license: License(name="Apache 2.0", license_type=APACHE_2_0),
  upload_time: 2022-07-28T10:23:45,
  ...
}
```

---

### 3️⃣ APPLICATION LAYER (DTO): Conversión para Serialización
**ARCHIVO:** `src/application/dtos/__init__.py`

**LÍNEA 60-95:** Definición de PackageDTO
```python
@dataclass(frozen=True)
class PackageDTO:
    """Application DTO for package data."""
    name: str
    version: str
    license: Optional[str]                  # ← AQUÍ: String, no License object
    upload_time: Optional[datetime]
    summary: Optional[str]
    home_page: Optional[str]
    # ... más campos
    aprobada: str
    motivo_rechazo: Optional[str]
    dependencias_directas: List[str]
    dependencias_transitivas: List[str]
```

---

### 4️⃣ APPLICATION LAYER (USE CASE): Mapeo Domain → DTO
**ARCHIVO:** `src/application/use_cases/__init__.py`

**LÍNEA 223-260:** Método _package_to_dto()
```python
def _package_to_dto(self, package: Package) -> PackageDTO:
    """Convert domain package to DTO, enriched with approval info."""
    pkg_name = package.identifier.name
    
    # Get approval info if available
    approval_info = self.approval_map.get(pkg_name)
    
    # ↓ EXTRAE LA LICENCIA DEL DOMAIN PACKAGE
    license_value = package.license.name if package.license else None
    # ↑ Si package.license existe, extrae .name; si no, None
    
    aprobada = approval_info.aprobada if approval_info else "En verificación"
    motivo_rechazo = approval_info.motivo_rechazo if approval_info else None
    
    return PackageDTO(
        name=package.identifier.name,
        version=package.identifier.version,
        license=license_value,              # ← AGREGA AQUÍ al DTO
        upload_time=package.upload_time,
        summary=package.summary,
        home_page=package.home_page,
        author=package.author,
        # ... más campos
        aprobada=aprobada,
        motivo_rechazo=motivo_rechazo,
        dependencias_directas=dependencias_directas,
        dependencias_transitivas=dependencias_transitivas
    )
```

**Transformación:**
```
Domain Package.license:
  License(name="Apache 2.0", license_type=APACHE_2_0)
         ↓
DTO:
  PackageDTO(license="Apache 2.0")
```

---

### 5️⃣ INFRASTRUCTURE LAYER (ADAPTER): Serialización a JSON
**ARCHIVO:** `src/infrastructure/adapters/report_adapter.py`

**LÍNEA 22-39:** Método save_report()
```python
async def save_report(self, result, format_type: str = "json") -> str:
    """Save analysis result or report DTO to file system."""
    output_path = self.settings.output_path
    
    try:
        # Support both domain AnalysisResult and dataclass ReportDTO
        if is_dataclass(result):
            # Convert dataclass to plain dict (ReportDTO -> serializable dict)
            report_data = asdict(result)    # ← AQUÍ se convierte TODO a dict
            # ↑ Esto incluye los PackageDTO, que incluyen el campo "license"
        else:
            # ... fallback para domain objects
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type.lower() == "json":
                json.dump(report_data, f, indent=2, ensure_ascii=False)  # ← GUARDADO A DISCO
            # ↑ Aquí se serializa el diccionario, incluyendo "license": "Apache 2.0"
```

**Resultado en JSON:**
```json
{
  "packages": [
    {
      "name": "requests",
      "version": "2.28.0",
      "license": "Apache 2.0",          ← AQUÍ LLEGA
      "upload_time": "2022-07-28T10:23:45",
      "aprobada": "Sí",
      "motivo_rechazo": "Sin problemas detectados",
      ...
    }
  ]
}
```

---

### 6️⃣ PERSISTENCE: Archivo JSON
**ARCHIVO:** `consolidated_report.json`

```json
{
  "timestamp": "2025-11-11T22:48:26",
  "packages": [
    {
      "name": "requests",
      "version": "2.28.0",
      "license": "Apache 2.0",            ← LICENCIA GUARDADA
      "upload_time": "2022-07-28T10:23:45",
      "summary": "A simple, yet elegant HTTP Library for Python",
      "home_page": "https://requests.readthedocs.io",
      "author": "Kenneth Reitz",
      "author_email": "me@kennethreitz.org",
      "maintainer": null,
      "maintainer_email": null,
      "keywords": null,
      "classifiers": [...],
      "requires_dist": ["charset-normalizer", ...],
      "project_urls": {...},
      "github_url": "https://github.com/psf/requests",
      "github_license": "Apache 2.0",
      "dependencies": ["charset-normalizer", ...],
      "is_maintained": true,
      "license_rejected": false,
      "aprobada": "Sí",
      "motivo_rechazo": "Sin problemas detectados",
      "dependencias_directas": ["charset-normalizer", "idna", ...],
      "dependencias_transitivas": [...]
    }
  ]
}
```

---

### 7️⃣ PRESENTATION: XLSX Report
**ARCHIVO:** `src/infrastructure/adapters/xlsx_report_adapter.py`

**LÍNEA 39-76:** Método _short_license()
```python
def _short_license(raw_license: Any) -> str:
    """Normalize license to short form for display."""
    if not raw_license:
        return "—"
    
    if not isinstance(raw_license, str):
        return "—"
    
    text = raw_license.lower()
    
    # Check common licenses
    if "mit" in text:
        return "MIT"
    elif "apache" in text:
        return "Apache"
    elif "bsd" in text:
        return "BSD"
    # ... más licenses
```

**LÍNEA 98:** Lectura desde JSON
```python
raw_license = pkg.get("license") or pkg.get("github_license") or "—"
# ↑ Lee el campo "license" del JSON cargado
```

**LÍNEA 99:** Normalización
```python
short = _short_license(raw_license)
# ↑ Convierte "Apache 2.0" → "Apache"
```

**LÍNEA 108-111:** Escritura a XLSX
```python
ws['D{}'] = short  # ← Columna "Licencia"
# ↑ Escribe "Apache" en el XLSX
```

---

## 📊 Matriz de Transformaciones

```
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 1: EXTRACCIÓN INICIAL                                          │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    src/infrastructure/adapters/pypi_adapter.py:123          │
│ Función:  _merge_pypi_data()                                        │
│ Entrada:  pypi_data["info"]["license"] = "Apache 2.0"              │
│ Acción:   license_name = info.get("license")                        │
│ Salida:   License(name="Apache 2.0", license_type=APACHE_2_0)      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 2: ALMACENAMIENTO EN DOMINIO                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    src/domain/entities/__init__.py:47-88                     │
│ Estructu: class License, class Package                               │
│ Entrada:  License(name="Apache 2.0", ...)                           │
│ Acción:   Package.license = license_obj                             │
│ Salida:   Package(..., license=License(...))                        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 3: MAPEO A DTO                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    src/application/use_cases/__init__.py:228                │
│ Función:  _package_to_dto()                                         │
│ Entrada:  package.license = License(...)                            │
│ Acción:   license_value = package.license.name                      │
│ Salida:   PackageDTO(license="Apache 2.0", ...)                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 4: SERIALIZACIÓN A JSON                                        │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    src/infrastructure/adapters/report_adapter.py:33         │
│ Función:  save_report() + asdict()                                  │
│ Entrada:  PackageDTO(license="Apache 2.0", ...)                    │
│ Acción:   report_data = asdict(report)                              │
│           json.dump(report_data, f)                                 │
│ Salida:   {"license": "Apache 2.0"} en JSON                         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 5: LECTURA DESDE PERSISTENCIA                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    consolidated_report.json                                  │
│ Formato:  JSON                                                      │
│ Contenido:{"license": "Apache 2.0", "aprobada": "Sí", ...}         │
│ Acceso:   pkg.get("license") o pkg["license"]                       │
│ Valor:    "Apache 2.0"                                              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 6: NORMALIZACIÓN PARA XLSX                                     │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    src/infrastructure/adapters/xlsx_report_adapter.py:39    │
│ Función:  _short_license()                                          │
│ Entrada:  raw_license = "Apache 2.0"                                │
│ Acción:   if "apache" in text: return "Apache"                      │
│ Salida:   "Apache"                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 7: ESCRITURA A XLSX                                            │
├─────────────────────────────────────────────────────────────────────┤
│ Lugar:    packages.xlsx                                             │
│ Columna:  D (Licencia)                                              │
│ Valor:    "Apache"                                                  │
│ Formato:  Excel cell                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Grep Quick Commands

Para encontrar dónde se usa la licencia:

```bash
# 1. Encontrar extracción inicial
grep -n "info.get.*license" src/infrastructure/adapters/pypi_adapter.py

# 2. Encontrar creación de License entity
grep -n "class License" src/domain/entities/__init__.py

# 3. Encontrar mapeo a DTO
grep -n "package.license" src/application/use_cases/__init__.py

# 4. Encontrar serialización
grep -n "json.dump" src/infrastructure/adapters/report_adapter.py

# 5. Encontrar uso en XLSX
grep -n "_short_license" src/infrastructure/adapters/xlsx_report_adapter.py

# 6. Encontrar en consolidated.json
grep -n '"license"' consolidated_report.json
```

---

## 🎬 Ejecución Paso a Paso

### Scenario: Analizar package "requests@2.28.0"

```
1. CLI: python -m src.interface.cli
   ↓
2. AnalyzePackagesUseCase.execute()
   ↓
3. MetadataProviderPort.enrich_package_metadata()
   ↓
4. PyPIClientAdapter._fetch_pypi_metadata("requests", "2.28.0")
   → Retorna: {"info": {"license": "Apache 2.0", ...}, ...}
   ↓
5. PyPIClientAdapter._merge_pypi_data()
   → license_name = "Apache 2.0"
   → license_obj = License(name="Apache 2.0", ...)
   → return Package(..., license=license_obj)
   ↓
6. AnalyzePackagesUseCase._package_to_dto()
   → license_value = "Apache 2.0"
   → return PackageDTO(license="Apache 2.0", ...)
   ↓
7. ReportDTO construido con PackageDTO
   ↓
8. FileReportSinkAdapter.save_report()
   → asdict(ReportDTO) = {..., "packages": [..., {"license": "Apache 2.0", ...}, ...]}
   → json.dump() → consolidated_report.json
   ↓
9. XLSXReportAdapter.generate_xlsx()
   → pkg.get("license") = "Apache 2.0"
   → _short_license("Apache 2.0") = "Apache"
   → ws['D...'] = "Apache"
   ↓
10. packages.xlsx generado con columna "Licencia": "Apache"
```

---

## ✅ Validación: Verificar que todo esté correcto

### Test 1: Verificar JSON
```bash
python -c "import json; data = json.load(open('consolidated_report.json')); print(data['packages'][0]['license'])"
# Debe imprimir: "Apache 2.0" (o el nombre de la licencia)
```

### Test 2: Verificar XLSX
```bash
python -c "from openpyxl import load_workbook; wb = load_workbook('packages.xlsx'); ws = wb.active; print(ws['D2'].value)"
# Debe imprimir: "Apache" (normalizada)
```

### Test 3: Verificar Domain Entity
```bash
# Buscar en pypi_adapter.py línea 140-145:
# license_obj = License(name=license_name, license_type=license_type)
# Debe encontrarse la creación del License object
```

