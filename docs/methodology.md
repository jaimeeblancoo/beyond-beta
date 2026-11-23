# Metodología

## Datos y muestra

Se selecciona el último Adj Close diario válido de cada mes. La configuración fija la ventana y el número de observaciones. Los datos posteriores quedan fuera de la muestra. Las fechas efectivas de precio y FX se guardan por activo. No se rellena un mes sin precio ni se descartan meses de forma implícita.

El precio ajustado incorpora los ajustes del proveedor por operaciones corporativas y dividendos. Es una aproximación a rentabilidad total, sujeta a revisiones y sin reconstruir todos los flujos, fiscalidad o costes individuales. No debe interpretarse como un precio histórico ejecutable. Todos los precios de una ejecución proceden de una misma descarga documentada; los snapshots anteriores se conservan al actualizar.

## Moneda y factores

Sea X el cambio en USD por EUR. Para ACS, PPFB, EUNH e IUSQ, P_USD = P_EUR * X. Nike y Roblox permanecen en USD. Para los descriptivos en euros se divide el precio USD de Nike y Roblox por X. La divisa de cotización no identifica la divisa de los subyacentes ni implica cobertura. IUSQ cotiza en EUR, pero es una clase USD acumulativa de acciones mundiales sin cobertura a EUR identificada.

Se usa el último FX no posterior a la fecha del precio, con la antigüedad máxima configurada en días naturales. Así no hay información de una fecha futura, aunque los cierres de distintos mercados y del FX no son simultáneos. El precio de cada mes representa el último dato disponible en su propio mercado; esta diferencia puede afectar a las regresiones mensuales.

### Regresiones en USD

La conversión a USD permite conservar el RF y los factores estadounidenses originales. Estos factores recogen riesgos de la renta variable de EE. UU. y pueden dejar fuera riesgos relevantes para otros mercados, el oro y la deuda pública.

### Qué exigiría estimar en EUR

Una estimación en EUR exigiría una prima de mercado, SMB, HML y un tipo libre de riesgo coherentes con esa moneda. Los factores regionales de Kenneth French también se publican en USD, por lo que cambiar de región no resuelve por sí solo la moneda. Al convertir una cartera larga-corta, el factor de moneda se aplica a su payoff de manera distinta a la de un activo financiado: no se divide SMB o HML por el nivel FX. Un Treasury estadounidense sin cobertura convertido a EUR contiene riesgo de cambio y no constituye automáticamente RF en euros.

## Rentabilidades y factores

R_t = P_t/P_(t-1) - 1. No se usa relleno implícito en pct_change. Se lee únicamente el bloque AAAAMM del CSV, se excluyen los datos anuales y se dividen una sola vez los valores porcentuales por 100. RF ya es mensual: no se divide entre 12. El hash fija la versión original; la unión por PeriodIndex mensual exige exactamente los meses comunes previstos por la configuración, sin NaN ni infinitos.

## Descriptivos

Rentabilidad acumulada = producto(1+R)-1. Rentabilidad anualizada geométrica = producto(1+R)^(12/T)-1. Media mensual = media aritmética; no es CAGR. Volatilidad mensual = desviación típica muestral (ddof=1) y anualizada = volatilidad mensual * sqrt(12), bajo la convención de escalado usual. Máxima caída = mínimo(riqueza/máximo histórico-1), incluyendo la riqueza inicial de uno. Con cierres mensuales se pueden ocultar caídas intrames. Correlaciones de Pearson sobre la misma muestra.

## CAPM y SML

R_i-RF = alfa_i + beta_i*(Mkt-RF) + error_i. OLS con intercepto; beta no se anualiza. Se exportan estimaciones, errores estándar, t, p, IC95, R², R² ajustado y N. Inferencia OLS principal y HAC/Newey-West como sensibilidad con retardos floor(4*(T/100)^(2/9)) calculados para la muestra efectiva, corrección finita y distribución t.

La SML virtual utiliza la media mensual RF más beta multiplicada por la media mensual Mkt-RF. Los puntos representan medias observadas en USD. Con intercepto y la misma muestra, la desviación vertical coincide con el alfa mensual estimado. Es una recta ilustrativa basada en medias históricas y una proxy bursátil; no identifica por sí sola la rentabilidad requerida ex ante. La significancia de alfa y beta se distingue visualmente. Los gráficos temporales de exceso del activo frente a exceso del mercado muestran una observación por mes. La SML muestra un punto por activo.

No rechazar alfa=0 no demuestra que el CAPM sea verdadero. Un alfa positivo no basta para hablar de rentabilidad anormal y no implica arbitraje. Una beta no significativa no demuestra ausencia de riesgo. Se contrastan varios coeficientes al 5 % nominal sin ajuste de multiplicidad; la evidencia es exploratoria y limitada por el tamaño muestral.

## Cartera y FF3

R_p,t = suma(w_i*R_i,t) con pesos estrictamente positivos configurados. Pesos constantes cada mes implican rebalanceo mensual, no buy-and-hold. La cartera se define en USD; el descriptivo EUR aplica la misma regla de pesos a las rentabilidades EUR y refleja diferencias de fecha FX de cada mercado. No se incluyen costes de rebalanceo ni impuestos.

R_p-RF = alfa + beta_m*(Mkt-RF) + beta_s*SMB + beta_h*HML + error. Las exposiciones son coeficientes estadísticos, no pesos invertidos. Se compara CAPM y FF3 de cartera en exactamente los mismos meses de la muestra efectiva. Se distingue R² de R² ajustado, sin atribuir causalidad ni asumir que añadir factores aporta una explicación económica suficiente.


## Frescura aproximada del cierre mensual

Se exige que la última fecha válida de cada mes esté dentro de max_month_end_age_days días naturales del fin de mes (siete por defecto). El margen detecta series truncadas y admite fines de semana y festivos. Para confirmar que un cierre corresponde al último día negociado habría que consultar el calendario de cada bolsa. Se conserva la fecha efectiva, no se rellena un precio ni se usa información futura. El mismo control se aplica a descargas y snapshots.
