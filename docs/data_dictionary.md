# Diccionario de datos

| Archivo o variable | Definición y unidad |
| --- | --- |
| data/raw/ticker.csv | Datos diarios Yahoo, índice Date local sin zona horaria; fuente intacta de esa descarga |
| Adj Close | Precio ajustado del proveedor, divisa original de cotización |
| EURUSD_X.csv Close | USD por EUR, cotización diaria Yahoo |
| F-F_Research_Data_Factors.csv | Copia del profesor CRSP 202609; porcentajes, bloque mensual más bloque anual |
| manifest.json | Identidad, divisa, campo, URL, fecha de descarga y SHA256 por ticker |
| prices_original | 61 precios en EUR para ACS, PPFB, EUNH e IUSQ; USD para Nike y Roblox |
| prices_usd / prices_eur | 61 precios convertidos, índice mensual AAAA-MM |
| returns_usd / returns_eur | 60 rentabilidades simples en decimal; 0,01 equivale a 1 % |
| observations | Mes, ticker, divisa original, fecha de precio, fecha FX, antigüedad natural y USD por EUR |
| factors_usd Mkt-RF | Rentabilidad del mercado bursátil estadounidense menos RF, decimal mensual |
| factors_usd SMB | Prima de tamaño, pequeñas menos grandes, decimal mensual |
| factors_usd HML | Prima de valor, alto menos bajo book-to-market, decimal mensual |
| factors_usd RF | Proxy de activo libre de riesgo estadounidense mensual, decimal |
| coefficient alpha | Intercepto de exceso de rentabilidad, decimal mensual |
| coefficient Mkt-RF / SMB / HML | Exposición estadística adimensional, no anualizada |
| std_error / t_stat / p_value | Inferencia OLS o HAC identificada por fila |
| ci_low / ci_high | IC bilateral del 95 %, misma escala que el coeficiente |
| r_squared / adj_r_squared | Proporción explicada y ajuste por parámetros |
| n_obs / hac_lags | Número de meses y retardos de la sensibilidad HAC |
| comparison | CAPM y FF3 de cartera: N, R², R² ajustado, AIC, BIC |
| validation.json | Controles de cobertura, ausencias, ventana, FX y factores |
| run_manifest.json | Esquema de etapas, run_id, ruta/hash del TOML efectivo, parámetros, versiones, código, entradas y artefactos de análisis/documentos |

Los meses son claves de periodo, no fechas de negociación. En Excel se muestran con el último día natural del mes. Las fechas efectivas de los precios y del FX se conservan por separado. El Excel, las tablas y las figuras de la entrega se versionan; los snapshots diarios y manifiestos locales se conservan por separado.

## Procedencia e integridad por etapa

`parameters` contiene los parámetros efectivos de la ejecución. `inputs` incluye hashes de los snapshots, del manifiesto de procedencia y del fichero original de factores. `code` registra commit, estado de cambios y hash de las fuentes de análisis; no atribuye los cambios locales al contenido exacto del commit base.

`analysis_outputs` enumera tablas, figuras y Excel, con hashes calculados después de generarlos. `report_inputs` registra fuentes manuales, plantilla y código de maquetación. `report_outputs` registra los archivos LaTeX/PDF y el contenido generado, después de esa etapa. No se incluye el propio manifiesto entre sus hashes. `report_pdf_compiled` distingue una compilación real de una generación de fuentes sin PDF.

`excel_validation.cached_results=false` significa que openpyxl dejó fórmulas sin caché y se solicitó recálculo al abrir. Una evidencia externa de valores y recálculo puede actualizar el hash del libro y su estado; obliga a regenerar los documentos para describir ese estado. `numeric_validation` enlaza la comprobación numérica independiente con su hash y run_id.

Los estados de escritura incompleta impiden validar documentos antiguos como si fueran la nueva ejecución. Los CSV sobrantes no entran en el inventario. La copia de la configuración efectiva y las entradas deben conservarse junto con todos los artefactos para reproducir una ejecución histórica.
