# 🎥 Ejemplo Real: Rastrear Licencia de "requests"

## Escenario: Analizar package requests@2.28.0

### 📍 PASO 1: PyPI API Fetch
**Archivo:** `src/infrastructure/adapters/pypi_adapter.py:88-102`

```python
# pypi_adapter.py

async def _fetch_pypi_metadata(self, package_name: str, version: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata from PyPI API."""
    url = f"{self.settings.pypi_base_url}/{package_name}/{version}/json"
    # ↓ URL real construida:
    # https://pypi.org/pypi/requests/2.28.0/json
    
    async with aiohttp.ClientSession(...) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
```

**Respuesta de PyPI (parcial):**
```json
{
  "info": {
    "name": "requests",
    "version": "2.28.0",
    "license": "Apache 2.0",           ← 🎯 AQUÍ ESTÁ LA LICENCIA
    "home_page": "https://requests.readthedocs.io",
    "author": "Kenneth Reitz",
    "summary": "A simple, yet elegant HTTP Library for Python",
    "classifiers": [
      "Development Status :: 5 - Production/Stable",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: Apache Software License"
    ]
  },
  "urls": [
    {
      "url": "https://files.pythonhosted.org/packages/.../requests-2.28.0.tar.gz",
      "filename": "requests-2.28.0.tar.gz",
      "size": 61621,
      "upload_time": "2022-07-28T10:23:45",
      "upload_time_iso_8601": "2022-07-28T10:23:45.670000Z",
      "digests": {...}
    }
  ]
}
```

**Output de _fetch_pypi_metadata():**
```python
{
    "info": {
        "name": "requests",
        "version": "2.28.0",
        "license": "Apache 2.0",     ← Se retorna completo
        ...
    },
    "urls": [...]
}
```

---

### 📍 PASO 2: Parsing en Domain
**Archivo:** `src/infrastructure/adapters/pypi_adapter.py:123-150`

```python
# pypi_adapter.py - _merge_pypi_data() method

def _merge_pypi_data(self, package: Package, pypi_data: Dict[str, Any]) -> Package:
    """Merge PyPI data into package."""
    info = pypi_data.get("info") or {}  # ← ACCESO AL PAYLOAD
    
    # Parse license information
    license_name = info.get("license")       # ← EXTRAE: "Apache 2.0"
    license_type = None
    license_obj = None
    
    # Ensure license_name is a non-empty string before parsing to satisfy type checkers
    if isinstance(license_name, str) and license_name.strip():  # ✓ "Apache 2.0" pasa el test
        license_type = self._parse_license_type(license_name)  # ← NORMALIZA
        # _parse_license_type("Apache 2.0") → LicenseType.APACHE_2_0
        
        license_obj = License(                # ← CREA DOMAIN ENTITY
            name="Apache 2.0",
            license_type=LicenseType.APACHE_2_0,
            url=None,
            is_rejected=False
        )
    
    # Parse upload time
    upload_time = None
    if "urls" in pypi_data and pypi_data["urls"]:
        upload_time_str = pypi_data["urls"][0].get("upload_time")
        if upload_time_str:
            try:
                upload_time = datetime.fromisoformat(upload_time_str.replace('Z', '+00:00'))
                # "2022-07-28T10:23:45" → datetime object
            except ValueError:
                pass
    
    # ... más fields ...
    
    return Package(
        identifier=PackageIdentifier(name="requests", version="2.28.0"),
        license=License(
            name="Apache 2.0",              ← ALMACENADO EN DOMAIN
            license_type=LicenseType.APACHE_2_0,
            url=None,
            is_rejected=False
        ),
        upload_time=datetime(2022, 7, 28, 10, 23, 45),
        summary="A simple, yet elegant HTTP Library for Python",
        home_page="https://requests.readthedocs.io",
        author="Kenneth Reitz",
        # ... más fields ...
        dependencies=[PackageIdentifier("charset-normalizer", "..."), ...]
    )
```

**Domain Entity Creada:**
```python
Package(
    identifier=PackageIdentifier(
        name="requests",
        version="2.28.0"
    ),
    license=License(
        name="Apache 2.0",                  ← ⭐ LICENCIA EN DOMAIN
        license_type=LicenseType.APACHE_2_0,
        url=None,
        is_rejected=False
    ),
    upload_time=datetime(2022, 7, 28, 10, 23, 45),
    summary="A simple, yet elegant HTTP Library for Python",
    home_page="https://requests.readthedocs.io",
    author="Kenneth Reitz",
    author_email=None,
    maintainer=None,
    # ... más fields ...
)
```

---

### 📍 PASO 3: Transformación a DTO
**Archivo:** `src/application/use_cases/__init__.py:223-260`

