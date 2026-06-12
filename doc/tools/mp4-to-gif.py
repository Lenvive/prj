#!/usr/bin/env python3
"""将 MP4/WebM 转为 GIF（依赖 ffmpeg）。

推荐配合 svg-to-video.html 使用：

    python doc/tools/mp4-to-gif.py input.mp4 -o output.gif --fps 15 --width 960
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_FPS = 15
DEFAULT_WIDTH = 960
DEFAULT_COLORS = 256
DEFAULT_DITHER = "bayer"
DEFAULT_BAYER_SCALE = 3


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        sys.exit("未找到 ffmpeg，请先安装并加入 PATH。")
    return path


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("必须大于或等于 0")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return parsed


def scale_filter(width: int | None, height: int | None) -> str:
    if width and height:
        return (
            f"scale={width}:{height}:flags=lanczos:"
            "force_original_aspect_ratio=decrease"
        )
    if width:
        return f"scale={width}:-1:flags=lanczos"
    if height:
        return f"scale=-1:{height}:flags=lanczos"
    return "scale=iw:ih:flags=lanczos"


def build_filter(
    *,
    fps: int,
    width: int | None,
    height: int | None,
    colors: int,
    dither: str,
    bayer_scale: int,
) -> str:
    paletteuse = f"[s1][p]paletteuse=dither={dither}"
    if dither == "bayer":
        paletteuse += f":bayer_scale={bayer_scale}"

    return (
        f"fps={fps},{scale_filter(width, height)},split[s0][s1];"
        f"[s0]palettegen=max_colors={colors}:stats_mode=diff[p];"
        f"{paletteuse}"
    )


def convert(
    src: Path,
    dst: Path | None,
    *,
    fps: int = DEFAULT_FPS,
    width: int | None = DEFAULT_WIDTH,
    height: int | None = None,
    loop: int = 0,
    start: float | None = None,
    duration: float | None = None,
    colors: int = DEFAULT_COLORS,
    dither: str = DEFAULT_DITHER,
    bayer_scale: int = DEFAULT_BAYER_SCALE,
    overwrite: bool = True,
    dry_run: bool = False,
) -> Path:
    if not src.is_file():
        raise FileNotFoundError(src)

    dst = dst or src.with_suffix(".gif")
    dst.parent.mkdir(parents=True, exist_ok=True)

    vf = build_filter(
        fps=fps,
        width=width,
        height=height,
        colors=colors,
        dither=dither,
        bayer_scale=bayer_scale,
    )

    cmd = [
        require_ffmpeg(),
        "-y" if overwrite else "-n",
    ]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += [
        "-i",
        str(src),
    ]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf",
        vf,
        "-loop",
        str(loop),
        str(dst),
    ]

    print("运行命令：")
    print(" ".join(f'"{part}"' if " " in part else part for part in cmd))
    if not dry_run:
        subprocess.run(cmd, check=True)
    return dst


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MP4/WebM → GIF（ffmpeg palette 优化）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="输入视频文件")
    parser.add_argument("-o", "--output", type=Path, help="输出 GIF（仅单文件时有效）")
    parser.add_argument("--fps", type=positive_int, default=DEFAULT_FPS, help="GIF 帧率")
    parser.add_argument("--width", type=positive_int, default=DEFAULT_WIDTH, help="输出宽度，高度等比")
    parser.add_argument("--height", type=positive_int, help="输出高度，高度优先级低于同时指定的宽高框")
    parser.add_argument("--loop", type=int, default=0, help="循环次数，0=无限")
    parser.add_argument("--start", type=non_negative_float, help="从第几秒开始截取")
    parser.add_argument("--duration", type=positive_float, help="截取时长，单位秒")
    parser.add_argument("--colors", type=positive_int, default=DEFAULT_COLORS, help="GIF 调色板颜色数")
    parser.add_argument(
        "--dither",
        choices=["bayer", "floyd_steinberg", "sierra2", "sierra2_4a", "none"],
        default=DEFAULT_DITHER,
        help="抖动算法",
    )
    parser.add_argument("--bayer-scale", type=positive_int, default=DEFAULT_BAYER_SCALE, help="bayer 抖动强度")
    parser.add_argument("--no-overwrite", action="store_true", help="输出文件存在时不覆盖")
    parser.add_argument("--dry-run", action="store_true", help="只打印 ffmpeg 命令，不执行")
    args = parser.parse_args()

    if len(args.inputs) > 1 and args.output:
        sys.exit("批量转换时不要指定 -o。")
    if args.colors > 256:
        sys.exit("GIF 调色板最多支持 256 色。")

    for src in args.inputs:
        out = args.output if len(args.inputs) == 1 else None
        result = convert(
            src,
            out,
            fps=args.fps,
            width=args.width,
            height=args.height,
            loop=args.loop,
            start=args.start,
            duration=args.duration,
            colors=args.colors,
            dither=args.dither,
            bayer_scale=args.bayer_scale,
            overwrite=not args.no_overwrite,
            dry_run=args.dry_run,
        )
        print(f"输出：{result}")


if __name__ == "__main__":
    main()
