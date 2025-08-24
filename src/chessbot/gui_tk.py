from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

from .board import (
    BISHOP,
    BLACK,
    EMPTY,
    KING,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
    Board,
    UndoSnapshot,
    idx_to_rf,
    idx_to_uci,
    piece_color,
    piece_type,
    promo_suffix,
    rf_to_idx,
)
from .engine import select_move
from .move import Move
from .movegen import generate_legal, in_check

SQUARE = 72  # pixels per square
BOARD_PX = SQUARE * 8

LIGHT = "#EEEED2"
DARK = "#769656"
HL_FROM = "#F6F669"  # selected square highlight
HL_TO = "#BACA2B"  # legal target highlight

USE_UNICODE_PIECES = True  # set False to show letters instead (e.g., 'P', 'k')

UNICODE_WHITE = {PAWN: "♙", KNIGHT: "♘", BISHOP: "♗", ROOK: "♖", QUEEN: "♕", KING: "♔"}
UNICODE_BLACK = {PAWN: "♟", KNIGHT: "♞", BISHOP: "♝", ROOK: "♜", QUEEN: "♛", KING: "♚"}


def piece_glyph(piece: int) -> str:
    if piece == EMPTY:
        return ""
    col = piece_color(piece)
    typ = piece_type(piece)
    if USE_UNICODE_PIECES:
        return (UNICODE_WHITE if col == WHITE else UNICODE_BLACK)[typ]
    # fallback: letters
    letter = {PAWN: "P", KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K"}[
        typ
    ]
    return letter if col == WHITE else letter.lower()


class ChessGUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Chessbot (Tk)")

        self.canvas = tk.Canvas(
            self.root, width=BOARD_PX, height=BOARD_PX, highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, columnspan=4)

        # Buttons
        tk.Button(self.root, text="Engine Move", command=self.engine_move).grid(
            row=1, column=0, sticky="ew"
        )
        tk.Button(self.root, text="Undo", command=self.undo).grid(
            row=1, column=1, sticky="ew"
        )
        tk.Button(self.root, text="Reset", command=self.reset).grid(
            row=1, column=2, sticky="ew"
        )
        self.depth_var = tk.IntVar(value=3)
        tk.Spinbox(self.root, from_=1, to=6, textvariable=self.depth_var, width=3).grid(
            row=1, column=3, sticky="e"
        )

        self.canvas.bind("<Button-1>", self.on_click)

        self.board = Board()
        self.history: List[UndoSnapshot] = (
            []
        )  # your push() returns immutable Previous snapshots
        self.selected: Optional[int] = None
        self.legal_from_selected: List[Move] = []

        self.draw_all()

    # ---------- drawing ----------
    def draw_all(self) -> None:
        self.canvas.delete("all")
        self._draw_squares()
        self._draw_highlights()
        self._draw_pieces()

    def _draw_squares(self) -> None:
        for r_gui in range(8):
            for f in range(8):
                x0 = f * SQUARE
                y0 = r_gui * SQUARE
                color = LIGHT if (f + r_gui) % 2 == 0 else DARK
                self.canvas.create_rectangle(
                    x0, y0, x0 + SQUARE, y0 + SQUARE, fill=color, width=0
                )

    def _draw_pieces(self) -> None:
        # Board rank 0 is the bottom (White home rank). GUI row 7 is bottom.
        for idx in range(128):
            if (idx & 0x88) != 0:
                continue
            f, r = idx_to_rf(idx)
            r_gui = 7 - r
            p = self.board.squares[idx]
            if p == EMPTY:
                continue
            glyph = piece_glyph(p)
            x = f * SQUARE + SQUARE // 2
            y = r_gui * SQUARE + SQUARE // 2
            self.canvas.create_text(
                x,
                y,
                text=glyph,
                font=("DejaVu Sans", int(SQUARE * 0.65), "bold"),
                fill="black" if piece_color(p) == BLACK else "white",
            )

    def _draw_highlights(self) -> None:
        # selected square
        if self.selected is not None:
            f, r = idx_to_rf(self.selected)
            r_gui = 7 - r
            x0, y0 = f * SQUARE, r_gui * SQUARE
            self.canvas.create_rectangle(
                x0, y0, x0 + SQUARE, y0 + SQUARE, outline=HL_FROM, width=4
            )

        # legal targets
        for m in self.legal_from_selected:
            f, r = idx_to_rf(m.to)
            r_gui = 7 - r
            x = f * SQUARE + SQUARE // 2
            y = r_gui * SQUARE + SQUARE // 2
            radius = SQUARE * 0.18
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius, fill=HL_TO, outline=""
            )

    # ---------- interaction ----------
    def on_click(self, ev: tk.Event) -> None:
        file_ = ev.x // SQUARE
        r_gui = ev.y // SQUARE
        rank = 7 - r_gui
        if not (0 <= file_ < 8 and 0 <= rank < 8):
            return
        idx = rf_to_idx(file_, rank)

        if self.selected is None:
            # select if piece of side-to-move
            p = self.board.squares[idx]
            if p != EMPTY and piece_color(p) == self.board.side_to_move:
                self.selected = idx
                self.legal_from_selected = [
                    m for m in generate_legal(self.board) if m.frm == idx
                ]
            else:
                self.selected = None
                self.legal_from_selected = []
        else:
            # second click: if it's a legal destination, make the move
            chosen = next((m for m in self.legal_from_selected if m.to == idx), None)
            if chosen is None:
                # reselect (maybe picked another piece)
                p = self.board.squares[idx]
                if p != EMPTY and piece_color(p) == self.board.side_to_move:
                    self.selected = idx
                    self.legal_from_selected = [
                        m for m in generate_legal(self.board) if m.frm == idx
                    ]
                else:
                    self.selected = None
                    self.legal_from_selected = []
            else:
                # handle promotion: if multiple legal moves to same 'to' with different promos, ask
                same_dest = [m for m in self.legal_from_selected if m.to == chosen.to]
                if any(m.promo for m in same_dest):
                    promo = self._prompt_promotion()
                    # find the matching promotion (default to queen if not found)
                    chosen = next(
                        (m for m in same_dest if (m.promo or 0) == promo), chosen
                    )

                prev = self.board.make_move(chosen.frm, chosen.to, chosen.promo or None)
                self.history.append(prev)
                self.selected = None
                self.legal_from_selected = []

                # end of move: check game over
                self._check_terminal()

        self.draw_all()

    def _prompt_promotion(self) -> int:
        # simple modal: returns piece type constant (QUEEN/ROOK/BISHOP/KNIGHT)
        win = tk.Toplevel(self.root)
        win.title("Promote to…")
        choice: dict[str, int] = {}

        def set_choice(v: int) -> None:
            choice["v"] = v
            win.destroy()

        for label, val in (
            ("Queen", QUEEN),
            ("Rook", ROOK),
            ("Bishop", BISHOP),
            ("Knight", KNIGHT),
        ):
            tk.Button(
                win, text=label, width=12, command=lambda v=val: set_choice(v)
            ).pack(padx=8, pady=4)
        win.grab_set()
        self.root.wait_window(win)
        return choice.get("v", QUEEN)

    # ---------- controls ----------
    def engine_move(self) -> None:
        ms = generate_legal(self.board)
        if not ms:
            self._check_terminal()
            return
        mv = select_move(self.board, depth=self.depth_var.get())
        prev = self.board.make_move(mv.frm, mv.to, mv.promo or None)
        self.history.append(prev)
        self.draw_all()
        self._check_terminal()

    def undo(self) -> None:
        if not self.history:
            return
        prev = self.history.pop()
        self.board.undo_move(prev)  # your Board.pop accepts the immutable snapshot
        self.selected = None
        self.legal_from_selected = []
        self.draw_all()

    def reset(self) -> None:
        self.board = Board()
        self.history.clear()
        self.selected = None
        self.legal_from_selected = []
        self.draw_all()

    def _check_terminal(self) -> None:
        side = self.board.side_to_move
        ms = generate_legal(self.board)
        if ms:
            return
        if in_check(self.board, side):
            winner = "Black" if side == WHITE else "White"
            messagebox.showinfo("Checkmate", f"Checkmate. {winner} wins.")
        else:
            messagebox.showinfo("Stalemate", "Draw by stalemate.")

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    ChessGUI().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
