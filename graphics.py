# -*- coding: utf-8 -*-
"""
graphics.py — Renderizado gráfico de la escena física.

Responsable de dibujar sobre la superficie Pygame:
  • Fondo y paneles de la ventana.
  • Imán de barra con polos N y S.
  • Bobina con espiras.
  • Líneas de campo magnético.
  • Flechas de corriente inducida animadas.
  • Indicadores visuales de flujo (color de la bobina).

Toda la lógica de *dónde* y *cómo* dibujar está aquí; la física
vive en physics.py y la interfaz en ui.py.
"""

import math
import pygame
import numpy as np
import config


# ---------------------------------------------------------------------------
# Helpers de dibujo
# ---------------------------------------------------------------------------

def _draw_arrow(surface: pygame.Surface,
                color: tuple,
                start: tuple,
                end: tuple,
                width: int = 2,
                head_size: int = 10) -> None:
    """
    Dibuja una flecha desde ``start`` hasta ``end``.

    Parameters
    ----------
    surface   : superficie Pygame destino.
    color     : color RGB.
    start     : punto de origen (x, y).
    end       : punto de destino (x, y).
    width     : grosor del tallo.
    head_size : tamaño de la punta.
    """
    pygame.draw.line(surface, color, start, end, width)
    # Calcular ángulo de la punta
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    # Dos líneas formando la punta
    for sign in (+1, -1):
        tip_angle = angle + sign * math.radians(140)
        tip_end   = (end[0] + head_size * math.cos(tip_angle),
                     end[1] + head_size * math.sin(tip_angle))
        pygame.draw.line(surface, color, end, tip_end, width)


def _draw_rounded_rect(surface: pygame.Surface,
                       color: tuple,
                       rect: pygame.Rect,
                       radius: int = 8,
                       border: int = 0,
                       border_color: tuple = None) -> None:
    """Dibuja un rectángulo con esquinas redondeadas."""
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border > 0 and border_color:
        pygame.draw.rect(surface, border_color, rect,
                         width=border, border_radius=radius)


# ---------------------------------------------------------------------------
# Clase principal de renderizado
# ---------------------------------------------------------------------------

