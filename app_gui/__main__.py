try:
    from app_gui.main import main
except ModuleNotFoundError as exc:
    if getattr(exc, "name", "") == "PySide6":
        print("PySide6 is not installed. Run: python3 -m pip install -r requirements.txt")
        raise SystemExit(1) from exc
    raise


if __name__ == "__main__":
    raise SystemExit(main())
