# Análisis: Impacto de Remover `--print-deps` de Snyk

## Situación Actual

### Flujo de Datos de Dependencias

```
┌─────────────────────────────────────────────────────────────┐
│                    Flujo Actual                              │
└─────────────────────────────────────────────────────────────┘

requirements.txt (usuario)
        ↓
        ├──→ pipgrip (dependency_resolver_adapter)
        │    └──→ DependencyGraph con árbol completo
        │         └──→ dependencies_map (USADO)
        │
        └──→ Snyk CLI
             ├──→ --print-deps (extrae dep_data)
             │    └──→ (NO USADO EN ABSOLUTO)
             └──→ Vulnerabilidades (extrae vuln_data)
                  └──→ vulnerabilities (USADO)
```

### Código Actual (use_cases/__init__.py línea 54-61)

```python
# Snyk devuelve AMBOS
dep_data, vuln_data = await self.vulnerability_scanner.scan_vulnerabilities(
    requirements_content
)

# Solo usamos vulnerabilities
vulnerabilities = self._extract_vulnerabilities(vuln_data)
# dep_data nunca se toca
```

---

## Validación: ¿Qué Pasa si Removemos `--print-deps`?

### Respuesta: NADA

**Impacto:** ✅ NINGUNO

**Razones:**

1. **El árbol de dependencias YA viene de pipgrip**
   - `dependencies_map` se construye desde `dependency_graph` (línea 50)
   - Eso viene 100% de pipgrip, NO de Snyk
   - Snyk solo proporciona vulnerabilidades

2. **`dep_data` nunca se utiliza**
   - Se extrae pero se ignora
   - No afecta a ningún flujo posterior
   - Es código muerto

3. **Snyk solo necesita `--json` para vulnerabilidades**
   - `--print-deps` es redundante en nuestro caso
   - Solo agrega peso a la respuesta JSON
   - Puede ralentizar el análisis innecesariamente

4. **Las vulnerabilidades se extraen correctamente sin `--print-deps`**
   - El campo "vulnerabilities" existe independiente de `--print-deps`
   - La salida JSON de Snyk sigue siendo válida

---

## Recomendación

### Propuesta: REMOVER `--print-deps`

**Beneficios:**
- ✅ Reduce tamaño de respuesta JSON de Snyk
- ✅ Puede acelerar análisis
- ✅ Elimina código muerto (dep_data)
- ✅ Hace el comando Snyk más simple y limpio
- ✅ Menos datos innecesarios en memoria

**Riesgo:**
- ❌ NINGUNO - el cambio es completamente seguro

---

## Cambio Propuesto

**Archivo:** `src/infrastructure/adapters/snyk_adapter.py`

### Antes:
```python
cmd = [
    self.settings.path,
    'test',
    '--json',
    f'--org={self.settings.org}',
    '--print-deps',      # ← REMOVER
    '--skip-unresolved',
    f'--file={requirements_path}'
]
```

### Después:
```python
cmd = [
    self.settings.path,
    'test',
    '--json',
    f'--org={self.settings.org}',
    '--skip-unresolved',
    f'--file={requirements_path}'
]
```

### Adaptación en el Retorno:
Ya que `dep_data` no se usa, podemos:

**Opción 1: Dejar como está**
```python
return {"dependencies": []}, vulnerabilities
```

**Opción 2: Simplificar (recomendado)**
```python
# Solo retornar vulnerabilities
return vulnerabilities
```

Esto requeriría cambiar la firma de `scan_vulnerabilities()` de:
```python
-> Tuple[Dict[str, Any], Dict[str, Any]]
```

A:
```python
-> Dict[str, Any]  # solo vulnerabilities
```

---

## Conclusión

**¿Remover `--print-deps`?** ✅ **SÍ, totalmente seguro**

No hay ninguna dependencia en `dep_data`. Todo el árbol de dependencias viene de pipgrip, que es más confiable y rápido que dejar que Snyk lo resuelva.
