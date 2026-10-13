"""
heuristics.py
Heuristik pemilihan variabel & urutan nilai. Fungsi murni (tanpa efek samping)
sehingga mudah dikombinasikan oleh solver.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from csp_model import CSP, Assignment

Domains = Dict[str, List[str]]


# ---------------- pemilihan variabel ----------------
def select_static(csp: CSP, assignment: Assignment) -> str:
    """Baseline: variabel pertama yang belum terisi menurut urutan tetap."""
    return next(v for v in csp.variables if v not in assignment)


def select_mrv(csp: CSP, assignment: Assignment, domains: Domains) -> Tuple[str, List[str]]:
    """MRV: variabel dengan sisa domain paling sedikit.
    Tie-break: degree heuristic (tetangga belum terisi terbanyak), lalu urutan statis.
    Return (variabel_terpilih, daftar_variabel_yang_seri_di_nilai_MRV)."""
    unassigned = [v for v in csp.variables if v not in assignment]
    min_size = min(len(domains[v]) for v in unassigned)
    tied = [v for v in unassigned if len(domains[v]) == min_size]
    chosen = min(tied, key=lambda v: (-csp.unassigned_degree(v, assignment),
                                      csp.variables.index(v)))
    return chosen, tied


# ---------------- urutan nilai ----------------
def order_static(values: Sequence[str], static_order: Sequence[str]) -> List[str]:
    """Baseline: urut menurut urutan nilai statis."""
    return sorted(values, key=lambda x: static_order.index(x))


def eliminated_options(csp: CSP, var: str, value: str,
                       assignment: Assignment, domains: Domains) -> int:
    """Berapa banyak nilai pada domain variabel LAIN (yang belum terisi)
    yang akan 'terbuang' bila var = value."""
    total = 0
    for other in csp.variables:
        if other == var or other in assignment:
            continue
        total += sum(1 for y in domains[other] if not csp.pair_ok(var, value, other, y))
    return total


def order_lcv(csp: CSP, var: str, values: Sequence[str], assignment: Assignment,
              domains: Domains, static_order: Sequence[str]) -> List[Tuple[str, int]]:
    """LCV: urutkan nilai dari yang paling sedikit membuang opsi variabel lain.
    Sort stabil -> seri mengikuti urutan statis. Return [(nilai, skor_terbuang)]."""
    base = order_static(values, static_order)
    scored = [(v, eliminated_options(csp, var, v, assignment, domains)) for v in base]
    return sorted(scored, key=lambda t: t[1])
