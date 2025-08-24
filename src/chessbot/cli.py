from __future__ import annotations

import argparse
from typing import Optional

from .board import BLACK, WHITE, Board, idx_to_uci, on_board, promo_suffix
from .engine import select_move
from .move import Move
from .movegen import generate_legal, in_check


# basic cli i/o
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chessbot", description="Minimal UCI-like CLI."
    )
    parser.add_argument(
        "--depth", type=int, default=3, help="Search depth for the engine."
    )

    args = parser.parse_args(argv)

    if hasattr(args, "depth") and args.depth is not None:
        depth = args.depth
    else:
        depth = 4
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

            ms = generate_legal(board)
            print(
                "moves:",
                " ".join(
                    f"{idx_to_uci(m.frm)}{idx_to_uci(m.to)}{promo_suffix(m.promo)}"
                    for m in ms
                ),
            )
            continue
        if text in {"e", "engine", "go", "bot"}:
            ms = generate_legal(board)
            if not ms:
                side = board.side_to_move
                if in_check(board, side):
                    print(
                        f"No legal moves: checkmate. {'Black' if side == WHITE else 'White'} wins."
                    )
                else:
                    print("No legal moves: stalemate.")
                return 0
            mv = select_move(board, depth=depth)
            print(f"Engine plays: {move_to_uci(mv)}")
            board.make_move(mv.frm, mv.to, mv.promo or None)
            print(board)
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


def move_to_uci(m: Move) -> str:
    return f"{idx_to_uci(m.frm)}{idx_to_uci(m.to)}{promo_suffix(m.promo)}"
