# -*- coding: utf-8 -*-
"""
bounded_checker.py — Bounded Model Checker (BMC) mini trên KripkeStructure.

Cài đặt theo đúng giáo trình CSE703093, Phụ lục A.3.3 (Listing A.11,
softsec/ch3_staticsat/bounded_checker.py). Ý tưởng BMC (mục 3.5): kiểm tra có tồn tại
đường đi độ dài TỐI ĐA k bước từ S0 tới một "trạng thái xấu" hay không. Kết quả "không vi phạm"
chỉ tin cậy trong phạm vi k, TRỪ KHI đã đạt completeness threshold (đã duyệt hết mọi trạng thái
đạt tới được) — khi đó kết luận an toàn là đầy đủ.

Thay đổi duy nhất so với giáo trình: import KripkeStructure từ module kripke.py cùng thư mục.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from kripke import KripkeStructure


@dataclass
class BMCResult:
    violated: bool
    counterexample: Optional[List[str]]   # đường đi từ S0 tới bad state, None nếu không vi phạm
    k: int
    reached_completeness_threshold: bool  # True nếu đã xét hết reachable states trước khi hết k


def bmc_check(model: "KripkeStructure", bad_states: Set[str], k: int) -> BMCResult:
    """Có tồn tại đường đi dài tối đa k bước từ S0 tới một trạng thái trong bad_states không?"""
    # Vi phạm ngay tại trạng thái khởi tạo (bước 0)
    for s0 in model.initial_states:
        if s0 in bad_states:
            return BMCResult(True, [s0], k, reached_completeness_threshold=True)

    visited: Set[str] = set(model.initial_states)
    frontier = [(s, [s]) for s in sorted(model.initial_states)]
    step = 0
    while frontier and step < k:
        next_frontier = []
        for state, path in frontier:
            for nxt in sorted(model.successors(state)):
                if nxt in bad_states:
                    return BMCResult(True, path + [nxt], k, reached_completeness_threshold=True)
                if nxt not in visited:
                    visited.add(nxt)
                    next_frontier.append((nxt, path + [nxt]))
        frontier = next_frontier
        step += 1

    # Còn frontier chưa duyệt khi hết k bước -> chưa đạt completeness threshold
    reached_ct = len(frontier) == 0
    return BMCResult(False, None, k, reached_completeness_threshold=reached_ct)


def find_completeness_threshold(model: "KripkeStructure", max_k: int = 1000) -> Optional[int]:
    """k nhỏ nhất sao cho BFS từ S0 đã chạm MỌI trạng thái đạt tới được
    (= độ sâu lớn nhất của đường đi ngắn nhất từ S0 — reachability diameter)."""
    total_reachable = len(model.reachable_states())
    visited: Set[str] = set(model.initial_states)
    frontier = list(model.initial_states)
    if len(visited) == total_reachable:
        return 0
    for k in range(1, max_k + 1):
        next_frontier = []
        for state in frontier:
            for nxt in model.successors(state):
                if nxt not in visited:
                    visited.add(nxt)
                    next_frontier.append(nxt)
        frontier = next_frontier
        if len(visited) == total_reachable:
            return k
        if not frontier:
            return k
    return None
