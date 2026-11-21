# -*- coding: utf-8 -*-
"""
config.py — Configuración central del simulador Faraday/Lenz.

Todas las constantes, dimensiones, colores y valores por defecto
están centralizados aquí para que el resto de módulos los importen
sin hardcodear valores dispersos.
"""

# ---------------------------------------------------------------------------
# VENTANA
# ---------------------------------------------------------------------------
WINDOW_WIDTH  = 1280
WINDOW_HEIGHT = 780
WINDOW_TITLE  = "Simulador — Ley de Faraday y Ley de Lenz"
FPS           = 60

# ---------------------------------------------------------------------------
# LAYOUT (píxeles)
# Dividimos la ventana en tres columnas:
#   SIM_PANEL  — zona de simulación gráfica (izquierda)
#   CTRL_PANEL — sliders y botones (centro)
#   INFO_PANEL — resultados numéricos (derecha)
# Las gráficas Matplotlib se renderizan sobre una superficie incrustada
# en la parte inferior de la zona de simulación.
# ---------------------------------------------------------------------------
SIM_PANEL_X      = 0
SIM_PANEL_Y      = 0
SIM_PANEL_WIDTH  = 700
SIM_PANEL_HEIGHT = WINDOW_HEIGHT

CTRL_PANEL_X      = 700
CTRL_PANEL_Y      = 0
CTRL_PANEL_WIDTH  = 280
CTRL_PANEL_HEIGHT = WINDOW_HEIGHT

INFO_PANEL_X      = 980
INFO_PANEL_Y      = 0
INFO_PANEL_WIDTH  = 300
INFO_PANEL_HEIGHT = WINDOW_HEIGHT

# Área de dibujo de la bobina/imán dentro del panel de simulación
SCENE_X      = SIM_PANEL_X + 10
SCENE_Y      = SIM_PANEL_Y + 10
SCENE_WIDTH  = SIM_PANEL_WIDTH - 20
SCENE_HEIGHT = 340          # los ~340 px superiores son la escena física

# Área de gráficas en tiempo real (parte inferior del panel de simulación)
PLOT_AREA_X      = SIM_PANEL_X
PLOT_AREA_Y      = SCENE_Y + SCENE_HEIGHT + 5
PLOT_AREA_WIDTH  = SIM_PANEL_WIDTH
PLOT_AREA_HEIGHT = WINDOW_HEIGHT - PLOT_AREA_Y - 5

# ---------------------------------------------------------------------------
# FÍSICA — valores por defecto
# ---------------------------------------------------------------------------
DEFAULT_B        = 1.0    # Intensidad del campo magnético [T]
DEFAULT_N        = 100    # Número de espiras
DEFAULT_A        = 0.05   # Área de la bobina [m²]
DEFAULT_R        = 10.0   # Resistencia [Ω]
DEFAULT_SPEED    = 1.0    # Velocidad del imán [m/s normalizada]

# Límites de los sliders
B_MIN, B_MAX     = 0.1, 5.0
N_MIN, N_MAX     = 10,  500
A_MIN, A_MAX     = 0.01, 0.20
R_MIN, R_MAX     = 1.0, 100.0
SPEED_MIN, SPEED_MAX = 0.1, 5.0

# Distancia de referencia imán–bobina para calcular el campo [m]
D_REFERENCE      = 1.0
# Factor de decaimiento del campo con la distancia (dipolo magnético ~1/r³)
FIELD_DECAY      = 3.0

# ---------------------------------------------------------------------------
# COLORES (R, G, B)
# ---------------------------------------------------------------------------
BLACK        = (  0,   0,   0)
WHITE        = (255, 255, 255)
GRAY_DARK    = ( 30,  30,  35)
GRAY_MED     = ( 55,  55,  60)
GRAY_LIGHT   = (180, 180, 185)
GRAY_PANEL   = ( 40,  40,  45)

