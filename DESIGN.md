# Hidato design notes

The first design step is to define the board and the rules that a completed board must satisfy.

## Board and goal

The input is a rectangular grid. A dot is an empty playable cell, a hash is a blocked cell, and a number is a fixed clue. If there are n playable cells, a completed board must use each number from 1 through n exactly once. Consecutive numbers must touch horizontally, vertically, or diagonally.

## Check the rules by hand

This board has two playable cells.

```text
1 #
# .
```

The bottom-right cell must contain 2. It touches 1 diagonally, so the board is satisfiable.

This board also has two playable cells.

```text
1 # 2
```

The two cells are separated by a blocked cell. No legal step connects them, so the board is unsatisfiable.

## Plan the implementation

1. Read the grid, validate clues, and list each playable cell's neighbors.
2. Use one Boolean variable for each possible cell and number pair. Write clauses for the placement rules, clues, and consecutive steps.
3. Save the clauses as DIMACS, run Glucose, and convert its answer into a completed grid or an UNSAT result.
4. Check both small cases and measure a larger satisfiable board.
