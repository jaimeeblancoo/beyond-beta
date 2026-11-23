# Configuración e integridad

## Configuración admitida y alternativas

El diseño predeterminado es una muestra concreta. Los parámetros de una ejecución salen de su TOML y de los resultados comprobados. Se admiten de dos a diez activos, solo EUR/USD, nombres y tickers únicos y pesos estrictamente positivos que sumen uno (tolerancia absoluta 1e-10). `Cartera` es un nombre reservado. Se exigen al menos doce rentabilidades para ejecutar el programa; una variante con menos de sesenta no cumple por sí sola los cinco años pedidos por el enunciado.

Se admite únicamente OLS como inferencia principal y la regla HAC `floor(4*(T/100)^(2/9))`, evaluada mediante código fijo seguro. La sensibilidad HAC siempre se exporta por separado. Solo se soportan rebalanceo `monthly`, `costs=0` y `taxes=0`. Otros valores y campos desconocidos se rechazan, no se ignoran. `factors.source` y `factors.url` son atribución y localización de la alternativa oficial; analizar nunca los usa para descargar o sustituir la copia fijada por hash.

`max_month_end_age_days=7` limita la distancia del último precio al fin del mes natural. Detecta truncamientos claros y tolera cierres por fines de semana o festivos habituales, sin acreditar el último día bursátil exacto. `max_fx_age_days` controla por separado la antigüedad del FX anterior o coincidente. Ambos controles se aplican a snapshots y descargas.

La raíz se descubre desde el directorio de ejecución buscando `pyproject.toml` del proyecto, o se indica con `--project-root`. Nunca se deduce del directorio del TOML. `--config` relativo se resuelve desde esa raíz; un archivo externo puede indicarse con ruta absoluta. Las rutas de datos siguen siendo relativas al proyecto. El manifiesto conserva la ruta y el hash del TOML realmente utilizado; generar el informe exige utilizar ese mismo archivo sin cambios.

```powershell
.\.venv\Scripts\python.exe -m beyond_beta.cli --config config/alternativa.toml analyze
.\.venv\Scripts\python.exe -m beyond_beta.cli --config config/alternativa.toml report
.\.venv\Scripts\python.exe scripts/verify_results.py --config config/alternativa.toml
.\.venv\Scripts\python.exe -m beyond_beta.cli --config config/alternativa.toml verify-artifacts
# El lanzador admite -Config y -SkipPdf; -Python permite elegir otro entorno.
.\scripts\run_analysis.ps1 -Command report -Config config/alternativa.toml -SkipPdf
```

`report --skip-pdf` genera solo fuentes; los PDF previos se archivan para no presentarlos como nuevos. La CI utiliza pruebas sintéticas sin red, sin datos docentes ni MiKTeX. La instalación de dependencias de CI sí necesita acceso al registro de paquetes.

## Integridad y límites de reproducción

El manifiesto identifica cada ejecución y registra parámetros, configuración, hashes de snapshots y de su procedencia, factores, versiones, commit y hash del código de análisis. Enumera explícitamente las ocho tablas, cinco figuras y Excel; no incorpora CSV sobrantes mediante un glob. Los documentos registran después sus fuentes manuales, plantilla, código de maquetación, LaTeX y PDF. No contiene su propio hash.

`report` rechaza tablas, figuras, Excel, entradas o configuración alteradas y ejecuciones incompletas. Si cambian los snapshots o su manifiesto debe repetirse `analyze`; una procedencia nueva no se asigna a resultados antiguos. Los datos anteriores se pueden conservar en una copia completa de la ejecución. Las figuras del informe deben pertenecer a esa misma ejecución. `verify-artifacts` comprueba también las fuentes y documentos finales registrados.

Un Excel recién generado por openpyxl tiene fórmulas sin valores calculados en caché; se solicita recálculo automático al abrirlo. Solo se afirma recálculo independiente si existe una evidencia de esa etapa registrada en el manifiesto. Abrir y guardar el libro puede cambiar su hash y exige verificarlo antes de utilizarlo de nuevo como artefacto de la ejecución. Las regresiones siguen siendo resultados Python, no un modelo interactivo del libro.

`pyproject.toml` separa dependencias de ejecución y herramientas de validación (`dev`). `requirements-lock.txt` fija las versiones del entorno Python revisado, no hashes de wheels ni el sistema operativo, las fuentes o MiKTeX. No se promete identidad binaria de PDF/Excel entre equipos. Las verificaciones realizadas y sus límites se describen en [Validación](validation.md).
