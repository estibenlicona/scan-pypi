"""Debug the approval engine second pass."""

from src.domain.models import PackageInfo, DependencyInfo
from src.domain.services.approval_engine import ApprovalEngine
from datetime import datetime
from dataclasses import replace

# Create test packages
colorama = PackageInfo(
    name="colorama",
    version="0.4.6",
    latest_version="0.4.6",
    license="BSD",
    upload_time=datetime(2020, 1, 1),
    summary="Cross-platform colored terminal text",
    is_maintained=False,
    aprobada="No",
    motivo_rechazo="Sin mantenimiento",
)

ipython = PackageInfo(
    name="ipython",
    version="9.7.0",
    latest_version="9.7.0",
    license="BSD",
    upload_time=datetime.now(),
    summary="IPython",
    is_maintained=True,
    aprobada="Sí",
)

dependencies_map = {
    "ipython": ["colorama==0.4.6"],
    "colorama": [],
}

# Simulate first pass by directly setting colorama as rejected
packages = [colorama, ipython]

engine = ApprovalEngine()
result = engine.evaluate_all_packages(packages, [], dependencies_map)

print("=== Result after two-pass evaluation ===")
for pkg in result:
    print(f"{pkg.name}:")
    print(f"  aprobada: {pkg.aprobada}")
    print(f"  dependencias_rechazadas: {pkg.dependencias_rechazadas}")
    print(f"  type: {type(pkg.dependencias_rechazadas)}")
