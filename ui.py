# -*- coding: utf-8 -*-
"""
ui.py — Gestión de la interfaz de usuario (panel de controles).

Contiene:
  • Slider    — control deslizante genérico.
  • Button    — botón con estados hover/pressed.
  • UIManager — gestiona todos los controles del panel central.

El UIManager expone:
  • handle_event(event) → procesa clics y arrastres del mouse.
  • render(surface)     → dibuja todos los controles.
  • Propiedades para leer los valores actuales de los sliders.
"""

import pygame
import config


# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------

class Slider:
    """
    Control deslizante horizontal.

    Parameters
    ----------
    x, y       : esquina superior izquierda del track.
    width      : longitud del track en píxeles.
    min_val    : valor mínimo.
    max_val    : valor máximo.
    value      : valor inicial.
    label      : texto mostrado encima del slider.
    fmt        : formato de cadena para mostrar el valor (e.g. "{:.1f}").
    is_int     : si True, el valor se redondea al entero más cercano.
    """

    TRACK_H    = 6
    HANDLE_R   = 9
    LABEL_OFST = -22

    def __init__(self, x: int, y: int, width: int,
                 min_val: float, max_val: float, value: float,
                 label: str, fmt: str = "{:.2f}", is_int: bool = False):
        self.x         = x
        self.y         = y
        self.width     = width
        self.min_val   = min_val
        self.max_val   = max_val
        self._value    = value
        self.label     = label
        self.fmt       = fmt
        self.is_int    = is_int
        self._dragging = False

    # ------------------------------------------------------------------
    @property
    def value(self) -> float:
        return float(int(round(self._value))) if self.is_int else self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = max(self.min_val, min(self.max_val, v))

    # ------------------------------------------------------------------
    def _val_to_x(self) -> int:
        t = (self._value - self.min_val) / (self.max_val - self.min_val)
        return int(self.x + t * self.width)

    def _x_to_val(self, px: int) -> float:
        t = (px - self.x) / self.width
        t = max(0.0, min(1.0, t))
        return self.min_val + t * (self.max_val - self.min_val)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Procesa eventos de mouse para arrastrar el slider.

        Returns
        -------
        bool : True si el valor cambió.
        """
        changed = False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hx = self._val_to_x()
            hy = self.y
            dist = ((event.pos[0] - hx) ** 2 +
                    (event.pos[1] - hy) ** 2) ** 0.5
            if dist <= self.HANDLE_R + 6:
                self._dragging = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False

        elif event.type == pygame.MOUSEMOTION and self._dragging:
            old = self._value
            self._value = self._x_to_val(event.pos[0])
            if self.is_int:
                self._value = round(self._value)
            changed = (self._value != old)

        return changed

    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface, fonts: dict) -> None:
        """Dibuja el track, el handle y las etiquetas."""
        ty = self.y

        # Track
        track_rect = pygame.Rect(self.x, ty - self.TRACK_H // 2,
                                 self.width, self.TRACK_H)
        pygame.draw.rect(surface, config.GRAY_MED, track_rect,
                         border_radius=3)

        # Fill del track (parte activa)
        fill_w = self._val_to_x() - self.x
        if fill_w > 0:
            fill_rect = pygame.Rect(self.x, ty - self.TRACK_H // 2,
                                    fill_w, self.TRACK_H)
            pygame.draw.rect(surface, config.COLOR_ACCENT, fill_rect,
                             border_radius=3)

        # Handle
        hx = self._val_to_x()
        color_h = config.WHITE if not self._dragging else config.COLOR_ACCENT
        pygame.draw.circle(surface, color_h, (hx, ty), self.HANDLE_R)
        pygame.draw.circle(surface, config.COLOR_ACCENT, (hx, ty),
                           self.HANDLE_R, 2)

        # Label
        lbl = fonts['small'].render(self.label, True, config.COLOR_TEXT_DIM)
        surface.blit(lbl, (self.x, ty + self.LABEL_OFST))

        # Valor numérico
        val_str = self.fmt.format(self.value)
        val_s   = fonts['small'].render(val_str, True, config.COLOR_TEXT)
        surface.blit(val_s, (self.x + self.width + 8, ty - 7))


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

class Button:
    """
    Botón con estados normal, hover y pressed.

    Parameters
    ----------
    x, y   : posición.
    w, h   : dimensiones.
    label  : texto.
    color  : color base.
    action : identificador de acción (string).
    """

    def __init__(self, x: int, y: int, w: int, h: int,
                 label: str, color: tuple, action: str):
        self.rect   = pygame.Rect(x, y, w, h)
        self.label  = label
        self.color  = color
        self.action = action
        self._hover   = False
        self._pressed = False
        self.active   = False   # resalta el botón cuando está activo (modo toggle)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        """
        Returns
        -------
        str | None : action string si fue presionado, None en otro caso.
        """
        if event.type == pygame.MOUSEMOTION:
            self._hover = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and self.rect.collidepoint(event.pos):
                self._pressed = False
                return self.action
            self._pressed = False

        return None

    # ------------------------------------------------------------------
    def render(self, surface: pygame.Surface, fonts: dict) -> None:
        """Dibuja el botón con efecto de hover/pressed/active."""
        if self._pressed:
            c = tuple(max(0, v - 40) for v in self.color)
        elif self.active:
            c = tuple(min(255, v + 60) for v in self.color)
        elif self._hover:
            c = tuple(min(255, v + 30) for v in self.color)
        else:
            c = self.color

        pygame.draw.rect(surface, c, self.rect, border_radius=6)
        pygame.draw.rect(surface, config.WHITE, self.rect, width=1,
                         border_radius=6)

        txt = fonts['small'].render(self.label, True, config.WHITE)
        tr  = txt.get_rect(center=self.rect.center)
        surface.blit(txt, tr)


# ---------------------------------------------------------------------------
# UIManager
# ---------------------------------------------------------------------------

class UIManager:
    """
    Gestiona todos los controles de la interfaz en el panel central.

    Crea y coordina:
    - Sliders: B, N, A, R, velocidad.
    - Botones de control: Iniciar, Pausar, Reiniciar.
    - Botones de modo: Manual, Automático.
    - Botones de experimentos predefinidos.

    Expone propiedades para leer el estado actual de cada parámetro.
    """

    def __init__(self):
        self._build_controls()
        self.running   = True    # True = corriendo / False = pausada
        self.mode      = 'auto'  # 'auto' o 'manual'
        self.step_mode = False   # True = modo paso a paso activo

    # ------------------------------------------------------------------
    # Construcción de controles
    # ------------------------------------------------------------------

    def _build_controls(self) -> None:
        """Instancia todos los sliders y botones con su disposición."""
        px     = config.CTRL_PANEL_X + 16
        pw     = config.CTRL_PANEL_WIDTH - 32
        sw     = pw - 55   # ancho útil del track del slider

        y = config.CTRL_PANEL_Y + 50

        # -------- SLIDERS --------
        self.sl_B = Slider(px, y, sw,
                           config.B_MIN, config.B_MAX,
                           config.DEFAULT_B,
                           "Campo magnético B  [T]",
                           fmt="{:.2f}")
        y += 52

        self.sl_N = Slider(px, y, sw,
                           config.N_MIN, config.N_MAX,
                           config.DEFAULT_N,
                           "Número de espiras N",
                           fmt="{:.0f}", is_int=True)
        y += 52

        self.sl_A = Slider(px, y, sw,
                           config.A_MIN, config.A_MAX,
                           config.DEFAULT_A,
                           "Área de la bobina A  [m²]",
                           fmt="{:.3f}")
        y += 52

        self.sl_R = Slider(px, y, sw,
                           config.R_MIN, config.R_MAX,
                           config.DEFAULT_R,
                           "Resistencia R  [Ω]",
                           fmt="{:.1f}")
        y += 52

        self.sl_speed = Slider(px, y, sw,
                               config.SPEED_MIN, config.SPEED_MAX,
                               config.DEFAULT_SPEED,
                               "Velocidad del imán",
                               fmt="{:.2f}")
        y += 60

        self._sliders = [self.sl_B, self.sl_N,
                         self.sl_A, self.sl_R, self.sl_speed]

        # -------- BOTONES DE CONTROL --------
        bw, bh = pw // 3 - 4, 34
        self.btn_start  = Button(px,              y, bw, bh,
                                 "▶ Iniciar",
                                 (40, 160, 80), "start")
        self.btn_pause  = Button(px + bw + 4,     y, bw, bh,
                                 "⏸ Pausar",
                                 (180, 130, 30), "pause")
        self.btn_reset  = Button(px + (bw + 4)*2, y, bw, bh,
                                 "↺ Reiniciar",
                                 (160, 50, 50), "reset")
        y += bh + 12

        # -------- BOTONES DE MODO --------
        bw2 = pw // 2 - 3
        self.btn_auto   = Button(px,          y, bw2, bh,
                                 "⚙ Automático",
                                 (50, 80, 180), "mode_auto")
        self.btn_manual = Button(px + bw2 + 6, y, bw2, bh,
                                 "✋ Manual",
                                 (80, 50, 160), "mode_manual")
        y += bh + 20

        # -------- EXPERIMENTOS --------
        exp_bw = pw // 2 - 3
        exp_bh = 30
        self.btn_exp = []

        experiments = [
            ("×2 Espiras",      (60, 90, 150),  config.EXPERIMENT_DOUBLE_N),
            ("×2 Campo B",      (60, 130, 80),  config.EXPERIMENT_DOUBLE_B),
            ("Invertir imán",   (150, 60, 90),  config.EXPERIMENT_INVERT_MAGNET),
            ("×2 Velocidad",    (130, 100, 40), config.EXPERIMENT_DOUBLE_SPEED),
            ("Restablecer",     (90, 90, 90),   config.EXPERIMENT_RESET),
        ]

        for i, (lbl, col, act) in enumerate(experiments):
            col_i = i % 2
            row_i = i // 2
            bx    = px + col_i * (exp_bw + 6)
            by    = y + row_i * (exp_bh + 6)
            self.btn_exp.append(
                Button(bx, by, exp_bw, exp_bh, lbl, col, act)
            )

        # Avanzar y tras los experimentos (3 filas)
        num_exp_rows = (len(experiments) + 1) // 2
        y += num_exp_rows * (exp_bh + 6) + 12

        # -------- EDUCACIONAL --------
        bw3 = pw // 2 - 3
        self.btn_step_mode = Button(
            px, y, bw3, bh,
            "⏩ Paso a Paso", (60, 50, 130), "step_mode")
        self.btn_what = Button(
            px + bw3 + 6, y, bw3, bh,
            "❓ ¿Qué ocurre?", (30, 90, 120), "what_happens")
        y += bh + 6
        self.btn_next_step = Button(
            px, y, pw, bh,
            "▶ Siguiente Paso", (40, 120, 55), "next_step")

        # Todos los botones en una lista plana para iteración
        self._buttons = [
            self.btn_start, self.btn_pause, self.btn_reset,
            self.btn_auto, self.btn_manual,
            *self.btn_exp,
            self.btn_step_mode, self.btn_what, self.btn_next_step,
        ]

    # ------------------------------------------------------------------
    # Propiedades de lectura
    # ------------------------------------------------------------------

    @property
    def B(self)     -> float: return self.sl_B.value
    @property
    def N(self)     -> int:   return int(self.sl_N.value)
    @property
    def A(self)     -> float: return self.sl_A.value
    @property
    def R(self)     -> float: return self.sl_R.value
    @property
    def speed(self) -> float: return self.sl_speed.value

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """
        Distribuye el evento a todos los controles.

        Returns
        -------
        str | None : acción disparada (si hubo alguna), o None.
        """
        # Sliders
        for sl in self._sliders:
            sl.handle_event(event)

        # Botones — omitir btn_next_step si step_mode está inactivo
        for btn in self._buttons:
            if btn is self.btn_next_step and not self.step_mode:
                continue
            action = btn.handle_event(event)
            if action:
                self._process_action(action)
                return action

        return None

    # ------------------------------------------------------------------
    def _process_action(self, action: str) -> None:
        """Actualiza el estado interno según la acción recibida."""
        if action == "start":
            self.running   = True
            self.step_mode = False
            self.btn_step_mode.active = False
        elif action == "pause":
            self.running = False
        elif action == "mode_auto":
            self.mode = 'auto'
        elif action == "mode_manual":
            self.mode = 'manual'
        elif action == "step_mode":
            self.step_mode = not self.step_mode
            self.btn_step_mode.active = self.step_mode
            if self.step_mode:
                self.running = False   # pausar al entrar en modo paso a paso
            else:
                self.running = True    # reanudar al salir
        # Las acciones next_step, what_happens, experimentos y reset
        # son manejadas en Simulation._apply_action

    # ------------------------------------------------------------------
    # Renderizado
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface, fonts: dict) -> None:
        """Dibuja el panel completo de controles."""
        px = config.CTRL_PANEL_X
        py = config.CTRL_PANEL_Y
        pw = config.CTRL_PANEL_WIDTH
        ph = config.CTRL_PANEL_HEIGHT

        # Fondo del panel
        pygame.draw.rect(surface, config.COLOR_BG_CTRL,
                         pygame.Rect(px, py, pw, ph))
        pygame.draw.rect(surface, config.GRAY_MED,
                         pygame.Rect(px, py, pw, ph), width=1)

        # Título del panel
        title_s = fonts['title'].render("CONTROLES", True, config.COLOR_ACCENT)
        surface.blit(title_s, (px + 14, py + 14))

        # Línea divisoria
        pygame.draw.line(surface, config.GRAY_MED,
                         (px + 10, py + 38),
                         (px + pw - 10, py + 38))

        # Sliders
        for sl in self._sliders:
            sl.render(surface, fonts)

        # Sección experimentos
        exp_title_y = (self.btn_exp[0].rect.y - 22
                       if self.btn_exp else py + 400)
        exp_lbl = fonts['small'].render("EXPERIMENTOS", True, config.COLOR_TEXT_DIM)
        surface.blit(exp_lbl, (px + 14, exp_title_y))

        # Sección educacional
        edu_title_y = self.btn_step_mode.rect.y - 18
        edu_lbl = fonts['small'].render("EDUCACIONAL", True, config.COLOR_TEXT_DIM)
        surface.blit(edu_lbl, (px + 14, edu_title_y))

        # Botones (btn_next_step solo visible en step_mode)
        for btn in self._buttons:
            if btn is self.btn_next_step and not self.step_mode:
                continue
            btn.render(surface, fonts)

        # Indicador de modo activo
        mode_str = ("MODO: AUTOMÁTICO" if self.mode == 'auto'
                    else "MODO: MANUAL")
        mode_col = (config.BLUE_LIGHT if self.mode == 'auto'
                    else config.PURPLE)
        mode_s   = fonts['small'].render(mode_str, True, mode_col)
        surface.blit(mode_s, (px + 14, py + ph - 28))

        # Indicador de estado corriendo/pausado
        state_str = "● CORRIENDO" if self.running else "⏸ PAUSADO"
        state_col = config.GREEN if self.running else config.YELLOW
        state_s   = fonts['small'].render(state_str, True, state_col)
        surface.blit(state_s, (px + 14, py + ph - 46))
