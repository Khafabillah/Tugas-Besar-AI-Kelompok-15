"""
inference.py
AC-3 (Arc Consistency 3) sebagai langkah INFERENCE.

  revise(csp, domains, xi, xj)  -> REVISE(Xi, Xj): hapus nilai Xi tanpa support di Xj
  ac3(csp, domains, queue)      -> generator: yield ArcEvent per arc yang diperiksa,
                                   return True/False (False = ada domain kosong)
  run_ac3(...)                  -> jalankan sampai habis tanpa jeda (preprocessing)

Konvensi arc (Xi -> Xj) mengikuti AIMA: nilai yang dihapus berasal dari domain Xi.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Optional, Tuple

from csp_model import CSP
from events import ArcEvent

Domains = Dict[str, List[str]]


def revise(csp: CSP, domains: Domains, xi: str, xj: str) -> List[str]:
    """REVISE(Xi, Xj). Mengubah domains[xi] di tempat; return nilai yang dihapus."""
    removed: List[str] = []
    for x in list(domains[xi]):
        has_support = any(csp.pair_ok(xi, x, xj, y) for y in domains[xj])
        if not has_support:
            domains[xi].remove(x)
            removed.append(x)
    return removed


def ac3(csp: CSP, domains: Domains, graph, queue: Optional[Iterable[Tuple[str, str]]] = None):
    """AC-3 sebagai generator. `domains` dimodifikasi di tempat."""
    q = deque(queue if queue is not None else csp.arcs(graph))
    while q:
        xi, xj = q.popleft()
        removed = revise(csp, domains, xi, xj)
        wipeout = len(domains[xi]) == 0
        yield ArcEvent(xi, xj, removed, wipeout)
        if removed:
            if wipeout:
                return False
            # domain Xi berubah -> periksa ulang arc (Xk -> Xi) untuk semua Xk != Xj
            for xk in csp.variables:
                if xk in graph[xi] and xk != xj and (xk, xi) not in q:
                    q.append((xk, xi))
    return True


def run_ac3(csp: CSP, domains: Domains, graph, queue=None):
    """Jalankan AC-3 sampai selesai. Return (ok, jumlah_arc, jumlah_nilai_dihapus)."""
    gen = ac3(csp, domains, graph, queue)
    arcs = removed = 0
    while True:
        try:
            ev = next(gen)
        except StopIteration as stop:
            return stop.value, arcs, removed
        arcs += 1
        removed += len(ev.removed)
