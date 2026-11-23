# Presentación

La [fuente Beamer](../reports/presentation/Presentacion_Beyond_Beta.tex) de la presentación de clase conserva diez diapositivas principales y seis de respaldo. Incluye la evolución de una inversión inicial de 100 USD y la caída de la cartera desde su máximo, ambas con frecuencia mensual.

Desde `reports/presentation/`, con XeLaTeX y Latin Modern disponibles, ejecuta el siguiente comando tres veces.

```bash
xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error Presentacion_Beyond_Beta.tex
```

El [generador](../scripts/build_presentation.py) produce los documentos de una ejecución local completa con sus gráficos de series. Ese flujo necesita que el informe, la configuración y el análisis local superen el control de integridad. Consulta la [guía de verificación](reviewer_guide.md).
