# Validación exploratoria en QtiPlot

QtiPlot es una aplicación externa; el proyecto no automatiza su interfaz ni genera un archivo `.qti` binario ficticio. Guarda aquí el proyecto real de QtiPlot (`.qti`) y las notas/decisiones de validación.

## Flujo reproducible

1. Ejecuta el análisis de Tracker y conserva `data/raw/caida_libre_tracker.csv` intacto. Para el archivo real, usa una copia exportada desde Tracker.
2. Abre QtiPlot y selecciona **File → Import → ASCII** (el nombre exacto puede cambiar según la versión). Elige el CSV/TXT, verifica que la coma/tabulación sea el separador de columnas y que la primera fila contenga los nombres.
3. Asigna las columnas `t (s)`, `x (m)` y `y (m)` como X/Y según corresponda. Revisa unidades, valores faltantes, orden temporal y la escala de los ejes.
4. Crea un gráfico de dispersión `y` vs. `t`. Inspecciona puntos atípicos, saltos y curvatura. No elimines puntos sin anotar la razón física o de seguimiento.
5. Ejecuta un ajuste polinómico de segundo orden sobre `y(t)`, equivalente a `c0 + c1*t + c2*t^2`. Compara `a_y = 2*c2` contra el parámetro `acceleration` de `report/generated/results.json` y `results_table.tex`.
6. Para movimiento horizontal aproximadamente uniforme, ajusta `x(t)` con una recta. Guarda capturas/notas de ecuación, errores de parámetros y residuos.
7. Guarda el archivo de trabajo como `qtiplot/validacion_caida_libre.qti` y registra versión de QtiPlot, datos importados, puntos excluidos (si los hubiera) y resultados.

## Plantilla de registro

- Archivo y hash SHA-256 del dato crudo:
- Versión de QtiPlot / sistema operativo:
- Columnas y unidades:
- Tipo de ajuste y rango de tiempo:
- Ecuación obtenida y error estándar de coeficientes:
- Aceleración vertical `2*c2`:
- R² / residuos:
- Puntos excluidos y justificación:
- Diferencia frente al ajuste de Python:

**Convención importante:** si el eje Y positivo apunta hacia arriba, la aceleración de caída será negativa; si apunta hacia abajo, será positiva. Compara magnitudes solo después de declarar la convención.
