from __future__ import annotations

import argparse
from pathlib import Path

from exam_materials_lib import iter_preprocessed_images, iter_raw_image_files, preprocessed_dir


MISSING_PILLOW = "Missing optional dependency: Pillow. Install with: python3 -m pip install Pillow"


def output_path_for(source: Path, output_dir: Path) -> Path:
    return output_dir / f"{source.stem}_ocr.png"


def input_images(root: Path) -> list[Path]:
    images = iter_raw_image_files(root)
    images.extend(path for path in iter_preprocessed_images(root) if not path.stem.endswith("_ocr"))
    return sorted(set(images))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="exam_materials")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--grayscale", action="store_true")
    parser.add_argument("--contrast", action="store_true")
    parser.add_argument("--binarize", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    output_dir = preprocessed_dir(root)
    images = input_images(root)
    targets = [output_path_for(path, output_dir) for path in images]
    skipped = sum(1 for target in targets if target.exists() and not args.force)

    if args.dry_run:
        print(f"input images found: {len(images)}")
        print(f"outputs planned: {len(targets) - skipped}")
        print(f"output folder: {output_dir}")
        print(f"skipped files: {skipped}")
        print("dry-run: no files written")
        return

    try:
        from PIL import Image, ImageOps, ImageEnhance
    except ImportError:
        print(MISSING_PILLOW)
        raise SystemExit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for source, target in zip(images, targets, strict=True):
        if target.exists() and not args.force:
            continue
        with Image.open(source) as image:
            processed = ImageOps.exif_transpose(image)
            if args.grayscale or args.binarize:
                processed = processed.convert("L")
            else:
                processed = processed.convert("RGB")
            if args.contrast:
                processed = ImageEnhance.Contrast(processed).enhance(1.5)
            if args.binarize:
                processed = processed.point(lambda pixel: 255 if pixel > 180 else 0)
            processed.save(target, format="PNG")
            written += 1

    print(f"input images found: {len(images)}")
    print(f"outputs written: {written}")
    print(f"output folder: {output_dir}")
    print(f"skipped files: {skipped}")


if __name__ == "__main__":
    main()
