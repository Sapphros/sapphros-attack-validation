import json
import sys
from pathlib import Path


HOST_REQUIREMENTS = {
    "sapphros-attack": {
        "minimum_memory_mb": 4096,
        "minimum_root_free_mb": 10240,
    },
    "sapphros-core": {
        "minimum_memory_mb": 12000,
        "minimum_root_free_mb": 20480,
    },
}


def validate_host(report: dict, expected_hostname: str) -> list[str]:
    errors = []
    requirements = HOST_REQUIREMENTS[expected_hostname]

    if report.get("hostname") != expected_hostname:
        errors.append(f"Unexpected hostname: {report.get('hostname')}")

    if report.get("distribution") != "Ubuntu":
        errors.append(f"Unsupported distribution: {report.get('distribution')}")

    if not str(report.get("version", "")).startswith("26."):
        errors.append(f"Unsupported Ubuntu version: {report.get('version')}")

    if report.get("memory_mb", 0) < requirements["minimum_memory_mb"]:
        errors.append("Insufficient memory")

    if report.get("root_free_mb", 0) < requirements["minimum_root_free_mb"]:
        errors.append("Insufficient free storage")

    return errors


def validate_reports(report_directory: Path) -> dict[str, list[str]]:
    results = {}

    for hostname in HOST_REQUIREMENTS:
        report_path = report_directory / f"{hostname}.json"

        if not report_path.exists():
            results[hostname] = ["Report file is missing"]
            continue

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            results[hostname] = validate_host(report, hostname)
        except (json.JSONDecodeError, OSError) as error:
            results[hostname] = [f"Unable to read report: {error}"]

    return results


def main() -> int:
    report_directory = Path("reports/hosts")
    results = validate_reports(report_directory)
    failed = False

    for hostname, errors in results.items():
        if errors:
            failed = True
            print(f"[FAIL] {hostname}")

            for error in errors:
                print(f"       - {error}")
        else:
            print(f"[PASS] {hostname}")

    print()
    print("Overall result:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
