# Compilación del informe académico

La fuente principal es [reports/report/informe.tex](../reports/report/informe.tex). El documento contiene portada, índice de contenidos, índices de figuras y tablas, cuerpo numerado y anexo de coeficientes. Las figuras se cargan mediante rutas relativas a `reports/figures/`.

## Compilación desde el entorno Python

Instalar Python 3.12 y las dependencias del proyecto, y disponer de XeLaTeX mediante MiKTeX o TeX Live. Desde la raíz:

```powershell
.\.venv\Scripts\python.exe scripts/compile_report.py
```

En Linux/macOS: `.venv/bin/python scripts/compile_report.py`. Se realizan tres pasadas, sin descargar datos ni recalcular las estimaciones. `BEYOND_BETA_XELATEX` permite indicar el ejecutable si no está en PATH.

## Compilación directa

Desde `reports/report/`, ejecutar tres veces:

```bash
xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error informe.tex
```

Los paquetes utilizados son habituales en una instalación de XeLaTeX: fontspec, babel, amsmath, amssymb, graphicx, booktabs, tabularx, longtable, array, xcolor, microtype, enumitem, caption, xurl, hyperref, fancyhdr y titlesec. La tipografía es Latin Modern. El PDF se genera junto a la fuente.

## Revisión de salida

Comprobar que los índices contienen nueve tablas y tres figuras y que sus páginas coinciden; que la portada no muestra número; que los preliminares utilizan numeración romana y el cuerpo empieza en 1; y que no aparecen referencias sin resolver, texto recortado ni tablas fuera de los márgenes.

La compilación del archivo entregado modifica la presentación del documento, sin reconstruir su procedencia numérica. La regeneración desde las entradas originales se realiza mediante `beyond_beta.cli report` después de validar el análisis y produce un manifiesto nuevo. No debe modificarse un manifiesto antiguo para atribuirle un PDF distinto.

El cuerpo utiliza flujo continuo con subsecciones para riesgo, diversificación, SML y sensibilidad. Las tablas tienen identificadores semánticos definidos junto a su contenido, columnas numéricas alineadas a la derecha y unidades locales. Las tres figuras disponen de títulos cortos en el índice y llamadas numeradas. La bibliografía del informe incluye las referencias de CAPM, FF3 y HAC y las fuentes de datos e instrumentos.
