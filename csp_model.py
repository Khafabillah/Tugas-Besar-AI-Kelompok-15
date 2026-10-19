"""
csp_model.py
Representasi murni CSP (X, D, C). Tidak tahu soal GUI maupun algoritma.

Constraint menyediakan DUA antarmuka:
  - violations(assignment): untuk mengecek assignment (parsial/penuh) -> dipakai
    Backtracking (cek saat assign) dan Min-Conflicts (hitung konflik).
  - pair_ok(a, va, b, vb): relasi BINER murni -> dipakai AC-3.
    Constraint global AtMost-1 didekomposisi menjadi relasi biner
    "tidak boleh ada dua variabel yang sama-sama bernilai Tamu".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

import config as cfg

Assignment = Dict[str, str]


@dataclass(frozen=True)
class Violation:
    kind: str                    # 'unary' | 'binary' | 'global'
    variables: Tuple[str, ...]
    message: str
    cost: int = 1


class Constraint(ABC):
    kind = "generic"

    @abstractmethod
    def violations(self, assignment: Assignment) -> List[Violation]:
        """Semua pelanggaran pada assignment (variabel kosong diabaikan)."""

    def pair_ok(self, a: str, va: str, b: str, vb: str) -> bool:
        """Relasi biner (a=va, b=vb) diperbolehkan? Default: tidak membatasi."""
        return True


class UnaryConstraint(Constraint):
    kind = "unary"

    def __init__(self, variable: str, allowed: Sequence[str]):
        self.variable = variable
        self.allowed = tuple(allowed)

    def violations(self, assignment):
        value = assignment.get(self.variable)
        if value is None or value in self.allowed:
            return []
        return [Violation("unary", (self.variable,),
                          f"{self.variable} wajib {'/'.join(self.allowed)}, bukan {value}!")]


class ForbiddenAdjacencyConstraint(Constraint):
    """Binary: dua kelompok terlarang tidak boleh bersebelahan di graf."""
    kind = "binary"

    def __init__(self, edges: Sequence[Tuple[str, str]], forbidden_pair: Tuple[str, str]):
        self.edges = list(edges)
        self._edge_set = {frozenset(e) for e in edges}
        self.forbidden = frozenset(forbidden_pair)

    def violations(self, assignment):
        out = []
        for a, b in self.edges:
            va, vb = assignment.get(a), assignment.get(b)
            if va is None or vb is None:
                continue
            if frozenset((va, vb)) == self.forbidden:
                out.append(Violation("binary", (a, b),
                                     f"{a} dan {b} bentrok! ({va} bersebelahan {vb})"))
        return out

    def pair_ok(self, a, va, b, vb):
        if frozenset((a, b)) in self._edge_set and frozenset((va, vb)) == self.forbidden:
            return False
        return True


class AtMostConstraint(Constraint):
    """Global: nilai tertentu muncul maksimal `limit` kali."""
    kind = "global"

    def __init__(self, value: str, limit: int):
        self.value = value
        self.limit = limit

    def violations(self, assignment):
        holders = [v for v in cfg.VARIABLES if assignment.get(v) == self.value]
        if len(holders) <= self.limit:
            return []
        return [Violation("global", tuple(holders),
                          f"{len(holders)} sektor diisi {self.value} "
                          f"(maks {self.limit}): {', '.join(holders)}",
                          cost=len(holders) - self.limit)]

    def pair_ok(self, a, va, b, vb):
        # Dekomposisi global -> biner hanya ekuivalen untuk limit == 1.
        if self.limit == 1 and va == self.value and vb == self.value:
            return False
        return True


def build_ring_graph(order: Sequence[str]):
    """Graf melingkar: elemen terakhir bertetangga dengan elemen pertama."""
    n = len(order)
    adjacency: Dict[str, List[str]] = {v: [] for v in order}
    edges: List[Tuple[str, str]] = []
    for i in range(n):
        a, b = order[i], order[(i + 1) % n]
        edges.append((a, b))
        adjacency[a].append(b)
        adjacency[b].append(a)
    return adjacency, edges


class CSP:
    def __init__(self, variables, domains, ring_order, adjacency, edges, constraints):
        self.variables: List[str] = list(variables)
        self.domains: Dict[str, List[str]] = {v: list(d) for v, d in domains.items()}
        self.ring_order = list(ring_order)
        self.neighbors: Dict[str, List[str]] = adjacency
        self.edges: List[Tuple[str, str]] = list(edges)
        self.constraints: List[Constraint] = list(constraints)

    # ---------- evaluasi assignment ----------
    def all_violations(self, assignment: Assignment) -> List[Violation]:
        out: List[Violation] = []
        for c in self.constraints:
            out.extend(c.violations(assignment))
        return out

    def violations_involving(self, assignment: Assignment, var: str) -> List[Violation]:
        return [v for v in self.all_violations(assignment) if var in v.variables]

    def total_conflicts(self, assignment: Assignment) -> int:
        return sum(v.cost for v in self.all_violations(assignment))

    def conflicted_variables(self, assignment: Assignment) -> Set[str]:
        out: Set[str] = set()
        for v in self.all_violations(assignment):
            out.update(v.variables)
        return out

    def is_complete(self, assignment: Assignment) -> bool:
        return all(v in assignment for v in self.variables)

    def is_solution(self, assignment: Assignment) -> bool:
        return self.is_complete(assignment) and self.total_conflicts(assignment) == 0

    # ---------- relasi biner (untuk AC-3 & LCV) ----------
    def pair_ok(self, a: str, va: str, b: str, vb: str) -> bool:
        return all(c.pair_ok(a, va, b, vb) for c in self.constraints)

    def arcs(self) -> List[Tuple[str, str]]:
        """Semua arc terarah. Karena global AtMost-1 didekomposisi ke semua
        pasangan, setiap pasangan variabel punya relasi biner."""
        return [(a, b) for a in self.variables for b in self.variables if a != b]

    # ---------- domain ----------
    def initial_domains(self) -> Dict[str, List[str]]:
        return {v: list(d) for v, d in self.domains.items()}

    def node_consistent_domains(self):
        """Pangkas domain dengan Unary Constraint. Return (domains, log)."""
        domains = self.initial_domains()
        log: List[str] = []
        for c in self.constraints:
            if isinstance(c, UnaryConstraint):
                before = domains[c.variable]
                after = [x for x in before if x in c.allowed]
                if after != before:
                    domains[c.variable] = after
                    log.append(f"Domain {c.variable} dipangkas -> {after}")
        return domains, log

    def unassigned_degree(self, var: str, assignment: Assignment) -> int:
        return sum(1 for n in self.neighbors[var] if n not in assignment)


SCENARIOS = ("standar", "utara_tamu")


def build_stadium_csp(scenario: str = "standar") -> CSP:
    """scenario 'utara_tamu' = skenario UJI opsional: Utara dipastikan Tamu
    (constraint Unary tambahan) agar propagasi AC-3 terlihat bekerja."""
    adjacency, edges = build_ring_graph(cfg.RING_ORDER)
    constraints: List[Constraint] = [
        UnaryConstraint(cfg.VIP_SECTOR, [cfg.NETRAL]),                       # (b)
        ForbiddenAdjacencyConstraint(edges, (cfg.TUAN_RUMAH, cfg.TAMU)),     # (a)
        AtMostConstraint(cfg.TAMU, cfg.MAX_TAMU_SECTORS),                    # (c)
    ]
    if scenario == "utara_tamu":
        constraints.append(UnaryConstraint("Utara", [cfg.TAMU]))
    domains = {v: list(cfg.DOMAIN) for v in cfg.VARIABLES}
    return CSP(cfg.VARIABLES, domains, cfg.RING_ORDER, adjacency, edges, constraints)
