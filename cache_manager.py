"""
cache_manager.py
Sistema de caché inteligente para análisis de dependencias.
Optimiza rendimiento evitando recálculos innecesarios en llamadas API.
"""

import json
import hashlib
import os
import time
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from datetime import datetime
import tempfile
import shutil


class DependencyCache:
    """
    Gestiona caché de dependencias, vulnerabilidades y metadatos PyPI.
    Reduce significativamente el tiempo de análisis en llamadas repetidas.
    """
    
    def __init__(self, cache_dir: str = ".cache", ttl_hours: int = 24):
        """
        Inicializa el sistema de caché.
        
        Args:
            cache_dir: Directorio para archivos de caché
            ttl_hours: Tiempo de vida del caché en horas
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600
        
        # Subdirectorios especializados
        (self.cache_dir / "pipgrip").mkdir(exist_ok=True)
        (self.cache_dir / "snyk").mkdir(exist_ok=True) 
        (self.cache_dir / "pypi").mkdir(exist_ok=True)
        
        print(f"💾 Cache inicializado: {cache_dir} (TTL: {ttl_hours}h)")

    def _get_cache_key(self, libraries: List[str]) -> str:
        """
        Genera clave única para conjunto de librerías.
        
        Args:
            libraries: Lista de librerías a analizar
            
        Returns:
            Hash único de 16 caracteres
        """
        # Normalizar y ordenar para consistencia
        normalized = sorted([lib.strip().lower() for lib in libraries])
        content = "|".join(normalized)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_cache_valid(self, cache_file: Path) -> bool:
        """
        Verifica si el archivo de caché está vigente.
        
        Args:
            cache_file: Ruta al archivo de caché
            
        Returns:
            True si el caché es válido, False si expiró
        """
        if not cache_file.exists():
            return False
        
        file_age = time.time() - cache_file.stat().st_mtime
        return file_age < self.ttl_seconds

    def get_pipgrip_cache(self, libraries: List[str]) -> Optional[Tuple[str, str]]:
        """
        Obtiene resultado de pipgrip desde caché.
        
        Args:
            libraries: Lista de librerías a resolver
            
        Returns:
            Tuple[temp_dir, requirements_path] si existe y es válido, None si no
        """
        cache_key = self._get_cache_key(libraries)
        cache_file = self.cache_dir / "pipgrip" / f"{cache_key}.json"
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Recrear archivo requirements temporal
                temp_dir = tempfile.mkdtemp(prefix="cached_pipgrip_")
                requirements_path = os.path.join(temp_dir, "requirements.txt")
                
                with open(requirements_path, 'w', encoding='utf-8') as req_f:
                    req_f.write(data['requirements_content'])
                
                print(f"📋 Cache HIT: pipgrip para {len(libraries)} librerías")
                return temp_dir, requirements_path
                
            except (json.JSONDecodeError, KeyError, OSError) as e:
                print(f"⚠️  Error leyendo caché pipgrip: {e}")
                cache_file.unlink(missing_ok=True)
        
        return None

    def set_pipgrip_cache(self, libraries: List[str], temp_dir: str, 
                         requirements_path: str) -> None:
        """
        Guarda resultado de pipgrip en caché.
        
        Args:
            libraries: Lista de librerías resueltas
            temp_dir: Directorio temporal usado
            requirements_path: Ruta al archivo requirements.txt generado
        """
        cache_key = self._get_cache_key(libraries)
        cache_file = self.cache_dir / "pipgrip" / f"{cache_key}.json"
        
        try:
            # Leer contenido del requirements
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements_content = f.read()
            
            cache_data: Dict[str, Any] = {
                'libraries': libraries,
                'requirements_content': requirements_content,
                'cached_at': datetime.now().isoformat(),
                'dependency_count': len([line for line in requirements_content.split('\n') if line.strip()])
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            print(f"💾 Cache STORED: pipgrip para {len(libraries)} librerías")
            
        except OSError as e:
            print(f"⚠️  Error guardando caché pipgrip: {e}")

    def get_snyk_cache(self, requirements_content: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Obtiene resultado de análisis Snyk desde caché.
        
        Args:
            requirements_content: Contenido del archivo requirements.txt
            
        Returns:
            Tuple[dependencies, vulnerabilities] si existe y es válido
        """
        # Hash del contenido para cache key
        content_hash = hashlib.sha256(requirements_content.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / "snyk" / f"{content_hash}.json"
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print("🔍 Cache HIT: análisis Snyk")
                    return data['dependencies'], data['vulnerabilities']
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  Error leyendo caché Snyk: {e}")
                cache_file.unlink(missing_ok=True)
        
        return None

    def set_snyk_cache(self, requirements_content: str, dependencies: Dict[str, Any], 
                      vulnerabilities: Dict[str, Any]) -> None:
        """
        Guarda resultado de Snyk en caché.
        
        Args:
            requirements_content: Contenido del requirements.txt analizado
            dependencies: Objeto de dependencias de Snyk
            vulnerabilities: Objeto de vulnerabilidades de Snyk
        """
        content_hash = hashlib.sha256(requirements_content.encode()).hexdigest()[:16]
        cache_file = self.cache_dir / "snyk" / f"{content_hash}.json"
        
        try:
            cache_data: Dict[str, Any] = {
                'dependencies': dependencies,
                'vulnerabilities': vulnerabilities,
                'requirements_hash': content_hash,
                'cached_at': datetime.now().isoformat(),
                'vulnerability_count': len(vulnerabilities.get('vulnerabilities', []))
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            print("🛡️  Cache STORED: análisis Snyk")
            
        except OSError as e:
            print(f"⚠️  Error guardando caché Snyk: {e}")

    def get_pypi_cache(self, package: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadatos PyPI desde caché.
        
        Args:
            package: Nombre del paquete
            version: Versión del paquete
            
        Returns:
            Dict con metadatos del paquete si existe y es válido
        """
        cache_key = f"{package}_{version}".replace("/", "_").replace("@", "_")
        cache_file = self.cache_dir / "pypi" / f"{cache_key}.json"
        
        if self._is_cache_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️  Error leyendo caché PyPI {package}: {e}")
                cache_file.unlink(missing_ok=True)
        
        return None

    def set_pypi_cache(self, package: str, version: str, metadata: Dict[str, Any]) -> None:
        """
        Guarda metadatos PyPI en caché.
        
        Args:
            package: Nombre del paquete
            version: Versión del paquete  
            metadata: Metadatos del paquete desde PyPI
        """
        cache_key = f"{package}_{version}".replace("/", "_").replace("@", "_")
        cache_file = self.cache_dir / "pypi" / f"{cache_key}.json"
        
        try:
            # Agregar información de caché
            cache_data: Dict[str, Any] = {
                **metadata,
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except OSError:
            # Fallo silencioso para metadatos PyPI (no crítico)
            pass

    def clear_expired_cache(self) -> Dict[str, int]:
        """
        Limpia archivos de caché expirados.
        
        Returns:
            Dict con estadísticas de limpieza por tipo
        """
        cleared_stats = {'pipgrip': 0, 'snyk': 0, 'pypi': 0}
        
        for subdir in ["pipgrip", "snyk", "pypi"]:
            cache_subdir = self.cache_dir / subdir
            for cache_file in cache_subdir.glob("*.json"):
                if not self._is_cache_valid(cache_file):
                    try:
                        cache_file.unlink()
                        cleared_stats[subdir] += 1
                    except OSError:
                        pass
        
        total_cleared = sum(cleared_stats.values())
        if total_cleared > 0:
            print(f"🧹 Cache limpiado: {total_cleared} archivos expirados")
            
        return cleared_stats

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas detalladas del caché.
        
        Returns:
            Dict con estadísticas por tipo de caché
        """
        stats: Dict[str, Any] = {}
        total_size = 0
        
        for subdir in ["pipgrip", "snyk", "pypi"]:
            cache_subdir = self.cache_dir / subdir
            valid_files = 0
            expired_files = 0
            subdir_size = 0
            
            for cache_file in cache_subdir.glob("*.json"):
                file_size = cache_file.stat().st_size
                subdir_size += file_size
                total_size += file_size
                
                if self._is_cache_valid(cache_file):
                    valid_files += 1
                else:
                    expired_files += 1
            
            stats[subdir] = {
                'valid_files': valid_files,
                'expired_files': expired_files,
                'size_bytes': subdir_size
            }
        
        stats['total'] = {
            'size_bytes': total_size,
            'size_mb': round(total_size / (1024 * 1024), 2)
        }
        
        return stats

    def clear_all_cache(self) -> None:
        """Limpia todo el caché (usar con precaución)."""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            (self.cache_dir / "pipgrip").mkdir(exist_ok=True)
            (self.cache_dir / "snyk").mkdir(exist_ok=True) 
            (self.cache_dir / "pypi").mkdir(exist_ok=True)
            print("🗑️  Todo el caché ha sido limpiado")
        except OSError as e:
            print(f"⚠️  Error limpiando caché: {e}")


# Instancia global de caché
_cache_instance: Optional[DependencyCache] = None

def get_cache() -> DependencyCache:
    """
    Obtiene la instancia global de caché (singleton).
    
    Returns:
        Instancia de DependencyCache
    """
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.getenv('CACHE_DIR', '.cache')
        ttl_hours = int(os.getenv('CACHE_TTL_HOURS', '24'))
        _cache_instance = DependencyCache(cache_dir=cache_dir, ttl_hours=ttl_hours)
    
    return _cache_instance

def is_cache_enabled() -> bool:
    """
    Verifica si el caché está habilitado vía variable de entorno.
    
    Returns:
        True si el caché está habilitado
    """
    return os.getenv('ENABLE_CACHE', 'true').lower() in ('true', '1', 'yes', 'on')