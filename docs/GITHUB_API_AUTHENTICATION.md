# GitHub API Authentication - Solución Rate Limiting

## Problema Actual
```
Error: Se ha superado el límite de solicitudes a la API para 181.206.82.250
```

**Causa:** Solicitudes **no autenticadas** a GitHub API tienen límite muy bajo.

---

## Comparativa de Límites

| Tipo | Límite | Por |
|------|--------|-----|
| **No autenticado** | **60 solicitudes** | **1 hora** |
| **Autenticado (Personal Token)** | **5,000 solicitudes** | **1 hora** |
| **Enterprise Cloud** | **15,000 solicitudes** | **1 hora** |

**Nuestro caso:** Pasamos de 60 a 5,000 solicitudes/hora (83x más)

---

## Solución: Usar Personal Access Token

### Paso 1: Crear un Personal Access Token en GitHub

1. Ve a: https://github.com/settings/tokens
2. Click en "Generate new token" → "Generate new token (classic)"
3. **Dale un nombre:** `scan-pypi-analysis`
4. **Selecciona scopes mínimos necesarios:**
   - ✅ `public_repo` (leer info de repos públicos)
   - ✅ `read:user` (leer info de usuario - opcional)
5. **Genera el token** y **GUÁRDALO** (no podrás verlo de nuevo)

**Nunca** commits este token al repositorio.

---

### Paso 2: Almacenar Token de Forma Segura

**Opción A: Variables de entorno (RECOMENDADO)**
```bash
# En tu terminal (Windows PowerShell)
$env:GITHUB_TOKEN="tu_token_aquí"
```

**Opción B: Archivo .env (local, no commitear)**
```env
GITHUB_TOKEN=tu_token_aquí
```

**Opción C: Archivo de configuración encriptado (producción)**
- Usar `python-dotenv` para cargar desde `.env`
- Nunca commitear `.env`

---

### Paso 3: Actualizar `pypi_adapter.py` para usar el token

**Cambio en `APISettings` (settings.py):**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de .env

class APISettings:
    """API configuration."""
    pypi_base_url: str = "https://pypi.org/pypi"
    github_base_url: str = "https://api.github.com"
    github_token: str = os.getenv("GITHUB_TOKEN", "")  # ← AGREGAR
    request_timeout: int = 10
```

**Cambio en `_fetch_github_metadata()` (pypi_adapter.py):**
```python
async def _fetch_github_metadata(self, github_url: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata from GitHub API with authentication."""
    repo_match = re.match(r'https://github\.com/([^/]+)/([^/]+)', github_url)
    if not repo_match:
        return None
    
    owner, repo = repo_match.groups()
    api_url = f"{self.settings.github_base_url}/repos/{owner}/{repo}"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    
    # Agregar token si está disponible
    if self.settings.github_token:
        headers["Authorization"] = f"Bearer {self.settings.github_token}"
    
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=self.settings.request_timeout)
    ) as session:
        try:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    # Rate limit alcanzado
                    remaining = response.headers.get("X-RateLimit-Remaining", "0")
                    reset_time = response.headers.get("X-RateLimit-Reset", "unknown")
                    self.logger.error(
                        f"GitHub API rate limit exceeded. Remaining: {remaining}, Reset: {reset_time}"
                    )
                else:
                    self.logger.warning(
                        f"GitHub API returned {response.status} for {owner}/{repo}"
                    )
                return None
        except asyncio.TimeoutError:
            self.logger.warning(f"Timeout fetching GitHub data for {owner}/{repo}")
            return None
        except Exception as e:
            self.logger.warning(f"Error fetching GitHub data for {owner}/{repo}: {e}")
            return None
```

---

## Monitoring: Verificar Rate Limit

**Headers de respuesta GitHub:**
```
X-RateLimit-Limit: 5000         # Límite total
X-RateLimit-Remaining: 4998     # Solicitudes restantes
X-RateLimit-Used: 2             # Solicitudes usadas
X-RateLimit-Reset: 1699732200   # Timestamp reset (UTC)
```

**Endpoint para verificar el límite:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.github.com/rate_limit
```

---

## Checklist de Implementación

- [ ] Crear Personal Access Token en GitHub
- [ ] Guardar token en variable de entorno `GITHUB_TOKEN`
- [ ] Agregar `github_token` a `APISettings`
- [ ] Cargar `python-dotenv` en `settings.py`
- [ ] Actualizar headers en `_fetch_github_metadata()`
- [ ] Manejar respuesta 403 (rate limit) correctamente
- [ ] Logging mejorado de headers de rate limit
- [ ] Probar con análisis completo
- [ ] Verificar que se consume menos del límite diario

---

## Referencias

- [GitHub API Rate Limits](https://docs.github.com/es/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Crear Personal Access Token](https://docs.github.com/es/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
- [Autenticación REST API](https://docs.github.com/es/rest/overview/authenticating-to-the-rest-api)
