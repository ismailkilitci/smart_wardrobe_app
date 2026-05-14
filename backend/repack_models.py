from __future__ import annotations

import zipfile
from pathlib import Path


def repack_torch_dir(src_dir: Path, out_file: Path) -> None:
    """Repack an extracted PyTorch zip-archive directory back into a single file.

    PyTorch expects zip entries to use forward slashes and to be under a
    top-level subdirectory (typically the original file stem).
    """

    src_dir = src_dir.resolve()
    if not src_dir.exists() or not src_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {src_dir}")

    base = src_dir.name
    out_file = out_file.resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    if out_file.exists():
        out_file.unlink()

    with zipfile.ZipFile(out_file, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(src_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(src_dir).as_posix()
                z.write(path, arcname=f"{base}/{rel}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    model_root = project_root / "backend" / "models"

    repack_torch_dir(model_root / "yolo_model", model_root / "yolo_model.pt")
    repack_torch_dir(model_root / "resnet_model", model_root / "resnet_model.pth")

    print("Repacked model files:")
    print(f"- {model_root / 'yolo_model.pt'}")
    print(f"- {model_root / 'resnet_model.pth'}")


if __name__ == "__main__":
    main()
