"""Antarmuka Pygame: pemilih algoritma, visualisasi graf, dan log langkah."""

from __future__ import annotations

from collections import deque
from typing import Optional

try:
    import pygame
except ImportError as exc:
    raise SystemExit("Pygame belum terpasang. Pasang dengan: py -m pip install pygame") from exc

import config as cfg
from algorithms import Solver, Step
from csp_model import build_stadium_csp


WIDTH, HEIGHT = 1280, 760
TOP_H = 100
LEFT_W = 760
BG = (27, 31, 39)
PANEL = (13, 17, 23)
TEXT = (225, 232, 238)
MUTED = (145, 158, 168)
ACCENT = (68, 138, 201)
OPTIONS = list(Solver.MODES.items())


class StadiumApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Keamanan Tribun Stadion — Simulasi CSP")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 16)
        self.small = pygame.font.SysFont("consolas", 13)
        self.title = pygame.font.SysFont("segoeui", 23, bold=True)
        self.csp = build_stadium_csp()
        self.mode_idx = 0
        self.dropdown_open = False
        self.assignment = {}
        self.domains = self.csp.initial_domains()
        self.current: Optional[str] = None
        self.logs = deque(maxlen=400)
        self.generator = None
        self.running = False
        self.paused = False
        self.finished = False
        self.success = False
        self.iteration = 0
        self.delay_ms = 650
        self.next_step_at = 0
        self.blink = False
        self.last_blink = 0
        self._log("Pilih algoritma lalu klik START. Space: jeda, N: satu langkah, R: reset.", "sys")
        self._layout()

    def _layout(self):
        self.dropdown_rect = pygame.Rect(24, 43, 475, 40)
        self.start_rect = pygame.Rect(514, 43, 132, 40)
        self.speed_rect = pygame.Rect(665, 43, 215, 40)
        self.body_left = pygame.Rect(0, TOP_H, LEFT_W, HEIGHT - TOP_H)
        self.body_right = pygame.Rect(LEFT_W, TOP_H, WIDTH - LEFT_W, HEIGHT - TOP_H)
        cx, cy, rx, ry = LEFT_W / 2, TOP_H + 305, 260, 206
        self.positions = {}
        order = self.csp.ring_order
        import math
        for i, sector in enumerate(order):
            angle = math.radians(-90 + i * 360 / len(order))
            self.positions[sector] = (int(cx + rx * math.cos(angle)), int(cy + ry * math.sin(angle)))

    def _log(self, message, kind="info"):
        self.logs.append((kind, message))

    def start(self):
        mode, label = OPTIONS[self.mode_idx]
        self.csp = build_stadium_csp()
        self.generator = Solver(self.csp, mode).solve()
        self.assignment = {}
        self.domains = self.csp.initial_domains()
        self.current = None
        self.iteration = 0
        self.running = True
        self.paused = False
        self.finished = False
        self.success = False
        self.logs.clear()
        self._log(f"=== MULAI: {label} ===", "header")
        self._advance()
        self.next_step_at = pygame.time.get_ticks() + self.delay_ms

    def _advance(self):
        if self.generator is None or self.finished:
            return
        try:
            step: Step = next(self.generator)
        except StopIteration:
            self.running = False
            self.finished = True
            return
        self.assignment = dict(step.assignment)
        self.domains = {v: list(d) for v, d in step.domains.items()}
        self.current = step.current
        self.iteration = step.iteration
        for kind, message in step.logs:
            self._log(message, kind)
        if step.done:
            self.running = False
            self.finished = True
            self.success = step.success

    def _legal_values(self, var):
        if var in self.assignment:
            return [self.assignment[var]]
        candidates = self.domains.get(var, self.csp.domains[var])
        return [value for value in candidates
                if not self.csp.violations_involving({**self.assignment, var: value}, var)]

    @staticmethod
    def _text(surface, value, pos, color=TEXT, font=None):
        surface.blit((font or pygame.font.SysFont("consolas", 15)).render(str(value), True, color), pos)

    def _draw_header(self):
        pygame.draw.rect(self.screen, (18, 23, 30), (0, 0, WIDTH, TOP_H))
        self._text(self.screen, "KEAMANAN TRIBUN STADION  |  CSP + LOCAL SEARCH", (24, 12), TEXT, self.title)
        pygame.draw.rect(self.screen, (38, 46, 56), self.dropdown_rect, border_radius=5)
        pygame.draw.rect(self.screen, (75, 88, 101), self.dropdown_rect, 1, border_radius=5)
        self._text(self.screen, OPTIONS[self.mode_idx][1], (self.dropdown_rect.x + 12, self.dropdown_rect.y + 11), TEXT, self.small)
        self._text(self.screen, "▾", (self.dropdown_rect.right - 25, self.dropdown_rect.y + 9), TEXT, self.font)
        pygame.draw.rect(self.screen, ACCENT if not self.running else (65, 75, 82), self.start_rect, border_radius=5)
        self._text(self.screen, "START" if not self.running else "RUNNING", (self.start_rect.x + 25, self.start_rect.y + 10), (255, 255, 255), self.font)
        self._text(self.screen, f"Jeda: {self.delay_ms} ms  [- / +]", (self.speed_rect.x, self.speed_rect.y + 11), MUTED, self.small)
        if self.dropdown_open:
            menu = pygame.Rect(self.dropdown_rect.x, TOP_H - 2, self.dropdown_rect.w, len(OPTIONS) * 34)
            pygame.draw.rect(self.screen, (34, 41, 50), menu, border_radius=4)
            for i, (_, label) in enumerate(OPTIONS):
                row = pygame.Rect(menu.x, menu.y + i * 34, menu.w, 34)
                if i == self.mode_idx:
                    pygame.draw.rect(self.screen, (53, 83, 108), row)
                self._text(self.screen, f"{i + 1}. {label}", (row.x + 10, row.y + 8), TEXT, self.small)

    def _draw_graph(self):
        pygame.draw.rect(self.screen, BG, self.body_left)
        cx, cy = self.positions["Utara"][0], int(TOP_H + 305)
        # Lapangan sebagai petunjuk visual di tengah graf.
        field = pygame.Rect(cx - 118, cy - 66, 236, 132)
        pygame.draw.rect(self.screen, (27, 90, 49), field, border_radius=18)
        pygame.draw.rect(self.screen, (137, 190, 147), field, 2, border_radius=18)
        pygame.draw.line(self.screen, (137, 190, 147), (cx, field.y), (cx, field.bottom), 2)
        pygame.draw.circle(self.screen, (137, 190, 147), (cx, cy), 25, 2)

        violations = self.csp.all_violations(self.assignment)
        clashing = {v for issue in violations for v in issue.variables}
        for a, b in self.csp.edges:
            pygame.draw.line(self.screen, (244, 55, 70) if a in clashing and b in clashing else (93, 112, 125),
                             self.positions[a], self.positions[b], 5 if a in clashing and b in clashing else 2)

        now = pygame.time.get_ticks()
        if now - self.last_blink > 350:
            self.blink = not self.blink
            self.last_blink = now
        for name in self.csp.variables:
            x, y = self.positions[name]
            group = self.assignment.get(name)
            color = cfg.GROUP_COLORS.get(group, (55, 71, 79))
            radius = 52
            if name == self.current:
                pygame.draw.circle(self.screen, (0, 229, 255), (x, y), radius + 8, 3)
            outline = (255, 40, 55) if name in clashing and self.blink else (211, 222, 228)
            pygame.draw.circle(self.screen, color, (x, y), radius)
            pygame.draw.circle(self.screen, outline, (x, y), radius, 5 if name in clashing else 2)
            label = name.replace("_", " ")
            lab = self.small.render(label, True, (255, 255, 255))
            self.screen.blit(lab, lab.get_rect(center=(x, y - 10)))
            val = (group or "kosong").replace("_", " ")
            val_surf = self.small.render(val, True, (255, 255, 255))
            self.screen.blit(val_surf, val_surf.get_rect(center=(x, y + 11)))
            legal = self._legal_values(name)
            domain_text = "{" + ", ".join(cfg.SHORT_NAMES[v] for v in legal) + "}"
            tx = x + radius + 8 if x < LEFT_W // 2 else x - radius - 75
            self._text(self.screen, domain_text, (tx, y - 7), (160, 222, 230), self.small)
            if name == cfg.VIP_SECTOR:
                self._text(self.screen, "VIP: Netral", (x - 38, y - radius - 21), (253, 216, 53), self.small)

        # Legend and CSP rules.
        lx, ly = 24, HEIGHT - 60
        for i, group in enumerate(cfg.DOMAIN):
            x = lx + i * 174
            pygame.draw.circle(self.screen, cfg.GROUP_COLORS[group], (x + 8, ly + 7), 7)
            self._text(self.screen, group.replace("_", " "), (x + 21, ly), TEXT, self.small)
        self._text(self.screen, "Aturan: Tuan Rumah ≠ Tamu bertetangga | Barat VIP = Netral | Maks. 1 sektor Tamu",
                   (24, HEIGHT - 27), MUTED, self.small)

    def _draw_log(self):
        pygame.draw.rect(self.screen, PANEL, self.body_right)
        pygame.draw.line(self.screen, (49, 59, 70), (LEFT_W, TOP_H), (LEFT_W, HEIGHT), 2)
        self._text(self.screen, "LIVE DEBUG LOG", (LEFT_W + 20, TOP_H + 16), (144, 202, 249), self.font)
        status = "BERJALAN" if self.running else ("PAUSE" if self.paused else ("SELESAI: VALID" if self.success else "SELESAI: GAGAL") if self.finished else "SIAP")
        self._text(self.screen, f"Status: {status}   Iterasi: {self.iteration}", (LEFT_W + 20, TOP_H + 43), TEXT, self.small)
        self._text(self.screen, f"Konflik: {self.csp.total_conflicts(self.assignment)}", (LEFT_W + 20, TOP_H + 64), TEXT, self.small)
        pygame.draw.line(self.screen, (49, 59, 70), (LEFT_W + 18, TOP_H + 88), (WIDTH - 18, TOP_H + 88), 1)
        available = HEIGHT - (TOP_H + 111) - 22
        line_h = 20
        max_lines = max(1, available // line_h)
        visible = list(self.logs)[-max_lines:]
        y = TOP_H + 102
        colors = {"header": (144, 202, 249), "mrv": (128, 222, 234), "lcv": (206, 147, 216),
                  "ac3": (255, 213, 79), "assign": (165, 214, 167), "clash": (255, 82, 82),
                  "backtrack": (255, 183, 77), "success": (105, 240, 174), "fail": (255, 138, 128),
                  "sys": MUTED, "info": TEXT}
        for kind, message in visible:
            color = colors.get(kind, TEXT)
            max_chars = 58
            chunks = [message[i:i + max_chars] for i in range(0, len(message), max_chars)] or [""]
            for chunk in chunks:
                if y > HEIGHT - 15:
                    break
                self._text(self.screen, chunk, (LEFT_W + 20, y), color, self.small)
                y += line_h

    def _draw(self):
        self.screen.fill(BG)
        self._draw_header()
        self._draw_graph()
        self._draw_log()
        pygame.display.flip()

    def run(self):
        alive = True
        while alive:
            now = pygame.time.get_ticks()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    alive = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = event.pos
                    if self.dropdown_open:
                        menu_top = TOP_H - 2
                        idx = (pos[1] - menu_top) // 34
                        if self.dropdown_rect.x <= pos[0] <= self.dropdown_rect.right and 0 <= idx < len(OPTIONS):
                            self.mode_idx = int(idx)
                        self.dropdown_open = False
                    elif self.dropdown_rect.collidepoint(pos):
                        self.dropdown_open = True
                    elif self.start_rect.collidepoint(pos) and not self.running:
                        self.start()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
                    self.delay_ms = max(80, min(2500, self.delay_ms + (-80 if event.button == 4 else 80)))
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        alive = False
                    elif event.key == pygame.K_SPACE and self.running:
                        self.paused = not self.paused
                        if not self.paused:
                            self.next_step_at = now + self.delay_ms
                    elif event.key == pygame.K_n and self.running and self.paused:
                        self._advance()
                    elif event.key == pygame.K_r:
                        self.running = self.paused = self.finished = False
                        self.generator = None
                        self.assignment = {}
                        self.domains = self.csp.initial_domains()
                        self.current = None
                        self.logs.clear()
                        self._log("Reset. Pilih algoritma lalu klik START.", "sys")
                    elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.delay_ms = max(80, self.delay_ms - 80)
                    elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.delay_ms = min(2500, self.delay_ms + 80)

            # Timer-based stepping keeps the event loop and rendering responsive.
            if self.running and not self.paused and now >= self.next_step_at:
                self._advance()
                self.next_step_at = now + self.delay_ms
            self._draw()
            self.clock.tick(60)
        pygame.quit()


def app():
    StadiumApp().run()
