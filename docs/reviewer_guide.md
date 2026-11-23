# Guía de verificación

1. Revisa el [informe](../reports/report/informe.pdf) y la [presentación](../reports/presentation/Presentacion_Beyond_Beta.pdf). Consulta las instrucciones de compilación del [informe](report_format.md) y de la [presentación](presentation.md).
2. Consulta la [configuración histórica](../config/analysis.toml), la [metodología](methodology.md) y las [fuentes](sources.md).
3. Contrasta los resultados con las [seis tablas agregadas](../reports/tables/).

| Paso | Implementación | Evidencia |
| --- | --- | --- |
| Cierres mensuales y cambio de divisa | [preparation.py](../src/beyond_beta/preparation.py) | Fechas y reglas descritas en [metodología](methodology.md) |
| Rentabilidades, cartera y estadísticos | [portfolio.py](../src/beyond_beta/portfolio.py), [descriptive.py](../src/beyond_beta/descriptive.py) | [Descriptivos en USD](../reports/tables/descriptive_usd.csv), [EUR](../reports/tables/descriptive_eur.csv) y [correlaciones](../reports/tables/correlations.csv) |
| CAPM y FF3 | [capm.py](../src/beyond_beta/capm.py), [factors.py](../src/beyond_beta/factors.py) | [CAPM](../reports/tables/capm.csv), [FF3](../reports/tables/ff3.csv) y [comparación](../reports/tables/comparison.csv) |
| Recálculo independiente desde un libro compatible | [verify_delivery.py](../scripts/verify_delivery.py), [pruebas](../tests/test_delivery.py) | NumPy y distribución t, incluido HAC Bartlett |

## Ejecutar las comprobaciones

Sigue la [instalación del README](../README.md) y ejecuta `python -m pytest -q` dentro del entorno. Las pruebas generan insumos sintéticos en directorios temporales, calculan resultados y comprueban que se detecten cambios en las salidas.

El recálculo íntegro de los resultados históricos requiere el libro de la entrega académica y sus ocho tablas CSV. El flujo desde las fuentes diarias requiere, además, los snapshots exactos y el manifiesto descritos en [data/README.md](../data/README.md). Con una ejecución local autorizada, invoca `python scripts/verify_delivery.py --project-root RUTA` sobre el directorio que contiene el libro, la configuración y las tablas. Para preparar datos y regenerar documentos, consulta [uso](usage.md).
