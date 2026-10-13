"""
events.py
Struktur data yang dipertukarkan antara solver (logika) dan UI (tampilan).
Solver TIDAK tahu pygame; UI hanya membaca objek-objek ini.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ArcEvent:
    """Hasil satu REVISE(xi, xj) di dalam AC-3."""
    xi: str
    xj: str
    removed: List[str]
    wipeout: bool = False


@dataclass
class Metrics:
    iterations: int = 0   # BT: percobaan assign | LS: jumlah perubahan nilai
    clashes: int = 0      # percobaan assign yang melanggar constraint
    backtracks: int = 0   # pembatalan assignment
    arc_checks: int = 0   # jumlah REVISE yang dijalankan AC-3
    removals: int = 0     # jumlah nilai yang dihapus AC-3


@dataclass
class Step:
    """Satu 'frame' proses pencarian."""
    assignment: Dict[str, str]
    logs: List[Tuple[str, str]] = field(default_factory=list)   # (kind, teks)
    current: Optional[str] = None                 # variabel yang dievaluasi
    domains: Dict[str, List[str]] = field(default_factory=dict)  # sisa domain var kosong
    focus: str = ""                               # ringkasan variabel yang dievaluasi
    arc: Optional[Tuple[str, str]] = None         # arc (xi -> xj) yang sedang diperiksa
    flash: Optional[str] = None                   # node yang domainnya baru berkurang
    metrics: Metrics = field(default_factory=Metrics)
    total_conflicts: int = 0
    weight: float = 1.0                           # pengali delay untuk langkah ini
    done: bool = False
    success: bool = False


@dataclass
class RunResult:
    label: str
    metrics: Metrics
    success: bool


@dataclass
class ViewModel:
    """Semua yang dibutuhkan Renderer untuk menggambar satu frame."""
    mode_label: str = "-"
    assignment: Dict[str, str] = field(default_factory=dict)
    current: Optional[str] = None
    domains: Dict[str, List[str]] = field(default_factory=dict)
    focus: str = ""
    arc: Optional[Tuple[str, str]] = None
    flash: Optional[str] = None
    metrics: Metrics = field(default_factory=Metrics)
    status: str = ""
    delay_ms: int = 650
    value_order: str = "asli"
    finished: bool = False
    success: bool = False
    log: List[Tuple[str, str]] = field(default_factory=list)
    log_scroll: int = 0
    results: Dict[int, RunResult] = field(default_factory=dict)
