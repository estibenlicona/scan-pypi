"""Test the approval engine directly to debug recursive validation."""

from src.domain.models import PackageInfo, DependencyInfo, VulnerabilityInfo
from src.domain.services.approval_engine import ApprovalEngine
from datetime import datetime

# Create test packages
colorama = PackageInfo(
    name="colorama",
    version="0.4.6",
    latest_version="0.4.6",
    license="BSD",
    upload_time=datetime(2020, 1, 1),  # Very old to fail maintenance check
    summary="Cross-platform colored terminal text",
    is_maintained=False,
)

ipython = PackageInfo(
    name="ipython",
    version="9.7.0",
    latest_version="9.7.0",
    license="BSD",
    upload_time=datetime.now(),
    summary="IPython",
    is_maintained=True,
)

stack_data = PackageInfo(
    name="stack-data",
    version="0.6.3",
    latest_version="0.6.3",
    license="MIT",
    upload_time=datetime(2020, 1, 1),  # Very old to fail maintenance check
    summary="Stack data",
    is_maintained=False,
)

# Create test data
packages = [colorama, ipython, stack_data]
vulnerabilities = []
dependencies_map = {
    "ipython": ["colorama==0.4.6", "stack-data==0.6.3"],
    "colorama": [],
    "stack-data": [],
}

# Test evaluation
engine = ApprovalEngine()

# First pass to get baseline statuses
print("=== First Pass ===")
result = engine.evaluate_all_packages(packages, vulnerabilities, dependencies_map)

for pkg in result:
    print(f"{pkg.name}: aprobada={pkg.aprobada}, rejected_deps={pkg.dependencias_rechazadas}, motivo={pkg.motivo_rechazo}")

# Now let's manually test the evaluation of ipython with rejected dependencies already in place
print("\n=== Manual Test with Pre-Rejected Dependencies ===")
# Create rejected versions using dataclass constructor
from dataclasses import replace
colorama_rejected = replace(colorama, aprobada="No", motivo_rechazo="Sin mantenimiento")
stack_data_rejected = replace(stack_data, aprobada="No", motivo_rechazo="Sin mantenimiento")

packages_with_rejected = [colorama_rejected, ipython, stack_data_rejected]
result2 = engine.evaluate_all_packages(packages_with_rejected, vulnerabilities, dependencies_map)

for pkg in result2:
    print(f"{pkg.name}: aprobada={pkg.aprobada}, rejected_deps={pkg.dependencias_rechazadas}, motivo={pkg.motivo_rechazo}")
