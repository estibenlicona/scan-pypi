"""Test to verify dependencias_rechazadas is being set correctly."""

from datetime import datetime
from src.application.dtos import PackageDTO
from src.application.use_cases import BuildConsolidatedReportUseCase

# Create a test PackageDTO with rejected dependencies
pkg_dto = PackageDTO(
    name="test-pkg",
    version="1.0.0",
    latest_version="1.0.0",
    license="MIT",
    upload_time=datetime.now(),
    summary="Test",
    aprobada="No",
    motivo_rechazo="Dependencias rechazadas",
    dependencias_rechazadas=["rejected-dep1", "rejected-dep2"],
)

print(f"PackageDTO.dependencias_rechazadas: {pkg_dto.dependencias_rechazadas}")

# Now test the _package_to_dict conversion
try:
    use_case = BuildConsolidatedReportUseCase(None, None)  # type: ignore
    dict_result = use_case._package_to_dict(pkg_dto)
    print(f"dict['dependencias_rechazadas']: {dict_result.get('dependencias_rechazadas')}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
