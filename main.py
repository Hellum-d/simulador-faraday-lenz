# -*- coding: utf-8 -*-
"""
main.py — Punto de entrada del Simulador de la Ley de Faraday y Ley de Lenz.

Arquitectura general
--------------------
  Simulation
    ├── Magnet          (posición, velocidad, polaridad)
    ├── Coil            (N, A, R)
    ├── PhysicsEngine   (cálculo de Φ, ε, I, dirección)
    ├── SceneRenderer   (dibujo Pygame de la escena)
    ├── PlotManager     (gráficas Matplotlib incrustadas)
    └── UIManager       (sliders, botones)

El bucle principal se ejecuta a 60 FPS e implementa el patrón
actualizar → dibujar en cada frame.

Ejecución
---------
    python main.py

Dependencias
------------
    pip install pygame numpy matplotlib
"""

import sys
import pygame
import config
from physics  import Magnet, Coil, PhysicsEngine, ExplainerEngine
from graphics import SceneRenderer
from plots    import PlotManager
from ui       import UIManager


# ---------------------------------------------------------------------------
# Clase Simulation
# ---------------------------------------------------------------------------

class Simulation:
    """
    Clase principal que integra todos los subsistemas.

    Responsabilidades
    -----------------
    1. Inicializar Pygame y crear la ventana.
    2. Instanciar Magnet, Coil, PhysicsEngine, SceneRenderer,
       PlotManager y UIManager.
    3. Ejecutar el bucle principal a 60 FPS.
    4. Distribuir eventos a los subsistemas.
    5. Coordinar actualizaciones de física y renderizado.
    6. Gestionar el arrastre del imán con el mouse (modo manual).
    7. Aplicar los experimentos predefinidos.
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(config.WINDOW_TITLE)

        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock  = pygame.time.Clock()

        self._build_fonts()
        self._build_entities()

        self._running     = True
        self._dragging_magnet = False
        self._elapsed       = 0.0

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    def _build_fonts(self) -> None:
        """Carga las fuentes Pygame."""
        try:
            font_path = None   # usa la fuente del sistema
            self.fonts = {
                'title' : pygame.font.SysFont("segoeui", config.FONT_SIZE_TITLE,  bold=True),
                'normal': pygame.font.SysFont("segoeui", config.FONT_SIZE_NORMAL),
                'small' : pygame.font.SysFont("segoeui", config.FONT_SIZE_SMALL),
                'large' : pygame.font.SysFont("segoeui", config.FONT_SIZE_LARGE,  bold=True),
            }
        except Exception:
            # Fallback a fuente por defecto de Pygame
            self.fonts = {
                'title' : pygame.font.Font(None, config.FONT_SIZE_TITLE  + 4),
                'normal': pygame.font.Font(None, config.FONT_SIZE_NORMAL + 4),
                'small' : pygame.font.Font(None, config.FONT_SIZE_SMALL  + 4),
                'large' : pygame.font.Font(None, config.FONT_SIZE_LARGE  + 4),
            }

    # ------------------------------------------------------------------
    def _build_entities(self) -> None:
        """Crea e interconecta todos los subsistemas."""
        # Entidades físicas
        self.magnet = Magnet(
            x=config.MAGNET_START_X,
            B0=config.DEFAULT_B
        )
        self.coil = Coil(
            N=config.DEFAULT_N,
            A=config.DEFAULT_A,
            R=config.DEFAULT_R
        )

        # Motor de física
        self.physics = PhysicsEngine(
            magnet=self.magnet,
            coil=self.coil,
            coil_center_px=config.COIL_CENTER_X,
            px_per_meter=200.0
        )

        # Renderizado de la escena
        self.renderer = SceneRenderer(self.screen, self.fonts)

        # Gráficas
        plot_rect = pygame.Rect(
            config.PLOT_AREA_X,
            config.PLOT_AREA_Y,
            config.PLOT_AREA_WIDTH,
            config.PLOT_AREA_HEIGHT
        )
        self.plot_manager = PlotManager(plot_rect)

        # Interfaz de usuario
        self.ui = UIManager()

        # Motor de explicaciones educativas
        self.explainer  = ExplainerEngine()
        self._edu_lines = []   # list[tuple[str,tuple]] activo en el panel

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Ejecuta el bucle principal hasta que el usuario cierre la ventana."""
        while self._running:
            dt = self.clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.05)   # clamp para evitar saltos grandes si lag

            self._handle_events()
            self._update(dt)
            self._render()

        self._cleanup()

    # ------------------------------------------------------------------
    # Manejo de eventos
    # ------------------------------------------------------------------

    def _handle_events(self) -> None:
        """Procesa la cola de eventos de Pygame."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
                return

            if event.type == pygame.KEYDOWN:
                self._handle_key(event)

            # Eventos de mouse para arrastrar el imán (modo manual)
            if self.ui.mode == 'manual':
                self._handle_magnet_drag(event)

            # Interfaz
            action = self.ui.handle_event(event)
            if action:
                self._apply_action(action)

    # ------------------------------------------------------------------
    def _handle_key(self, event: pygame.event.Event) -> None:
        """Atajos de teclado."""
        if event.key == pygame.K_ESCAPE:
            self._running = False
        elif event.key == pygame.K_SPACE:
            self.ui.running = not self.ui.running
        elif event.key == pygame.K_r:
            self._reset()
        elif event.key == pygame.K_m:
            self.ui.mode = ('manual' if self.ui.mode == 'auto' else 'auto')
            self.magnet.mode = self.ui.mode

    # ------------------------------------------------------------------
    def _handle_magnet_drag(self, event: pygame.event.Event) -> None:
        """
        Detecta y gestiona el arrastre del imán con el mouse.

        El usuario hace clic sobre el imán y lo arrastra
        horizontalmente. La posición se pasa al Magnet y la física
        se recalcula instantáneamente.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            magnet_rect = pygame.Rect(
                self.magnet.pixel_x,
                config.COIL_CENTER_Y - config.MAGNET_HEIGHT // 2,
                config.MAGNET_WIDTH,
                config.MAGNET_HEIGHT
            )
            if magnet_rect.collidepoint(mx, my):
                self._dragging_magnet = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging_magnet = False

        elif event.type == pygame.MOUSEMOTION and self._dragging_magnet:
            dt = self.clock.get_time() / 1000.0 or 0.016
            self.magnet.set_position_from_mouse(
                event.pos[0],
                config.MAGNET_X_MIN,
                config.MAGNET_X_MAX,
                dt
            )

    # ------------------------------------------------------------------
    def _apply_action(self, action: str) -> None:
        """
        Procesa las acciones disparadas por botones de la UI.

        Acciones de control
        -------------------
        start  → reanuda la simulación.
        pause  → congela la simulación.
        reset  → restablece todo al estado inicial.

        Acciones de modo
        ----------------
        mode_auto   → el imán oscila automáticamente.
        mode_manual → el imán se arrastra con el mouse.

        Experimentos predefinidos
        -------------------------
        double_n       → duplica el número de espiras.
        double_b       → duplica la intensidad del campo.
        invert_magnet  → invierte la polaridad del imán.
        double_speed   → duplica la velocidad del imán.
        reset          → restablece todos los parámetros por defecto.
        """
        if action == "reset" or action == config.EXPERIMENT_RESET:
            self._reset()
            return

        if action == "mode_auto":
            self.magnet.mode = 'auto'
            return
        if action == "mode_manual":
            self.magnet.mode = 'manual'
            return

        if action == config.EXPERIMENT_DOUBLE_N:
            new_N = min(self.ui.sl_N.value * 2, config.N_MAX)
            self.ui.sl_N.value = new_N
            return

        if action == config.EXPERIMENT_DOUBLE_B:
            new_B = min(self.ui.sl_B.value * 2, config.B_MAX)
            self.ui.sl_B.value = new_B
            return

        if action == config.EXPERIMENT_INVERT_MAGNET:
            self.magnet.invert_polarity()
            return

        if action == config.EXPERIMENT_DOUBLE_SPEED:
            new_s = min(self.ui.sl_speed.value * 2, config.SPEED_MAX)
            self.ui.sl_speed.value = new_s
            return

        if action == "step_mode":
            # UIManager ya toggleó step_mode; aquí limpiamos si se desactivó
            if not self.ui.step_mode:
                self._edu_lines = []
            return

        if action == "next_step":
            self._step_advance()
            return

        if action == "what_happens":
            self._edu_lines = self.explainer.full_analysis(
                self.physics, self.magnet)
            return

    # ------------------------------------------------------------------
    def _step_advance(self) -> None:
        """
        Avanza la simulación exactamente STEP_DT segundos y genera
        la explicación paso a paso.

        Sincroniza primero los parámetros desde la UI, igual que
        ``_update``, para que los sliders afecten al paso.
        """
        self.magnet.B0         = self.ui.B
        self.magnet.auto_speed = self.ui.speed
        self.coil.update_params(N=self.ui.N, A=self.ui.A, R=self.ui.R)

        dt = ExplainerEngine.STEP_DT
        if self.magnet.mode == 'auto':
            self.magnet.update(dt, config.MAGNET_X_MIN, config.MAGNET_X_MAX)

        self.physics.update(dt)
        self.plot_manager.update(self.physics)
        self._elapsed += dt

        # Generar explicación con el estado resultante
        self._edu_lines = self.explainer.step_explanation(
            self.physics, self.magnet)

    # ------------------------------------------------------------------
    def _reset(self) -> None:
        """Restablece la simulación al estado inicial."""
        # Sliders
        self.ui.sl_B.value     = config.DEFAULT_B
        self.ui.sl_N.value     = config.DEFAULT_N
        self.ui.sl_A.value     = config.DEFAULT_A
        self.ui.sl_R.value     = config.DEFAULT_R
        self.ui.sl_speed.value = config.DEFAULT_SPEED
        # Imán
        self.magnet.x        = float(config.MAGNET_START_X)
        self.magnet.velocity = 0.0
        self.magnet.polarity = 1
        self.magnet.mode     = 'auto'
        self.ui.mode         = 'auto'
        self.ui.running      = True
        # Historial y panel educativo
        self.physics.reset_history()
        self._elapsed   = 0.0
        self._edu_lines = []

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------

    def _update(self, dt: float) -> None:
        """
        Actualiza todos los subsistemas para el frame actual.

        Orden de actualización
        ----------------------
        1. Sincronizar parámetros de la UI con Coil y Magnet.
        2. Mover el imán (si modo auto y simulación corriendo).
        3. Calcular física.
        4. Actualizar datos de las gráficas.
        """
        # 1. Sincronizar parámetros
        self.magnet.B0          = self.ui.B
        self.magnet.auto_speed  = self.ui.speed
        self.magnet.mode        = self.ui.mode
        self.coil.update_params(N=self.ui.N, A=self.ui.A, R=self.ui.R)

        if not self.ui.running:
            return

        self._elapsed += dt

        # 2. Mover imán (modo auto)
        if self.magnet.mode == 'auto':
            self.magnet.update(dt,
                               config.MAGNET_X_MIN,
                               config.MAGNET_X_MAX)

        # 3. Física
        self.physics.update(dt)

        # 4. Gráficas (solo si hay datos)
        self.plot_manager.update(self.physics)

    # ------------------------------------------------------------------
    # Renderizado
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Dibuja todos los elementos de la ventana."""
        self.screen.fill(config.COLOR_BG_SIM)

        # Escena física (imán, bobina, líneas de campo, flechas)
        self.renderer.render(self.magnet, self.physics, self.clock.get_time() / 1000.0)

        # Panel de información numérica + panel educativo
        self.renderer.render_info_panel(self.physics, self._elapsed,
                                        self._edu_lines or None)

        # Gráficas en tiempo real
        self.plot_manager.render(self.screen)

        # Panel de controles (UI)
        self.ui.render(self.screen, self.fonts)

        # Título de la ventana con FPS actuales
        fps = int(self.clock.get_fps())
        pygame.display.set_caption(
            f"{config.WINDOW_TITLE}  —  {fps} FPS")

        pygame.display.flip()

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def _cleanup(self) -> None:
        """Libera recursos antes de salir."""
        self.plot_manager.close()
        pygame.quit()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    """Crea la simulación y la ejecuta."""
    sim = Simulation()
    sim.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
