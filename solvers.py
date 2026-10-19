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
W_SELECT, W_ASSIGN, W_CLASH, W_BACK, W_ARC = 0.8, 1.0, 1.0, 1.0, 0.45


def short(values) -> str:
    return " ".join(cfg.SHORT_NAMES.get(v, v) for v in values) or "(kosong)"


class Solver(ABC):
    def __init__(self, csp: CSP, label: str):
        self.csp = csp
        self.label = label
        self.metrics = Metrics()

    def _step(self, assignment: Assignment, logs, *, current=None, domains=None,
              focus="", arc=None, flash=None, weight=1.0, done=False, success=False) -> Step:
        doms = {v: list(d) for v, d in (domains or {}).items() if v not in assignment}
        return Step(assignment=dict(assignment), logs=list(logs), current=current,
                    domains=doms, focus=focus, arc=arc, flash=flash,
                    metrics=replace(self.metrics),
                    total_conflicts=self.csp.total_conflicts(assignment),
                    weight=weight, done=done, success=success)

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

    def __init__(self, csp: CSP, config: HeuristicConfig, static_order: Sequence[str]):
        super().__init__(csp, config.label)
        self.config = config
        self.static_order = list(static_order)

    # ---------------- entry ----------------
    def solve(self):
        csp, hc = self.csp, self.config
        assignment: Assignment = {}
        domains = csp.initial_domains()

        flags = [n for n, on in (("MRV", hc.use_mrv), ("LCV", hc.use_lcv),
                                 ("AC-3", hc.use_ac3)) if on] or ["tanpa heuristik"]
        logs = [("sys", f"[INIT] Stadion kosong. {hc.label} ({', '.join(flags)})")]
        if hc.node_consistency:
            domains, prune = csp.node_consistent_domains()
            logs += [("info", f"[UNARY] {m}") for m in prune]
        else:
            logs.append(("order", "[STATIC] Tanpa pruning: constraint Unary dicek saat assign."))
        if hc.use_ac3:
            ok, arcs, removed = run_ac3(csp, domains)
            self.metrics.arc_checks += arcs
            self.metrics.removals += removed
            logs.append(("ac3", f"[AC-3] Preprocessing: {arcs} arc diperiksa, "
                                f"{removed} nilai dihapus"))
        yield self._step(assignment, logs, domains=domains)

        ok = yield from self.backtrack(assignment, domains)

        if ok:
            summary = ", ".join(f"{v}={assignment[v]}" for v in csp.variables)
            yield self._step(assignment, [
                ("success", f"[SELESAI] Solusi valid: {self.metrics.iterations} iterasi, "
                            f"{self.metrics.backtracks} backtrack, "
                            f"{self.metrics.arc_checks} arc."),
                ("success", summary)], done=True, success=True)
        else:
            yield self._step(assignment, [("fail", "[GAGAL] Tidak ada solusi.")],
                             done=True)

    BACKTRACK = None  # alias diisi di bawah kelas

    # ---------------- fungsi inti ----------------
    def backtrack(self, assignment: Assignment, domains):
        csp, hc, m = self.csp, self.config, self.metrics
        if csp.is_complete(assignment):
            return True

        # ---- 1. pilih variabel ----
        if hc.use_mrv:
            var, tied = select_mrv(csp, assignment, domains)
            n = len(domains[var])
            logs = [("info", f"Memeriksa Tribun {var}..."),
                    ("mrv", f"[MRV] Memilih {var} ({n} sisa domain)")]
            if len(tied) > 1:
                logs.append(("mrv", f"[MRV] Seri di {n} nilai: {', '.join(tied)} "
                                    f"-> tie-break degree: {var}"))
        else:
            var = select_static(csp, assignment)
            logs = [("info", f"Memeriksa Tribun {var}..."),
                    ("order", f"[STATIC] Variabel berikutnya (urutan tetap): {var}")]
        yield self._step(assignment, logs, current=var, domains=domains,
                         focus=f"{var} | domain: {short(domains[var])}", weight=W_SELECT)

        # ---- 2. urutkan nilai ----
        candidates = list(domains[var])
        if hc.use_lcv:
            scored = order_lcv(csp, var, candidates, assignment, domains, self.static_order)
            values = [v for v, _ in scored]
            if len(values) > 1:
                desc = " < ".join(f"{v}({s})" for v, s in scored)
                logs = [("lcv", f"[LCV] Opsi terbuang {var}: {desc}")]
                base_first = order_static(candidates, self.static_order)[0]
                if values[0] != base_first:
                    logs.append(("lcv", f"[LCV] Mengurutkan opsi {values[0]} "
                                        f"sebelum {base_first}"))
                yield self._step(assignment, logs, current=var, domains=domains,
                                 focus=f"{var} | urutan LCV: {short(values)}",
                                 weight=W_SELECT)
        else:
            values = order_static(candidates, self.static_order)
            if len(values) > 1:
                yield self._step(assignment, [
                    ("order", f"[STATIC] Urutan nilai {var}: {', '.join(values)}")],
                    current=var, domains=domains,
                    focus=f"{var} | urutan statis: {short(values)}", weight=W_SELECT)

        # ---- 3. coba tiap nilai ----
        for idx, value in enumerate(values):
            pending = values[idx + 1:]
            focus = f"{var}={value} | belum dicoba: {short(pending)}"
            m.iterations += 1
            assignment[var] = value

            violations = csp.violations_involving(assignment, var)
            if violations:
                m.clashes += 1
                logs = [("assign", f"[TRY] {var} <- {value}")]
                logs += [("clash", f"[CLASH] {v.message}") for v in violations]
                yield self._step(assignment, logs, current=var, domains=domains,
                                 focus=focus, weight=W_CLASH)
                del assignment[var]
                m.backtracks += 1
                nxt = f"sisa nilai: {short(pending)}" if pending else "nilai habis"
                yield self._step(assignment, [
                    ("backtrack", f"[BACKTRACK] Konflik di {var}={value}, "
                                  f"membatalkan assignment ({nxt})")],
                    current=var, domains=domains, focus=focus, weight=W_BACK)
                continue

            yield self._step(assignment, [
                ("assign", f"[ASSIGN] {var} <- {value} (konsisten)")],
                current=var, domains=domains, focus=focus, weight=W_ASSIGN)

            child = {v: list(d) for v, d in domains.items()}
            if hc.use_ac3:
                child[var] = [value]
                queue = [(xk, var) for xk in csp.variables if xk != var]
                gen = ac3(csp, child, queue)
                ok, wiped = True, None
                while True:
                    try:
                        ev = next(gen)
                    except StopIteration as stop:
                        ok = stop.value
                        break
                    m.arc_checks += 1
                    m.removals += len(ev.removed)
                    head = f"[AC-3] Memeriksa Arc ({ev.xi} -> {ev.xj})..."
                    if ev.removed:
                        logs = [("ac3", f"{head} Domain {', '.join(ev.removed)} "
                                        f"dihapus dari {ev.xi}")]
                    else:
                        logs = [("ac3_ok", f"{head} tanpa perubahan")]
                    if ev.wipeout:
                        wiped = ev.xi
                        logs.append(("clash", f"[AC-3] Domain {ev.xi} KOSONG!"))
                    yield self._step(assignment, logs, current=var, domains=child,
                                     focus=focus, arc=(ev.xi, ev.xj),
                                     flash=ev.xi if ev.removed else None, weight=W_ARC)
                if not ok:
                    del assignment[var]
                    m.backtracks += 1
                    yield self._step(assignment, [
                        ("backtrack", f"[BACKTRACK] Dead end di {var}={value} "
                                      f"(domain {wiped} kosong), membatalkan assignment")],
                        current=var, domains=domains, focus=focus, weight=W_BACK)
                    continue

            if (yield from self.backtrack(assignment, child)):
                return True

            del assignment[var]
            m.backtracks += 1
            yield self._step(assignment, [
                ("backtrack", f"[BACKTRACK] Cabang {var}={value} buntu, "
                              f"membatalkan assignment")],
                current=var, domains=domains, focus=focus, weight=W_BACK)

        # ---- 4. dead end ----
        yield self._step(assignment, [
            ("backtrack", f"[BACKTRACK] Dead end di {var}: semua nilai gagal, "
                          f"kembali ke variabel sebelumnya")],
            current=var, domains=domains, weight=W_BACK)
        return False


