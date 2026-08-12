# Wordle Solver

A dependency-free Python solving engine with both CLI and Tkinter interfaces. It scores duplicate letters correctly, filters candidates from feedback history, and ranks next guesses by expected information gain.

## Feedback notation

- `g` — correct letter in the correct position (green)
- `y` — letter exists in another position (yellow)
- `b` — no remaining unmatched occurrence of that letter (gray/black)

Duplicate letters are resolved in two passes: exact matches consume positions first, then remaining letter counts decide yellow matches. This mirrors the important repeated-letter behavior of the game.

## Solver pipeline

```text
answer list + allowed probes -> feedback history -> candidate filter
remaining candidates -> feedback partitions per guess -> Shannon entropy ranking
```

For large candidate sets, a letter/position-frequency heuristic creates a bounded probe pool before the full entropy calculation. Small sets are ranked across the complete allowed list.

## Run

Requirements: Python 3.10+. The solver and GUI use only the standard library.

```bash
python gui.py
```

or on Windows, run `start_solver.bat`.

CLI examples:

```bash
python solver.py --top 10
python solver.py --guess crane --feedback bybbb --top 10
python solver.py --guess crane --feedback bybbb --guess storm --feedback bbyyy
```

Custom word lists:

```bash
python solver.py --answers-file path\answers.txt --allowed-file path\probes.txt
```

One lowercase or uppercase five-letter alphabetic word is expected per line.

## Tests

```bash
python -m unittest discover -v
```

The tests cover duplicate letters in guesses and answers, exact/no-match feedback, multi-round filtering, and entropy tie-breaking.

## Word-list boundary

The repository contains a deliberately small original demonstration list, not an official game corpus. It proves the workflow but is not exhaustive. Supply a word corpus that you are entitled to use for broader solving.

This project is unaffiliated with the game or its owners. Names and marks belong to their respective owners.

## License

Original source and the small example word lists are MIT licensed.