```python
# use_cases/__init__.py - _package_to_dto() method

def _package_to_dto(self, package: Package) -> PackageDTO:
    """Convert domain package to DTO, enriched with approval info."""
    pkg_name = package.identifier.name  # "requests"
    
    # Get approval info if available
    approval_info = self.approval_map.get(pkg_name)
    # approval_map["requests"] = PackageInfo(
    #     name="requests",
    #     aprobada="Sí",
    #     motivo_rechazo="Sin problemas detectados",
    #     dependencias_directas=["charset-normalizer", ...],
    #     dependencias_transitivas=[...]
    # )
    
    # ⭐ EXTRAE LA LICENCIA DEL DOMAIN PACKAGE
    license_value = package.license.name if package.license else None
    # package.license = License(name="Apache 2.0", ...)
    # license_value = "Apache 2.0"
    
    aprobada = approval_info.aprobada if approval_info else "En verificación"
    # aprobada = "Sí"
    
    motivo_rechazo = approval_info.motivo_rechazo if approval_info else None
    # motivo_rechazo = "Sin problemas detectados"
    
    dependencias_directas = approval_info.dependencias_directas if approval_info else []
    # dependencias_directas = ["charset-normalizer", "idna", "urllib3"]
    
    dependencias_transitivas = approval_info.dependencias_transitivas if approval_info else []
    # dependencias_transitivas = [...]
    
    return PackageDTO(
        name="requests",
        version="2.28.0",
        license="Apache 2.0",               ← ⭐ LICENCIA EN DTO
        upload_time=datetime(2022, 7, 28, 10, 23, 45),
        summary="A simple, yet elegant HTTP Library for Python",
        home_page="https://requests.readthedocs.io",
        author="Kenneth Reitz",
        author_email=None,
        maintainer=None,
        maintainer_email=None,
        keywords=None,
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License"
        ],
        requires_dist=[
            "charset-normalizer (>=2,<3)",
            "idna (>=2.5,<4)",
            "urllib3 (>=1.21.1,<1.27)"
        ],
        project_urls={
            "Documentation": "https://requests.readthedocs.io",
            "Source": "https://github.com/psf/requests"
        },
        github_url="https://github.com/psf/requests",
        github_license="Apache 2.0",
        dependencies=["charset-normalizer", "idna", "urllib3"],
        is_maintained=True,
        license_rejected=False,
        aprobada="Sí",
        motivo_rechazo="Sin problemas detectados",
        dependencias_directas=["charset-normalizer", "idna", "urllib3"],
        dependencias_transitivas=[...]
    )
```

---

### 📍 PASO 4: Construcción de ReportDTO
**Archivo:** `src/application/use_cases/__init__.py:200-220`

```python
# use_cases/__init__.py - _to_dto() method

def _to_dto(self, result: AnalysisResult) -> AnalysisResultDTO:
    """Convert analysis result to DTO."""
    # ... conversión de vulnerabilidades ...
    
    # Convert packages
    packages_dtos = [self._package_to_dto(pkg) for pkg in result.get_all_packages()]
    # packages_dtos[0] es el PackageDTO creado en PASO 3
    
    # Convert maintained packages
    maintained_dtos = [self._package_to_dto(pkg) for pkg in result.maintained_packages]
    # maintained_dtos[0] también es el PackageDTO de requests
    
    return AnalysisResultDTO(
        timestamp=datetime.now(),
        vulnerabilities=[...],      # Vulnerabilidades encontradas
        packages=[                  # ← TODOS los packages
            PackageDTO(
                name="requests",
                version="2.28.0",
                license="Apache 2.0",   ← ⭐ INCLUIDA AQUÍ
                upload_time=...,
                aprobada="Sí",
                motivo_rechazo="Sin problemas detectados",
                dependencias_directas=[...],
                dependencias_transitivas=[...],
                # ... más fields ...
            ),
            # ... más packages ...
        ],
        maintained_packages=[...],  # Filtered packages
        policy_applied="default"
    )
```

**ReportDTO Structure:**
```python
AnalysisResultDTO(
    timestamp=datetime(...),
    vulnerabilities=[...],
    packages=[
        PackageDTO(
            name="requests",
            version="2.28.0",
            license="Apache 2.0",      ← DENTRO DEL DTO
            upload_time=datetime(...),
            summary="...",
            aprobada="Sí",
            motivo_rechazo="Sin problemas detectados",
            dependencias_directas=["charset-normalizer", "idna", "urllib3"],
            dependencias_transitivas=[...],
            # ... más fields ...
        ),
        # ... más packages ...
    ],
    maintained_packages=[...],
    policy_applied="default"
)
```

---

### 📍 PASO 5: Serialización a JSON
**Archivo:** `src/infrastructure/adapters/report_adapter.py:22-46`

