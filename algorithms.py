"""Algoritma CSP dan local search sebagai generator langkah yang dapat dianimasikan."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, Generator, List, Optional, Tuple

import config as cfg
from csp_model import Assignment, CSP
from heuristics import order_lcv, order_static, select_mrv, select_static
from inference import ac3


@dataclass
class Step:
    assignment: Assignment
    domains: Dict[str, List[str]]
    current: Optional[str] = None
    logs: List[Tuple[str, str]] = field(default_factory=list)
    iteration: int = 0
    done: bool = False
    success: bool = False


class Solver:
    MODES = {
        "minconflicts": "Local Search (Min-Conflicts)",
        "naive": "Baseline Backtracking (Naif)",
        "mrv": "Backtracking + MRV",
        "mrv_lcv": "Backtracking + MRV + LCV",
        "ac3": "Backtracking + MRV + LCV + AC-3",
    }

    def __init__(self, csp: CSP, mode: str, max_steps: int = 250):
        if mode not in self.MODES:
            raise ValueError(f"Mode algoritma tidak dikenal: {mode}")
        self.csp = csp
        self.mode = mode
        self.name = self.MODES[mode]
        self.max_steps = max_steps

    def solve(self) -> Generator[Step, None, None]:
        if self.mode == "minconflicts":
            yield from self._min_conflicts()
        else:
            yield from self._backtracking()

    def _min_conflicts(self):
        csp, rng = self.csp, random.Random()
        assignment = {v: rng.choice(csp.domains[v]) for v in csp.variables}
        domains = csp.initial_domains()
        yield Step(dict(assignment), domains, logs=[("header", "[START] State awal diacak penuh.")])
        for iteration in range(1, self.max_steps + 1):
            violations = csp.all_violations(assignment)
            if not violations:
                yield Step(dict(assignment), domains, iteration=iteration, done=True,
                           success=True, logs=[("success", "[SELESAI] Konflik = 0, solusi valid.")])
                return
            var = rng.choice(sorted(csp.conflicted_variables(assignment)))
            scores = []
            for value in csp.domains[var]:
                trial = dict(assignment)
                trial[var] = value
                scores.append((csp.total_conflicts(trial), value))
            minimum = min(score for score, _ in scores)
            candidates = [value for score, value in scores if score == minimum]
            assignment[var] = rng.choice(candidates)
            yield Step(dict(assignment), domains, var, [("assign", f"[MIN-CONFLICTS] Iterasi {iteration}: ubah {var} -> {assignment[var]} (konflik {csp.total_conflicts(assignment)}).")], iteration)
            if csp.is_solution(assignment):
                yield Step(dict(assignment), domains, iteration=iteration, done=True,
                           success=True, logs=[("success", "[SELESAI] Konflik = 0, solusi valid.")])
                return
        yield Step(dict(assignment), domains, iteration=self.max_steps, done=True,
                   success=False, logs=[("fail", f"[GAGAL] Batas {self.max_steps} iterasi tercapai.")])

    def _backtracking(self):
        csp = self.csp
        assignment: Assignment = {}
        domains, unary_logs = csp.node_consistent_domains()
        iteration = 0
        for message in unary_logs:
            yield Step({}, {v: list(d) for v, d in domains.items()}, logs=[("info", f"[UNARY] {message}")])

        def run_search():
            nonlocal iteration
            if csp.is_complete(assignment):
                return csp.is_solution(assignment)

            if self.mode == "naive":
                var = select_static(csp, assignment)
                options = list(csp.domains[var])
            elif self.mode == "ac3":
                var, tied = select_mrv(csp, assignment, domains)
                options = list(domains[var])
                yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                           [("mrv", f"[MRV] Memilih {var} ({len(options)} sisa domain; tie: {', '.join(tied)}).")])
            else:
                legal = {v: [x for x in csp.domains[v]
                             if not csp.violations_involving({**assignment, v: x}, v)]
                         for v in csp.variables if v not in assignment}
                var, tied = select_mrv(csp, assignment, legal)
                options = list(legal[var])
                yield Step(dict(assignment), {**{v: list(d) for v, d in legal.items()}, **{v: list(csp.domains[v]) for v in assignment}}, var,
                           [("mrv", f"[MRV] Memilih {var} ({len(options)} sisa domain; tie: {', '.join(tied)}).")])

            if self.mode in ("mrv_lcv", "ac3"):
                scored = order_lcv(csp, var, options, assignment, domains,
                                   cfg.STATIC_VALUE_ORDERS["asli"])
                options = [value for value, _ in scored]
                if scored:
                    label = " -> ".join(value.replace("_", " ") for value in options)
                    yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                               [("lcv", f"[LCV] Urutan opsi: {label} (paling sedikit membatasi dulu).")])
            else:
                options = order_static(options, cfg.STATIC_VALUE_ORDERS["asli"])

            for value in options:
                iteration += 1
                assignment[var] = value
                yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                           [("assign", f"[ASSIGN] Coba {var} = {value.replace('_', ' ')}.")], iteration)
                conflicts = csp.violations_involving(assignment, var)
                if conflicts:
                    yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                               [("clash", f"[KONFLIK] {conflicts[0].message}")], iteration)
                    del assignment[var]
                    continue

                saved = {v: list(d) for v, d in domains.items()}
                consistent = True
                if self.mode == "ac3":
                    domains[var] = [value]
                    stream = ac3(csp, domains)
                    while True:
                        try:
                            arc_event = next(stream)
                        except StopIteration as stop:
                            consistent = bool(stop.value)
                            break
                        removed_text = ("; hapus " + ", ".join(arc_event.removed)
                                        if arc_event.removed else "; tidak ada nilai dihapus")
                        yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                                   [("ac3" if not arc_event.wipeout else "fail",
                                     f"[AC-3] Memeriksa Arc ({arc_event.xi} -> {arc_event.xj}){removed_text}.")], iteration)
                        if arc_event.wipeout:
                            consistent = False
                            break
                if consistent:
                    found = yield from run_search()
                    if found:
                        return True
                else:
                    yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                               [("backtrack", f"[BACKTRACK] Domain kosong setelah {var} = {value}; mundur.")], iteration)

                domains.clear()
                domains.update(saved)
                del assignment[var]
                yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, var,
                           [("backtrack", f"[BACKTRACK] Membatalkan {var} = {value.replace('_', ' ')}.")], iteration)
            return False

        found = yield from run_search()
        message = "[SELESAI] Solusi ditemukan, semua constraint terpenuhi." if found else "[SELESAI] Tidak ditemukan solusi."
        yield Step(dict(assignment), {v: list(d) for v, d in domains.items()}, iteration=iteration,
                   done=True, success=found, logs=[("success" if found else "fail", message)])
