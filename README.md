# Sistema de análisis de datos experimentales de física

Pipeline reproducible para llevar datos de seguimiento de video desde Tracker hasta un informe científico LaTeX: validación del CSV/TXT, exploración y ajuste de referencia en QtiPlot, limpieza y suavizado, cinemática numérica, ajuste físico, estadísticas, figuras de publicación y tablas automáticas.

> El archivo `data/raw/caida_libre_tracker.csv` es **sintético y demostrativo**, no una medición real. Sustitúyelo por tu exportación de Tracker antes de presentar conclusiones experimentales.

## 1. Requisitos e instalación

- Python 3.10 o posterior.
- Git.
- Para el informe: una distribución LaTeX con `IEEEtran`, `babel`, `amsmath`, `graphicx`, `siunitx`, `cite` y BibTeX.
- Tracker y QtiPlot son aplicaciones externas; su instalación depende del sistema operativo.

```bash
git clone <URL-DE-TU-REPOSITORIO>
cd analisis-datos-fisicos
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Fase A — adquisición con Tracker

Ejemplo propuesto: caída libre de una esfera pequeña y de alto contraste.

1. Usa un trípode; la cámara debe permanecer inmóvil. Coloca la cámara lejos en relación con el tamaño de la escena y usa zoom óptico moderado para reducir perspectiva.
2. Sitúa una regla o patrón de longitud conocida **en el mismo plano vertical** que la trayectoria. La regla debe estar lo más cerca posible del plano de movimiento. No calibres con una escala situada delante o detrás del objeto.
3. Orienta el eje óptico perpendicular al plano de movimiento, evita grabar desde arriba/abajo o en diagonal y procura que el objeto no se acerque a la cámara. Esto reduce paralaje y distorsión de perspectiva.
4. Usa iluminación uniforme, fondo contrastante, enfoque fijo y una frecuencia de cuadros conocida. Evita desenfoque de movimiento y asegúrate de que todo el recorrido quede dentro del encuadre.
5. En Tracker, abre el video, configura la frecuencia de cuadros correcta, añade una vara de calibración sobre la longitud conocida, establece origen y ejes y define el plano de referencia. La coordenada vertical puede aumentar hacia arriba o hacia abajo; anota la convención.
6. Crea una pista de masa puntual y marca el mismo punto físico del objeto en cada cuadro (por ejemplo, su centro). Usa avance cuadro a cuadro; revisa los puntos dudosos sin corregirlos de forma arbitraria.
7. Exporta la tabla de datos como CSV o TXT con columnas de tiempo, x e y. Usa metros y segundos o convierte explícitamente las unidades antes del análisis.
8. Copia el archivo original sin modificar a `data/raw/`. No guardes videos grandes en Git; archívalos fuera del repositorio con una copia de seguridad y documenta su nombre/hash.

El cargador reconoce encabezados como `t`, `time`, `tiempo`, `x`, `x (m)`, `y (m)`. Si el archivo de Tracker usa otros nombres, modifica los alias en `src/data_loader.py` de manera explícita.

## 3. Fase B — inspección y validación en QtiPlot

Abre QtiPlot e importa el CSV/TXT ASCII. Comprueba el delimitador, los encabezados, las unidades, el orden del tiempo, los valores perdidos y la forma de `y(t)`. Grafica `y` contra `t` y ajusta un polinomio cuadrático `c0 + c1*t + c2*t²`. La aceleración estimada por QtiPlot es `2*c2`. Para `x(t)`, un ajuste lineal puede servir como control de movimiento horizontal.

Compara el ajuste, errores de parámetros y residuos con Python. Guarda el proyecto real `.qti` y una bitácora en `qtiplot/`; se proporciona una guía paso a paso en `qtiplot/README.md`. No se incluye un `.qti` falso: ese archivo debe ser generado por QtiPlot instalado en tu equipo.

## 4. Fase C — pipeline Python

Ejecuta con el archivo sintético de ejemplo:

```bash
python -m src.main
```

O especifica un archivo propio y parámetros experimentales:

```bash
python -m src.main --input data/raw/mi_experimento.csv \
  --smoothing savgol --window 9 --polyorder 2 \
  --sigma-position 0.002 --sigma-scale-relative 0.003 --gravity 9.81