```python
# report_adapter.py - save_report() method

async def save_report(self, result, format_type: str = "json") -> str:
    """Save analysis result or report DTO to file system."""
    output_path = self.settings.output_path  # "consolidated_report.json"
    
    try:
        # Support both domain AnalysisResult and dataclass ReportDTO
        if is_dataclass(result):
            # Convert dataclass to plain dict (ReportDTO -> serializable dict)
            report_data = asdict(result)  # ← 🎯 AQUÍ OCURRE LA MAGIA
            # Esto convierte:
            # AnalysisResultDTO → Dict[str, Any]
            # 
            # Resultado:
            # {
            #     "timestamp": "2025-11-11T22:48:26.123456",
            #     "vulnerabilities": [...],
            #     "packages": [
            #         {
            #             "name": "requests",
            #             "version": "2.28.0",
            #             "license": "Apache 2.0",        ← ⭐ CONVERTIDA A STRING
            #             "upload_time": "2022-07-28T10:23:45",
            #             "summary": "A simple, yet elegant HTTP Library...",
            #             "aprobada": "Sí",
            #             "motivo_rechazo": "Sin problemas detectados",
            #             "dependencias_directas": ["charset-normalizer", "idna", "urllib3"],
            #             "dependencias_transitivas": [...],
            #             ... más fields ...
            #         },
            #         ... más packages ...
            #     ],
            #     "maintained_packages": [...],
            #     "policy_applied": "default"
            # }
        else:
            # Fallback para domain AnalysisResult
            report_data = self._convert_to_dict(result)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            if format_type.lower() == "json":
                json.dump(report_data, f, indent=2, ensure_ascii=False)
                # ↓ GUARDADO A DISCO
                # Archivo: consolidated_report.json
                # Contenido: JSON con "license": "Apache 2.0" para cada package
            else:
                f.write(str(report_data))
        
        self.logger.info(f"Report saved to {output_path}")
        return os.path.abspath(output_path)
```

**Conversión asdict():**
```python
# Entrada (ReportDTO con PackageDTO):
AnalysisResultDTO(
    timestamp=datetime(2025, 11, 11, 22, 48, 26),
    packages=[
        PackageDTO(
            name="requests",
            version="2.28.0",
            license="Apache 2.0",
            ...
        )
    ]
)

# Salida (Dict):
{
    "timestamp": "2025-11-11T22:48:26",
    "packages": [
        {
            "name": "requests",
            "version": "2.28.0",
            "license": "Apache 2.0",
            ...
        }
    ]
}
```

---

### 📍 PASO 6: Archivo JSON Guardado
**Archivo:** `consolidated_report.json`

```json
{
  "timestamp": "2025-11-11T22:48:26",
  "vulnerabilities": [],
  "packages": [
    {
      "name": "requests",
      "version": "2.28.0",
      "license": "Apache 2.0",                    ← ⭐ AQUÍ ESTÁ
      "upload_time": "2022-07-28T10:23:45",
      "summary": "A simple, yet elegant HTTP Library for Python",
      "home_page": "https://requests.readthedocs.io",
      "author": "Kenneth Reitz",
      "author_email": "me@kennethreitz.org",
      "maintainer": null,
      "maintainer_email": null,
      "keywords": null,
      "classifiers": [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Software Development :: Libraries"
      ],
      "requires_dist": [
        "charset-normalizer (>=2,<3)",
        "idna (>=2.5,<4)",
        "urllib3 (>=1.21.1,<1.27)"
      ],
      "project_urls": {
        "Documentation": "https://requests.readthedocs.io",
        "Source": "https://github.com/psf/requests"
      },
      "github_url": "https://github.com/psf/requests",
      "github_license": "Apache 2.0",
      "dependencies": [
        "charset-normalizer",
        "idna",
        "urllib3"
      ],
      "is_maintained": true,
      "license_rejected": false,
      "aprobada": "Sí",
      "motivo_rechazo": "Sin problemas detectados",
      "dependencias_directas": [
        "charset-normalizer",
        "idna",
        "urllib3"
      ],
      "dependencias_transitivas": [
        "charset-normalizer",
        "idna",
        "urllib3"
      ]
    }
  ],
  "maintained_packages": [
    {
      "name": "requests",
      "version": "2.28.0",
      "license": "Apache 2.0",                    ← TAMBIÉN AQUÍ
      ...
    }
  ],
  "policy_applied": "default"
}
```

---

### 📍 PASO 7: Lectura para XLSX
**Archivo:** `src/infrastructure/adapters/xlsx_report_adapter.py:98-110`

