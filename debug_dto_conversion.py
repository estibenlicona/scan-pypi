"""Debug the full pipeline."""

from src.domain.models import PackageInfo
from src.application.dtos import PackageDTO

# Create a test PackageInfo with rejected deps
pkg_info = PackageInfo(
    name="test",
    version="1.0",
    latest_version="1.0",
    summary="Test",
    aprobada="No",
    dependencias_rechazadas=["colorama", "stack-data"],
)

print(f"PackageInfo.dependencias_rechazadas: {pkg_info.dependencias_rechazadas}")

# Now create a DTO with it
dto = PackageDTO(
    name="test",
    version="1.0",
    aprobada="No",
    dependencias_rechazadas=["colorama", "stack-data"],
)

print(f"PackageDTO.dependencias_rechazadas: {dto.dependencias_rechazadas}")

# Now convert to dict like _package_to_dict does
pkg_dict = {
    "package": dto.name,
    "aprobada": dto.aprobada,
    "dependencias_rechazadas": dto.dependencias_rechazadas,
}

print(f"dict['dependencias_rechazadas']: {pkg_dict['dependencias_rechazadas']}")

# Check JSON serialization
import json
json_str = json.dumps(pkg_dict, default=str)
print(f"JSON: {json_str}")
