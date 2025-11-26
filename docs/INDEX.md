# Documentation Index# 📚 Documentación de Licencias - Índice Rápido



## Quick Start## 🚀 Empieza Aquí (5 min)



1. **[README.md](README.md)** - Project overview, architecture, setup**Pregunta:** ¿Dónde se extrae la licencia?

2. **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current status, completed features, tests

3. **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - How to run tests**→ Lee:** [`FINAL_ANSWER_LICENSE.md`](./FINAL_ANSWER_LICENSE.md)



## Feature Documentation---



### License Extraction## 📖 Documentación por Tema

- **[LICENSE_EXTRACTION_FLOW.md](LICENSE_EXTRACTION_FLOW.md)** - 4-tier license detection cascade

- **[LICENSE_VALIDATOR_ENCAPSULATION.md](LICENSE_VALIDATOR_ENCAPSULATION.md)** - LicenseValidator implementation### 1️⃣ Visión General (15 min)

**→ Lee:** [`LICENSE_EXTRACTION_FLOW.md`](./LICENSE_EXTRACTION_FLOW.md)

### Retry & Resilience- 7 capas de transformación

- **[RETRY_POLICY_IMPLEMENTATION.md](RETRY_POLICY_IMPLEMENTATION.md)** - Exponential backoff strategy- Diagrama visual

- Debugging guide

## Reference Guides

### 2️⃣ Referencia Técnica (20 min)

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common patterns and usage examples**→ Lee:** [`LICENSE_EXTRACTION_DETAILED.md`](./LICENSE_EXTRACTION_DETAILED.md)

- Líneas exactas de código

---- Commandos grep

- Tests

## File Organization

### 3️⃣ Mapa Visual (15 min)

```**→ Lee:** [`LICENSE_EXTRACTION_MAP.md`](./LICENSE_EXTRACTION_MAP.md)

docs/- Árbol completo

├── README.md                                      ← Start here- Matriz archivo/línea/acción

├── PROJECT_STATUS.md                              ← Feature status & completion- Relaciones

├── TESTING_GUIDE.md                               ← Test execution

├── LICENSE_EXTRACTION_FLOW.md                     ← License logic### 4️⃣ Ejemplo Real (25 min)

├── LICENSE_VALIDATOR_ENCAPSULATION.md             ← License implementation**→ Lee:** [`LICENSE_EXTRACTION_EXAMPLE.md`](./LICENSE_EXTRACTION_EXAMPLE.md)

├── RETRY_POLICY_IMPLEMENTATION.md                 ← Retry strategy- Paso a paso con requests@2.28.0

└── QUICK_REFERENCE.md                             ← Common patterns- Entrada → salida

```- Código real



## What's Implemented### 5️⃣ Cómo Usar Docs (10 min)

**→ Lee:** [`README_LICENSE_DOCS.md`](./README_LICENSE_DOCS.md)

### Phase 1: License Extraction ✅- Descripción de cada doc

2-tier detection with regex patterns + heuristics covering 15+ license variations- Guía de lectura

- Referencias cruzadas

### Phase 2: Retry Policy ✅

Exponential backoff with max 30s wait for PyPI API calls (3 retries)### 6️⃣ Índice Completo (5 min)

**→ Lee:** [`INDEX_LICENSE_DOCS.md`](./INDEX_LICENSE_DOCS.md)

### Phase 3: LicenseValidator Encapsulation ✅- Matriz pregunta → documento

4-level cascade: PyPI direct → expression → classifiers → GitHub- Rutas de aprendizaje



### Phase 4: Package Deduplication ✅---

2-level dedup (domain + adapter) using `{name}@{version}` keys

## 🎯 Respuesta Rápida

### Phase 5: Root Library Ordering ✅

Libraries from requirements.scan.txt appear first in original order```

PyPI → pypi_adapter.py:123 → License entity → Package

### Phase 6: Excel Styling ✅→ use_cases:228 → PackageDTO → report_adapter.py:39 

Pastel colors: blue for roots, red for rejected packages→ json.dump() → consolidated_report.json

```

### Phase 7: Workspace Cleanup ✅

Organized tests, consolidated documentation, removed obsolete files---



---## 📊 Matriz: Pregunta → Documento



## Running the Application| Pregunta | Documento | Tiempo |

|----------|-----------|--------|

```bash| Resumen ejecutivo | `FINAL_ANSWER_LICENSE.md` | 5 min |

# Setup| ¿Cómo fluye? | `LICENSE_EXTRACTION_FLOW.md` | 15 min |

python -m venv .venv| ¿Dónde está? | `LICENSE_EXTRACTION_MAP.md` | 15 min |

.venv\Scripts\activate| ¿Línea exacta? | `LICENSE_EXTRACTION_DETAILED.md` | 20 min |

pip install -r requirements.txt| ¿Ejemplo? | `LICENSE_EXTRACTION_EXAMPLE.md` | 25 min |

| ¿Cómo leer? | `README_LICENSE_DOCS.md` | 10 min |

# Run analysis| ¿Qué leer? | `INDEX_LICENSE_DOCS.md` | 5 min |

python -m src.interface.cli.main

---

# Output files

# - consolidated_report.json  (structured dependency report)## 🔧 Verificación Rápida

# - report.xlsx              (styled Excel with dedup, ordering, colors)

``````bash

# Ver licencia en JSON

## Testingpython -c "import json; d=json.load(open('../consolidated_report.json')); print(d['packages'][0]['license'])"



```bash# Ver en XLSX

# All testspython -c "from openpyxl import load_workbook; wb=load_workbook('../packages.xlsx'); print(wb.active['D2'].value)"

pytest tests/```



# Unit tests only---

pytest tests/unit/

## 📁 Archivos en Esta Carpeta

# Integration tests only

pytest tests/integration/```

docs/

# With coverage├─ FINAL_ANSWER_LICENSE.md              ← EMPIEZA AQUÍ

pytest tests/ --cov=src├─ INDEX_LICENSE_DOCS.md                ← Índice completo

```├─ README_LICENSE_DOCS.md               ← Cómo usar docs

├─ LICENSE_EXTRACTION_FLOW.md           ← 7 capas

---├─ LICENSE_EXTRACTION_DETAILED.md       ← Línea exacta

├─ LICENSE_EXTRACTION_EXAMPLE.md        ← Paso a paso

## Architecture Layers├─ LICENSE_EXTRACTION_MAP.md            ← Mapa visual

├─ QUICK_REFERENCE.md                  ← Referencia rápida

| Layer | Purpose | Examples |├─ QUICK_SUMMARY.md                    ← Resumen

|-------|---------|----------|├─ SOLUTION_FINAL.md                   ← Soluciones

| **Domain** | Pure business logic | ApprovalEngine, DependencyGraph, LicenseValidator |├─ README.md                            ← Docs originales

| **Application** | Use cases & orchestration | AnalyzePackagesUseCase, DTOs |└─ (ESTE ARCHIVO)                      ← Índice rápido

| **Infrastructure** | Adapters & integrations | SNYKAdapter, PyPIAdapter, XLSXReportAdapter |```

| **Interface** | Entry points | CLI (main.py), HTTP (app.py) |

---

---

**¿No sabes por dónde empezar?** → Lee `FINAL_ANSWER_LICENSE.md` (5 min)

## Support


For detailed information on specific features, see the feature documentation above.