BacktrackingSolver.BACKTRACK = BacktrackingSolver.backtrack   # alias sesuai spesifikasi


# ======================================================================
# Local Search: Min-Conflicts
# ======================================================================
class MinConflictsSolver(Solver):
    def __init__(self, csp: CSP, max_steps: int = 200, noise: float = 0.15,
                 seed: Optional[int] = None):
        super().__init__(csp, "Local Search: Min-Conflicts")
        self.max_steps = max_steps
        self.noise = noise          # peluang random walk untuk lolos dari plateau
        self.rng = random.Random(seed)

    def _random_state(self) -> Assignment:
        csp = self.csp
        state: Assignment = {}
        for _ in range(50):   # ulangi sampai state awal benar-benar melanggar
            state = {v: self.rng.choice(csp.domains[v]) for v in csp.variables}
            if csp.total_conflicts(state) > 0:
                break
        return state

    def solve(self):
        csp, m = self.csp, self.metrics
        a = self._random_state()
        logs = [("sys", "[INIT] State acak penuh (boleh melanggar constraint):"),
                ("info", ", ".join(f"{v}={a[v]}" for v in csp.variables))]
        logs += [("clash", f"[CLASH] {v.message}") for v in csp.all_violations(a)]
        logs.append(("info", f"Total konflik awal = {csp.total_conflicts(a)}"))
        yield self._step(a, logs, weight=W_SELECT)

        for _ in range(self.max_steps + 1):
            conflicted = [v for v in csp.variables if v in csp.conflicted_variables(a)]
            total = csp.total_conflicts(a)
            if not conflicted:
                summary = ", ".join(f"{v}={a[v]}" for v in csp.variables)
                yield self._step(a, [
                    ("success", f"[SELESAI] Konflik = 0 setelah {m.iterations} iterasi."),
                    ("success", summary)], done=True, success=True)
                return
            if m.iterations >= self.max_steps:
                break

            m.iterations += 1
            var = self.rng.choice(conflicted)
            old = a[var]
            scores: Dict[str, int] = {}
            for val in csp.domains[var]:
                trial = dict(a)
                trial[var] = val
                scores[val] = csp.total_conflicts(trial)
            best = min(scores.values())
            cands = [v for v, s in scores.items() if s == best]
            if len(cands) > 1 and old in cands:
                cands.remove(old)
            new = self.rng.choice(cands)
            walk = self.rng.random() < self.noise
            if walk:   # random walk: pilih nilai acak (bukan yang sekarang)
                new = self.rng.choice([v for v in csp.domains[var] if v != old])

            logs = [("info", f"Memeriksa Tribun {var}..."),
                    ("info", f"[LS] Memilih {var} dari {len(conflicted)} sektor berkonflik: "
                             f"{', '.join(conflicted)}")]
            logs += [("clash", f"[CLASH] {x.message}") for x in csp.violations_involving(a, var)]
            logs.append(("info", "[LS] Skor konflik jika diubah: " +
                         ", ".join(f"{cfg.SHORT_NAMES[v]}={s}" for v, s in scores.items())))
            if walk:
                logs.append(("info", f"[LS] Random walk ({self.noise:.0%}): "
                                     f"mencoba nilai acak untuk lolos dari plateau"))
            yield self._step(a, logs, current=var,
                             focus=f"{var}={old} | total konflik {total}", weight=W_SELECT)

            a[var] = new
            yield self._step(a, [
                ("backtrack", f"[MIN-CONFLICT] {var}: {old} -> {new} "
                              f"(konflik {total} -> {csp.total_conflicts(a)})")],
                current=var, focus=f"{var}: {old} -> {new}", weight=W_ASSIGN)

        yield self._step(a, [("fail", f"[GAGAL] Batas {self.max_steps} langkah tercapai.")],
                         done=True)


# ======================================================================
# Peta tombol -> solver
# ======================================================================
MODE_LABELS = {1: "MinConf", 2: "Naif", 3: "MRV", 4: "MRV+LCV", 5: "MRV+LCV+AC3"}

_BT_CONFIGS = {
    2: HeuristicConfig("Backtracking Naif"),
    3: HeuristicConfig("Backtracking + MRV", use_mrv=True, node_consistency=True),
    4: HeuristicConfig("Backtracking + MRV + LCV", use_mrv=True, use_lcv=True,
                       node_consistency=True),
    5: HeuristicConfig("Backtracking + MRV + LCV + AC-3", use_mrv=True, use_lcv=True,
                       use_ac3=True, node_consistency=True),
}


def create_solver(mode: int, csp: CSP, static_order: Sequence[str]) -> Solver:
    if mode == 1:
        return MinConflictsSolver(csp)
    return BacktrackingSolver(csp, _BT_CONFIGS[mode], static_order)
