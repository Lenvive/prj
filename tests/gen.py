"""Generate test data under tests/data: one 10 GiB file and a folder of 10 small files."""

from __future__ import annotations

import argparse
from pathlib import Path

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MiB
SIZE_10_GIB = 10 * 1024 * 1024 * 1024
SMALL_FILE_COUNT = 10
SMALL_FILE_SIZE = 64 * 1024  # 64 KiB
DEFAULT_LARGE_NAME = "test_10gb.bin"
DEFAULT_SMALL_DIR_NAME = "small_files"


def generate_file(
    path: Path,
    size: int,
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


def generate_small_files(
    directory: Path,
    count: int = SMALL_FILE_COUNT,
    size: int = SMALL_FILE_SIZE,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(1, count + 1):
        path = directory / f"file_{i:02d}.bin"
        generate_file(path, size, chunk_size=min(CHUNK_SIZE, size))
    print(f"Created {count} files ({size:,} bytes each) in {directory}")


def main() -> None:
    data_dir = Path(__file__).resolve().parent / "data"
    parser = argparse.ArgumentParser(description="Generate test data for PyLocalSend.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=data_dir / DEFAULT_LARGE_NAME,
        help=f"Large file path (default: tests/data/{DEFAULT_LARGE_NAME})",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=SIZE_10_GIB,
        help="Large file size in bytes (default: 10 GiB)",
    )
    parser.add_argument(
        "--small-dir",
        type=Path,
        default=data_dir / DEFAULT_SMALL_DIR_NAME,
        help=f"Directory for small files (default: tests/data/{DEFAULT_SMALL_DIR_NAME})",
    )
    parser.add_argument(
        "--small-count",
        type=int,
        default=SMALL_FILE_COUNT,
        help=f"Number of small files (default: {SMALL_FILE_COUNT})",
    )
    parser.add_argument(
        "--small-size",
        type=int,
        default=SMALL_FILE_SIZE,
        help=f"Each small file size in bytes (default: {SMALL_FILE_SIZE})",
    )
    args = parser.parse_args()

    generate_file(args.output.resolve(), args.size)
    generate_small_files(
        args.small_dir.resolve(),
        count=args.small_count,
        size=args.small_size,
    )


if __name__ == "__main__":
    main()
