# Beyond Beta

**El CAPM y los modelos multifactoriales en la práctica**  
Inversiones Financieras · CUNEF Universidad · Curso 2026–2027

**Autores** — Alonso Castro Freibott, Pablo Caonabo Crespo de la Cruz, Carlos Segovia Domínguez y Jaime Blanco González.  
**Profesor** — Javier Fernández Sánchez de la Viña.

Estudiamos cuánto explica el mercado estadounidense de la rentabilidad de seis activos y si los factores de tamaño y valor mejoran el ajuste para una cartera equiponderada. Utilizamos 61 cierres ajustados mensuales de septiembre de 2021 a septiembre de 2026 y 60 rentabilidades de octubre de 2021 a septiembre de 2026. Las regresiones están en USD y los descriptivos se calculan también en EUR.

| Activo | Ticker | Cotización |
| --- | --- | --- |
| ACS | ACS.MC | EUR |
| iShares Physical Gold ETC | PPFB.DE | EUR |
| Nike | NKE | USD |
| Roblox | RBLX | USD |
| iShares Core € Govt Bond UCITS ETF | EUNH.DE | EUR |
| iShares MSCI ACWI UCITS ETF | IUSQ.DE | EUR |

## Resultados

La cartera acumula **42,30 %** en USD. Registra **7,31 %** de rentabilidad geométrica anual, **17,91 %** de volatilidad anualizada y una caída máxima del **31,88 %** entre cierres mensuales. Su beta CAPM es **0,7888**. El R² ajustado pasa de **0,4882** en CAPM a **0,4848** en FF3. El contraste conjunto de SMB y HML da **p = 0,4500** con OLS. El alfa de la cartera es compatible con cero en ambos modelos al 5 % nominal.

| Material | Ruta |
| --- | --- |
| Informe académico | [PDF](reports/report/informe.pdf) · [Fuente LaTeX](reports/report/informe.tex) · [Compilación](docs/report_format.md) |
| Presentación de la edición pública | [PDF](reports/presentation/Presentacion_Beyond_Beta.pdf) · [Fuente Beamer](reports/presentation/Presentacion_Beyond_Beta.tex) · [Compilación](docs/presentation.md) |
| Coeficientes e inferencia OLS y HAC | [CAPM](reports/tables/capm.csv) · [FF3](reports/tables/ff3.csv) |
| Comparación de modelos | [R², R² ajustado, AIC y BIC](reports/tables/comparison.csv) |
| Resultados descriptivos | [USD](reports/tables/descriptive_usd.csv) · [EUR](reports/tables/descriptive_eur.csv) · [Correlaciones](reports/tables/correlations.csv) |
| Método y código | [Metodología](docs/methodology.md) · [Código Python](src/beyond_beta/) · [Fuentes](docs/sources.md) · [Guía de verificación](docs/reviewer_guide.md) |

Alineamos cierres ajustados mensuales, tipos de cambio y factores, calculamos las rentabilidades y estimamos ambas regresiones sobre los mismos 60 meses. La cartera se rebalancea cada mes, con peso 1/6 por activo y sin costes ni impuestos.

La entrega académica utiliza el mismo informe enlazado arriba. Su Excel adjunto contiene las observaciones mensuales, las conversiones de divisa, las fórmulas de rentabilidad y los resultados de las regresiones exportados por Python. Aquí se pueden abrir y compilar los documentos con sus figuras agregadas, revisar el código y ejecutar pruebas con datos sintéticos. El recálculo histórico requiere el libro y las tablas mensuales privadas. Reconstruir el análisis completo requiere además los cierres diarios, los tipos de cambio y la copia de factores utilizada.

## Verificar el código

Instala Python 3.12 y ejecuta desde la raíz en Windows PowerShell.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

En Linux o macOS, usa `python3.12 -m venv .venv` y `.venv/bin/python`. Las pruebas crean sus propias series sintéticas y cubren el flujo desde los datos hasta la exportación y el recálculo. La instalación requiere conexión. Las pruebas se ejecutan sin acceder a proveedores de datos.

Las conclusiones corresponden a una muestra histórica. Las condiciones de autoría y reutilización se recogen en [RIGHTS.md](RIGHTS.md).