```

El pipeline produce:

- `data/processed/*_processed.csv`: datos ordenados, filtrados y variables cinemáticas derivadas.
- `report/figures/`: posición, velocidad, aceleración y residuos, cada una en PNG de 300 DPI y PDF vectorial.
- `report/generated/results.json`: configuración, limpieza, coeficientes, incertidumbres, R², RMSE, MAE y error relativo.
- `report/generated/results.tex` y `results_table.tex`: macros y tabla LaTeX que el artículo incluye automáticamente.
- `report/generated/results.json` también informa un cribado robusto de posibles valores atípicos (MAD); no elimina puntos automáticamente, para evitar exclusiones sin justificación experimental.

### Métodos numéricos y convenciones

La posición se expresa en m y el tiempo en s. Se calcula el desplazamiento desde la primera observación, las componentes de velocidad y aceleración mediante `numpy.gradient` con el vector de tiempos real y `edge_order=2`. Por defecto se filtra con Savitzky–Golay; también se ofrece media móvil o ningún filtro.

Derivar amplifica el ruido: en diferencias finitas una fluctuación de posición se divide entre `dt` para la velocidad y, aproximadamente, entre `dt²` para aceleración. Por eso se suaviza antes de derivar, se conserva la señal cruda y se ajusta el modelo físico a las posiciones originales, sin usar el suavizado como sustituto de los datos medidos.

La incertidumbre de derivadas mostrada es una aproximación para errores de coordenada independientes y muestreo casi uniforme: `sigma_v ≈ sigma_r/(sqrt(2)*dt)` y `sigma_a ≈ sqrt(6)*sigma_r/dt²`. `--sigma-position` representa la incertidumbre estándar absoluta de posición (incluye seguimiento y calibración, si se ha estimado). `--sigma-scale-relative` añade una contribución de escala relativa en cuadratura a la incertidumbre de la coordenada usada en el ajuste. La covarianza de `curve_fit` estima la incertidumbre de parámetros bajo el modelo y los pesos especificados; no sustituye un presupuesto metrológico completo.

El modelo ajustado es `y(t)=y0+v0*t+0.5*a*t²`. Se informa `|a|` frente a la magnitud de `g` para que la convención de eje no altere la comparación. El valor local de gravedad puede diferir ligeramente de 9.81 m/s² y debe justificarse según ubicación/altura y precisión requerida.

## 5. Fase D — informe LaTeX

Después de ejecutar Python:

```bash
cd report
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

El documento usa una plantilla de artículo tipo IEEE. Las figuras PDF y la tabla estadística se insertan desde `report/figures/` y `report/generated/`. Si compilas antes de ejecutar el pipeline, faltarán archivos generados. Edita autor, institución, discusión y conclusiones con los resultados de tu experimento real.

## 6. Notebook exploratorio

Abre `notebooks/exploracion.ipynb` desde Jupyter para inspeccionar los datos de demostración, visualizar `y(t)` y revisar el ajuste. El notebook complementa, pero no reemplaza, el pipeline reproducible `src/main.py`.

## 7. Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas verifican derivadas con una trayectoria analítica, recuperación de aceleración conocida, mapeo de encabezados Tracker, descarte de filas incompletas y rechazo de tiempos duplicados.

## 8. Estructura del proyecto

```text
analisis-datos-fisicos/
├── data/
│   ├── raw/                  # fuente original de Tracker, inmutable
│   └── processed/            # salidas reproducibles locales
├── src/
│   ├── data_loader.py
│   ├── kinematics.py
│   ├── curve_fitting.py
│   ├── plotting.py
│   └── main.py
├── qtiplot/                  # proyecto .qti real y bitácora
├── report/
│   ├── main.tex
│   ├── referencias.bib
│   ├── figures/
│   └── generated/
├── notebooks/exploracion.ipynb
├── tests/test_scientific_pipeline.py
├── requirements.txt
└── README.md
```

## 9. Git y GitHub: flujo por ramas

```bash
git init
git branch -M main
git add .gitignore README.md requirements.txt src tests data/raw qtiplot report notebooks
git commit -m "chore: inicializa pipeline de análisis experimental"
git remote add origin https://github.com/USUARIO/analisis-datos-fisicos.git
git push -u origin main

# Trabajo de cinemática
git switch -c feature/cinematica
git add src/kinematics.py tests
git commit -m "feat: calcula variables cinematicas e incertidumbres"
git push -u origin feature/cinematica

# Gráficas
git switch main
git pull --ff-only
git switch -c feature/graficas
git add src/plotting.py
git commit -m "feat: genera graficas cientificas a 300 dpi"
git push -u origin feature/graficas

# Informe
git switch main
git pull --ff-only
git switch -c docs/informe-latex
git add report qtiplot README.md
git commit -m "docs: agrega informe latex y protocolo de validacion"
git push -u origin docs/informe-latex
```

Abre Pull Requests hacia `main`, ejecuta pruebas y revisa el resultado antes de fusionar. Convención: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`. No versionar videos (`.mp4`, `.mov`), entornos virtuales, cachés ni archivos auxiliares de LaTeX. Los CSV/TXT originales pequeños y necesarios para reproducibilidad sí deben versionarse en `data/raw/`; nunca se sobrescriben.

## Referencias metodológicas

- Tracker / Open Source Physics: <https://physlets.org/tracker/>.
- Savitzky, A. y Golay, M. J. E. (1964), “Smoothing and Differentiation of Data by Simplified Least Squares Procedures”, *Analytical Chemistry*, 36(8), 1627–1639.
- Taylor, J. R. (1997), *An Introduction to Error Analysis*, 2.ª ed.

## Ejecutar en GitHub Codespaces

1. Sube esta carpeta a un repositorio GitHub independiente llamado `analisis-datos-fisicos`.
2. En GitHub, abre **Code → Codespaces → Create codespace on main**.
3. Espera a que el entorno instale las dependencias y abre la terminal integrada.
4. Ejecuta el pipeline de ejemplo:

```bash
python -m src.main
```

Para ejecutar las pruebas:

```bash
python -m unittest discover -s tests -v
```

Para analizar un CSV exportado de Tracker, súbelo a `data/raw/` y ejecuta el comando documentado en la sección **Fase C — pipeline Python** de este README. El entorno de Codespaces no incluye Tracker ni QtiPlot: esas aplicaciones se usan localmente para capturar y validar los datos; luego sube el CSV resultante al repositorio.

GitHub Actions ejecuta automáticamente las pruebas al hacer `push` o abrir un Pull Request. La generación del informe y las gráficas se realiza ejecutando el pipeline desde Codespaces o un entorno Python local.
