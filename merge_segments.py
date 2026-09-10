#!/usr/bin/env python3
"""Merge MP4 recordings in chronological filename order without re-encoding."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    files = sorted(args.directory.glob("*.mp4"))
    if len(files) < 2:
        raise SystemExit("Need at least two MP4 files")
    manifest = args.directory / ".concat.txt"
    manifest.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in files))
    try:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "warning", "-f", "concat",
            "-safe", "0", "-i", str(manifest), "-c", "copy", "-movflags", "+faststart",
            "-y", str(args.output)
        ], check=True)
    finally:
        manifest.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