class SceneRenderer:
    """
    Renderiza la escena física completa sobre un área Pygame.

    Parameters
    ----------
    surface : superficie Pygame principal.
    fonts   : dict con fuentes Pygame {'title', 'normal', 'small', 'large'}.
    """

    def __init__(self, surface: pygame.Surface, fonts: dict):
        self.surface = surface
        self.fonts   = fonts

        self.coil_cx = config.COIL_CENTER_X
        self.coil_cy = config.COIL_CENTER_Y
        self._anim_t = 0.0

        self._bg_cache = None
        self._build_bg()
        self._build_static_caches(fonts)

    # ------------------------------------------------------------------
    # Fondo estático
    # ------------------------------------------------------------------

    def _build_bg(self) -> None:
        """Crea la capa de fondo estático de la escena."""
        w = config.SCENE_WIDTH
        h = config.SCENE_HEIGHT
        self._bg_cache = pygame.Surface((w, h))
        self._bg_cache.fill(config.COLOR_BG_SIM)
        grid_color = (28, 28, 36)
        for gx in range(0, w, 40):
            pygame.draw.line(self._bg_cache, grid_color, (gx, 0), (gx, h))
        for gy in range(0, h, 40):
            pygame.draw.line(self._bg_cache, grid_color, (0, gy), (w, gy))

    def _build_static_caches(self, fonts: dict) -> None:
        """Pre-computa superficies, rects y textos que no cambian cada frame."""
        cx = self.coil_cx
        cy = self.coil_cy
        cw = config.COIL_WIDTH
        ch = config.COIL_HEIGHT

        # --- Fondo de la bobina (SRCALPHA, allocado una sola vez) ---
        self._coil_bg = pygame.Surface((cw * 2, ch * 2), pygame.SRCALPHA)
        self._coil_bg.fill((50, 50, 60, 120))
        self._coil_bg_pos = (cx - cw, cy - ch)

        # --- Rects de las espiras (posición fija, solo cambia el color) ---
        n_turns = config.COIL_TURNS_DRAW
        spacing = (ch * 2) // (n_turns + 1)
        turn_w  = 10
        self._coil_turn_rects = [
            (pygame.Rect(cx - cw - turn_w, (cy - ch) + spacing * (i + 1) - 4, turn_w, 8),
             pygame.Rect(cx + cw,          (cy - ch) + spacing * (i + 1) - 4, turn_w, 8))
            for i in range(n_turns)
        ]
        self._coil_inner_rect = pygame.Rect(cx - cw, cy - ch, cw * 2, ch * 2)

        # --- Labels de la bobina pre-renderizados por estado ---
        self._coil_labels = {
            "increasing": fonts['small'].render("BOBINA", True, config.COLOR_FLUX_INC),
            "decreasing": fonts['small'].render("BOBINA", True, config.COLOR_FLUX_DEC),
            "constant":   fonts['small'].render("BOBINA", True, config.COLOR_COIL),
        }
        self._coil_label_y = cy + ch + 14

        # --- Labels del imán por polaridad ---
        self._magnet_surfs = {
            1:  (fonts['normal'].render("S", True, config.WHITE),
                 fonts['normal'].render("N", True, config.WHITE)),
            -1: (fonts['normal'].render("N", True, config.WHITE),
                 fonts['normal'].render("S", True, config.WHITE)),
        }

        # --- Labels de dirección de corriente ---
        self._arrow_dir_surfs = {
            "ccw": fonts['small'].render("↺ CCW", True, config.COLOR_ARROW_CCW),
            "cw":  fonts['small'].render("↻ CW",  True, config.COLOR_ARROW_CW),
        }

        # --- Ángulos base de las flechas (constante) ---
        self._arrow_base_offsets = [k * (math.pi / 2) for k in range(4)]

        # --- Superficie reutilizable para líneas de campo (SRCALPHA) ---
        self._field_surface  = pygame.Surface(
            (config.SCENE_WIDTH, config.SCENE_HEIGHT), pygame.SRCALPHA)
        self._last_field_key = None   # (magnet_px_bucket, flux_status, alpha_bucket)

        # --- t values para Bézier (reducidos a 20 segmentos) ---
        n_pts = 20
        self._bezier_t = [k / n_pts for k in range(n_pts + 1)]

        # --- Rect del borde de escena ---
        self._scene_border_rect = pygame.Rect(
            config.SCENE_X, config.SCENE_Y,
            config.SCENE_WIDTH, config.SCENE_HEIGHT)

    # ------------------------------------------------------------------
    # Renderizado principal
    # ------------------------------------------------------------------

    def render(self, magnet, physics, dt: float) -> None:
        """
        Punto de entrada principal; dibuja toda la escena para un frame.

        Parameters
        ----------
        magnet  : instancia Magnet con posición actual.
        physics : instancia PhysicsEngine con estado físico actual.
        dt      : delta de tiempo [s] para animar.
        """
        self._anim_t += dt

        # --- Fondo ---
        self.surface.blit(self._bg_cache,
                          (config.SCENE_X, config.SCENE_Y))

        # --- Líneas de campo magnético ---
        self._draw_field_lines(magnet, physics)

        # --- Imán ---
        self._draw_magnet(magnet)

        # --- Bobina ---
        self._draw_coil(physics)

        # --- Flechas de corriente (Ley de Lenz) ---
        if abs(physics.current) > 1e-9:
            self._draw_current_arrows(physics)

        pygame.draw.rect(self.surface, config.GRAY_MED,
                         self._scene_border_rect, width=1, border_radius=4)

    # ------------------------------------------------------------------
    # Líneas de campo magnético
    # ------------------------------------------------------------------

    def _draw_field_lines(self, magnet, physics) -> None:
        """Dibuja líneas de campo; reconstruye la superficie solo cuando cambia el estado."""
        mx     = magnet.pixel_x
        B_norm = min(abs(physics._compute_B_eff()) / (magnet.B0 * 2.0), 1.0)
        alpha  = int(60 + 180 * B_norm)

        # Agrupar la posición en buckets de 3px para reducir reconstrucciones
        field_key = (mx // 3, physics.flux_status, alpha // 8)
        if field_key != self._last_field_key:
            self._rebuild_field_surface(mx, physics.flux_status, alpha)
            self._last_field_key = field_key

        self.surface.blit(self._field_surface, (config.SCENE_X, config.SCENE_Y))

    def _rebuild_field_surface(self, mx: int, flux_status: str, alpha: int) -> None:
        """Redibuja la superficie de líneas de campo sobre la superficie reutilizable."""
        self._field_surface.fill((0, 0, 0, 0))   # limpiar sin reasignar

        if flux_status == "increasing":
            base_rgb = config.COLOR_FLUX_INC[:3]
        elif flux_status == "decreasing":
            base_rgb = config.COLOR_FLUX_DEC[:3]
        else:
            base_rgb = config.COLOR_FIELD_LINE[:3]
        line_color = (*base_rgb, alpha)

        n_lines = config.FIELD_LINE_COUNT
        half_h  = config.COIL_HEIGHT
        my      = config.COIL_CENTER_Y

        for i in range(n_lines):
            t      = (i / (n_lines - 1)) if n_lines > 1 else 0.5
            y_off  = -half_h + 2 * half_h * t
            p0     = (mx + config.MAGNET_WIDTH // 2, my + int(y_off * 0.6))
            p1     = (self.coil_cx - config.COIL_WIDTH, self.coil_cy + int(y_off))
            pts    = self._bezier_field_line(p0, p1, curvature=0.3)
            if len(pts) >= 2:
                pygame.draw.lines(self._field_surface, line_color, False, pts, 1)
            if len(pts) >= 4:
                mid = len(pts) // 2
                _draw_arrow(self._field_surface, line_color,
                            pts[mid - 1], pts[mid], width=1, head_size=6)

    # ------------------------------------------------------------------
    def _bezier_field_line(self, p0: tuple, p1: tuple,
                           curvature: float = 0.3) -> list:
        """Curva de Bézier cuadrática usando el array de t pre-calculado."""
        ctrl_x = (p0[0] + p1[0]) / 2.0
        ctrl_y = (p0[1] + p1[1]) / 2.0 - abs(p1[0] - p0[0]) * curvature
        ox, oy = config.SCENE_X, config.SCENE_Y
        pts = []
        for t in self._bezier_t:
            mt = 1.0 - t
            x  = mt * mt * p0[0] + 2 * mt * t * ctrl_x + t * t * p1[0]
            y  = mt * mt * p0[1] + 2 * mt * t * ctrl_y + t * t * p1[1]
            pts.append((int(x - ox), int(y - oy)))
        return pts

    # ------------------------------------------------------------------
    # Imán
    # ------------------------------------------------------------------

    def _draw_magnet(self, magnet) -> None:
        """
        Dibuja el imán de barra con etiquetas N y S.

        El imán se divide en dos mitades: polo N (rojo) y polo S (azul).
        La orientación depende de la polaridad: si polarity = +1 el polo N
        está a la derecha (apuntando hacia la bobina); si = -1, a la izquierda.
        """
        mx  = magnet.pixel_x
        my  = config.COIL_CENTER_Y
        mw  = config.MAGNET_WIDTH
        mh  = config.MAGNET_HEIGHT

        rect_full = pygame.Rect(mx, my - mh // 2, mw, mh)

        # Mitad izquierda y derecha
        rect_left  = pygame.Rect(mx,          my - mh // 2, mw // 2, mh)
        rect_right = pygame.Rect(mx + mw // 2, my - mh // 2, mw // 2, mh)

        if magnet.polarity == 1:
            color_left, color_right = config.COLOR_MAGNET_S, config.COLOR_MAGNET_N
        else:
            color_left, color_right = config.COLOR_MAGNET_N, config.COLOR_MAGNET_S

        _draw_rounded_rect(self.surface, color_left,  rect_left,
                           radius=6, border=2, border_color=config.WHITE)
        _draw_rounded_rect(self.surface, color_right, rect_right,
                           radius=6, border=2, border_color=config.WHITE)

        # Usar superficies de texto pre-renderizadas
        surf_left, surf_right = self._magnet_surfs[magnet.polarity]
        self.surface.blit(surf_left,  surf_left.get_rect(center=rect_left.center))
        self.surface.blit(surf_right, surf_right.get_rect(center=rect_right.center))

        # Borde exterior del imán
        pygame.draw.rect(self.surface, config.GRAY_LIGHT, rect_full,
                         width=2, border_radius=6)

        # Indicador de velocidad (pequeñas flechas de movimiento)
        if abs(magnet.velocity) > 5:
            self._draw_velocity_indicator(magnet)

    # ------------------------------------------------------------------
    def _draw_velocity_indicator(self, magnet) -> None:
        """Dibuja pequeñas flechas sobre el imán indicando su dirección."""
        direction = 1 if magnet.velocity > 0 else -1
        cx = magnet.pixel_x + config.MAGNET_WIDTH // 2
        cy = config.COIL_CENTER_Y - config.MAGNET_HEIGHT // 2 - 18
        for i in range(3):
            ax = cx - 20 + i * 20
            _draw_arrow(self.surface, config.CYAN,
                        (ax, cy), (ax + direction * 14, cy),
                        width=2, head_size=6)

    # ------------------------------------------------------------------
    # Bobina
    # ------------------------------------------------------------------

    def _draw_coil(self, physics) -> None:
        """
        Dibuja la bobina con espiras.

        El color de la bobina cambia según el estado del flujo:
          • verde  → flujo creciente
          • rojo   → flujo decreciente
          • amarillo → flujo constante

        Las espiras se dibujan como rectángulos solapados para
        simular el enrollado.
        """
        cx = self.coil_cx
        cy = self.coil_cy
        cw = config.COIL_WIDTH
        ch = config.COIL_HEIGHT

        # Color según estado del flujo
        if physics.flux_status == "increasing":
            coil_color = config.COLOR_FLUX_INC
        elif physics.flux_status == "decreasing":
            coil_color = config.COLOR_FLUX_DEC
        else:
            coil_color = config.COLOR_COIL

        # Fondo cacheado (sin allocar Surface cada frame)
        self.surface.blit(self._coil_bg, self._coil_bg_pos)

        # Espiras usando rects pre-calculados
        for left_r, right_r in self._coil_turn_rects:
            pygame.draw.rect(self.surface, coil_color, left_r,  border_radius=2)
            pygame.draw.rect(self.surface, coil_color, right_r, border_radius=2)

        pygame.draw.rect(self.surface, coil_color,
                         self._coil_inner_rect, width=3, border_radius=4)

        # Label pre-renderizado por estado
        label = self._coil_labels[physics.flux_status]
        self.surface.blit(label, (cx - label.get_width() // 2, self._coil_label_y))

    # ------------------------------------------------------------------
    # Flechas de corriente (Ley de Lenz)
    # ------------------------------------------------------------------

    def _draw_current_arrows(self, physics) -> None:
        """
        Dibuja flechas circulares alrededor de la bobina representando
        la corriente inducida.

        Las flechas se animan con el tiempo para dar sensación de flujo.
        La dirección depende del signo de la corriente:
          • ccw (antihoraria) → corriente se opone al aumento del flujo
          • cw  (horaria)     → corriente se opone a la disminución

        La intensidad visual escala con |I| para reforzar la magnitud.
        """
        cx = self.coil_cx
        cy = self.coil_cy
        r  = config.CURRENT_ARROW_RADIUS

        # Intensidad visual (normalizada 0..1)
        I_norm = min(abs(physics.current) / 0.5, 1.0)
        if I_norm < 0.02:
            return

        # Color según dirección
        if physics.current_dir == "ccw":
            arrow_color = config.COLOR_ARROW_CCW
        else:
            arrow_color = config.COLOR_ARROW_CW

        # Animar posición angular
        speed_factor = config.ARROW_ANIM_SPEED * I_norm
        if physics.current_dir == "cw":
            phase = (self._anim_t * speed_factor) % (2 * math.pi)
        else:
            phase = -(self._anim_t * speed_factor) % (2 * math.pi)

        # 4 flechas usando offsets pre-calculados
        width     = max(1, int(2 + 3 * I_norm))
        head_size = max(6, int(8 + 6 * I_norm))
        for base_offset in self._arrow_base_offsets:
            a1 = phase + base_offset
            a2 = a1 + 0.35
            p1 = (cx + r * math.cos(a1), cy + r * math.sin(a1))
            p2 = (cx + r * math.cos(a2), cy + r * math.sin(a2))
            _draw_arrow(self.surface, arrow_color,
                        (int(p1[0]), int(p1[1])),
                        (int(p2[0]), int(p2[1])),
                        width=width, head_size=head_size)

        # Texto pre-renderizado
        if physics.current_dir in self._arrow_dir_surfs:
            txt_s = self._arrow_dir_surfs[physics.current_dir]
            self.surface.blit(txt_s, (cx - txt_s.get_width() // 2, cy - r - 20))

    # ------------------------------------------------------------------
    # Panel de resultados numéricos
    # ------------------------------------------------------------------

    def render_info_panel(self, physics, elapsed: float,
                          edu_lines: list = None) -> None:
        """
        Renderiza el panel derecho con los valores físicos actuales.

        Parameters
        ----------
        physics   : PhysicsEngine con el estado actual.
        elapsed   : tiempo total transcurrido [s].
        edu_lines : lista de (texto, color) del ExplainerEngine,
                    o None para mostrar el mensaje educativo genérico.
        """
        px = config.INFO_PANEL_X
        py = config.INFO_PANEL_Y
        pw = config.INFO_PANEL_WIDTH
        ph = config.INFO_PANEL_HEIGHT

        # Fondo
        panel_rect = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(self.surface, config.COLOR_BG_INFO, panel_rect)
        pygame.draw.rect(self.surface, config.GRAY_MED, panel_rect, width=1)

        y = py + 14
        margin = px + 12
        line_h = 26

        # Título
        title = self.fonts['title'].render("RESULTADOS", True, config.COLOR_ACCENT)
        self.surface.blit(title, (margin, y))
        y += line_h + 4

        pygame.draw.line(self.surface, config.GRAY_MED,
                         (margin, y), (px + pw - 12, y))
        y += 10

        # Datos numéricos
        def row(label: str, value: str, color: tuple = config.COLOR_TEXT):
            lbl_s = self.fonts['small'].render(label, True, config.COLOR_TEXT_DIM)
            val_s = self.fonts['normal'].render(value, True, color)
            self.surface.blit(lbl_s, (margin, y))
            self.surface.blit(val_s, (margin, y + 14))

        # Flujo
        flux_color = (config.COLOR_FLUX_INC if physics.flux_status == "increasing"
                      else config.COLOR_FLUX_DEC if physics.flux_status == "decreasing"
                      else config.COLOR_FLUX_CONST)
        row("Flujo magnético (Φ)",
            f"{physics.flux:.4f}  Wb", flux_color)
        y += line_h + 10

        # dΦ/dt
        row("Variación del flujo (dΦ/dt)",
            f"{physics.d_flux_dt:.4f}  Wb/s",
            config.ORANGE if abs(physics.d_flux_dt) > 0.0001 else config.COLOR_TEXT)
        y += line_h + 10

        # FEM
        emf_color = (config.GREEN if physics.emf > 0
                     else config.RED if physics.emf < 0
                     else config.COLOR_TEXT)
        row("FEM inducida (ε)",
            f"{physics.emf:.4f}  V", emf_color)
        y += line_h + 10

        # Corriente
        I_color = (config.COLOR_ARROW_CCW if physics.current > 0
                   else config.COLOR_ARROW_CW if physics.current < 0
                   else config.COLOR_TEXT)
        row("Corriente inducida (I)",
            f"{physics.current:.6f}  A", I_color)
        y += line_h + 10

        # Dirección
        dir_map = {"ccw": "↺ Antihoraria (CCW)",
                   "cw":  "↻ Horaria (CW)",
                   "none": "— Sin corriente"}
        dir_txt = dir_map.get(physics.current_dir, "?")
        dir_col = (config.COLOR_ARROW_CCW if physics.current_dir == "ccw"
                   else config.COLOR_ARROW_CW if physics.current_dir == "cw"
                   else config.COLOR_TEXT_DIM)
        row("Dirección de corriente", dir_txt, dir_col)
        y += line_h + 10

        # Estado del flujo
        status_map = {"increasing": ("▲ Creciendo", config.COLOR_FLUX_INC),
                      "decreasing": ("▼ Decreciendo", config.COLOR_FLUX_DEC),
                      "constant":   ("■ Constante", config.COLOR_FLUX_CONST)}
        st_txt, st_col = status_map.get(physics.flux_status,
                                        ("?", config.COLOR_TEXT))
        row("Estado del flujo", st_txt, st_col)
        y += line_h + 10

        # Tiempo transcurrido
        row("Tiempo", f"{elapsed:.1f}  s", config.COLOR_TEXT_DIM)
        y += line_h + 20

        # Separador
        pygame.draw.line(self.surface, config.GRAY_MED,
                         (margin, y), (px + pw - 12, y))
        y += 12

        # Panel educativo: explicación detallada o mensaje genérico
        if edu_lines:
            self._render_edu_lines(edu_lines, margin, y, pw - 24)
        else:
            msg = physics.get_educational_message()
            self._render_wrapped_text(msg, margin, y, pw - 24,
                                      config.CYAN, self.fonts['small'])

    # ------------------------------------------------------------------
    def _render_edu_lines(self, lines: list, x: int, y: int,
                           max_width: int) -> int:
        """
        Renderiza la lista de (texto, color) del ExplainerEngine.

        Líneas con texto vacío ("") producen un pequeño espacio vertical.
        El renderizado se detiene si se alcanza el borde inferior del panel.

        Parameters
        ----------
        lines     : lista de tuplas (texto, color_rgb).
        x, y      : posición inicial.
        max_width : ancho máximo en píxeles para el word-wrap.

        Returns
        -------
        int : coordenada y final.
        """
        font   = self.fonts['small']
        line_h = font.get_linesize() + 2
        y_max  = config.INFO_PANEL_Y + config.INFO_PANEL_HEIGHT - 8
        BLACK  = (0, 0, 0)

        for text, color in lines:
            if y >= y_max:
                break
            if color == BLACK or not text:
                # línea vacía → espacio pequeño
                y += line_h // 2
                continue
            y = self._render_wrapped_text(text, x, y, max_width, color, font)

        return y

    # ------------------------------------------------------------------
    def _render_wrapped_text(self, text: str, x: int, y: int,
                              max_width: int, color: tuple,
                              font: pygame.font.Font) -> int:
        """
        Renderiza texto con ajuste automático de línea.

        Returns
        -------
        int : coordenada y final tras renderizar el texto.
        """
        words  = text.split()
        line   = ""
        line_h = font.get_linesize() + 2

        for word in words:
            test = (line + " " + word).strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    surf = font.render(line, True, color)
                    self.surface.blit(surf, (x, y))
                    y += line_h
                line = word

        if line:
            surf = font.render(line, True, color)
            self.surface.blit(surf, (x, y))
            y += line_h

        return y
