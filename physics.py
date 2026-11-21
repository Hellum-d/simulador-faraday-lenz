# -*- coding: utf-8 -*-
"""
physics.py — Motor de física del simulador Faraday/Lenz.

Contiene:
  • Magnet   — representa el imán de barra (posición, velocidad, polaridad).
  • Coil     — representa la bobina (N, A, R).
  • PhysicsEngine — calcula Φ, dΦ/dt, ε, I y la dirección de la corriente.

Ecuaciones implementadas
------------------------
Flujo magnético:
    Φ = B_eff · A · cos(θ)
donde B_eff es el campo efectivo en la posición del imán y
θ es el ángulo entre B y la normal a la bobina (aquí θ = 0 → cos = 1).

Campo efectivo (modelo dipolo magnético):
    B_eff = B₀ · (d_ref / d)^decay_exp
donde d es la distancia imán-bobina y d_ref la distancia de referencia.

Ley de Faraday:
    ε = −N · dΦ/dt

Ley de Ohm:
    I = ε / R

Ley de Lenz:
    El signo de I indica el sentido: el campo inducido por I se opone
    a la variación dΦ/dt. Cuando dΦ/dt > 0 (flujo crece) la corriente
    induce un campo contrario al que produce el aumento.
"""

import math
import numpy as np
from collections import deque
import config


# ---------------------------------------------------------------------------
# Magnet
# ---------------------------------------------------------------------------

class Magnet:
    """
    Representa el imán de barra.

    Parámetros
    ----------
    x : float
        Posición horizontal en unidades de píxeles (se normaliza internamente).
    B0 : float
        Intensidad nominal del campo magnético [T].
    polarity : int
        +1  → polo N apunta hacia la bobina.
        -1  → polo S apunta hacia la bobina (imán invertido).

    Atributos calculados
    --------------------
    velocity : float
        Velocidad horizontal actual [px/s] (positiva = acercándose a la bobina).
    """

    def __init__(self, x: float, B0: float = config.DEFAULT_B,
                 polarity: int = 1):
        self.x        = float(x)       # posición en px
        self.B0       = B0             # campo nominal [T]
        self.polarity = polarity       # +1 o -1
        self.velocity = 0.0            # px/s

        # Modo de movimiento: 'manual' (mouse) o 'auto' (oscilación)
        self.mode         = 'auto'
        self.auto_speed   = config.DEFAULT_SPEED   # velocidad normalizada
        self._auto_dir    = 1          # dirección de la oscilación automática

    # ------------------------------------------------------------------
    def update(self, dt: float, x_min: float, x_max: float) -> None:
        """
        Actualiza la posición del imán en modo automático.

        En modo manual la posición es controlada externamente mediante
        ``set_position_from_mouse``.

        Parameters
        ----------
        dt    : delta de tiempo [s] desde el último frame.
        x_min : límite izquierdo de movimiento [px].
        x_max : límite derecho de movimiento [px].
        """
        if self.mode != 'auto':
            return

        # Velocidad en píxeles por segundo escalada por el parámetro de velocidad
        speed_px = self.auto_speed * 120.0   # 120 px/s base

        prev_x = self.x
        self.x += self._auto_dir * speed_px * dt

        # Rebotar en los límites
        if self.x >= x_max:
            self.x        = x_max
            self._auto_dir = -1
        elif self.x <= x_min:
            self.x        = x_min
            self._auto_dir = 1

        # Velocidad real (con signo) en px/s
        self.velocity = (self.x - prev_x) / dt if dt > 0 else 0.0

    # ------------------------------------------------------------------
    def set_position_from_mouse(self, mouse_x: float,
                                x_min: float, x_max: float,
                                dt: float) -> None:
        """
        Actualiza posición y velocidad cuando el usuario arrastra el imán.

        Parameters
        ----------
        mouse_x : posición horizontal del puntero [px].
        x_min   : límite izquierdo [px].
        x_max   : límite derecho [px].
        dt      : delta de tiempo [s].
        """
        prev_x   = self.x
        self.x   = float(np.clip(mouse_x, x_min, x_max))
        self.velocity = (self.x - prev_x) / dt if dt > 0 else 0.0

    # ------------------------------------------------------------------
    def invert_polarity(self) -> None:
        """Invierte la polaridad del imán (simula dar vuelta el imán)."""
        self.polarity *= -1

    # ------------------------------------------------------------------
    @property
    def pixel_x(self) -> int:
        """Coordenada entera para dibujo."""
        return int(self.x)


# ---------------------------------------------------------------------------
# Coil
# ---------------------------------------------------------------------------

