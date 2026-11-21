# -*- coding: utf-8 -*-
"""
plots.py — Gráficas en tiempo real incrustadas en Pygame.

Usa Matplotlib con backend Agg (sin ventana propia) para renderizar
las tres gráficas a un buffer RGBA, que luego se convierte en una
superficie Pygame y se dibuja sobre la ventana principal.

Gráficas implementadas
-----------------------
1. Flujo magnético Φ(t)       — línea verde
2. FEM inducida ε(t)          — línea naranja/rojo
3. Corriente inducida I(t)    — línea azul

El historial se limita a los últimos ``PLOT_HISTORY_SECONDS`` segundos.

Rendimiento
-----------
Re-renderizar una figura Matplotlib es costoso (~40 ms). Para no bloquear
el bucle principal de 60 FPS, todo el render de Matplotlib se ejecuta en un
**hilo de trabajo dedicado**:

  • El hilo principal sólo entrega una instantánea de datos (barato) y, al
    dibujar, blitea la última superficie lista. Nunca espera a Matplotlib.
  • El hilo de trabajo regenera la superficie ~7 veces por segundo usando
    artistas persistentes (``set_data``) y ``buffer_rgba`` (sin codificar PNG),
    lo que evita los dos costes dominantes del enfoque anterior:
    la recreación de los ejes (``cla``) y la compresión/descompresión PNG.

Así la simulación corre a 60 FPS estables mientras las gráficas se actualizan
de forma asíncrona, manteniendo exactamente el mismo aspecto visual.
"""

import time
import threading
import numpy as np
import matplotlib
matplotlib.use("Agg")   # backend sin ventana GUI
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pygame
import config


