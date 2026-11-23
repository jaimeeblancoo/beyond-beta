# Fuentes y derechos de redistribución

Revisión realizada el 19 de noviembre de 2026. Acceso público no equivale a una licencia de redistribución.

## Precios y software de descarga

Yahoo Finance, históricos por ticker: https://finance.yahoo.com/

API utilizada: https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html

El proyecto yfinance distingue su licencia de software de los derechos sobre los datos y remite a las condiciones de Yahoo; señala uso personal de la API. No se interpreta la licencia del paquete como permiso para publicar históricos. Se guardan precios y resultados que contienen fuentes en carpetas ignoradas por Git. La [ayuda oficial de Yahoo Finance](https://help.yahoo.com/kb/account/SLN2310.html) limita la redistribución de la información suministrada. La edición publica tablas con resultados agregados y los gráficos de riqueza normalizada y caída de la cartera. Los archivos con precios, tipos de cambio y rentabilidades mensuales individuales se custodian localmente.

Fuente: https://github.com/ranaroussi/yfinance

## Factores Fama French

Biblioteca: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

Definiciones de factores estadounidenses: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html

Factores regionales y moneda USD: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_developed.html

Descarga oficial actual, que puede cambiar de versión: https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip

Se conserva la copia del profesor, cabecera CRSP 202609, con el copyright 2026 de Eugene F. Fama y Kenneth R. French. SHA256: a3894d74d553cab812eabbe706bdbf443c97eb20b24b05e3e5f3ce47e46b90bb. Se recibió el 19 de noviembre de 2026 y no se altera. No se ha identificado una licencia inequívoca de redistribución en las páginas primarias consultadas ni en el fichero. Por ello no se versiona el CSV. No se afirma que una descarga oficial posterior sea idéntica; debe obtenerse la copia del profesor para reproducir esta ejecución exacta.

Las fuentes describen RF como proxy de un mes estadounidense; desde junio de 2024 procede de ICE BofA US 1-Month Treasury Bill Index y antes de Ibbotson. La revisión de la metodología del proveedor debe distinguirse de cambios hechos por este proyecto.

## Identidad de los dos activos añadidos

EUNH.DE: iShares Core € Govt Bond UCITS ETF EUR (Dist), ISIN IE00B4WXJJ64. Bonos públicos de la zona euro, clase EUR de distribución semestral, lanzamiento 17 de abril de 2009. La divisa del subyacente es EUR; no se infiere una cobertura a otra moneda. El símbolo EUNH aparece en la ficha alemana y se contrasta con la identidad y moneda EUR devueltas por Yahoo. Se validan 61 cierres mensuales para la ventana fijada.

Ficha primaria: https://www.ishares.com/gls-download/literature/fact-sheet/iega-ishares-core-govt-bond-ucits-etf-fund-fact-sheet-en-de.pdf

IUSQ.DE: iShares MSCI All Country World UCITS ETF USD (Acc), ISIN IE00B6R52259. Clase USD de acumulación, acciones mundiales desarrolladas y emergentes. Lanzamiento 21 de octubre de 2011; cotización Xetra IUSQ en EUR desde 2 de abril de 2012. No se identifica como clase con cobertura EUR; cotizar en EUR no elimina la exposición de los subyacentes. Se validan 61 cierres mensuales.

Ficha y tabla Listings primaria: https://www.ishares.com/uk/individual/en/products/251850/ishares-msci-acwi-ucits-etf

## Métodos estadísticos y materiales docentes

OLS y covarianza HAC: documentación oficial de statsmodels.

https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html

https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html

El enunciado se ha revisado localmente y no se incorpora al repositorio porque su redistribución no está aclarada. La fecha de entrega debe verificarse con la documentación vigente del curso.