class Coil:
    """
    Representa la bobina receptora.

    Parámetros
    ----------
    N : int   — número de espiras.
    A : float — área de cada espira [m²].
    R : float — resistencia total [Ω].
    """

    def __init__(self, N: int = config.DEFAULT_N,
                 A: float = config.DEFAULT_A,
                 R: float = config.DEFAULT_R):
        self.N = int(N)
        self.A = float(A)
        self.R = float(R)

    # ------------------------------------------------------------------
    def update_params(self, N: int = None, A: float = None,
                      R: float = None) -> None:
        """Actualiza parámetros de la bobina desde los sliders."""
        if N is not None: self.N = int(N)
        if A is not None: self.A = float(A)
        if R is not None: self.R = float(R)


# ---------------------------------------------------------------------------
# PhysicsEngine
# ---------------------------------------------------------------------------

class PhysicsEngine:
    """
    Calcula en cada frame el estado electromagnético completo.

    Responsabilidades
    -----------------
    1. Calcular el campo efectivo B_eff en función de la distancia imán–bobina.
    2. Calcular el flujo magnético Φ = B_eff · A · cos(0) = B_eff · A
       (la normal a la bobina es paralela al eje de movimiento del imán,
       por lo que cos(θ) = 1 en el eje de simetría).
    3. Calcular dΦ/dt mediante diferencia finita de primer orden.
    4. Calcular la FEM inducida ε = −N · dΦ/dt.
    5. Calcular la corriente I = ε / R.
    6. Determinar la dirección de la corriente (horaria / antihoraria)
       según la Ley de Lenz.
    7. Mantener historial de las últimas ``history_len`` muestras para
       las gráficas en tiempo real.

    Parámetros del modelo de campo
    --------------------------------
    El imán se modela como un dipolo magnético. A lo largo del eje del dipolo:

        B_eff = B₀ · (d_ref / d)^FIELD_DECAY

    Con FIELD_DECAY = 3 reproduce el comportamiento dipolar real.
    Se aplica el signo de la polaridad del imán.
    """

    # Distancia mínima para evitar singularidad [px]
    _D_MIN_PX = 5.0

    def __init__(self, magnet: Magnet, coil: Coil,
                 coil_center_px: float,
                 px_per_meter: float = 200.0):
        """
        Parameters
        ----------
        magnet        : instancia Magnet.
        coil          : instancia Coil.
        coil_center_px: posición horizontal de la bobina en px.
        px_per_meter  : escala de conversión píxeles → metros.
        """
        self.magnet        = magnet
        self.coil          = coil
        self.coil_center_px = float(coil_center_px)
        self.px_per_meter  = px_per_meter

        # Estado físico actual
        self.flux          = 0.0   # Φ [Wb]
        self.d_flux_dt     = 0.0   # dΦ/dt [Wb/s]
        self.emf           = 0.0   # ε [V]
        self.current       = 0.0   # I [A]
        self.flux_status   = "constant"   # "increasing" / "decreasing" / "constant"
        self.current_dir   = "none"       # "cw" / "ccw" / "none"

        # Para diferencia finita
        self._prev_flux    = 0.0
        self._prev_time    = 0.0

        # Historial para gráficas (deque de longitud fija)
        max_history = config.PLOT_HISTORY_SECONDS * FPS_APPROX
        self.time_history    = deque(maxlen=int(max_history))
        self.flux_history    = deque(maxlen=int(max_history))
        self.emf_history     = deque(maxlen=int(max_history))
        self.current_history = deque(maxlen=int(max_history))

        self._elapsed = 0.0   # tiempo acumulado [s]

    # ------------------------------------------------------------------
    def _distance_meters(self) -> float:
        """
        Calcula la distancia horizontal imán–bobina en metros.

        El frente del imán (polo que apunta a la bobina) está en
        ``magnet.x + MAGNET_WIDTH/2`` (si se mueve de izquierda a derecha).
        La bobina está en ``coil_center_px``.
        """
        magnet_front = self.magnet.x + config.MAGNET_WIDTH / 2.0
        dist_px      = max(abs(self.coil_center_px - magnet_front),
                           self._D_MIN_PX)
        return dist_px / self.px_per_meter

    # ------------------------------------------------------------------
    def _compute_B_eff(self) -> float:
        """
        Campo efectivo en la posición de la bobina.

            B_eff = polarity · B₀ · (d_ref / d)^decay

        Returns
        -------
        float : campo efectivo con signo [T].
        """
        d      = self._distance_meters()
        d_ref  = config.D_REFERENCE
        decay  = config.FIELD_DECAY
        B_eff  = (self.magnet.polarity
                  * self.magnet.B0
                  * (d_ref / d) ** decay)
        return float(B_eff)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        """
        Actualiza todo el estado físico para el frame actual.

        Llamar una vez por frame después de actualizar la posición del imán.

        Parameters
        ----------
        dt : delta de tiempo [s].
        """
        if dt <= 0:
            return

        self._elapsed += dt

        # 1. Campo efectivo
        B_eff = self._compute_B_eff()

        # 2. Flujo magnético: Φ = B_eff · A · cos(0) = B_eff · A
        self.flux = B_eff * self.coil.A

        # 3. Variación del flujo: dΦ/dt ≈ ΔΦ / Δt
        self.d_flux_dt = (self.flux - self._prev_flux) / dt

        # 4. Ley de Faraday: ε = −N · dΦ/dt
        self.emf = -self.coil.N * self.d_flux_dt

        # 5. Ley de Ohm: I = ε / R
        self.current = self.emf / self.coil.R if self.coil.R != 0 else 0.0

        # 6. Estado del flujo
        threshold = 1e-6   # umbral para considerar "constante"
        if self.d_flux_dt > threshold:
            self.flux_status = "increasing"
        elif self.d_flux_dt < -threshold:
            self.flux_status = "decreasing"
        else:
            self.flux_status = "constant"

        # 7. Dirección de corriente según Ley de Lenz
        #    corriente > 0 → antihoraria (se opone al aumento del flujo positivo)
        #    corriente < 0 → horaria
        if abs(self.current) < 1e-9:
            self.current_dir = "none"
        elif self.current > 0:
            self.current_dir = "ccw"
        else:
            self.current_dir = "cw"

        # 8. Actualizar historial
        self.time_history.append(self._elapsed)
        self.flux_history.append(self.flux)
        self.emf_history.append(self.emf)
        self.current_history.append(self.current)

        # Guardar para próxima diferencia finita
        self._prev_flux = self.flux

    # ------------------------------------------------------------------
    def get_educational_message(self) -> str:
        """
        Genera un mensaje educativo dinámico basado en el estado actual.

        Returns
        -------
        str : mensaje para mostrar en el panel informativo.
        """
        if self.flux_status == "increasing":
            if abs(self.emf) > 0.01:
                return ("El flujo magnético aumenta. "
                        "Según la Ley de Lenz, la corriente inducida "
                        "genera un campo opuesto al cambio.")
            return "El flujo magnético está aumentando."

        if self.flux_status == "decreasing":
            if abs(self.emf) > 0.01:
                return ("El flujo magnético disminuye. "
                        "La FEM inducida genera una corriente que "
                        "intenta mantener el flujo.")
            return "El flujo magnético está disminuyendo."

        # Flujo constante
        if abs(self.emf) < 0.001:
            return ("El flujo magnético permanece constante. "
                    "No hay FEM inducida (Ley de Faraday).")

        return "Estado electromagnético estabilizándose."

    # ------------------------------------------------------------------
    def reset_history(self) -> None:
        """Limpia el historial de datos (útil al reiniciar la simulación)."""
        self.time_history.clear()
        self.flux_history.clear()
        self.emf_history.clear()
        self.current_history.clear()
        self._elapsed  = 0.0
        self._prev_flux = 0.0

    # ------------------------------------------------------------------
    @property
    def history_arrays(self):
        """
        Devuelve los historiales como arrays NumPy para graficar.

        Returns
        -------
        tuple : (t, flux, emf, current) como np.ndarray.
        """
        t   = np.array(self.time_history,    dtype=np.float64)
        phi = np.array(self.flux_history,    dtype=np.float64)
        emf = np.array(self.emf_history,     dtype=np.float64)
        I   = np.array(self.current_history, dtype=np.float64)
        return t, phi, emf, I


