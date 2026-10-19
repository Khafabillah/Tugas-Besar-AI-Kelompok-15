"""
renderer.py
Semua kode menggambar (pygame). Hanya MEMBACA ViewModel; tidak ada logika CSP
selain memanggil csp.all_violations() untuk menyorot sektor yang melanggar.
"""

from __future__ import annotations

import math
import textwrap

import pygame

import config as cfg
from csp_model import CSP
from events import ViewModel
from solvers import MODE_LABELS

NODE_R = 57
LOG_LINE_H = 17


class Renderer:
    def __init__(self, screen: pygame.Surface, csp: CSP):
        self.screen = screen
        self.csp = csp
        mono = "consolas,dejavusansmono,menlo,couriernew,monospace"
        sans = "arial,helvetica,dejavusans,sans"
        self.f_title = pygame.font.SysFont(sans, 22, bold=True)
        self.f_node = pygame.font.SysFont(sans, 15, bold=True)
        self.f_node_s = pygame.font.SysFont(sans, 14)
        self.f_small = pygame.font.SysFont(sans, 13)
        self.f_chip = pygame.font.SysFont(sans, 12, bold=True)
        self.f_mono = pygame.font.SysFont(mono, 14)
        self.f_mono_b = pygame.font.SysFont(mono, 14, bold=True)
        self.char_w = max(1, self.f_mono.size("M")[0])
        self.positions = self._layout()

    def _layout(self):
        cx, cy, rx, ry = cfg.LEFT_W / 2, 385, 240, 215
        self.center = (cx, cy)
        order = self.csp.ring_order
        pos = {}
        for i, name in enumerate(order):
            ang = math.radians(-90 + i * 360 / len(order))
            pos[name] = (cx + rx * math.cos(ang), cy + ry * math.sin(ang))
        return pos

    # ------------------------------------------------------------------
    def _text(self, text, font, color, pos, anchor="center"):
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        setattr(rect, anchor, (int(pos[0]), int(pos[1])))
        self.screen.blit(surf, rect)
        return rect

    def draw(self, vm: ViewModel):
        self.screen.fill(cfg.BG)
        self._draw_left(vm)
        self._draw_right(vm)

    # ------------------------------------------------------------------
    # KIRI: visualisasi graf
    # ------------------------------------------------------------------
    def _draw_left(self, vm: ViewModel):
        s = self.screen
        cx, cy = self.center
        blink = (pygame.time.get_ticks() // 350) % 2 == 0

        self._text("KEAMANAN TRIBUN STADION - CSP", self.f_title, (236, 239, 241),
                   (cfg.LEFT_W / 2, 26))
        if vm.finished:
            txt, col = (("SOLUSI VALID", (105, 240, 174)) if vm.success
                        else ("GAGAL MENEMUKAN SOLUSI", (255, 138, 128)))
            self._text(txt, self.f_node, col, (cfg.LEFT_W / 2, 56))

        # lapangan
        pitch = pygame.Rect(cx - 120, cy - 70, 240, 140)
        pygame.draw.rect(s, (27, 94, 32), pitch, border_radius=8)
        pygame.draw.rect(s, (165, 214, 167), pitch, 2, border_radius=8)
        pygame.draw.line(s, (165, 214, 167), (cx, cy - 70), (cx, cy + 70), 2)
        pygame.draw.circle(s, (165, 214, 167), (int(cx), int(cy)), 26, 2)

        violations = self.csp.all_violations(vm.assignment)
        clashing, bad_pairs = set(), set()
        for v in violations:
            clashing.update(v.variables)
            if v.kind == "binary":
                bad_pairs.add(frozenset(v.variables))

        # edge graf
        for a, b in self.csp.edges:
            pa, pb = self.positions[a], self.positions[b]
            if frozenset((a, b)) in bad_pairs:
                pygame.draw.line(s, (255, 23, 68), pa, pb, 7)
            else:
                pygame.draw.line(s, (84, 110, 122), pa, pb, 2)

        # arc AC-3 yang sedang diperiksa
        if vm.arc:
            self._draw_arc(vm.arc[0], vm.arc[1])

        # node
        for name in self.csp.variables:
            self._draw_node(vm, name, name in clashing, blink)

        # legenda & aturan
        for i, g in enumerate(cfg.DOMAIN):
            x = 40 + i * 165
            pygame.draw.rect(s, cfg.GROUP_COLORS[g], (x, cfg.WINDOW_H - 62, 18, 18),
                             border_radius=4)
            self._text(f"{g.replace('_', ' ')} ({cfg.SHORT_NAMES[g]})", self.f_small,
                       (207, 216, 220), (x + 26, cfg.WINDOW_H - 53), "midleft")
        rules = ("Aturan: (a) Tuan Rumah tidak bersebelahan dgn Tamu  "
                 "(b) Barat VIP = Netral  (c) maks 1 Tamu")
        self._text(rules, self.f_small, (120, 144, 156), (cfg.LEFT_W / 2, cfg.WINDOW_H - 32))
        extra = "   + skenario uji: Utara wajib Tamu" if self._has_extra() else ""
        self._text(f"Total konflik: {self.csp.total_conflicts(vm.assignment)}{extra}",
                   self.f_small, (236, 239, 241), (cfg.LEFT_W / 2, cfg.WINDOW_H - 12))

    def _has_extra(self):
        return sum(1 for c in self.csp.constraints if c.kind == "unary") > 1

    def _draw_arc(self, xi, xj):
        s = self.screen
        pi, pj = self.positions[xi], self.positions[xj]
        dx, dy = pj[0] - pi[0], pj[1] - pi[1]
        d = math.hypot(dx, dy) or 1
        ux, uy = dx / d, dy / d
        start = (pi[0] + ux * NODE_R, pi[1] + uy * NODE_R)
        tip = (pj[0] - ux * (NODE_R + 4), pj[1] - uy * (NODE_R + 4))
        col = (255, 213, 79)
        pygame.draw.line(s, col, start, tip, 4)
        px, py = -uy, ux
        base = (tip[0] - ux * 16, tip[1] - uy * 16)
        pygame.draw.polygon(s, col, [tip, (base[0] + px * 8, base[1] + py * 8),
                                     (base[0] - px * 8, base[1] - py * 8)])

    def _draw_node(self, vm: ViewModel, name: str, clash: bool, blink: bool):
        s = self.screen
        x, y = self.positions[name]
        ix, iy = int(x), int(y)
        group = vm.assignment.get(name)
        fill = cfg.GROUP_COLORS.get(group, cfg.EMPTY_COLOR)
        txt_col = cfg.GROUP_TEXT_COLORS.get(group, (207, 216, 220))

        if vm.current == name:
            pygame.draw.circle(s, (0, 229, 255), (ix, iy), NODE_R + 9, 3)
        if vm.arc and name == vm.arc[0]:
            pygame.draw.circle(s, (255, 213, 79), (ix, iy), NODE_R + 14, 3)
        if vm.flash == name:
            pygame.draw.circle(s, (255, 112, 67), (ix, iy), NODE_R + 20, 4)

        pygame.draw.circle(s, fill, (ix, iy), NODE_R)
        if clash:
            outline, width = ((255, 23, 68) if blink else (255, 255, 255)), 7
        elif vm.finished and vm.success:
            outline, width = (105, 240, 174), 4
        else:
            outline, width = (144, 164, 174), 2
        pygame.draw.circle(s, outline, (ix, iy), NODE_R, width)

        self._text(name.replace("_", " "), self.f_node, txt_col, (x, y - 9))
        self._text(group.replace("_", " ") if group else "kosong", self.f_node_s,
                   txt_col, (x, y + 11))

        top = y - NODE_R - 14
        if name == cfg.VIP_SECTOR:
            self._text("VIP (wajib Netral)", self.f_small, (253, 216, 53), (x, top))
            top -= 15
        if clash:
            self._text("CLASH!", self.f_node, (255, 82, 82), (x, top))

        # sisa domain legal (chip kecil) di bawah node
        if name not in vm.assignment and name in vm.domains:
            self._draw_domain_chips(vm.domains[name], x, y + NODE_R + 16)

    def _draw_domain_chips(self, values, x, y):
        if not values:
            self._text("DOMAIN KOSONG", self.f_chip, (255, 82, 82), (x, y))
            return
        w, gap = 30, 4
        total = len(values) * w + (len(values) - 1) * gap
        left = x - total / 2
        for i, v in enumerate(values):
            rect = pygame.Rect(int(left + i * (w + gap)), int(y - 9), w, 18)
            pygame.draw.rect(self.screen, cfg.GROUP_COLORS[v], rect, border_radius=5)
            self._text(cfg.SHORT_NAMES[v], self.f_chip, cfg.GROUP_TEXT_COLORS[v], rect.center)

    # ------------------------------------------------------------------
    # KANAN: live debug
    # ------------------------------------------------------------------
    def _draw_right(self, vm: ViewModel):
        s = self.screen
        x0 = cfg.LEFT_W
        w = cfg.WINDOW_W - x0
        pygame.draw.rect(s, cfg.PANEL_BG, (x0, 0, w, cfg.WINDOW_H))
        pygame.draw.line(s, (48, 54, 61), (x0, 0), (x0, cfg.WINDOW_H), 2)
        px = x0 + 14
        y = 12

        def header(text):
            nonlocal y
            self._text(text, self.f_mono_b, (144, 202, 249), (px, y), "topleft")
            y += LOG_LINE_H + 3

        def line(text, color=(236, 239, 241)):
            nonlocal y
            self._text(text, self.f_mono, color, (px, y), "topleft")
            y += LOG_LINE_H

        m = vm.metrics
        header("LIVE DEBUG")
        line(f"Mode      : {vm.mode_label}")
        line(f"Status    : {vm.status}")
        line(f"Iterasi   : {m.iterations:<5} Clash     : {m.clashes}")
        line(f"Backtrack : {m.backtracks:<5} Arc dicek : {m.arc_checks} (hapus {m.removals})")
        line(f"Dievaluasi: {vm.focus or '-'}", (128, 222, 234))
        line(f"Kecepatan : {vm.delay_ms} ms | urutan nilai statis: {vm.value_order}",
             (176, 190, 197))
        y += 6

        header("PERBANDINGAN (run terakhir tiap mode)")
        line(f"{'Mode':<16}{'Iter':>5}{'Clash':>6}{'Back':>6}{'Arc':>5}  OK",
             (176, 190, 197))
        for key in range(1, 6):
            r = vm.results.get(key)
            label = f"[{key}] {MODE_LABELS[key]}"[:16]
            if r is None:
                line(f"{label:<16}{'-':>5}{'-':>6}{'-':>6}{'-':>5}", (96, 108, 118))
            else:
                mm = r.metrics
                line(f"{label:<16}{mm.iterations:>5}{mm.clashes:>6}{mm.backtracks:>6}"
                     f"{mm.arc_checks:>5}  {'ya' if r.success else 'TIDAK'}",
                     (105, 240, 174) if r.success else (255, 138, 128))
        y += 6

        header("LOG ALGORITMA")
        help_h = 4 * LOG_LINE_H + 12
        log_bottom = cfg.WINDOW_H - help_h
        self._draw_log(vm, px, y, w - 28, log_bottom)

        hy = log_bottom + 6
        for t in ("[1] MinConf [2] Naif [3] +MRV [4] +LCV [5] +AC-3",
                  "[R] Reset  [Spasi] Pause  [N] 1 langkah  [+/-] Kecepatan",
                  "[O] Urutan nilai  [S] Skenario uji  [Roda] Scroll log",
                  "[Esc] Keluar"):
            self._text(t, self.f_mono, (120, 144, 156), (px, hy), "topleft")
            hy += LOG_LINE_H

    def _draw_log(self, vm: ViewModel, x, top, width, bottom):
        pygame.draw.rect(self.screen, (11, 15, 20), (x - 6, top - 2, width + 12, bottom - top))
        max_chars = max(20, width // self.char_w)
        rows = []
        for kind, text in vm.log[-250:]:
            color = cfg.LOG_COLORS.get(kind, cfg.LOG_COLORS["info"])
            for i, part in enumerate(textwrap.wrap(text, max_chars, subsequent_indent="   ")
                                     or [""]):
                rows.append((part, color))
        visible = max(1, (bottom - top - 4) // LOG_LINE_H)
        max_scroll = max(0, len(rows) - visible)
        vm.log_scroll = max(0, min(vm.log_scroll, max_scroll))
        end = len(rows) - vm.log_scroll
        for i, (part, color) in enumerate(rows[max(0, end - visible):end]):
            self._text(part, self.f_mono, color, (x, top + i * LOG_LINE_H), "topleft")
