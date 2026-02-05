from app.infrastructure.persistence.data_paths import data_dir


def uds_data_dir():
    return data_dir() / "uds"