```python
# xlsx_report_adapter.py - generate_xlsx() method

def generate_xlsx(self, report_path: str, output_file: str) -> bool:
    """Generate XLSX report from consolidated report JSON."""
    try:
        # Load the consolidated report
        with open(report_path, 'r', encoding='utf-8') as f:
            report_data = json.load(f)  # ← Lee consolidated_report.json
        
        # ... setup ...
        
        # Iterate through packages
        for idx, pkg in enumerate(report_data.get("packages", []), 1):
            # ⭐ ACCEDE AL CAMPO "license" DEL JSON
            raw_license = pkg.get("license") or pkg.get("github_license") or "—"
            # pkg.get("license") = "Apache 2.0"
            
            # Normalize license
            short = _short_license(raw_license)
            # _short_license("Apache 2.0") = "Apache"
            
            # ... write other columns ...
            
            # Write license to column D
            ws['D{}'.format(ws.max_row)] = short
            # ↓ Columna D, fila actual: "Apache"
```

**Método _short_license():**
```python
def _short_license(raw_license: Any) -> str:
    """Normalize license to short form for display."""
    if not raw_license:
        return "—"
    
    if not isinstance(raw_license, str):
        return "—"
    
    text = raw_license.lower()  # "apache 2.0"
    
    # Check common licenses
    if "mit" in text:
        return "MIT"
    elif "apache" in text:              # ← ✓ COINCIDE
        return "Apache"                 # ← RETORNA ESTO
    elif "bsd" in text:
        return "BSD"
    # ... más licenses ...
    
    # If no common pattern found, extract first line
    first_line = next((ln.strip() for ln in raw_license.splitlines() if ln.strip()), raw_license)
    
    # If still too long, truncate
    return first_line[:30] if len(first_line) > 30 else first_line
```

---

### 📍 PASO 8: Archivo XLSX Generado
**Archivo:** `packages.xlsx`

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Nombre | Versión | Fecha | **Licencia** | Aprobada | Estado/Comentario | Dependencias |
| requests | 2.28.0 | 2022-07-28 | **Apache** | Sí | Sin problemas detectados | charset-normalizer, idna, urllib3 |
| ... | ... | ... | ... | ... | ... | ... |

---

## 📊 Resumen Visual del Flujo Completo

```
┌─────────────────────────────────────┐
│ PyPI API Response                   │
│ {                                   │
│   "info": {                         │
│     "license": "Apache 2.0"    ← INPUT
│   }                                 │
│ }                                   │
└──────────────┬──────────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ PyPIClientAdapter        │
    │ _merge_pypi_data()       │
    │                          │
    │ license_name = "Apache 2.0"
    │ license_obj = License(...) ← DOMAIN ENTITY
    │ return Package(license=...) │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ Domain Package           │
    │ .license                 │
    │ = License(               │
    │   name="Apache 2.0"  ← STORED
    │   type=APACHE_2_0    │
    │ )                        │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ UseCase._package_to_dto()│
    │                          │
    │ license_value =          │
    │ package.license.name     │
    │ = "Apache 2.0"       ← EXTRACTED
    │                          │
    │ return PackageDTO(       │
    │   license="Apache 2.0" │
    │ )                        │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ ReportDTO with           │
    │ PackageDTO list          │
    │                          │
    │ {                        │
    │   license: "Apache 2.0" │
    │ }                        │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ report_adapter.save()    │
    │                          │
    │ asdict(ReportDTO)        │
    │ ↓                        │
    │ json.dump()          ← SERIALIZE
    │ ↓                        │
    │ consolidated_report.json │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ consolidated_report.json │
    │ {                        │
    │   license: "Apache 2.0" │← PERSISTED
    │ }                        │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ XLSXAdapter              │
    │ json.load()              │
    │ pkg.get("license")       │
    │ = "Apache 2.0"       ← READ
    │                          │
    │ _short_license()         │
    │ = "Apache"           ← NORMALIZE
    │                          │
    │ ws['D...'] = "Apache"    │
    └──────────────┬─────────────┘
                   │
                   ▼
    ┌──────────────────────────┐
    │ packages.xlsx            │
    │ Column D (Licencia)      │
    │ = "Apache"           ← OUTPUT
    └──────────────────────────┘
```

---

## ✅ Validación Final

**Verify en JSON:**
```bash
# Ver que la licencia está en el JSON
python -c "
import json
with open('consolidated_report.json') as f:
    data = json.load(f)
pkg = data['packages'][0]
print(f\"Package: {pkg['name']}@{pkg['version']}\")
print(f\"License: {pkg['license']}\")
print(f\"Status: {pkg['aprobada']}\")
print(f\"Reason: {pkg['motivo_rechazo']}\")
"
```

**Output esperado:**
```
Package: requests@2.28.0
License: Apache 2.0
Status: Sí
Reason: Sin problemas detectados
```

**Verify en XLSX:**
```bash
# Ver que la licencia está en el XLSX
python -c "
from openpyxl import load_workbook
wb = load_workbook('packages.xlsx')
ws = wb.active
print(f\"Header: {ws['D1'].value}\")
print(f\"First package license: {ws['D2'].value}\")
"
```

**Output esperado:**
```
Header: Licencia
First package license: Apache
```

