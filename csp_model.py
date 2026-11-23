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
    pairwise = False

    @abstractmethod
    def violations(self, assignment: Assignment, counter=None) -> List[Violation]:
        """Semua pelanggaran pada assignment (variabel kosong diabaikan)."""

    def pair_ok(self, a: str, va: str, b: str, vb: str) -> bool:
        """Relasi biner (a=va, b=vb) diperbolehkan? Default: tidak membatasi."""
        return True


class UnaryConstraint(Constraint):
    kind = "unary"

    def __init__(self, variable: str, allowed: Sequence[str]):
        self.variable = variable
        self.allowed = tuple(allowed)

    def violations(self, assignment, counter=None):
        value = assignment.get(self.variable)
        if value is None:
            return []
        if counter is not None:
            counter["constraint_checks"] += 1
        if value in self.allowed:
            return []
        return [Violation("unary", (self.variable,),
                          f"{self.variable} wajib {'/'.join(self.allowed)}, bukan {value}!")]


class ForbiddenAdjacencyConstraint(Constraint):
    """Binary: pasangan nilai terlarang tidak boleh bersebelahan di graf."""
    kind = "binary"
    pairwise = True

    def __init__(self, edges: Sequence[Tuple[str, str]],
                 forbidden_pairs: Sequence[Tuple[str, str]]):
        self.edges = list(edges)
        self._edge_set = {frozenset(e) for e in edges}
        self.forbidden = [frozenset(p) for p in forbidden_pairs]

    def _bad(self, va, vb) -> bool:
        return frozenset((va, vb)) in self.forbidden

    def violations(self, assignment, counter=None):
        out = []
        for a, b in self.edges:
            va, vb = assignment.get(a), assignment.get(b)
            if va is None or vb is None:
                continue
            if counter is not None:
                counter["constraint_checks"] += 1
            if self._bad(va, vb):
                out.append(Violation("binary", (a, b),
                                     f"{a} dan {b} bentrok! ({va} bersebelahan {vb})"))
        return out

    def pair_ok(self, a, va, b, vb):
        return not (frozenset((a, b)) in self._edge_set and self._bad(va, vb))


class AtMostConstraint(Constraint):
    """Global: nilai tertentu muncul maksimal `limit` kali."""
    kind = "global"

    def __init__(self, value: str, limit: int, variables=None):
        self.value = value
        self.limit = limit
        self.variables = list(variables if variables is not None else cfg.VARIABLES)
        self.pairwise = limit == 1

    def violations(self, assignment, counter=None):
        if counter is not None:
            counter["constraint_checks"] += 1
        holders = [v for v in self.variables if assignment.get(v) == self.value]
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
        self.pair_constraints = [c for c in self.constraints if c.pairwise]
        self.reset_counters()

    def reset_counters(self):
        """Reset operation counts used by headless experiments."""
        self.check_counters = {"constraint_checks": 0, "pair_checks": 0,
                               "assignment_checks": 0, "unary_checks": 0}

    # ---------- evaluasi assignment ----------
    def all_violations(self, assignment: Assignment, *, count=True) -> List[Violation]:
        if count:
            self.check_counters["assignment_checks"] += 1
        out: List[Violation] = []
        for c in self.constraints:
            out.extend(c.violations(assignment, counter=self.check_counters if count else None))
        return out

    def violations_involving(self, assignment: Assignment, var: str, *, count=True) -> List[Violation]:
        return [v for v in self.all_violations(assignment, count=count) if var in v.variables]

    def total_conflicts(self, assignment: Assignment, *, count=True) -> int:
        return sum(v.cost for v in self.all_violations(assignment, count=count))

    def conflicted_variables(self, assignment: Assignment, *, count=True) -> Set[str]:
        out: Set[str] = set()
        for v in self.all_violations(assignment, count=count):
            out.update(v.variables)
        return out

    def is_complete(self, assignment: Assignment) -> bool:
        return all(v in assignment for v in self.variables)

    def is_solution(self, assignment: Assignment) -> bool:
        return self.is_complete(assignment) and self.total_conflicts(assignment) == 0

    # ---------- relasi biner (untuk AC-3 & LCV) ----------
    def pair_ok(self, a: str, va: str, b: str, vb: str, *, count=True) -> bool:
        if count:
            self.check_counters["pair_checks"] += 1
        for c in self.pair_constraints:
            if count:
                self.check_counters["constraint_checks"] += 1
            if not c.pair_ok(a, va, b, vb):
                return False
        return True

    def constraint_graph(self, domains: Dict[str, List[str]]) -> Dict[str, Set[str]]:
        """Graf constraint: a--b bila ADA pasangan nilai (x in D(a), y in D(b))
        yang dilarang. Hanya pasangan ini yang perlu menjadi arc di AC-3
        (global AtMost-1 menghubungkan semua variabel yang masih bisa bernilai Tamu)."""
        graph: Dict[str, Set[str]] = {v: set() for v in self.variables}
        for a in self.variables:
            for b in self.variables:
                if a != b and any(not self.pair_ok(a, x, b, y)
                                  for x in domains[a] for y in domains[b]):
                    graph[a].add(b)
        return graph

    def use_constraint_graph_for_degree(self, domains=None):
        """Use active binary constraints for the MRV degree tie-break."""
        if domains is None:
            domains, _ = self.node_consistent_domains()
        graph = self.constraint_graph(domains)
        order = {v: i for i, v in enumerate(self.variables)}
        self.neighbors = {v: sorted(graph[v], key=order.get) for v in self.variables}
        self.reset_counters()

    def arcs(self, graph: Dict[str, Set[str]]) -> List[Tuple[str, str]]:
        return [(a, b) for a in self.variables for b in self.variables if b in graph[a]]

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
                self.check_counters["unary_checks"] += len(before)
                self.check_counters["constraint_checks"] += len(before)
                after = [x for x in before if x in c.allowed]
                if after != before:
                    domains[c.variable] = after
                    log.append(f"Domain {c.variable} dipangkas -> {after}")
        return domains, log

    def unassigned_degree(self, var: str, assignment: Assignment) -> int:
        return sum(1 for n in self.neighbors[var] if n not in assignment)


SCENARIOS = ("standar", "longgar")


def build_stadium_csp(scenario: str = "standar") -> CSP:
    adjacency, edges = build_ring_graph(cfg.RING_ORDER)
    unary = cfg.UNARY_BY_SCENARIO[scenario]
    constraints: List[Constraint] = [UnaryConstraint(v, unary[v]) for v in cfg.VARIABLES]  # (b)
    constraints.append(ForbiddenAdjacencyConstraint(                                      # (a)
        edges, [(cfg.TUAN_RUMAH, cfg.TAMU)]))
    constraints.append(ForbiddenAdjacencyConstraint(                                      # (d)
        edges, [(x, cfg.TAMU) for x in cfg.FORBIDDEN_PREMIUM_NEIGHBORS]))
    constraints.append(AtMostConstraint(cfg.TAMU, cfg.MAX_TAMU_SECTORS, cfg.VARIABLES))  # (c)
    domains = {v: list(cfg.DOMAIN) for v in cfg.VARIABLES}
    csp = CSP(cfg.VARIABLES, domains, cfg.RING_ORDER, adjacency, edges, constraints)
    csp.use_constraint_graph_for_degree(csp.node_consistent_domains()[0])
    csp.scenario = scenario
    return csp
