# Simulador — Ley de Faraday y Ley de Lenz

Simulador interactivo y educativo de **inducción electromagnética** escrito en Python.
Un imán de barra se mueve frente a una bobina y el programa calcula y muestra, en tiempo real,
el flujo magnético, la fuerza electromotriz (FEM) inducida y la corriente resultante, junto con
el sentido de la corriente según la Ley de Lenz.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.5%2B-green)
![NumPy](https://img.shields.io/badge/NumPy-1.26%2B-013243?logo=numpy)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.8%2B-orange)

---

## Características

- **Escena animada a 60 FPS**: imán con polos N/S, bobina con espiras, líneas de campo y flechas
  animadas de la corriente inducida.
- **Código de colores del flujo**: la bobina se pinta verde cuando el flujo crece, rojo cuando
  decrece y amarillo cuando es constante.
- **Gráficas en tiempo real** (Matplotlib incrustado en Pygame) de:
  - Flujo magnético Φ(t)
  - FEM inducida ε(t)
  - Corriente inducida I(t)
- **Parámetros ajustables con sliders**: campo B, número de espiras N, área A, resistencia R y
  velocidad del imán.
- **Dos modos de movimiento**:
  - *Automático*: el imán oscila solo.
  - *Manual*: arrastra el imán con el mouse.
- **Experimentos predefinidos**: ×2 espiras, ×2 campo B, invertir imán, ×2 velocidad y restablecer.
- **Modo educativo**:
  - *Paso a paso*: avanza la simulación de 0.05 s en 0.05 s con una explicación de cada paso.
  - *¿Qué ocurre?*: análisis completo del estado actual en lenguaje sencillo.

## Física implementada

| Magnitud | Ecuación |
|---|---|
| Campo efectivo (modelo dipolo) | B_eff = B₀ · (d_ref / d)³ |
| Flujo magnético | Φ = B_eff · A · cos θ |
| Ley de Faraday | ε = −N · dΦ/dt |
| Ley de Ohm | I = ε / R |
| Ley de Lenz | El campo creado por I se opone a la variación de Φ |

## Instalación

Requiere **Python 3.10 o superior**.

```bash
git clone https://github.com/<tu-usuario>/simulador-faraday-lenz.git
cd simulador-faraday-lenz
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

### Atajos de teclado

| Tecla | Acción |
|---|---|
| `Espacio` | Iniciar / pausar |
| `R` | Reiniciar la simulación |
| `M` | Alternar modo automático / manual |
| `Esc` | Salir |

## Estructura del proyecto

```
.
├── main.py           # Punto de entrada y bucle principal (clase Simulation)
├── config.py         # Constantes: ventana, layout, física, colores, fuentes
├── physics.py        # Magnet, Coil, PhysicsEngine y ExplainerEngine
├── graphics.py       # Renderizado de la escena (imán, bobina, campo, flechas)
├── plots.py          # Gráficas Matplotlib en un hilo de trabajo
├── ui.py             # Sliders, botones y UIManager
└── requirements.txt  # Dependencias
```

### Arquitectura

```
Simulation
 ├── Magnet          posición, velocidad, polaridad
 ├── Coil            N, A, R
 ├── PhysicsEngine   cálculo de Φ, ε, I y sentido de la corriente
 ├── ExplainerEngine explicaciones educativas
 ├── SceneRenderer   dibujo Pygame de la escena
 ├── PlotManager     gráficas Matplotlib incrustadas
 └── UIManager       sliders y botones
```

Las gráficas se renderizan en un **hilo separado** con el backend `Agg` de Matplotlib, de modo
que la simulación mantiene 60 FPS estables mientras las curvas se actualizan de forma asíncrona.

## Autor

Santiago
