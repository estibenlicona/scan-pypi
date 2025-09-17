"""
Modelos de datos usando Pydantic V2 para validación estricta de tipos.
Esto resuelve los errores de codificación y tipos desconocidos.
"""

from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime


class PackageInfo(BaseModel):
    """Modelo para información de un paquete de PyPI."""
    model_config = ConfigDict(validate_assignment=True, extra='allow')
    
    package: str = Field(..., description="Nombre del paquete")
    version: str = Field(..., description="Versión del paquete")
    license: Optional[str] = Field(default=None, description="Licencia del paquete")
    upload_time: Optional[str] = Field(default=None, description="Tiempo de subida del paquete")
    summary: Optional[str] = Field(default=None, description="Resumen del paquete")
    home_page: Optional[str] = Field(default=None, description="Página principal del paquete")
    author: Optional[str] = Field(default=None, description="Autor del paquete")
    author_email: Optional[str] = Field(default=None, description="Email del autor")
    maintainer: Optional[str] = Field(default=None, description="Mantenedor del paquete")
    maintainer_email: Optional[str] = Field(default=None, description="Email del mantenedor")
    keywords: Optional[str] = Field(default=None, description="Palabras clave")
    classifiers: List[str] = Field(default_factory=list, description="Clasificadores del paquete")
    requires_dist: List[str] = Field(default_factory=list, description="Dependencias requeridas")
    project_urls: Dict[str, str] = Field(default_factory=dict, description="URLs del proyecto")
    github_url: Optional[str] = Field(default=None, description="URL del repositorio GitHub")
    github_license: Optional[str] = Field(default=None, description="Licencia desde GitHub")
    snyk_license: Optional[str] = Field(default=None, description="Licencia desde Snyk")
    license_rejected: bool = Field(default=False, description="Si la licencia fue rechazada")
    dependencies: List[str] = Field(default_factory=list, description="Lista de dependencias del paquete")
    
    @field_validator('package', 'version')
    @classmethod
    def validate_required_fields(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Campo requerido no puede estar vacío')
        return v.strip()
    
    @field_validator('upload_time')
    @classmethod
    def validate_upload_time(cls, v: Optional[str]) -> Optional[str]:
        if v:
            try:
                # Validar que sea un formato de fecha válido
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('Formato de fecha inválido')
        return v


class DependencyNode(BaseModel):
    """Modelo para nodos del árbol de dependencias."""
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)
    
    name: str = Field(..., description="Nombre de la dependencia")
    version: str = Field(..., description="Versión de la dependencia")
    dependencies: List[DependencyNode] = Field(default_factory=list, description="Subdependencias")  # type: ignore


class SnykVulnerability(BaseModel):
    """Modelo para vulnerabilidades de Snyk."""
    model_config = ConfigDict(validate_assignment=True, extra='forbid')
    
    id: Optional[str] = Field(None, description="ID de la vulnerabilidad")
    title: Optional[str] = Field(None, description="Título de la vulnerabilidad")
    description: Optional[str] = Field(None, description="Descripción de la vulnerabilidad")
    severity: Optional[str] = Field(None, description="Severidad de la vulnerabilidad")
    packageName: Optional[str] = Field(None, description="Nombre del paquete afectado")
    version: Optional[str] = Field(None, description="Versión afectada")
    type: Optional[str] = Field(None, description="Tipo de issue (license, vulnerability)")
    license: Optional[str] = Field(None, description="Licencia problemática")


class ConsolidatedReport(BaseModel):
    """Modelo para el reporte consolidado."""
    model_config = ConfigDict(
        validate_assignment=True,
        extra='forbid',
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    )
    
    timestamp: str = Field(..., description="Timestamp de generación del reporte")
    vulnerabilities: List[SnykVulnerability] = Field(default_factory=list, description="Vulnerabilidades encontradas")  # type: ignore
    packages: List[PackageInfo] = Field(default_factory=list, description="Paquetes analizados")  # type: ignore
    filtered_packages: List[PackageInfo] = Field(default_factory=list, description="Paquetes filtrados")  # type: ignore


class LibraryList(BaseModel):
    """Modelo para validar listas de librerías de entrada."""
    model_config = ConfigDict(validate_assignment=True)
    
    libraries: List[str] = Field(..., min_length=1, description="Lista de librerías a analizar")
    
    @field_validator('libraries')
    @classmethod
    def validate_libraries(cls, v: List[str]) -> List[str]:
        # Filtrar elementos vacíos y validar formato
        valid_libs: List[str] = []
        for lib in v:
            lib = lib.strip()
            if lib:
                # Validación básica de formato de paquete
                if any(char in lib for char in ['<', '>', '!', ';']):
                    # Caracteres problemáticos que pueden causar errores
                    raise ValueError(f'Formato de librería inválido: {lib}')
                valid_libs.append(lib)
        
        if not valid_libs:
            raise ValueError('La lista debe contener al menos una librería válida')
        
        return valid_libs


class PipgripResult(BaseModel):
    """Modelo para resultado de pipgrip."""
    model_config = ConfigDict(validate_assignment=True)
    
    requirements_content: str = Field(..., description="Contenido del archivo requirements.txt")
    dependency_count: int = Field(..., ge=0, description="Número de dependencias resueltas")


# Actualizar referencias forward para Pydantic V2
DependencyNode.model_rebuild()
ConsolidatedReport.model_rebuild()
DependencyNode.model_rebuild()