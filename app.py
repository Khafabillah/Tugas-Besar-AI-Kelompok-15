"""
app.py
Loop utama pygame: input keyboard, penjadwalan langkah (jeda), dan penyajian.

Jeda antar langkah dilakukan NON-BLOKIR (membandingkan pygame.time.get_ticks()
dengan waktu langkah berikutnya) sehingga jendela tetap responsif dan bisa
di-pause / diubah kecepatannya, tetapi efeknya sama dengan delay per langkah.
"""

from __future__ import annotations

from dataclasses import replace

import pygame

import config as cfg
from csp_model import SCENARIOS, build_stadium_csp
from events import RunResult, ViewModel
from renderer import Renderer
from solvers import MODE_LABELS, create_solver

KEY_TO_MODE = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4,
               pygame.K_5: 5, pygame.K_6: 6, pygame.K_7: 7, pygame.K_8: 8,
               pygame.K_KP1: 1, pygame.K_KP2: 2, pygame.K_KP3: 3, pygame.K_KP4: 4,
               pygame.K_KP5: 5, pygame.K_KP6: 6, pygame.K_KP7: 7, pygame.K_KP8: 8}
MAX_LOG = 500


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Simulasi CSP - Keamanan Tribun Stadion")
        pygame.display.set_mode((cfg.WINDOW_W, cfg.WINDOW_H), pygame.RESIZABLE)
        # Render at the original logical size, then scale into the resizable window.
        self.screen = pygame.Surface((cfg.WINDOW_W, cfg.WINDOW_H))
        self.clock = pygame.time.Clock()

        self.scenario_idx = 0
        self.csp = build_stadium_csp(SCENARIOS[self.scenario_idx])
        self.renderer = Renderer(self.screen, self.csp)

        self.order_names = list(cfg.STATIC_VALUE_ORDERS)
        self.order_idx = 0
        self.vm = ViewModel(delay_ms=cfg.BASE_DELAY_MS, value_order=self.order_names[0])

        self.generator = None
        self.mode = None
        self.running = False
        self.paused = False
        self.next_at = 0
        self.alive = True
        self.log("header", "=== Simulasi CSP Keamanan Tribun Stadion ===")
        self.log("sys", "Klik algoritma atau tekan 1-8 untuk memilih solver.")

    # ---------------- util ----------------
    def log(self, kind, text):
        self.vm.log.append((kind, text))
        if len(self.vm.log) > MAX_LOG:
            del self.vm.log[:len(self.vm.log) - MAX_LOG]

    @property
    def static_order(self):
        return cfg.STATIC_VALUE_ORDERS[self.order_names[self.order_idx]]

    def _clear_view(self):
        vm = self.vm
        vm.assignment, vm.current, vm.domains = {}, None, {}
        vm.focus, vm.arc, vm.flash = "", None, None
        vm.finished = vm.success = False
        vm.metrics = replace(vm.metrics, iterations=0, clashes=0, backtracks=0,
                             arc_checks=0, removals=0, fc_checks=0, fc_removals=0,
                             constraint_checks=0, pair_checks=0, assignment_checks=0,
                             unary_checks=0)
        vm.log_scroll = 0

    # ---------------- kontrol ----------------
    def start_mode(self, mode: int):
        self._stop()
        self._clear_view()
        solver = create_solver(mode, self.csp, self.static_order)
        self.mode = mode
        self.generator = solver.solve()
        self.vm.mode_label = f"[{mode}] {solver.label}"
        self.running, self.paused = True, False
        self.next_at = 0
        self.log("header", f"\n=== MULAI: {solver.label} "
                           f"(skenario: {SCENARIOS[self.scenario_idx]}, "
                           f"urutan nilai: {self.order_names[self.order_idx]}) ===")

    def _stop(self):
        if self.generator is not None:
            self.generator.close()
        self.generator = None
        self.running = False

    def reset(self):
        self._stop()
        self._clear_view()
        self.vm.mode_label = "-"
        self.paused = False
        self.log("sys", "[RESET] Stadion dikosongkan.")

    def toggle_scenario(self):
        self.scenario_idx = (self.scenario_idx + 1) % len(SCENARIOS)
        self._stop()
        self._clear_view()
        self.csp = build_stadium_csp(SCENARIOS[self.scenario_idx])
        self.renderer.csp = self.csp
        self.vm.results.clear()          # hasil lama tidak sebanding lagi
        self.vm.mode_label = "-"
        self.log("sys", f"[SKENARIO] {SCENARIOS[self.scenario_idx]} "
                        f"(tabel perbandingan dikosongkan)")

    def toggle_pause(self):
        if self.running:
            self.paused = not self.paused
            self.log("sys", "[PAUSE]" if self.paused else "[RESUME]")

    def step_once(self):
        if self.running and self.paused:
            self._advance()

    def adjust_speed(self, faster):
        if faster:
            self.vm.delay_ms = max(40, int(self.vm.delay_ms * 0.7))
        else:
            self.vm.delay_ms = min(3000, int(self.vm.delay_ms * 1.4))

    def cycle_order(self):
        self.order_idx = (self.order_idx + 1) % len(self.order_names)
        self.vm.value_order = self.order_names[self.order_idx]
        self.log("sys", f"[SETTING] Urutan nilai statis: {self.vm.value_order} "
                        f"(berlaku pada run berikutnya)")

    def _activate_control(self, action):
        if not action:
            return
        if action.startswith("mode_"):
            self.start_mode(int(action.split("_", 1)[1]))
        elif action == "reset":
            self.reset()
        elif action == "pause":
            self.toggle_pause()
        elif action == "step":
            self.step_once()
        elif action == "slower":
            self.adjust_speed(faster=False)
        elif action == "faster":
            self.adjust_speed(faster=True)
        elif action == "scenario":
            self.toggle_scenario()
        elif action == "order":
            self.cycle_order()

    def _viewport(self):
        window = pygame.display.get_surface()
        width, height = window.get_size()
        scale = min(width / cfg.WINDOW_W, height / cfg.WINDOW_H)
        draw_width = max(1, round(cfg.WINDOW_W * scale))
        draw_height = max(1, round(cfg.WINDOW_H * scale))
        offset_x = (width - draw_width) // 2
        offset_y = (height - draw_height) // 2
        return scale, offset_x, offset_y, draw_width, draw_height

    def _to_canvas_position(self, position):
        scale, offset_x, offset_y, draw_width, draw_height = self._viewport()
        x = position[0] - offset_x
        y = position[1] - offset_y
        if x < 0 or y < 0 or x >= draw_width or y >= draw_height:
            return None
        return int(x / scale), int(y / scale)

    def _advance(self):
        try:
            step = next(self.generator)
        except StopIteration:
            self.running = False
            return
        vm = self.vm
        vm.assignment, vm.current, vm.domains = step.assignment, step.current, step.domains
        vm.focus, vm.arc, vm.flash, vm.metrics = step.focus, step.arc, step.flash, step.metrics
        for kind, text in step.logs:
            self.log(kind, text)
        if step.done:
            self.running = False
            vm.finished, vm.success = True, step.success
            final_conflicts = step.total_conflicts if self.mode == 1 else None
            vm.results[self.mode] = RunResult(vm.mode_label, step.metrics, step.success,
                                              final_conflicts)
        else:
            self.next_at = pygame.time.get_ticks() + int(vm.delay_ms * step.weight)

    # ---------------- input ----------------
    def handle(self, event):
        if event.type == pygame.QUIT:
            self.alive = False
        elif event.type == pygame.VIDEORESIZE:
            width, height = max(960, event.w), max(570, event.h)
            pygame.display.set_mode((width, height), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEWHEEL:
            self.vm.log_scroll = max(0, self.vm.log_scroll + event.y * 3)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            canvas_pos = self._to_canvas_position(event.pos)
            if canvas_pos is not None:
                self._activate_control(self.renderer.action_at(canvas_pos))
        elif event.type == pygame.KEYDOWN:
            k = event.key
            if k in KEY_TO_MODE:
                self.start_mode(KEY_TO_MODE[k])
            elif k == pygame.K_r:
                self.reset()
            elif k == pygame.K_SPACE and self.running:
                self.toggle_pause()
            elif k == pygame.K_n and self.running and self.paused:
                self.step_once()
            elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS, pygame.K_UP):
                self.adjust_speed(faster=True)
            elif k in (pygame.K_MINUS, pygame.K_KP_MINUS, pygame.K_DOWN):
                self.adjust_speed(faster=False)
            elif k == pygame.K_o:
                self.cycle_order()
            elif k == pygame.K_s:
                self.toggle_scenario()
            elif k == pygame.K_ESCAPE:
                self.alive = False

    # ---------------- loop ----------------
    def _status(self):
        if self.vm.finished:
            return "SELESAI — SOLUSI VALID" if self.vm.success else "SELESAI — GAGAL"
        if self.running:
            return "PAUSE" if self.paused else "Berjalan"
        return "Siap"

    def run(self):
        while self.alive:
            for event in pygame.event.get():
                self.handle(event)
            if self.running and not self.paused and pygame.time.get_ticks() >= self.next_at:
                self._advance()
            self.vm.status = self._status()
            self.renderer.draw(self.vm)
            self.renderer.mouse_position = (self._to_canvas_position(pygame.mouse.get_pos())
                                            or (-1, -1))
            window = pygame.display.get_surface()
            window.fill(cfg.BG)
            _scale, offset_x, offset_y, draw_width, draw_height = self._viewport()
            scaled = pygame.transform.smoothscale(self.screen, (draw_width, draw_height))
            window.blit(scaled, (offset_x, offset_y))
            pygame.display.flip()
            self.clock.tick(cfg.FPS)
        pygame.quit()
