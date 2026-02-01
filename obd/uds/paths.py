from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def uds_data_dir() -> Path:
    return project_root() / "data" / "uds"
