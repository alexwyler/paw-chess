from __future__ import annotations

from dataclasses import dataclass

from .board import PROMO_MAP

FLAG_NONE = 0
FLAG_PROMOTION = 1 << 0
FLAG_EN_PASSANT = 1 << 1
FLAG_CASTLE = 1 << 2
FLAG_DOUBLE_PAWN = 1 << 3


@dataclass(frozen=True)
class Move:
    frm: int
    to: int
    promo: int = 0
    flags: int = FLAG_NONE

    @staticmethod
    def from_uci(uci: str) -> "Move":
        """Parse 'e2e4' or 'e7e8q' (promo)."""
        uci = uci.strip().lower()
        if len(uci) not in (4, 5):
            raise ValueError("UCI must be 4 or 5 chars")
        frm_file = ord(uci[0]) - ord("a")
        frm_rank = int(uci[1]) - 1
        to_file = ord(uci[2]) - ord("a")
        to_rank = int(uci[3]) - 1
        frm_idx = (frm_rank << 4) | frm_file
        to_idx = (to_rank << 4) | to_file
        promo = 0
        flags = FLAG_NONE
        if len(uci) == 5:
            p = uci[4]
            if p not in PROMO_MAP:
                raise ValueError("Invalid promotion piece (q/r/b/n)")
            promo = PROMO_MAP[p]
            flags |= FLAG_PROMOTION
        return Move(frm_idx, to_idx, promo, flags)
