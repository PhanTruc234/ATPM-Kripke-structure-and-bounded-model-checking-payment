# -*- coding: utf-8 -*-
"""
kripke.py — Cấu trúc Kripke K = (S, S0, R, L).

Cài đặt theo đúng giáo trình CSE703093, Phụ lục A.1.1 (softsec/ch1_models/kripke.py):
lớp KripkeStructure với add_state, set_initial, add_transition, successors, reachable_states,
find_path, to_tikz. Nhóm 07 bổ sung:
  - from_dict(): nạp đúng định dạng JSON mà phần mềm SpecVerificationLab/SecLabFramework dùng
    ({"states", "initial", "labeling", "transitions"}), để cùng 1 mô hình chạy được ở cả 2 nơi;
  - deadlock_states(): trạng thái không có cạnh đi ra (vi phạm tính "total" của R).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Set


@dataclass
class KripkeStructure:
    """Mô hình Kripke structure dùng cho kiểm chứng."""
    states: Set[str] = field(default_factory=set)
    initial_states: Set[str] = field(default_factory=set)
    transitions: Dict[str, Set[str]] = field(default_factory=dict)
    labels: Dict[str, Set[str]] = field(default_factory=dict)

    # ---- xây dựng mô hình (giáo trình A.1.1) ----
    def add_state(self, state: str, atomic_props: Iterable[str] = ()) -> None:
        self.states.add(state)
        self.labels.setdefault(state, set()).update(atomic_props)
        self.transitions.setdefault(state, set())

    def set_initial(self, *states: str) -> None:
        for s in states:
            if s not in self.states:
                raise ValueError(f"Trạng thái '{s}' chưa được khai báo")
            self.initial_states.add(s)

    def add_transition(self, src: str, dst: str) -> None:
        if src not in self.states or dst not in self.states:
            raise ValueError(f"Chuyển ({src} -> {dst}) tham chiếu trạng thái chưa khai báo")
        self.transitions[src].add(dst)

    # ---- truy vấn (giáo trình A.1.1) ----
    def label_of(self, state: str) -> FrozenSet[str]:
        return frozenset(self.labels.get(state, set()))

    def successors(self, state: str) -> Set[str]:
        return set(self.transitions.get(state, set()))

    def reachable_states(self) -> Set[str]:
        """Tập trạng thái đạt tới được từ S0 (BFS/DFS)."""
        visited: Set[str] = set()
        frontier: List[str] = list(self.initial_states)
        while frontier:
            s = frontier.pop()
            if s in visited:
                continue
            visited.add(s)
            for nxt in self.successors(s):
                if nxt not in visited:
                    frontier.append(nxt)
        return visited

    def is_reachable(self, target: str) -> bool:
        return target in self.reachable_states()

    def find_path(self, target: str) -> List[str] | None:
        """Đường đi ngắn nhất (BFS) từ S0 tới target — chính là counterexample."""
        for start in sorted(self.initial_states):
            visited = {start}
            queue = deque([(start, [start])])
            while queue:
                node, path = queue.popleft()
                if node == target:
                    return path
                for nxt in sorted(self.successors(node)):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append((nxt, path + [nxt]))
        return None

    def to_tikz(self) -> str:
        """Xuất TikZ (thư viện automata) để chèn vào báo cáo LaTeX."""
        lines = ["\\begin{tikzpicture}[->,>=stealth,shorten >=1pt,auto,node distance=2.5cm,semithick]"]
        for s in sorted(self.states):
            style = "initial,accepting" if s in self.initial_states else ""
            props = ",".join(sorted(self.labels.get(s, []))).replace("_", "\\_")
            lines.append(f"  \\node[state,{style}] ({s}) {{{s.replace('_', chr(92) + '_')}\\\\{{\\tiny {props}}}}};")
        for src, dsts in sorted(self.transitions.items()):
            for dst in sorted(dsts):
                lines.append(f"  \\path ({src}) edge ({dst});")
        lines.append("\\end{tikzpicture}")
        return "\n".join(lines)

    # ---- bổ sung của nhóm 07 ----
    def deadlock_states(self) -> Set[str]:
        return {s for s in self.states if not self.transitions.get(s)}

    @classmethod
    def from_dict(cls, d: dict) -> "KripkeStructure":
        k = cls()
        for s in d["states"]:
            k.add_state(s, d.get("labeling", {}).get(s, []))
        k.set_initial(*d.get("initial", []))
        for src, dst in d.get("transitions", []):
            k.add_transition(src, dst)
        return k