class PlotManager:
    """
    Gestiona las tres gráficas en tiempo real.

    Parameters
    ----------
    area_rect : pygame.Rect — área de la ventana donde se dibujan las gráficas.
    """

    # Cadencia objetivo del hilo de gráficas (segundos) → ~7 Hz
    _PLOT_INTERVAL = 1.0 / 7.0

    def __init__(self, area_rect: pygame.Rect):
        self.rect = area_rect

        # Crear figura Matplotlib con 3 subplots verticales
        dpi = 90
        fig_w = area_rect.width  / dpi
        fig_h = area_rect.height / dpi
        self.fig, self.axes = plt.subplots(3, 1,
                                           figsize=(fig_w, fig_h),
                                           dpi=dpi)
        self._canvas = self.fig.canvas
        self._style_figure()
        self._make_artists()

        # --- Estado compartido entre hilo principal y trabajador ---
        self._latest_surface = None     # superficie lista (swap atómico)
        self._pending        = None     # instantánea de datos por procesar
        self._last_snapshot  = 0.0       # throttle del hilo principal
        self._lock           = threading.Lock()
        self._wake           = threading.Event()
        self._stop           = threading.Event()

        # Hilo de trabajo: único que toca fig/canvas/axes tras este punto
        self._worker = threading.Thread(target=self._worker_loop,
                                        name="PlotWorker", daemon=True)
        self._worker.start()

    # ------------------------------------------------------------------
    # Estilo (elementos estáticos: se fijan una sola vez)
    # ------------------------------------------------------------------

    def _style_figure(self) -> None:
        """Aplica el estilo oscuro a la figura y los ejes (una sola vez)."""
        self.fig.patch.set_facecolor(config.PLOT_BACKGROUND)

        labels = [
            "Flujo magnético  Φ (Wb)",
            "FEM inducida  ε (V)",
            "Corriente inducida  I (A)",
        ]

        for ax, ylabel in zip(self.axes, labels):
            ax.set_facecolor(config.PLOT_BACKGROUND)
            ax.tick_params(colors="#aaaaaa", labelsize=7)
            ax.set_ylabel(ylabel, color="#aaaaaa", fontsize=7)
            ax.yaxis.set_label_coords(-0.06, 0.5)
            for spine in ax.spines.values():
                spine.set_color("#333344")
            ax.grid(True, color="#222230", linewidth=0.5)
            ax.xaxis.set_major_formatter(
                ticker.FuncFormatter(lambda v, _: f"{v:.0f}s"))
            ax.tick_params(axis='x', labelsize=6)

        self.axes[-1].set_xlabel("Tiempo (s)", color="#aaaaaa", fontsize=7)
        self.fig.tight_layout(pad=0.6, h_pad=0.4)

    def _make_artists(self) -> None:
        """Crea las líneas persistentes (una por subplot)."""
        colors = [config.PLOT_LINE_FLUX,
                  config.PLOT_LINE_EMF,
                  config.PLOT_LINE_CURRENT]
        self._lines = [
            ax.plot([], [], color=c, linewidth=1.2, antialiased=True)[0]
            for ax, c in zip(self.axes, colors)
        ]

    # ------------------------------------------------------------------
    # Actualización (hilo principal — barato, no bloquea)
    # ------------------------------------------------------------------

    def update(self, physics) -> None:
        """
        Entrega una instantánea del historial al hilo de gráficas.

        Se ejecuta cada frame pero está limitada a la cadencia de gráficas,
        por lo que el coste medio por frame es despreciable.

        Parameters
        ----------
        physics : PhysicsEngine con historial de datos.
        """
        now = time.perf_counter()
        if now - self._last_snapshot < self._PLOT_INTERVAL:
            return
        self._last_snapshot = now

        t, flux, emf, current = physics.history_arrays
        if len(t) < 2:
            return

        with self._lock:
            self._pending = (t, flux, emf, current)
        self._wake.set()

    # ------------------------------------------------------------------
    # Hilo de trabajo (todo el coste de Matplotlib vive aquí)
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Regenera la superficie de gráficas de forma asíncrona."""
        while not self._stop.is_set():
            # Esperar a que haya datos nuevos (con timeout para poder parar)
            if not self._wake.wait(timeout=0.2):
                continue
            self._wake.clear()

            with self._lock:
                data = self._pending
                self._pending = None
            if data is None:
                continue

            try:
                self._latest_surface = self._render_figure(data)  # swap atómico
            except Exception:
                # Nunca dejar caer el hilo por un fallo puntual de render
                pass

    def _render_figure(self, data) -> pygame.Surface:
        """Dibuja la figura con los datos dados y devuelve una Surface Pygame."""
        t, flux, emf, current = data

        # Ventana temporal: últimos PLOT_HISTORY_SECONDS segundos
        t_end   = t[-1]
        t_start = max(t[0], t_end - config.PLOT_HISTORY_SECONDS)
        mask    = t >= t_start
        t_w     = t[mask]
        series  = (flux[mask], emf[mask], current[mask])

        for ax, line, y in zip(self.axes, self._lines, series):
            line.set_data(t_w, y)
            ax.set_xlim(t_start, t_end + 0.1)
            if y.size:
                y_min = y.min()
                y_max = y.max()
                span  = y_max - y_min
                if span > 1e-12:
                    margin = span * 0.15
                    ax.set_ylim(y_min - margin, y_max + margin)
                else:
                    # Serie plana: rango simétrico pequeño para evitar warning
                    pad = abs(y_max) * 0.15 + 1e-6
                    ax.set_ylim(y_min - pad, y_max + pad)

        # Rasterizar a buffer RGBA (sin PNG) y copiar a una Surface propia
        self._canvas.draw()
        w, h = self._canvas.get_width_height()
        buf  = self._canvas.buffer_rgba()
        # .copy() desliga la Surface del buffer del canvas (que se reusa)
        return pygame.image.frombuffer(buf, (w, h), "RGBA").copy()

    # ------------------------------------------------------------------
    # Renderizado (hilo principal — sólo un blit)
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        """
        Dibuja la última superficie de gráficas lista sobre la ventana.

        Parameters
        ----------
        surface : superficie Pygame principal.
        """
        surf = self._latest_surface   # lectura atómica de la referencia
        if surf is None:
            # Fondo de espera mientras el primer render está en curso
            pygame.draw.rect(surface, (12, 12, 18), self.rect)
            return

        # Escalar sólo si difiere en tamaño (normalmente coincide exacto)
        if surf.get_size() != (self.rect.width, self.rect.height):
            surf = pygame.transform.smoothscale(
                surf, (self.rect.width, self.rect.height))
        surface.blit(surf, (self.rect.x, self.rect.y))

    # ------------------------------------------------------------------

    def close(self) -> None:
        """Detiene el hilo de trabajo y libera los recursos de Matplotlib."""
        self._stop.set()
        self._wake.set()
        if self._worker.is_alive():
            self._worker.join(timeout=1.0)
        plt.close(self.fig)
