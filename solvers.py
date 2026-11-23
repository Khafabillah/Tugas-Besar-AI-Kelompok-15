"""
solvers.py
Dua keluarga algoritma, keduanya GENERATOR yang meng-yield `Step`.
UI memanggil next() sesuai jeda -> proses terlihat step-by-step tanpa memblokir.

  BacktrackingSolver : satu fungsi backtrack() dengan flag heuristik
                       (use_mrv, use_lcv, use_ac3) lewat HeuristicConfig.
  MinConflictsSolver : Local Search murni.
  create_solver()    : peta tombol [1]..[5] -> solver.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence

import config as cfg
from csp_model import CSP, Assignment
from events import Metrics, Step
from heuristics import order_lcv, order_static, select_mrv, select_static
from inference import ac3, run_ac3

# Bobot delay per jenis langkah (dikali BASE_DELAY_MS)
W_SELECT, W_ASSIGN, W_CLASH, W_BACK, W_ARC = 0.8, 1.0, 1.0, 1.0, 0.3


def short(values) -> str:
    return " ".join(cfg.SHORT_NAMES.get(v, v) for v in values) or "(kosong)"


class Solver(ABC):
    def __init__(self, csp: CSP, label: str, trace=True):
        self.csp = csp
        self.label = label
        self.trace = trace
        self.metrics = Metrics()
        self.solution = None
        self.success = False
        self.finished = False
        self.final_conflicts = None
        self.csp.reset_counters()

    def _sync_metrics(self):
        self.metrics.constraint_checks = self.csp.check_counters["constraint_checks"]
        self.metrics.pair_checks = self.csp.check_counters["pair_checks"]
        self.metrics.assignment_checks = self.csp.check_counters["assignment_checks"]
        self.metrics.unary_checks = self.csp.check_counters["unary_checks"]

    def _step(self, assignment: Assignment, logs, *, current=None, domains=None,
              focus="", arc=None, flash=None, weight=1.0, done=False, success=False) -> Step:
        self._sync_metrics()
        doms = {v: list(d) for v, d in (domains or {}).items() if v not in assignment}
        return Step(assignment=dict(assignment), logs=list(logs), current=current,
                    domains=doms, focus=focus, arc=arc, flash=flash,
                    metrics=replace(self.metrics),
                    total_conflicts=self.csp.total_conflicts(assignment, count=False),
                    weight=weight, done=done, success=success)

    def _emit_step(self, assignment: Assignment, logs, **kwargs):
        if self.trace:
            yield self._step(assignment, logs, **kwargs)
        else:
            # A yield point keeps headless runs interruptible without building UI frames.
            yield None

    @abstractmethod
    def solve(self):
        ...


# ======================================================================
# Backtracking dengan flag heuristik
# ======================================================================
@dataclass(frozen=True)
class HeuristicConfig:
    label: str
    use_mrv: bool = False
    use_lcv: bool = False
    use_fc: bool = False
    use_ac3: bool = False
    node_consistency: bool = False   # pangkas domain dengan constraint Unary


class BacktrackingSolver(Solver):
    """
    backtrack(assignment, domains):
      1. pilih variabel  : statis | MRV
      2. urutkan nilai   : statis | LCV
      3. untuk tiap nilai: assign -> cek constraint (clash => backtrack)
                           -> [opsional] AC-3 sebagai inference (domain kosong => backtrack)
                           -> rekursi
      4. semua nilai gagal => dead end, return False
    """

    def __init__(self, csp: CSP, config: HeuristicConfig, static_order: Sequence[str],
                 trace=True):
        super().__init__(csp, config.label, trace=trace)
        self.config = config
        self.static_order = list(static_order)

    # ---------------- entry ----------------
    def solve(self):
        csp, hc = self.csp, self.config
        assignment: Assignment = {}
        domains = csp.initial_domains()

        logs = []
        if self.trace:
            flags = [n for n, on in (("NC", hc.node_consistency), ("MRV", hc.use_mrv),
                                     ("LCV", hc.use_lcv), ("FC", hc.use_fc),
                                     ("AC-3", hc.use_ac3)) if on] or ["tanpa heuristik"]
            logs.append(("sys", f"[INIT] Stadion kosong. {hc.label} ({', '.join(flags)})"))
        if hc.node_consistency:
            domains, prune = csp.node_consistent_domains()
            if self.trace:
                locked = sum(1 for v in csp.variables if len(domains[v]) == 1)
                logs.append(("info", f"[UNARY] Node consistency: {len(prune)} domain dipangkas, "
                                     f"{locked} variabel terkunci 1 nilai"))
        elif self.trace:
            logs.append(("order", "[STATIC] Tanpa pruning: constraint Unary dicek saat assign."))
        self.graph = {}
        if hc.use_ac3 or hc.use_fc:
            self.graph = csp.constraint_graph(domains)
        if hc.use_ac3:
            n_arcs = len(csp.arcs(self.graph))
            ok, arcs, removed = run_ac3(csp, domains, self.graph)
            self.metrics.arc_checks += arcs
            self.metrics.removals += removed
            if self.trace:
                logs.append(("ac3", f"[AC-3] Graf constraint: {n_arcs} arc "
                                    f"(hanya pasangan yang bisa melanggar)"))
                logs.append(("ac3", f"[AC-3] Preprocessing: {arcs} arc diperiksa, "
                                    f"{removed} nilai dihapus"))
        yield from self._emit_step(assignment, logs, domains=domains)

        ok = yield from self.backtrack(assignment, domains)
        self.success = ok
        self.solution = dict(assignment) if ok else None
        self.final_conflicts = csp.total_conflicts(assignment, count=False) if ok else None
        self._sync_metrics()
        self.finished = True

        if ok:
            summary = (", ".join(f"{v}={assignment[v]}" for v in csp.variables)
                       if self.trace else "")
            yield from self._emit_step(assignment, [
                ("success", f"[SELESAI] Solusi valid: {self.metrics.iterations} iterasi, "
                            f"{self.metrics.backtracks} backtrack, "
                            f"{self.metrics.arc_checks} arc."),
                ("success", summary)], done=True, success=True)
        else:
            yield from self._emit_step(assignment, [("fail", "[GAGAL] Tidak ada solusi.")],
                                       done=True)

    BACKTRACK = None  # alias diisi di bawah kelas

    # ---------------- fungsi inti ----------------
    def backtrack(self, assignment: Assignment, domains):
        csp, hc, m = self.csp, self.config, self.metrics
        if csp.is_complete(assignment):
            return True

        # ---- 1. pilih variabel ----
        logs = []
        if hc.use_mrv:
            var, tied = select_mrv(csp, assignment, domains)
            if self.trace:
                n = len(domains[var])
                logs = [("info", f"Memeriksa Tribun {var}..."),
                        ("mrv", f"[MRV] Memilih {var} ({n} sisa domain)")]
            if self.trace and len(tied) > 1:
                who = ", ".join(tied) if len(tied) <= 4 else f"{len(tied)} variabel"
                logs.append(("mrv", f"[MRV] Seri di {n} nilai ({who}) "
                                    f"-> tie-break degree/urutan: {var}"))
        else:
            var = select_static(csp, assignment)
            if self.trace:
                logs = [("info", f"Memeriksa Tribun {var}..."),
                        ("order", f"[STATIC] Variabel berikutnya (urutan tetap): {var}")]
        yield from self._emit_step(assignment, logs, current=var, domains=domains,
                                   focus=f"{var} | domain: {short(domains[var])}" if self.trace else "",
                                   weight=W_SELECT)

        # ---- 2. urutkan nilai ----
        candidates = list(domains[var])
        if hc.use_lcv:
            scored = order_lcv(csp, var, candidates, assignment, domains, self.static_order)
            values = [v for v, _ in scored]
            if len(values) > 1 and self.trace:
                desc = " < ".join(f"{v}({s})" for v, s in scored)
                logs = [("lcv", f"[LCV] Opsi terbuang {var}: {desc}")]
                base_first = order_static(candidates, self.static_order)[0]
                if values[0] != base_first:
                    logs.append(("lcv", f"[LCV] Mengurutkan opsi {values[0]} "
                                        f"sebelum {base_first}"))
                yield from self._emit_step(assignment, logs, current=var, domains=domains,
                                           focus=f"{var} | urutan LCV: {short(values)}",
                                           weight=W_SELECT)
        else:
            values = order_static(candidates, self.static_order)
            if len(values) > 1 and self.trace:
                yield from self._emit_step(assignment, [
                    ("order", f"[STATIC] Urutan nilai {var}: {', '.join(values)}")],
                    current=var, domains=domains,
                    focus=f"{var} | urutan statis: {short(values)}", weight=W_SELECT)

        # ---- 3. coba tiap nilai ----
        for idx, value in enumerate(values):
            pending = values[idx + 1:]
            focus = f"{var}={value} | belum dicoba: {short(pending)}" if self.trace else ""
            m.iterations += 1
            assignment[var] = value

            violations = csp.violations_involving(assignment, var)
            if violations:
                m.clashes += 1
                logs = []
                if self.trace:
                    logs = [("assign", f"[TRY] {var} <- {value}")]
                    logs += [("clash", f"[CLASH] {v.message}") for v in violations]
                yield from self._emit_step(assignment, logs, current=var, domains=domains,
                                           focus=focus, weight=W_CLASH)
                del assignment[var]
                m.backtracks += 1
                nxt = (f"sisa nilai: {short(pending)}" if pending else "nilai habis") \
                    if self.trace else ""
                yield from self._emit_step(assignment, [
                    ("backtrack", f"[BACKTRACK] Konflik di {var}={value}, "
                                  f"membatalkan assignment ({nxt})")],
                    current=var, domains=domains, focus=focus, weight=W_BACK)
                continue

            logs = [("assign", f"[ASSIGN] {var} <- {value} (konsisten)")] if self.trace else []
            yield from self._emit_step(assignment, logs,
                current=var, domains=domains, focus=focus, weight=W_ASSIGN)

            child = {v: list(d) for v, d in domains.items()}
            if hc.use_fc or hc.use_ac3:
                child[var] = [value]

            if hc.use_fc:
                wiped = []
                for other in self.graph[var]:
                    if other in assignment:
                        continue
                    removed = []
                    for candidate in list(child[other]):
                        m.fc_checks += 1
                        if not csp.pair_ok(var, value, other, candidate):
                            child[other].remove(candidate)
                            removed.append(candidate)
                    m.fc_removals += len(removed)
                    if removed:
                        logs = [("fc", f"[FC] {other}: hapus {short(removed)}")] \
                            if self.trace else []
                        yield from self._emit_step(assignment, logs, current=var,
                                                   domains=child, focus=focus,
                                                   weight=W_ARC)
                    if not child[other]:
                        wiped.append(other)
                if wiped:
                    del assignment[var]
                    m.backtracks += 1
                    logs = [("backtrack", f"[FC] Domain {', '.join(wiped)} kosong; "
                                           f"membatalkan {var}={value}")] if self.trace else []
                    yield from self._emit_step(assignment, logs,
                        current=var, domains=domains, focus=focus, weight=W_BACK)
                    continue

            if hc.use_ac3:
                queue = [(xk, var) for xk in csp.variables if xk in self.graph[var]]
                gen = ac3(csp, child, self.graph, queue)
                ok, wiped = True, None
                while True:
                    try:
                        ev = next(gen)
                    except StopIteration as stop:
                        ok = stop.value
                        break
                    m.arc_checks += 1
                    m.removals += len(ev.removed)
                    logs = []
                    if self.trace:
                        head = f"[AC-3] Memeriksa Arc ({ev.xi} -> {ev.xj})..."
                        if ev.removed:
                            logs = [("ac3", f"{head} Domain {', '.join(ev.removed)} "
                                            f"dihapus dari {ev.xi}")]
                        else:
                            logs = [("ac3_ok", f"{head} tanpa perubahan")]
                    if ev.wipeout:
                        wiped = ev.xi
                        if self.trace:
                            logs.append(("clash", f"[AC-3] Domain {ev.xi} KOSONG!"))
                    yield from self._emit_step(assignment, logs, current=var, domains=child,
                                               focus=focus, arc=(ev.xi, ev.xj),
                                               flash=ev.xi if ev.removed else None,
                                               weight=W_ARC)
                if not ok:
                    del assignment[var]
                    m.backtracks += 1
                    logs = [("backtrack", f"[BACKTRACK] Dead end di {var}={value} "
                                           f"(domain {wiped} kosong), membatalkan assignment")] \
                        if self.trace else []
                    yield from self._emit_step(assignment, logs,
                        current=var, domains=domains, focus=focus, weight=W_BACK)
                    continue

            if (yield from self.backtrack(assignment, child)):
                return True

            del assignment[var]
            m.backtracks += 1
            logs = [("backtrack", f"[BACKTRACK] Cabang {var}={value} buntu, "
                                   f"membatalkan assignment")] if self.trace else []
            yield from self._emit_step(assignment, logs,
                current=var, domains=domains, focus=focus, weight=W_BACK)

        # ---- 4. dead end ----
        logs = [("backtrack", f"[BACKTRACK] Dead end di {var}: semua nilai gagal, "
                               f"kembali ke variabel sebelumnya")] if self.trace else []
        yield from self._emit_step(assignment, logs,
            current=var, domains=domains, weight=W_BACK)
        return False


BacktrackingSolver.BACKTRACK = BacktrackingSolver.backtrack   # alias sesuai spesifikasi


# ======================================================================
# Local Search: Min-Conflicts
# ======================================================================
class MinConflictsSolver(Solver):
    def __init__(self, csp: CSP, max_steps: int = 400, noise: float = 0.15,
                 seed: Optional[int] = None, trace=True):
        super().__init__(csp, "Local Search: Min-Conflicts", trace=trace)
        self.max_steps = max_steps
        self.noise = noise          # peluang random walk untuk lolos dari plateau
        self.seed = seed
        self.rng = random.Random(seed)

    def _random_state(self, domains) -> Assignment:
        csp = self.csp
        state: Assignment = {}
        for _ in range(50):   # ulangi sampai state awal benar-benar melanggar
            state = {v: self.rng.choice(domains[v]) for v in csp.variables}
            if csp.total_conflicts(state) > 0:
                break
        return state

    def solve(self):
        csp, m = self.csp, self.metrics
        domains, _ = csp.node_consistent_domains()
        a = self._random_state(domains)
        logs = []
        if self.trace:
            initial_violations = csp.all_violations(a, count=False)
            initial_conflicts = sum(v.cost for v in initial_violations)
            logs = [("sys", "[INIT] State acak penuh (boleh melanggar constraint):"),
                    ("info", ", ".join(f"{v}={a[v]}" for v in csp.variables))]
            logs += [("clash", f"[CLASH] {v.message}") for v in initial_violations]
            logs.append(("info", f"Total konflik awal = {initial_conflicts}"))
        yield from self._emit_step(a, logs, weight=W_SELECT)

        failure_reason = f"Batas {self.max_steps} langkah tercapai."
        for _ in range(self.max_steps + 1):
            violations = csp.all_violations(a)
            conflicted_set = {v for violation in violations for v in violation.variables}
            conflicted = [v for v in csp.variables if v in conflicted_set]
            total = sum(v.cost for v in violations)
            if not conflicted:
                self.success = True
                self.solution = dict(a)
                self.final_conflicts = 0
                self._sync_metrics()
                self.finished = True
                summary = (", ".join(f"{v}={a[v]}" for v in csp.variables)
                           if self.trace else "")
                yield from self._emit_step(a, [
                    ("success", f"[SELESAI] Konflik = 0 setelah {m.iterations} iterasi."),
                    ("success", summary)], done=True, success=True)
                return
            if m.iterations >= self.max_steps:
                break

            movable = [v for v in conflicted if len(domains[v]) > 1]
            if not movable:
                failure_reason = "Semua variabel berkonflik hanya punya satu nilai legal."
                break

            m.iterations += 1
            var = self.rng.choice(movable)
            old = a[var]
            scores: Dict[str, int] = {}
            for val in domains[var]:
                trial = dict(a)
                trial[var] = val
                scores[val] = csp.total_conflicts(trial)
            best = min(scores.values())
            cands = [v for v, s in scores.items() if s == best]
            alternatives = [v for v in domains[var] if v != old]
            if len(cands) > 1 and old in cands:
                cands.remove(old)
            if not cands:
                cands = [old]
            new = self.rng.choice(cands)
            walk = self.rng.random() < self.noise
            if walk and alternatives:   # random walk tetap di domain unary-legal
                new = self.rng.choice(alternatives)

            logs = []
            if self.trace:
                logs = [("info", f"Memeriksa Tribun {var}..."),
                        ("info", f"[LS] Memilih {var} dari {len(conflicted)} sektor berkonflik: "
                                 f"{', '.join(conflicted)}")]
                involved = csp.violations_involving(a, var, count=False)
                logs += [("clash", f"[CLASH] {x.message}") for x in involved]
                logs.append(("info", "[LS] Skor konflik jika diubah: " +
                             ", ".join(f"{cfg.SHORT_NAMES[v]}={s}" for v, s in scores.items())))
                if walk:
                    logs.append(("info", f"[LS] Random walk ({self.noise:.0%}): "
                                         f"mencoba nilai acak untuk lolos dari plateau"))
            yield from self._emit_step(a, logs, current=var,
                                       focus=(f"{var}={old} | total konflik {total}"
                                              if self.trace else ""),
                                       weight=W_SELECT)

            a[var] = new
            move_logs = []
            if self.trace:
                new_total = csp.total_conflicts(a, count=False)
                move_logs = [("backtrack", f"[MIN-CONFLICT] {var}: {old} -> {new} "
                              f"(konflik {total} -> {new_total})")]
            yield from self._emit_step(a, move_logs,
                current=var, focus=(f"{var}: {old} -> {new}" if self.trace else ""),
                weight=W_ASSIGN)

        self.success = False
        self.solution = None
        self.final_conflicts = csp.total_conflicts(a, count=False)
        self._sync_metrics()
        self.finished = True
        yield from self._emit_step(a, [("fail", f"[GAGAL] {failure_reason}")], done=True)


# ======================================================================
# Peta tombol -> solver
# ======================================================================
MODE_LABELS = {
    1: "MinConf",
    2: "Naif+NC",
    3: "MRV",
    4: "LCV",
    5: "FC",
    6: "MAC/AC-3",
    7: "MRV+LCV",
    8: "MRV+LCV+MAC",
}

_BT_CONFIGS = {
    2: HeuristicConfig("Backtracking Naif + Node Consistency", node_consistency=True),
    3: HeuristicConfig("Backtracking + MRV", use_mrv=True, node_consistency=True),
    4: HeuristicConfig("Backtracking + LCV", use_lcv=True, node_consistency=True),
    5: HeuristicConfig("Backtracking + Forward Checking", use_fc=True,
                       node_consistency=True),
    6: HeuristicConfig("Backtracking + MAC (AC-3)", use_ac3=True,
                       node_consistency=True),
    7: HeuristicConfig("Backtracking + MRV + LCV", use_mrv=True, use_lcv=True,
                       node_consistency=True),
    8: HeuristicConfig("Backtracking + MRV + LCV + MAC (AC-3)", use_mrv=True,
                       use_lcv=True, use_ac3=True, node_consistency=True),
}


def create_solver(mode: int, csp: CSP, static_order: Sequence[str], *, seed=None,
                  trace=True) -> Solver:
    if mode == 1:
        return MinConflictsSolver(csp, seed=seed, trace=trace)
    return BacktrackingSolver(csp, _BT_CONFIGS[mode], static_order, trace=trace)