RED          = (220,  50,  50)
RED_LIGHT    = (255, 100, 100)
BLUE         = ( 50, 100, 220)
BLUE_LIGHT   = (100, 150, 255)
GREEN        = ( 50, 200,  80)
GREEN_LIGHT  = (100, 230, 130)
YELLOW       = (240, 210,  50)
ORANGE       = (240, 140,  30)
CYAN         = ( 50, 210, 210)
MAGENTA      = (200,  60, 200)
PURPLE       = (130,  60, 200)

# Colores semánticos del simulador
COLOR_FLUX_INC   = GREEN        # flujo creciente
COLOR_FLUX_DEC   = RED          # flujo decreciente
COLOR_FLUX_CONST = YELLOW       # flujo constante
COLOR_COIL       = (200, 160,  60)   # cobre/bobina
COLOR_MAGNET_N   = RED_LIGHT
COLOR_MAGNET_S   = BLUE_LIGHT
COLOR_FIELD_LINE = (100, 180, 255)
COLOR_ARROW_CW   = (255, 120,  40)   # corriente horaria
COLOR_ARROW_CCW  = ( 40, 200, 120)   # corriente antihoraria
COLOR_BG_SIM     = ( 18,  18,  24)   # fondo zona simulación
COLOR_BG_CTRL    = GRAY_PANEL
COLOR_BG_INFO    = ( 22,  22,  28)
COLOR_ACCENT     = CYAN
COLOR_TEXT       = WHITE
COLOR_TEXT_DIM   = GRAY_LIGHT

# ---------------------------------------------------------------------------
# DIMENSIONES VISUALES (píxeles dentro de la escena)
# ---------------------------------------------------------------------------
COIL_CENTER_X    = SCENE_X + SCENE_WIDTH  // 2
COIL_CENTER_Y    = SCENE_Y + SCENE_HEIGHT // 2
COIL_WIDTH       = 60    # semiancho del rectángulo de la bobina
COIL_HEIGHT      = 110   # semialto
COIL_TURNS_DRAW  = 8     # espiras dibujadas (visual)

MAGNET_WIDTH     = 110
MAGNET_HEIGHT    = 44
MAGNET_START_X   = SCENE_X + 80   # posición x de inicio del imán

# Rango de movimiento horizontal del imán (en píxeles dentro de la escena)
MAGNET_X_MIN     = SCENE_X + 20
MAGNET_X_MAX     = COIL_CENTER_X - COIL_WIDTH - 10

# Radio de las flechas de corriente alrededor de la bobina
CURRENT_ARROW_RADIUS = COIL_HEIGHT + 30

# ---------------------------------------------------------------------------
# GRÁFICAS
# ---------------------------------------------------------------------------
PLOT_HISTORY_SECONDS = 20    # segundos de historial mostrado
PLOT_BACKGROUND      = "#0d0d12"
PLOT_LINE_FLUX       = "#44dd88"
PLOT_LINE_EMF        = "#ff6644"
PLOT_LINE_CURRENT    = "#4499ff"

# ---------------------------------------------------------------------------
# FUENTES
# ---------------------------------------------------------------------------
FONT_SIZE_TITLE  = 18
FONT_SIZE_NORMAL = 14
FONT_SIZE_SMALL  = 12
FONT_SIZE_LARGE  = 22

# ---------------------------------------------------------------------------
# ANIMACIÓN
# ---------------------------------------------------------------------------
FIELD_LINE_COUNT   = 9      # líneas de campo dibujadas por lado
ARROW_ANIM_SPEED   = 3.0    # velocidad de animación de flechas de corriente
BLINK_PERIOD       = 1.2    # segundos para el parpadeo de indicadores

# ---------------------------------------------------------------------------
# EXPERIMENTOS PREDEFINIDOS
# ---------------------------------------------------------------------------
EXPERIMENT_DOUBLE_N      = "double_n"
EXPERIMENT_DOUBLE_B      = "double_b"
EXPERIMENT_INVERT_MAGNET = "invert_magnet"
EXPERIMENT_DOUBLE_SPEED  = "double_speed"
EXPERIMENT_RESET         = "reset"
