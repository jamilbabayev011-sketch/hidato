"""Decide and solve Hidato with a hand-written DIMACS encoding and Glucose."""

import argparse
from itertools import combinations
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter


def read_board(path):
    board = [line.split() for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line.strip()]
    if not board or any(len(row) != len(board[0]) for row in board):
        raise ValueError("expected a nonempty rectangular grid")
    cells = [(r, c) for r, row in enumerate(board) for c, token in enumerate(row)
             if token != "#"]
    if not cells:
        raise ValueError("expected at least one playable cell")
    # Look up a clue by its number. The value is its index in cells.
    clues = {}
    for i, (r, c) in enumerate(cells):
        token = board[r][c]
        if token == ".":
            continue
        if not token.isascii() or not token.isdecimal():
            raise ValueError(f"invalid token at row {r+1}, column {c+1}: {token}")
        number = int(token)
        if not 1 <= number <= len(cells) or number in clues:
            raise ValueError(f"out-of-range or repeated clue: {number}")
        clues[number] = i
    return board, cells, clues


def neighbors(cells):
    # Only playable cells are in this lookup, so it also filters out holes and edges.
    indices = {cell: i for i, cell in enumerate(cells)}
    return [[indices[r + dr, c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1)
             if (dr or dc) and (r + dr, c + dc) in indices]
            for r, c in cells]


def variable(n, i, k):
    # Give each cell a block of n IDs. DIMACS IDs start at 1.
    return i * n + k


def clauses(n, adjacent, clues):
    # Each cell gets one number and each number gets one cell.
    groups = ([variable(n, i, k) for k in range(1, n + 1)] for i in range(n))
    placements = ([variable(n, i, k) for i in range(n)] for k in range(1, n + 1))
    for group_set in (groups, placements):
        for group in group_set:
            # Pick at least one option, then rule out every pair.
            yield group
            for a, b in combinations(group, 2):
                yield (-a, -b)

    # A fixed clue needs just one literal to force its placement.
    for k, i in clues.items():
        yield (variable(n, i, k),)

    # If this cell holds k, one of its neighbors has to hold k + 1.
    for i, nearby in enumerate(adjacent):
        for k in range(1, n):
            yield [-variable(n, i, k), *(variable(n, j, k + 1) for j in nearby)]


def write_cnf(path, n, adjacent, clues):
    # DIMACS needs the clause count up front, so count before writing.
    count = 2 * n * (1 + n * (n - 1) // 2) + len(clues) + n * (n - 1)
    with path.open("w", encoding="ascii", newline="\n") as output:
        output.write(f"p cnf {n*n} {count}\n")
        for clause in clauses(n, adjacent, clues):
            # A zero marks the end of each DIMACS clause.
            output.write(" ".join(map(str, clause)) + " 0\n")
    return count


def solve(solver, cnf, timeout, stats):
    start = perf_counter()
    try:
        result = subprocess.run(
            [solver, "-model", str(cnf.resolve())], capture_output=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    finally:
        if stats:
            print(f"Glucose wall time: {perf_counter() - start:.3f} s", file=sys.stderr)
    if stats:
        for line in result.stdout.splitlines():
            if line.startswith("c"):
                print(line, file=sys.stderr)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
    # Glucose uses exit codes 10 and 20 for SAT and UNSAT.
    expected = {10: "s SATISFIABLE", 20: "s UNSATISFIABLE"}
    lines = result.stdout.splitlines()
    if result.returncode not in expected or expected[result.returncode] not in lines:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ValueError(f"unexpected Glucose output (exit {result.returncode}): {detail}")
    if result.returncode == 20:
        return None
    # The v lines contain the model. Positive IDs are the placements we keep.
    return {int(token) for line in lines if line.startswith("v ")
            for token in line.split()[1:] if int(token) > 0}


def decode(board, cells, adjacent, clues, model):
    n = len(cells)
    path = {}
    if len(model) != n:
        raise ValueError("Glucose model has an unexpected number of true variables")
    used_cells = set()
    for literal in model:
        # Undo the ID calculation to recover the cell index and number.
        i, offset = divmod(literal - 1, n)
        k = offset + 1
        if i >= n or i in used_cells or k in path:
            raise ValueError("Glucose model does not define a bijection")
        used_cells.add(i)
        path[k] = i
    if any(path[k] != i for k, i in clues.items()):
        raise ValueError("Glucose model violates a clue")
    if any(path[k + 1] not in adjacent[path[k]] for k in range(1, n)):
        raise ValueError("Glucose model violates adjacency")
    # Start from a copy so the blocked cells stay in the printed grid.
    solution = [row.copy() for row in board]
    for k, i in path.items():
        r, c = cells[i]
        solution[r][c] = str(k)
    return solution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path, help="whitespace-separated Hidato board")
    parser.add_argument("--solver", default=os.getenv("GLUCOSE", "glucose"),
                        help="Glucose 4.2.1 executable (default: GLUCOSE or glucose)")
    parser.add_argument("--cnf", type=Path, help="save the generated DIMACS file")
    parser.add_argument("--stats", action="store_true", help="show statistics on stderr")
    parser.add_argument("--timeout", type=float, help="Glucose timeout in seconds")
    args = parser.parse_args()
    if args.timeout is not None and not (0 < args.timeout < float("inf")):
        parser.error("--timeout must be positive and finite")
    try:
        if args.cnf and (args.cnf.resolve() == args.instance.resolve()
                         or (args.cnf.exists() and args.cnf.samefile(args.instance))):
            raise ValueError("--cnf must differ from the instance file")
        board, cells, clues = read_board(args.instance)
        adjacent = neighbors(cells)
        with TemporaryDirectory(prefix="hidato-") as directory:
            cnf = args.cnf or Path(directory) / "hidato.cnf"
            start = perf_counter()
            count = write_cnf(cnf, len(cells), adjacent, clues)
            if args.stats:
                print(f"CNF: {len(cells)**2} variables, {count} clauses, "
                      f"{perf_counter() - start:.3f} s to write", file=sys.stderr)
            model = solve(args.solver, cnf, args.timeout, args.stats)
        if model is None:
            print("UNSATISFIABLE")
        else:
            solution = decode(board, cells, adjacent, clues, model)
            print("SATISFIABLE")
            width = len(str(len(cells)))
            for row in solution:
                print(" ".join(f"{token:>{width}}" for token in row))
        return 0
    except subprocess.TimeoutExpired:
        print("UNKNOWN (Glucose timed out)")
        return 124
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
