# Datos locales

`raw/` guarda precios diarios, el manifiesto de descarga y la copia del profesor de los factores. `processed/` guarda las tablas preparadas y la validación. Ambas carpetas se generan o se aportan localmente y están excluidas de Git.

Antes de ejecutar, coloca el CSV del profesor en `raw/F-F_Research_Data_Factors.csv`. El hash debe coincidir con la versión CRSP 202609 fijada en `config/analysis.toml`. El comando `download` obtiene los precios y conserva su procedencia. `analyze` no usa Internet.

Para repetir exactamente una ejecución, conserva el CSV del profesor, los siete archivos diarios (seis activos y EUR/USD), `manifest.json`, la configuración y `reports/run_manifest.json`. Yahoo y Kenneth French pueden revisar históricos; una descarga nueva no garantiza valores idénticos. Las actualizaciones explícitas de precios archivan la copia previa.

Consulta `docs/sources.md` antes de redistribuir datos. No se ha encontrado una autorización inequívoca para publicar una copia de los factores ni se presume permiso para los datos de Yahoo. Publicar el código no exige publicar los datos brutos.
