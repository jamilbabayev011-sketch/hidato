"""Run the checked-in Hidato examples and a reproducible size sweep."""

import argparse
import os
from pathlib import Path
import platform
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent


def endpoint_board(size):
    """Keep the endpoints of a row-by-row snake path."""
    board = [["."] * size for _ in range(size)]
    board[0][0] = "1"
    board[-1][-1 if size % 2 else 0] = str(size * size)
    return "\n".join(" ".join(row) for row in board) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", default=os.getenv("GLUCOSE", "glucose"))
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--sizes", type=int, nargs="*", default=[4, 6, 8, 10])
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes):
        parser.error("board sizes must be at least 2")
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout must be positive and finite")

    print(f"{platform.platform()} | Python {platform.python_version()}", flush=True)
    with TemporaryDirectory(prefix="hidato-benchmark-") as directory:
        inputs = sorted((ROOT / "instances").glob("*.txt"))
        for size in args.sizes:
            path = Path(directory) / f"endpoints-{size}x{size}.txt"
            path.write_text(endpoint_board(size), encoding="ascii")
            inputs.append(path)
        for path in inputs:
            result = subprocess.run(
                [sys.executable, str(ROOT / "hidato.py"), str(path),
                 "--stats", "--solver", args.solver, "--timeout", str(args.timeout)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode not in (0, 124):
                print(result.stderr, file=sys.stderr, end="")
                return result.returncode
            for line in result.stderr.splitlines():
                if line.startswith(("CNF:", "Glucose wall time:")):
                    print(f"{path.name} | {line}", flush=True)
            print(f"{path.name} | {result.stdout.splitlines()[0]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
