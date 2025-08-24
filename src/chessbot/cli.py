from __future__ import annotations

import argparse
from typing import Optional

from .board import Board, idx_to_uci, on_board, promo_suffix
from .move import Move


# basic cli i/o
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chessbot", description="Minimal UCI-like CLI."
    )
    args = parser.parse_args(argv)

    board = Board()
    print(board)
    print("Enter UCI moves like e2e4, g8f6, or 'quit'.")

    while True:
        try:
            text = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if text in {"q", "quit", "exit"}:
            print("bye")
            return 0
        if text in {"m", "moves"}:
            from .movegen import generate_legal

            ms = generate_legal(board)
            print(
                "moves:",
                " ".join(
                    f"{idx_to_uci(m.frm)}{idx_to_uci(m.to)}{promo_suffix(m.promo)}"
                    for m in ms
                ),
            )
            continue
        if not text:
            continue
        try:
            mv = Move.from_uci(text)
        except Exception as e:  # noqa: BLE001 (fine for CLI)
            print(f"parse error: {e}")
            continue

        # Very light checks for now
        if not (on_board(mv.frm) and on_board(mv.to)):
            print("off-board square")
            continue
        if board.piece_at(mv.frm) == 0:
            print("no piece on source square")
            continue

        undo_snapshot = board.make_move(mv.frm, mv.to, mv.promo or None)
        print(board)
    return 0
