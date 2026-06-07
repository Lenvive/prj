"""Generate a 2 GiB test file under tests/data."""

from __future__ import annotations

import argparse
from pathlib import Path

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB
SIZE_10_GIB = 10 * 1024 * 1024 * 1024
DEFAULT_NAME = "test_10gb.bin"


def generate_file(
    path: Path,
    size: int = SIZE_10_GIB,
    chunk_size: int = CHUNK_SIZE,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    block = b"\x00" * chunk_size
    written = 0
    with path.open("wb") as f:
        while written < size:
            n = min(chunk_size, size - written)
            f.write(block if n == chunk_size else block[:n])
            written += n
    print(f"Wrote {written:,} bytes ({written / (1024**3):.2f} GiB) -> {path}")


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    parser = argparse.ArgumentParser(description="Generate large test files.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=data_dir / DEFAULT_NAME,
        help=f"Output path (default: tests/data/{DEFAULT_NAME})",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=SIZE_10_GIB,
        help="File size in bytes (default: 10 GiB)",
    )
    args = parser.parse_args()
    generate_file(args.output.resolve(), args.size)


if __name__ == "__main__":
    main()
