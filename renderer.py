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

NODE_R = 37
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
        self.f_chip = pygame.font.SysFont(sans, 11, bold=True)
        self.f_tiny = pygame.font.SysFont(sans, 10)
        self.f_lab = pygame.font.SysFont(sans, 11, bold=True)
        self.f_mono = pygame.font.SysFont(mono, 14)
        self.f_mono_b = pygame.font.SysFont(mono, 14, bold=True)
        self.char_w = max(1, self.f_mono.size("M")[0])
        self.positions = self._layout()

    def _layout(self):
        cx, cy, rx, ry = cfg.LEFT_W / 2, 392, 235, 218
        self.center = (cx, cy)
        order = self.csp.ring_order
        step = 360 / len(order)
        start_angle = 180 - (6 - 1) / 2 * step     # 6 zona Barat berpusat di sisi kiri
        pos, self.angles = {}, {}
        for i, name in enumerate(order):
            ang = math.radians(start_angle + i * step)
            self.angles[name] = ang
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

        self._text("KEAMANAN TRIBUN STADION - 16 SUB-ZONA", self.f_title, (236, 239, 241),
                   (cfg.LEFT_W / 2, 26))
        if vm.finished:
            txt, col = (("SOLUSI VALID", (105, 240, 174)) if vm.success
                        else ("GAGAL MENEMUKAN SOLUSI", (255, 138, 128)))
            self._text(txt, self.f_node, col, (cfg.LEFT_W / 2, 54))

        # lapangan
        pitch = pygame.Rect(cx - 110, cy - 62, 220, 124)
        pygame.draw.rect(s, (27, 94, 32), pitch, border_radius=8)
        pygame.draw.rect(s, (165, 214, 167), pitch, 2, border_radius=8)
        pygame.draw.line(s, (165, 214, 167), (cx, cy - 62), (cx, cy + 62), 2)
        pygame.draw.circle(s, (165, 214, 167), (int(cx), int(cy)), 24, 2)

        # label sektor besar (di dalam cincin)
        groups = {}
        for name in self.csp.variables:
            groups.setdefault(cfg.ZONE_SECTOR[name], []).append(self.positions[name])
        for label, pts in groups.items():
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            lx, ly = cx + (mx - cx) * 0.68, cy + (my - cy) * 0.68
            self._text(label, self.f_small, (96, 125, 139), (lx, ly))

        violations = self.csp.all_violations(vm.assignment)
        clashing, bad_pairs = set(), set()
        for v in violations:
            clashing.update(v.variables)
            if v.kind == "binary":
                bad_pairs.add(frozenset(v.variables))

        for a, b in self.csp.edges:
            pa, pb = self.positions[a], self.positions[b]
            if frozenset((a, b)) in bad_pairs:
                pygame.draw.line(s, (255, 23, 68), pa, pb, 7)
            else:
                pygame.draw.line(s, (84, 110, 122), pa, pb, 2)

        if vm.arc:
            self._draw_arc(vm.arc[0], vm.arc[1])

        for name in self.csp.variables:
            self._draw_node(vm, name, name in clashing, blink)

        # legenda & aturan
        for i, g in enumerate(cfg.DOMAIN):
            x = 22 + i * 140
            pygame.draw.rect(s, cfg.GROUP_COLORS[g], (x, cfg.WINDOW_H - 60, 16, 16),
                             border_radius=4)
            self._text(f"{g.replace('_', ' ')} ({cfg.SHORT_NAMES[g]})", self.f_small,
                       (207, 216, 220), (x + 22, cfg.WINDOW_H - 52), "midleft")
        self._text("(a) Tuan Rumah tidak bersebelahan dgn Tamu   (b) tiap zona punya domain unary",
                   self.f_small, (120, 144, 156), (cfg.LEFT_W / 2, cfg.WINDOW_H - 34))
        self._text("(c) maks 1 sektor Tamu   (d) VIP/Media tidak bersebelahan dgn Tamu",
                   self.f_small, (120, 144, 156), (cfg.LEFT_W / 2, cfg.WINDOW_H - 19))
        self._text(f"Skenario: {getattr(self.csp, 'scenario', '-')}  |  "
                   f"Total konflik: {self.csp.total_conflicts(vm.assignment)}",
                   self.f_small, (236, 239, 241), (cfg.LEFT_W / 2, cfg.WINDOW_H - 4), "midbottom")

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
        base = (tip[0] - ux * 14, tip[1] - uy * 14)
        pygame.draw.polygon(s, col, [tip, (base[0] + px * 7, base[1] + py * 7),
                                     (base[0] - px * 7, base[1] - py * 7)])

    def _draw_node(self, vm: ViewModel, name: str, clash: bool, blink: bool):
        s = self.screen
        x, y = self.positions[name]
        ix, iy = int(x), int(y)
        group = vm.assignment.get(name)
        fill = cfg.GROUP_COLORS.get(group, cfg.EMPTY_COLOR)
        txt_col = cfg.GROUP_TEXT_COLORS.get(group, (207, 216, 220))

        if vm.current == name:
            pygame.draw.circle(s, (0, 229, 255), (ix, iy), NODE_R + 6, 3)
        if vm.arc and name == vm.arc[0]:
            pygame.draw.circle(s, (255, 213, 79), (ix, iy), NODE_R + 10, 3)
        if vm.flash == name:
            pygame.draw.circle(s, (255, 112, 67), (ix, iy), NODE_R + 14, 4)

        pygame.draw.circle(s, fill, (ix, iy), NODE_R)
        if clash:
            outline, width = ((255, 23, 68) if blink else (255, 255, 255)), 6
        elif vm.finished and vm.success:
            outline, width = (105, 240, 174), 3
        else:
            outline, width = (144, 164, 174), 2
        pygame.draw.circle(s, outline, (ix, iy), NODE_R, width)

        self._text(f"#{cfg.ZONE_NUMBER[name]}", self.f_tiny, txt_col, (x, y - 17))
        self._text(cfg.ZONE_LABEL[name], self.f_lab, txt_col, (x, y - 3))
        self._text(group.replace("_", " ") if group else "kosong", self.f_tiny,
                   txt_col, (x, y + 13))

        if clash:   # penanda CLASH di sisi dalam cincin
            cx, cy = self.center
            ux, uy = (cx - x), (cy - y)
            d = math.hypot(ux, uy) or 1
            self._text("CLASH!", self.f_chip, (255, 82, 82),
                       (x + ux / d * (NODE_R + 14), y + uy / d * (NODE_R + 14)))

        # sisa domain (chip) di sisi luar cincin
        if name not in vm.assignment and name in vm.domains:
            self._draw_domain_chips(vm.domains[name], name, x, y)

    def _draw_domain_chips(self, values, name, x, y):
        ang = self.angles[name]
        ux, uy = math.cos(ang), math.sin(ang)
        cw, ch, gap, cols = 24, 15, 3, 3
        if not values:
            bw, bh = 80, 15
        else:
            rows = [values[i:i + cols] for i in range(0, len(values), cols)]
            bw = min(len(values), cols) * cw + (min(len(values), cols) - 1) * gap
            bh = len(rows) * ch + (len(rows) - 1) * gap
        ccx = x + ux * (NODE_R + 8 + bw / 2 * abs(ux))
        ccy = y + uy * (NODE_R + 8 + bh / 2 * abs(uy))
        if not values:
            self._text("DOMAIN KOSONG", self.f_chip, (255, 82, 82), (ccx, ccy))
            return
        top = ccy - bh / 2
        for r, row in enumerate(rows):
            rw = len(row) * cw + (len(row) - 1) * gap
            left = ccx - rw / 2
            for i, v in enumerate(row):
                rect = pygame.Rect(int(left + i * (cw + gap)), int(top + r * (ch + gap)), cw, ch)
                pygame.draw.rect(self.screen, cfg.GROUP_COLORS[v], rect, border_radius=4)
                self._text(cfg.SHORT_NAMES[v], self.f_chip, cfg.GROUP_TEXT_COLORS[v],
                           rect.center)

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
                  "[O] Urutan nilai  [S] Skenario  [Roda] Scroll log",
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
