# Hidato with Glucose SAT

## Decision problem

Given a rectangular grid with playable cells $C$, let $n=|C|\ge 1$. The input includes a partial clue map $g:C\rightharpoonup \{1,\ldots,n\}$. Blocked cells are outside $C$. The question is whether there exists a bijection $f:C\to\{1,\ldots,n\}$ satisfying both conditions.

- $f(c)=g(c)$ for every clue cell $c$.
- For each $k=1,\ldots,n-1$, write $f^{-1}(k)=(r,c)$ and $f^{-1}(k+1)=(r',c')$. Require $\max(|r-r'|,|c-c'|)=1$.

This is a decision problem. A satisfying assignment gives one completed board, and multiple completions are allowed.

## CNF encoding

Index playable cells $i=0,\ldots,n-1$ in row-major order. Variable $x_{i,k}$ means cell $i$ contains $k$, with DIMACS identifier $in+k$.

1. For each cell, require exactly one number. For each number, require exactly one cell. Each exactly-one constraint uses one disjunction of the group and a pairwise clause $\neg a\lor\neg b$ for every pair of variables in it.
2. A clue $k$ at cell $i$ gives the unit clause $x_{i,k}$.
3. For every cell $i$ and $k<n$, add $\neg x_{i,k}\lor\bigvee_{j\in N(i)}x_{j,k+1}$, where $N(i)$ contains the playable horizontal, vertical and diagonal neighbors. An empty neighborhood gives the unit clause $\neg x_{i,k}$.

The exactly-one clauses turn any satisfying assignment into a bijection. The clue and successor clauses give the remaining puzzle rules. Conversely, any Hidato completion satisfies every clause when exactly its cell-number pairs are true.

For $m$ clues the DIMACS file has $n^2$ variables and $2n(1+\binom{n}{2})+m+n(n-1)=n^3+n+m$ clauses. The Python script writes the clauses directly with the standard library and streams them to disk. A sequential-counter encoding could reduce the exactly-one constraints to linear clauses per group by adding auxiliary variables. Another option is to remove cell-number candidates whose graph distance from a clue exceeds the difference between the two numbers.

## Run the solver

Use Python 3.10 or newer and the single-threaded executable from [Glucose 4.2.1](https://github.com/audemard/glucose/releases/tag/4.2.1). On Linux or WSL, build the official source with CMake, a C++ compiler and zlib development headers. Run these commands from the extracted Glucose source directory.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build --target glucose-simp
```

Run the solver from the Hidato project directory.

```sh
python3 hidato.py instances/small-sat.txt --solver /path/to/glucose/build/glucose-simp
python3 hidato.py instances/small-unsat.txt --solver /path/to/glucose/build/glucose-simp --cnf board.cnf --stats
```

On the Windows development machine, the locally built executable is in the Git-ignored `.local` directory. If you have that build and installed Python through uv, use the following PowerShell command.

```powershell
& (uv python find 3.12) hidato.py instances/small-sat.txt --solver .\.local\glucose.exe
```

The input is a whitespace-separated grid, with one row per line and equal numbers of tokens per row. Use `.` for a blank, `#` for a blocked cell and an integer from 1 to $n$ for a clue. Clues must be distinct. Blank lines are ignored. Endpoint clues are optional.

- `--solver PATH` selects the Glucose executable. The default is the `GLUCOSE` environment variable or `glucose` on PATH.
- `--cnf PATH` saves the generated DIMACS CNF file. Without it, the formula is stored in a temporary directory.
- `--stats` writes the CNF size, encoding time, Glucose wall time and available solver statistics to stderr.
- `--timeout SECONDS` limits the time spent in Glucose.

The script prints `SATISFIABLE` and a completed grid, or `UNSATISFIABLE` when the puzzle has no completion. Both decisions exit with status 0. A timeout prints `UNKNOWN (Glucose timed out)` and exits with status 124. Input and solver errors exit with status 2.

## Included instances

| File | Expected | Reason |
| --- | --- | --- |
| `small-sat.txt` | SAT | The eight playable cells can be numbered clockwise around the blocked center, starting at the top left. |
| `small-unsat.txt` | UNSAT | Clues 1 and 2 are two columns apart, so there is no legal step between them. |
| `hard-12x12.txt` | SAT | A row-by-row snake connects the upper-left clue 1 to the lower-left clue 144. Glucose took 33.677 s in the size sweep. |

## Experiments

`benchmark.py` runs the included instances and generates square boards with the two endpoints of a known snake path as clues. It reports encoding and solver wall times separately. Wall times include Glucose process startup, loading, preprocessing and search. The solver checks the decoded path before reporting SAT.

```sh
python3 benchmark.py --solver /path/to/glucose/build/glucose-simp \
  --timeout 35 --sizes 4 6 8 10 11 13 14
```

Measured with Python 3.12.13 and a native Windows build of Glucose 4.2.1 on an Intel Core i7-13650HX. The local solver was built from the upstream tag with Windows compatibility changes for POSIX timing, resource limits and output functions. The search code used the upstream defaults. Times are from individual runs with 35- or 45-second cutoffs.

| Board | Variables | Clauses | Write (s) | Glucose wall (s) | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| Small SAT | 64 | 524 | 0.002 | 0.133 | SAT |
| Small UNSAT | 64 | 523 | 0.001 | 0.029 | UNSAT |
| 4x4 | 256 | 4,114 | 0.004 | 0.032 | SAT |
| 6x6 | 1,296 | 46,694 | 0.025 | 0.053 | SAT |
| 8x8 | 4,096 | 262,210 | 0.128 | 0.208 | SAT |
| 10x10 | 10,000 | 1,000,102 | 0.477 | 1.270 | SAT |
| 11x11 | 14,641 | 1,771,684 | 0.833 | 1.986 | SAT |
| 12x12 | 20,736 | 2,986,130 | 1.410 | 33.677 | SAT |
| 13x13 | 28,561 | 4,826,980 | 2.332 | 2.444 | SAT |
| 14x14 | 38,416 | 7,529,734 | 3.483 | 35.047 | Timeout |

The largest completed board in this sweep was 13x13. The endpoint placement and solver search both vary across sizes, and the measured runtimes vary accordingly. A separate run of the checked-in 12x12 board returned SAT in 34.241 s and reported 262,815 conflicts.
