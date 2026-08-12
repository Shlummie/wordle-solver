from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Callable

from solver import (
    WORD_LENGTH,
    apply_feedback_history,
    choose_best_guess,
    load_solver_data,
    rank_guesses,
)


STATE_ORDER = ["b", "y", "g"]
STATE_STYLES = {
    "b": {"label": "Gray", "bg": "#787c7e", "fg": "#ffffff"},
    "y": {"label": "Yellow", "bg": "#c9b458", "fg": "#ffffff"},
    "g": {"label": "Green", "bg": "#6aaa64", "fg": "#ffffff"},
}
BLANK_TILE_STYLE = {"bg": "#d3d6da", "fg": "#1a1a1b"}


class GuessRow:
    def __init__(self, master: tk.Widget, row_number: int) -> None:
        self.row_number = row_number
        self.states = ["b"] * WORD_LENGTH
        self.tiles: list[tk.Button] = []

        self.frame = tk.Frame(master, bg="#f7f6f3")
        self.label = tk.Label(
            self.frame,
            text=f"Guess {row_number}",
            bg="#f7f6f3",
            fg="#222222",
            font=("Segoe UI", 11, "bold"),
            width=8,
            anchor="w",
        )
        self.label.grid(row=0, column=0, padx=(0, 10), pady=6, sticky="w")

        self.guess_var = tk.StringVar()
        self.guess_var.trace_add("write", self._sync_guess)
        self.entry = tk.Entry(
            self.frame,
            textvariable=self.guess_var,
            width=8,
            justify="center",
            font=("Consolas", 16, "bold"),
            relief="solid",
            bd=1,
        )
        self.entry.grid(row=0, column=1, padx=(0, 12), pady=6)

        for index in range(WORD_LENGTH):
            tile = tk.Button(
                self.frame,
                text=" ",
                width=4,
                height=2,
                font=("Consolas", 14, "bold"),
                relief="flat",
                bd=0,
                command=lambda idx=index: self.cycle_state(idx),
            )
            tile.grid(row=0, column=index + 2, padx=4, pady=6)
            self.tiles.append(tile)

        self.clear_button = tk.Button(
            self.frame,
            text="Clear",
            command=self.clear,
            bg="#ece8df",
            fg="#222222",
            activebackground="#ddd7cb",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
        )
        self.clear_button.grid(row=0, column=WORD_LENGTH + 2, padx=(12, 0), pady=6)

        self._refresh_tiles()

    def _sync_guess(self, *_: object) -> None:
        current = self.guess_var.get()
        cleaned = "".join(character for character in current.upper() if character.isalpha())
        cleaned = cleaned[:WORD_LENGTH]

        if current != cleaned:
            self.guess_var.set(cleaned)
            return

        self._refresh_tiles()

    def _refresh_tiles(self) -> None:
        letters = self.guess_var.get()

        for index, tile in enumerate(self.tiles):
            letter = letters[index] if index < len(letters) else " "
            if letter == " ":
                tile.configure(
                    text=" ",
                    bg=BLANK_TILE_STYLE["bg"],
                    fg=BLANK_TILE_STYLE["fg"],
                    activebackground=BLANK_TILE_STYLE["bg"],
                    activeforeground=BLANK_TILE_STYLE["fg"],
                )
                continue

            style = STATE_STYLES[self.states[index]]
            tile.configure(
                text=letter,
                bg=style["bg"],
                fg=style["fg"],
                activebackground=style["bg"],
                activeforeground=style["fg"],
            )

    def cycle_state(self, index: int) -> None:
        current_state = self.states[index]
        next_state_index = (STATE_ORDER.index(current_state) + 1) % len(STATE_ORDER)
        self.states[index] = STATE_ORDER[next_state_index]
        self._refresh_tiles()

    def clear(self) -> None:
        self.states = ["b"] * WORD_LENGTH
        self.guess_var.set("")

    def bind_submit(self, callback: Callable[..., str | None]) -> None:
        self.entry.bind("<Return>", callback)

    def focus(self) -> None:
        self.entry.focus_set()

    def get_history_item(self) -> tuple[str, str] | None:
        guess = self.guess_var.get().strip()
        if not guess:
            return None
        if len(guess) != WORD_LENGTH:
            raise ValueError(
                f"Guess {self.row_number} must contain exactly {WORD_LENGTH} letters."
            )
        return guess.lower(), "".join(self.states)


class WordleSolverGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Wordle Solver")
        self.root.configure(bg="#f7f6f3")
        self.root.minsize(930, 620)

        try:
            self.answers, self.allowed_guesses = load_solver_data()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Word List Error", str(exc))
            self.root.destroy()
            raise SystemExit(1) from exc

        self.rows: list[GuessRow] = []
        self.remaining_var = tk.StringVar()
        self.best_guess_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.preview_var = tk.StringVar()

        self._build_layout()
        self.reset_board()

    def _build_layout(self) -> None:
        shell = tk.Frame(self.root, bg="#f7f6f3", padx=24, pady=24)
        shell.pack(fill="both", expand=True)

        title = tk.Label(
            shell,
            text="Wordle Solver",
            bg="#f7f6f3",
            fg="#1a1a1b",
            font=("Segoe UI", 22, "bold"),
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            shell,
            text="Type a guess, then click each tile until it matches Wordle: gray, yellow, or green.",
            bg="#f7f6f3",
            fg="#444444",
            font=("Segoe UI", 11),
        )
        subtitle.pack(anchor="w", pady=(4, 18))

        board = tk.Frame(shell, bg="#ffffff", padx=20, pady=20, relief="solid", bd=1)
        board.pack(fill="x")

        hint = tk.Label(
            board,
            text="Tile order cycles Gray -> Yellow -> Green. Empty rows are ignored.",
            bg="#ffffff",
            fg="#555555",
            font=("Segoe UI", 10),
        )
        hint.pack(anchor="w", pady=(0, 10))

        rows_frame = tk.Frame(board, bg="#ffffff")
        rows_frame.pack(fill="x")

        for row_number in range(1, 7):
            row = GuessRow(rows_frame, row_number)
            row.frame.pack(fill="x")
            row.bind_submit(self._handle_submit)
            self.rows.append(row)

        controls = tk.Frame(board, bg="#ffffff")
        controls.pack(fill="x", pady=(12, 0))

        update_button = tk.Button(
            controls,
            text="Update Suggestions",
            command=self.solve,
            bg="#1f6feb",
            fg="#ffffff",
            activebackground="#1558b0",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
        )
        update_button.pack(side="left")

        reset_button = tk.Button(
            controls,
            text="Reset Board",
            command=self.reset_board,
            bg="#ece8df",
            fg="#222222",
            activebackground="#ddd7cb",
            relief="flat",
            bd=0,
            padx=16,
            pady=10,
        )
        reset_button.pack(side="left", padx=(10, 0))

        results = tk.Frame(shell, bg="#f7f6f3")
        results.pack(fill="both", expand=True, pady=(18, 0))
        results.grid_columnconfigure(0, weight=1)
        results.grid_columnconfigure(1, weight=1)
        results.grid_rowconfigure(1, weight=1)

        summary = tk.Frame(results, bg="#f7f6f3")
        summary.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        remaining = tk.Label(
            summary,
            textvariable=self.remaining_var,
            bg="#f7f6f3",
            fg="#1a1a1b",
            font=("Segoe UI", 14, "bold"),
        )
        remaining.pack(anchor="w")

        best_guess = tk.Label(
            summary,
            textvariable=self.best_guess_var,
            bg="#f7f6f3",
            fg="#1a1a1b",
            font=("Segoe UI", 12),
        )
        best_guess.pack(anchor="w", pady=(2, 0))

        status = tk.Label(
            summary,
            textvariable=self.status_var,
            bg="#f7f6f3",
            fg="#555555",
            font=("Segoe UI", 10),
        )
        status.pack(anchor="w", pady=(2, 0))

        guesses_panel = tk.Frame(results, bg="#ffffff", padx=16, pady=16, relief="solid", bd=1)
        guesses_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        guesses_title = tk.Label(
            guesses_panel,
            text="Top Next Guesses",
            bg="#ffffff",
            fg="#1a1a1b",
            font=("Segoe UI", 12, "bold"),
        )
        guesses_title.pack(anchor="w", pady=(0, 10))

        self.guesses_list = tk.Listbox(
            guesses_panel,
            font=("Consolas", 12),
            relief="flat",
            height=12,
            activestyle="none",
        )
        self.guesses_list.pack(fill="both", expand=True)

        candidates_panel = tk.Frame(
            results, bg="#ffffff", padx=16, pady=16, relief="solid", bd=1
        )
        candidates_panel.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        candidates_title = tk.Label(
            candidates_panel,
            textvariable=self.preview_var,
            bg="#ffffff",
            fg="#1a1a1b",
            font=("Segoe UI", 12, "bold"),
        )
        candidates_title.pack(anchor="w", pady=(0, 10))

        self.candidates_list = tk.Listbox(
            candidates_panel,
            font=("Consolas", 12),
            relief="flat",
            height=12,
            activestyle="none",
        )
        self.candidates_list.pack(fill="both", expand=True)

    def _handle_submit(self, _event: tk.Event[tk.Entry]) -> str | None:
        self.solve()
        return "break"

    def reset_board(self) -> None:
        for row in self.rows:
            row.clear()

        self.status_var.set("No feedback entered yet. These are the best opening guesses.")
        self.solve()
        self.rows[0].focus()

    def _collect_history(self) -> list[tuple[str, str]]:
        history: list[tuple[str, str]] = []

        for row in self.rows:
            item = row.get_history_item()
            if item is None:
                continue
            history.append(item)

        return history

    def _fill_listbox(self, listbox: tk.Listbox, rows: list[str]) -> None:
        listbox.delete(0, tk.END)

        for row in rows:
            listbox.insert(tk.END, row)

    def solve(self) -> None:
        try:
            history = self._collect_history()
        except ValueError as exc:
            messagebox.showerror("Invalid Guess", str(exc))
            return

        candidates = apply_feedback_history(self.answers, history)
        ranked_guesses = rank_guesses(candidates, self.allowed_guesses, limit=10)
        best_guess = choose_best_guess(candidates, self.allowed_guesses)

        self.remaining_var.set(f"Remaining candidates: {len(candidates)}")
        self.best_guess_var.set(
            f"Best next guess: {best_guess.upper()}" if best_guess else "Best next guess: none"
        )

        if not history:
            self.status_var.set("No feedback entered yet. These are the best opening guesses.")
        elif not candidates:
            self.status_var.set("No candidates match the current feedback.")
        else:
            self.status_var.set(f"Applied {len(history)} guess history rows.")

        guess_lines = []
        for index, (guess, entropy) in enumerate(ranked_guesses, start=1):
            marker = " *" if guess in candidates else ""
            guess_lines.append(f"{index:>2}. {guess.upper()}  {entropy:0.3f}{marker}")
        if not guess_lines:
            guess_lines = ["No ranked guesses available."]
        self._fill_listbox(self.guesses_list, guess_lines)

        if candidates:
            preview_count = min(25, len(candidates))
            self.preview_var.set(f"Candidate Preview ({preview_count} shown)")
            preview_lines = [word.upper() for word in candidates[:preview_count]]
        else:
            self.preview_var.set("Candidate Preview")
            preview_lines = ["No candidates remain."]
        self._fill_listbox(self.candidates_list, preview_lines)


def main() -> int:
    root = tk.Tk()
    WordleSolverGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
