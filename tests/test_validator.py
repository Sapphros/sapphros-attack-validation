from pathlib import Path

from sapphros_validator.validator import validate_host, validate_reports


def valid_report(hostname: str = "sapphros-attack") -> dict:
    return {
        "hostname": hostname,
        "distribution": "Ubuntu",
        "version": "26.04",
        "kernel": "7.0.0-31-generic",
        "architecture": "x86_64",
        "processor_cores": 6,
        "memory_mb": 8192,
        "root_free_mb": 50000,
    }


def test_valid_attack_report_passes():
    errors = validate_host(
        valid_report(),
        "sapphros-attack",
    )

    assert errors == []


def test_wrong_hostname_fails():
    report = valid_report(hostname="unexpected-host")

    errors = validate_host(report, "sapphros-attack")

    assert "Unexpected hostname: unexpected-host" in errors


def test_insufficient_memory_fails():
    report = valid_report()
    report["memory_mb"] = 1024

    errors = validate_host(report, "sapphros-attack")

    assert "Insufficient memory" in errors


def test_missing_reports_fail(tmp_path: Path):
    results = validate_reports(tmp_path)

    assert results["sapphros-attack"] == ["Report file is missing"]
    assert results["sapphros-core"] == ["Report file is missing"]