# Aproximación de FPS para dimensionar el deque del historial
FPS_APPROX = config.FPS


# ---------------------------------------------------------------------------
# ExplainerEngine
# ---------------------------------------------------------------------------

class ExplainerEngine:
    """
    Genera explicaciones educativas dinámicas basadas en el estado físico.

    Cada método devuelve una lista de tuplas (texto, color_RGB) lista para
    que el renderer las muestre sin lógica de presentación aquí.

    Dos modos de explicación
    ------------------------
    step_explanation() — Narración paso a paso de UN avance de simulación.
                         Sigue la cadena causal completa con numeración.
    full_analysis()    — Análisis completo en prosa del estado actual.
                         Muestra causa → efecto → consecuencia en lenguaje
                         accesible para cualquier estudiante.
    """

    # Fracción de tiempo que avanza cada "paso" en modo paso a paso [s]
    STEP_DT: float = 0.05

    # Colores semánticos (definidos aquí para no importar config en el renderer)
    _C_HEADER  = (240, 210,  50)   # amarillo — títulos/cabeceras
    _C_MOTION  = (220, 220, 220)   # blanco suave — movimiento
    _C_FLUX_UP = ( 50, 200,  80)   # verde — flujo creciente
    _C_FLUX_DN = (220,  50,  50)   # rojo — flujo decreciente
    _C_FLUX_CT = (200, 180,  40)   # amarillo — flujo constante
    _C_FARADAY = (240, 140,  30)   # naranja — Ley de Faraday
    _C_OHM     = ( 50, 210, 210)   # cian — Ley de Ohm
    _C_LENZ_CC = ( 50, 200, 120)   # verde-azul — Lenz antihorario
    _C_LENZ_CW = (255, 120,  40)   # naranja — Lenz horario
    _C_VALUE   = (240, 210,  50)   # amarillo — valores numéricos
    _C_DIM     = (160, 160, 165)   # gris — texto secundario
    _C_NONE    = (   0,   0,   0)  # marcador de línea vacía

    # ------------------------------------------------------------------
    def step_explanation(self, physics, magnet) -> list:
        """
        Explicación de UN paso: sigue la cadena causal numerada.

        Parameters
        ----------
        physics : PhysicsEngine con el estado DESPUÉS del avance.
        magnet  : Magnet con posición y velocidad actualizadas.

        Returns
        -------
        list[tuple[str, tuple]] — pares (texto, color_rgb).
        """
        lines = []
        v     = magnet.velocity
        phi   = physics.flux
        dphi  = physics.d_flux_dt
        emf   = physics.emf
        I     = physics.current

        # ---- Cabecera ----
        lines.append(("── PASO ADELANTE ──", self._C_HEADER))
        lines.append(("", self._C_NONE))

        # ---- 1. Movimiento ----
        if abs(v) > 2.0:
            speed_ms = abs(v) / 200.0
            dir_word = "acercando a" if v > 0 else "alejando de"
            lines.append((f"1. MOVIMIENTO", self._C_MOTION))
            lines.append((
                f"El imán se está {dir_word} la bobina"
                f" (v ≈ {speed_ms:.3f} m/s).",
                self._C_DIM))
        else:
            lines.append(("1. MOVIMIENTO", self._C_MOTION))
            lines.append(("El imán está prácticamente en reposo.",
                           self._C_DIM))
        lines.append(("", self._C_NONE))

        # ---- 2. Flujo ----
        lines.append(("2. FLUJO MAGNÉTICO (Φ)", self._C_FARADAY))
        if physics.flux_status == "increasing":
            c = self._C_FLUX_UP
            lines.append(("El flujo magnético está aumentando.", c))
            lines.append((
                f"Φ = {phi:.4f} Wb  |  dΦ/dt = +{abs(dphi):.4f} Wb/s",
                self._C_VALUE))
        elif physics.flux_status == "decreasing":
            c = self._C_FLUX_DN
            lines.append(("El flujo magnético está disminuyendo.", c))
            lines.append((
                f"Φ = {phi:.4f} Wb  |  dΦ/dt = −{abs(dphi):.4f} Wb/s",
                self._C_VALUE))
        else:
            lines.append(("El flujo magnético es constante.", self._C_FLUX_CT))
            lines.append((f"Φ = {phi:.4f} Wb  |  dΦ/dt ≈ 0", self._C_VALUE))
        lines.append(("", self._C_NONE))

        # ---- 3. Ley de Faraday ----
        lines.append(("3. LEY DE FARADAY", self._C_FARADAY))
        if abs(emf) > 0.001:
            lines.append((
                "La variación del flujo genera una FEM inducida:",
                self._C_DIM))
            sign = "+" if emf >= 0 else ""
            lines.append((f"ε = −N·(dΦ/dt) = {sign}{emf:.4f} V",
                           self._C_VALUE))
        else:
            lines.append(("Sin variación de flujo, no hay FEM.", self._C_DIM))
            lines.append(("ε = 0 V", self._C_VALUE))
        lines.append(("", self._C_NONE))

        # ---- 4. Ley de Ohm ----
        lines.append(("4. LEY DE OHM  (I = ε / R)", self._C_OHM))
        if abs(I) > 1e-9:
            lines.append(("La FEM produce una corriente inducida:", self._C_DIM))
            sign = "+" if I >= 0 else ""
            lines.append((f"I = {sign}{I:.6f} A", self._C_VALUE))
        else:
            lines.append(("Sin FEM, la corriente es cero.", self._C_DIM))
            lines.append(("I = 0 A", self._C_VALUE))
        lines.append(("", self._C_NONE))

        # ---- 5. Ley de Lenz ----
        lines.append(("5. LEY DE LENZ", self._C_FARADAY))
        if physics.current_dir == "ccw":
            lines.append(("La corriente circula en sentido antihorario (↺).",
                           self._C_LENZ_CC))
            lines.append(("Su campo se opone al aumento del flujo.", self._C_DIM))
        elif physics.current_dir == "cw":
            lines.append(("La corriente circula en sentido horario (↻).",
                           self._C_LENZ_CW))
            lines.append(("Su campo intenta mantener el flujo decreciente.",
                           self._C_DIM))
        else:
            lines.append(("Sin corriente inducida, no hay campo opuesto.",
                           self._C_DIM))

        return lines

    # ------------------------------------------------------------------
    def full_analysis(self, physics, magnet) -> list:
        """
        Análisis completo de la cadena causa–efecto del estado actual.

        Parameters
        ----------
        physics : PhysicsEngine con estado actual.
        magnet  : Magnet con posición y velocidad actuales.

        Returns
        -------
        list[tuple[str, tuple]] — pares (texto, color_rgb).
        """
        v   = magnet.velocity
        phi = physics.flux
        emf = physics.emf
        I   = physics.current

        lines = []
        lines.append(("▶  ANÁLISIS ACTUAL", self._C_HEADER))
        lines.append(("", self._C_NONE))

        # Movimiento
        if abs(v) > 2.0:
            speed_ms = abs(v) / 200.0
            if v > 0:
                lines.append((
                    f"El imán se está acercando a la bobina"
                    f" (v ≈ {speed_ms:.3f} m/s).",
                    self._C_MOTION))
            else:
                lines.append((
                    f"El imán se está alejando de la bobina"
                    f" (v ≈ {speed_ms:.3f} m/s).",
                    self._C_MOTION))
        else:
            lines.append(("El imán está en reposo.", self._C_MOTION))
        lines.append(("", self._C_NONE))

        # Flujo
        if physics.flux_status == "increasing":
            lines.append(("Como consecuencia, el flujo que atraviesa",
                           self._C_FLUX_UP))
            lines.append(("las espiras está aumentando.", self._C_FLUX_UP))
        elif physics.flux_status == "decreasing":
            lines.append(("Como consecuencia, el flujo que atraviesa",
                           self._C_FLUX_DN))
            lines.append(("las espiras está disminuyendo.", self._C_FLUX_DN))
        else:
            lines.append(("El flujo magnético permanece constante.",
                           self._C_FLUX_CT))
        lines.append((f"Φ = {phi:.4f} Wb", self._C_VALUE))
        lines.append((f"dΦ/dt = {physics.d_flux_dt:.4f} Wb/s", self._C_VALUE))
        lines.append(("", self._C_NONE))

        # Faraday
        if abs(emf) > 0.001:
            lines.append(("Según la Ley de Faraday, la variación",
                           self._C_FARADAY))
            lines.append(("del flujo genera una FEM inducida.", self._C_FARADAY))
            sign = "+" if emf >= 0 else ""
            lines.append((f"ε = {sign}{emf:.4f} V", self._C_VALUE))
        else:
            lines.append(("No hay variación de flujo.", self._C_DIM))
            lines.append(("Por la Ley de Faraday, ε = 0 V.", self._C_DIM))
        lines.append(("", self._C_NONE))

        # Ohm + Lenz
        if abs(I) > 1e-9:
            sign_i = "+" if I >= 0 else ""
            lines.append((f"La corriente inducida resultante es:", self._C_OHM))
            lines.append((f"I = ε/R = {sign_i}{I:.6f} A", self._C_VALUE))
            lines.append(("", self._C_NONE))
            if physics.current_dir == "ccw":
                lines.append(("Según la Ley de Lenz, la corriente",
                               self._C_LENZ_CC))
                lines.append(("circula en sentido antihorario (↺)",
                               self._C_LENZ_CC))
                lines.append(("para oponerse al aumento del flujo.",
                               self._C_DIM))
            elif physics.current_dir == "cw":
                lines.append(("Según la Ley de Lenz, la corriente",
                               self._C_LENZ_CW))
                lines.append(("circula en sentido horario (↻)", self._C_LENZ_CW))
                lines.append(("para mantener el flujo que decrece.",
                               self._C_DIM))
        else:
            lines.append(("Sin FEM, no se induce corriente.", self._C_DIM))
            lines.append(("I = 0 A", self._C_VALUE))

        return lines
