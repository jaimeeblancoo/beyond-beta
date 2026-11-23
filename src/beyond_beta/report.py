"""Documentos de una ejecución validada; nunca modifica documentación manual."""
from fractions import Fraction
from pathlib import Path
import pandas as pd
from scipy.stats import f as fisher_f
from .config import hac_lags
from .latex import write_report, write_markdown_document
from .provenance import validate_analysis, record_report, artifact_hashes, write_json

MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']


def pct(value):
    return f'{value * 100:.2f} %'.replace('.', ',')


def num(value, digits=4):
    return f'{value:.{digits}f}'.replace('.', ',')


def coef(term, value):
    return pct(value) if term == 'alpha' else num(value)


def pval(value):
    return '<0,0001' if value < .0001 else num(value)


def period_label(value):
    period = pd.Period(value, freq='M')
    return f'{MONTHS[period.month - 1]} de {period.year}'


def span(index):
    return f'{period_label(index[0])} a {period_label(index[-1])}'


def weight_label(value):
    rational = Fraction(float(value)).limit_denominator(10000)
    return f'{rational.numerator}/{rational.denominator} ({value * 100:.4f} %)'


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |',
                      *['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]])


def build_documents(config, run):
    """Construye contenido sin compilar: también permite verificar variantes de muestra."""
    root = config['root']; folder = root / 'reports/tables'
    stats = pd.read_csv(folder / 'descriptive_usd.csv', index_col=0)
    eur = pd.read_csv(folder / 'descriptive_eur.csv', index_col=0)
    returns = pd.read_csv(folder / 'returns_usd.csv', index_col=0)
    returns.index = pd.PeriodIndex(returns.index, freq='M')
    capm = pd.read_csv(folder / 'capm.csv'); ff = pd.read_csv(folder / 'ff3.csv')
    comparison = pd.read_csv(folder / 'comparison.csv')
    ols = capm[capm.inference == config['inference']['primary']]
    alpha = ols[ols.term == 'alpha'].set_index('asset'); beta = ols[ols.term == 'Mkt-RF'].set_index('asset')
    hac_alpha = capm[(capm.inference == 'HAC') & (capm.term == 'alpha')].set_index('asset')
    ff_ols = ff[ff.inference == 'OLS']; ff_hac = ff[ff.inference == 'HAC']
    assets = config['assets']; sample = config['sample']; n = len(assets['names']); count = len(returns)
    price_index = pd.period_range(sample['price_start'], sample['price_end'], freq='M')
    if list(returns.columns) != assets['names'] + ['Cartera'] or count != sample['expected_returns'] or not (capm.n_obs == count).all() or not (ff.n_obs == count).all():
        raise ValueError('Las tablas no corresponden al universo o muestra configurados')
    equal = max(assets['weights']) - min(assets['weights']) < 1e-12
    portfolio_label = 'equiponderada' if equal else 'con ponderaciones configuradas'
    sample_text = f'{len(price_index)} precios ({span(price_index)}) y {count} rentabilidades mensuales ({span(returns.index)})'
    subtitle = span(returns.index) + ' | ' + sample['currency']
    strategy = f'La cartera es {portfolio_label}. Al comienzo de cada mes se restablecen los pesos, todos positivos y con suma de uno. El cálculo omite costes de rebalanceo e impuestos.'
    blocks = []
    def heading(text): blocks.append(('heading', text))
    def paragraph(text): blocks.append(('paragraph', text))
    def table(headers, rows, widths, key, title): blocks.append(('table', (headers, rows, widths, key, title)))
    def latex(text): blocks.append(('latex', text))
    def figure(name, caption, width=490): blocks.append(('figure', (name, caption, width)))
    def page(): blocks.append(('page', None))
    weights_rows = [[name, ticker, currency, weight_label(weight)] for name, ticker, currency, weight in zip(assets['names'], assets['tickers'], assets['currencies'], assets['weights'])]
    p = stats.loc['Cartera']
    heading('Análisis histórico con CAPM y Fama–French')
    paragraph(f'Comparamos la rentabilidad y el riesgo de {n} activos. El análisis pregunta qué proporción de la variación de sus excesos de rentabilidad mensual explica el mercado estadounidense y si añadir tamaño y valor mejora el ajuste para la cartera. La muestra contiene {sample_text}. Las regresiones se estiman en {sample["currency"]} y las estadísticas descriptivas también se presentan en EUR.')

    paragraph(f'La cartera acumuló un {pct(p.cumulative_return)}. Su rentabilidad geométrica anualizada fue del {pct(p.geometric_annual_return)} y su volatilidad anualizada, del {pct(p.vol_annual)}. La mayor caída entre cierres mensuales fue del {pct(abs(p.max_drawdown_monthly))} desde un máximo previo.')

    paragraph(f'En la cartera, R² pasa de {num(comparison.iloc[0].r_squared)} a {num(comparison.iloc[1].r_squared)}, mientras R² ajustado pasa de {num(comparison.iloc[0].adj_r_squared)} a {num(comparison.iloc[1].adj_r_squared)}. El incremento de ajuste bruto es pequeño frente a los dos regresores adicionales.')
    page(); heading('Datos y decisión de moneda')
    if assets['tickers'] == ['ACS.MC', 'PPFB.DE', 'NKE', 'RBLX', 'EUNH.DE', 'IUSQ.DE']:
        paragraph('La selección ilustrativa combina tres acciones individuales con oro físico, bonos soberanos de la zona euro y renta variable mundial. El enunciado plantea cuatro series y el registro del proyecto recoge la aprobación docente para ampliarlas a seis. El conjunto permite contrastar exposiciones distintas. Su carácter ilustrativo limita la generalización de los resultados.')
    paragraph('PPFB es iShares Physical Gold ETC, ISIN IE00B4ND3602. EUNH es iShares Core € Govt Bond UCITS ETF EUR (Dist), ISIN IE00B4WXJJ64. IUSQ es iShares MSCI All Country World UCITS ETF USD (Acc), ISIN IE00B6R52259. En los gráficos se utilizan los alias Oro PPFB, Bonos euro y Bolsa mundial. Las fichas de BlackRock/iShares se identifican en las referencias.')
    table(['Activo','Ticker','Cotización','Peso'], [row[:-1] + [row[-1].replace('.', ',')] for row in weights_rows], [125,90,75,200], 'universe', 'Instrumentos y pesos de la cartera')
    paragraph(strategy)
    weight_constraint = rf'w_i=1/{n}' if equal else rf'\sum_{{i=1}}^{{{n}}} w_i=1'
    latex(rf'\[R_{{p,t}}=\sum_{{i=1}}^{{{n}}} w_i R_{{i,t}},\qquad {weight_constraint}.\]')
    paragraph(sample_text + '. Se emplea una copia fija de los datos. El precio mensual corresponde al último cierre ajustado disponible del mes. El cierre ajustado aproxima la rentabilidad total antes de impuestos y está sujeto a revisiones del proveedor.')
    paragraph('Los cierres se toman cerca del fin de mes. Cada conversión utiliza el EUR/USD de la fecha del cierre o el último disponible anterior. Los límites de antigüedad y las fechas efectivas se documentan en los materiales de reproducción.')
    paragraph('EUR/USD se expresa como USD por EUR. Los activos cotizados en EUR se convierten a USD multiplicando por el cambio; los cotizados en USD permanecen en su moneda. Para los descriptivos EUR se realiza la conversión inversa. Las rentabilidades se calculan sobre precios expresados en la moneda de análisis.')
    factor_file = Path(config['factors']['file']).name
    factor_source = config['factors']['source'].replace('Copia del profesor, base', 'copia facilitada por el docente con cabecera')
    paragraph(f'Los factores estadounidenses proceden de {factor_file} ({factor_source}), de la biblioteca de Kenneth R. French. Las series mensuales, incluido el tipo libre de riesgo RF, se expresan en tanto por uno y se alinean con los retornos de los activos. La referencia en USD recoge parcialmente los riesgos de Europa, bolsa mundial, oro y bonos.')
    currency_text='Cotizar en EUR no implica que los subyacentes sean europeos ni que exista cobertura EUR. '
    if 'IUSQ.DE' in assets['tickers']:currency_text+='IUSQ es una clase USD acumulativa con cotización Xetra EUR. '
    if 'EUNH.DE' in assets['tickers']:currency_text+='EUNH representa deuda pública de la zona euro y no se considera libre de riesgo. '
    paragraph(currency_text+'La alternativa de un análisis principal EUR exigiría rediseñar mercado, factores y RF; los factores regionales de Kenneth French también se publican en USD. Un Treasury USD sin cobertura contiene riesgo de cambio al convertirlo a EUR.')
    latex(r'El CAPM se toma como referencia de mercado \cite{sharpe}. FF3 añade tamaño y valor \cite{ff,factors}. En las ecuaciones, $R_{i,t}$ es el retorno simple mensual, $RF_t$ el tipo libre de riesgo mensual y $(Mkt-RF)_t$ la prima de mercado. Los precios proceden de Yahoo Finance \cite{yahoo}.')
    page(); heading('Resultados descriptivos')
    table(['Activo','Acumulada','Geom anual','Media mes','Vol anual','Máx caída'], [[name,pct(r.cumulative_return),pct(r.geometric_annual_return),pct(r.mean_monthly),pct(r.vol_annual),pct(r.max_drawdown_monthly)] for name,r in stats.iterrows()], [105,77,77,77,77,77], 'descriptive-usd', 'Rentabilidad y riesgo en USD')
    paragraph('Cifras en USD. La media mensual es aritmética, mientras que la rentabilidad anualizada geométrica incorpora capitalización. La volatilidad usa desviación típica muestral y raíz de 12. La máxima caída incluye la riqueza inicial y solo observa cierres mensuales, por lo que puede ocultar caídas intrames.')
    paragraph(f'ACS acumuló {pct(stats.loc["ACS","cumulative_return"])} frente a {pct(stats.loc["Nike","cumulative_return"])} de Nike. La escala lineal conserva esa diferencia de riqueza y comprime las series próximas a 100. Roblox combina una media mensual positiva con crecimiento geométrico negativo, por el efecto de encadenar fuertes subidas y pérdidas.') if {'ACS','Nike','Roblox'}.issubset(stats.index) else None
    latex(r'La figura~\ref{fig:wealth} permite comparar las trayectorias de riqueza desde una inversión inicial común.')
    figure('wealth_usd.png', f'Riqueza con base 100 en {period_label(price_index[0])}. Cartera rebalanceada mensualmente.')
    page(); heading('Diversificación y contraste en euros')
    corr = returns.corr()
    if {'Oro PPFB','Bolsa mundial','Bonos euro'}.issubset(corr.index):
        gold_corr = corr.loc['Oro PPFB', 'Bolsa mundial']
        bonds_corr = corr.loc['Bonos euro', 'Bolsa mundial']
        latex(rf'En la figura~\ref{{fig:correlations}}, la correlación de Bolsa mundial con Oro PPFB es {num(gold_corr)} y con Bonos euro, {num(bonds_corr)}.')
        if gold_corr < bonds_corr:
            paragraph('En esta muestra, el oro se movió menos en sintonía con la bolsa mundial que los bonos soberanos de la zona euro. Esa menor correlación favorece la diversificación frente al riesgo bursátil. El efecto sobre el riesgo total también depende de los pesos y las volatilidades.')
    else:
        latex(r'La figura~\ref{fig:correlations} muestra en qué medida los activos tienden a moverse juntos. La diversificación depende de estas relaciones, de los pesos y de las volatilidades.')
    if equal:
        paragraph('Los pesos iguales en capital no implican contribuciones iguales al riesgo.')
    figure('correlations_usd.png', f'Correlaciones de Pearson en los {count} meses comunes, en USD.', 410)
    paragraph('Cada activo forma parte de la cartera, por lo que su propia rentabilidad contribuye a la correlación que observamos entre ambos. Las correlaciones pueden cambiar fuera de la muestra. Incluso los activos poco ligados a la bolsa están expuestos a riesgos como los tipos de interés, el crédito, las materias primas o la divisa.')
    table(['Activo','Geom anual EUR','Vol anual EUR','Acumulada EUR'], [[name,pct(r.geometric_annual_return),pct(r.vol_annual),pct(r.cumulative_return)] for name,r in eur.iterrows()], [150,115,110,115], 'descriptive-eur', 'Rentabilidad y riesgo en EUR')
    paragraph('Para el cálculo en euros aplicamos los mismos pesos a las rentabilidades en EUR. Cada activo conserva su fecha efectiva de cierre. Las regresiones se estiman en USD.')
    paragraph(f'La volatilidad anualizada de Bonos euro es {pct(stats.loc["Bonos euro","vol_annual"])} en USD y {pct(eur.loc["Bonos euro","vol_annual"])} en EUR. La diferencia muestra que la moneda influye en el riesgo observado, sin aislar una contribución causal del cambio.') if 'Bonos euro' in stats.index else None
    page(); heading('CAPM por activo')
    paragraph('En el CAPM teórico, la beta mide la exposición al riesgo de mercado y determina la prima de rentabilidad esperada del activo.')
    latex(r'\[E(R_i)=R_f+\beta_i[E(R_M)-R_f].\]')
    paragraph(f'En la aplicación empírica se estima por mínimos cuadrados ordinarios (OLS) una regresión con intercepto sobre {count} excesos de rentabilidad mensuales comunes a los activos y a la cartera.')
    latex(r'\[R_{i,t}-R_{f,t}=\alpha_i+\beta_i(R_{M,t}-R_{f,t})+\varepsilon_{i,t}.\]')
    latex(r'El contraste \(H_0:\alpha_i=0\) evalúa si la rentabilidad media difiere de la indicada por la referencia CAPM. El contraste \(H_0:\beta_i=0\) evalúa la sensibilidad lineal al mercado. Ambos se realizan al 5 \% nominal. La significación de beta acredita sensibilidad al factor. Un alfa compatible con cero indica que los datos son compatibles con esa implicación del modelo. La validez general del CAPM requiere evidencia adicional. La inferencia convencional supone homocedasticidad y ausencia de autocorrelación.')
    latex(r'La tabla~\ref{tab:capm} resume la sensibilidad al mercado y el alfa mensual por activo y para la cartera.')
    table(['Activo','Alfa mes','p alfa','Beta','p beta','R²','R² ajustado'], [[name,pct(alpha.loc[name,'coefficient']),pval(alpha.loc[name,'p_value']),num(beta.loc[name,'coefficient']),pval(beta.loc[name,'p_value']),num(alpha.loc[name,'r_squared']),num(alpha.loc[name,'adj_r_squared'])] for name in stats.index], [105,69,63,63,63,63,64], 'capm', 'CAPM por activo y cartera (OLS)')
    positive = list(alpha.index[(alpha.p_value < .05) & (alpha.coefficient > 0)])
    negative = list(alpha.index[(alpha.p_value < .05) & (alpha.coefficient < 0)])
    for sign, names in [('positivo', positive), ('negativo', negative)]:
        if names:
            paragraph(f'Alfa {sign} y significativo al 5 % nominal con OLS en ' + ' y '.join(names) + '.')
    if not positive and not negative:
        paragraph('Ningún alfa CAPM resulta significativo al 5 % con OLS.')
    significant_betas = beta.loc[assets['names'], 'p_value'] < .05
    market_assets = significant_betas[significant_betas].index.tolist()
    if market_assets:
        paragraph('El contraste de beta detecta sensibilidad bursátil en '
                  + ', '.join(market_assets[:-1]) + (' y ' if len(market_assets) > 1 else '')
                  + market_assets[-1] + '.')
    if 'Bonos euro' in negative:
        paragraph('En Bonos euro, los tipos de interés y la duración de la deuda de la zona euro, la conversión '
                  'a USD y la elección de la referencia bursátil pueden contribuir a la desviación media. '
                  'La regresión estima esa desviación conjunta frente a la referencia utilizada.')
    lowest, highest = alpha.loc[assets['names'], 'r_squared'].agg(['idxmin', 'idxmax'])
    paragraph(f'Entre los activos, el R² va de {num(alpha.loc[lowest, "r_squared"])} en {lowest} a {num(alpha.loc[highest, "r_squared"])} en {highest}.')
    portfolio_beta = beta.loc['Cartera', 'coefficient']
    asset_betas = beta.loc[assets['names'], 'coefficient']
    weighted_beta = sum(weight * estimate for weight, estimate in zip(assets['weights'], asset_betas))
    paragraph(f'La beta de la cartera es {num(portfolio_beta)}. Un aumento de un punto porcentual en el exceso mensual del mercado se asocia con un cambio estimado de {num(portfolio_beta, 2)} puntos porcentuales en el exceso de la cartera.')
    highest_beta = asset_betas.idxmax()
    paragraph(f'{highest_beta} presenta la mayor beta entre los activos ({num(asset_betas.loc[highest_beta])}). La volatilidad resume el riesgo total observado. La beta mide sensibilidad al mercado y el R², la proporción de variación del exceso de rentabilidad que recoge el modelo. El residuo puede incluir riesgo específico y riesgos comunes omitidos. La diversificación tiende a reducir el componente específico.')
    if highest_beta == 'Roblox' and alpha.loc['Roblox', 'p_value'] >= .05:
        paragraph(f'En Roblox, el alfa es compatible con cero y el R² es {pct(alpha.loc["Roblox", "r_squared"])}. '
                  'La sensibilidad estimada al mercado convive con una proporción elevada de variación residual.')
    if 'Bolsa mundial' in beta.index and beta.loc['Bolsa mundial', 'p_value'] < .05 and alpha.loc['Bolsa mundial', 'p_value'] >= .05:
        paragraph(f'En IUSQ, la beta es significativa y el alfa mensual estimado es {pct(alpha.loc["Bolsa mundial", "coefficient"])} '
                  f'(p = {pval(alpha.loc["Bolsa mundial", "p_value"])}). El modelo explica el '
                  f'{pct(alpha.loc["Bolsa mundial", "r_squared"])} de la variación de su exceso de rentabilidad mensual. El alfa es compatible con cero al 5 %.')
    if 'Oro PPFB' in beta.index and beta.loc['Oro PPFB', 'p_value'] >= .05:
        paragraph(f'Para Oro PPFB, la beta estimada es {num(beta.loc["Oro PPFB", "coefficient"])} (p = {pval(beta.loc["Oro PPFB", "p_value"])}). La evidencia de sensibilidad lineal al mercado es insuficiente al 5 %. El oro sigue expuesto a riesgos propios de precio y divisa.')
    if 'Oro PPFB' in alpha.index and alpha.loc['Oro PPFB', 'p_value'] >= .05:
        paragraph(f'El alfa de Oro PPFB también es compatible con cero (p = {pval(alpha.loc["Oro PPFB", "p_value"])}).')
    latex(rf'\Needspace{{6\baselineskip}}\[\widehat\beta_p=\sum_{{i=1}}^{{{n}}}w_i\widehat\beta_i.\]')
    paragraph(f'Al ponderar las betas individuales se obtiene {num(weighted_beta)}, que coincide hasta el redondeo con la estimación directa de la cartera. La igualdad se deriva de la linealidad de OLS con pesos constantes que suman uno y regresiones con intercepto sobre los mismos meses, moneda, RF y factor de mercado.')
    page(); heading('SML estimada con medias históricas')
    latex(r'En la figura~\ref{fig:sml}, la distancia vertical entre cada punto y la recta mide el alfa de Jensen mensual respecto a la referencia utilizada.')
    figure('sml_usd.png', 'SML estimada con medias históricas mensuales en USD.')
    paragraph('Para cada beta, la recta suma la media de RF y la prima media de mercado multiplicada por esa beta. Los puntos muestran las rentabilidades medias observadas en los mismos meses y en USD. Los puntos rellenos señalan alfas significativos y los cuadrados, betas no significativas al 5 % con OLS.')
    paragraph('Las desviaciones respecto a la recta pueden reflejar exposiciones a riesgos que el modelo omite.')
    page(); heading('Rentabilidad y volatilidad')
    latex(r'La figura~\ref{fig:risk_return} permite evaluar si los activos más volátiles también obtuvieron mayor crecimiento anualizado.')
    figure('risk_return_usd.png', 'Volatilidad anualizada y rentabilidad anualizada geométrica en USD.')
    paragraph('La volatilidad mide la dispersión de las rentabilidades mensuales. El crecimiento depende de cómo se encadenan esas rentabilidades, de modo que una media mensual positiva puede coexistir con una pérdida acumulada. El gráfico es descriptivo. La SML relaciona rentabilidad esperada con beta, mientras que aquí se representa volatilidad total.')
    page(); heading('Cartera y Fama–French de tres factores')
    latex(r'En la tabla~\ref{tab:ff3}, el alfa, su error estándar y su intervalo se expresan en porcentaje mensual. Las exposiciones y sus errores e intervalos son adimensionales.')
    table(['Término','Estimación','Error est','t','p','IC95 inf','IC95 sup'], [[r.term,coef(r.term, r.coefficient),coef(r.term, r.std_error),num(r.t_stat),pval(r.p_value),coef(r.term, r.ci_low),coef(r.term, r.ci_high)] for _,r in ff_ols.iterrows()], [80,75,70,60,60,72,73], 'ff3', 'Coeficientes FF3 de la cartera (OLS)')
    paragraph('SMB mide la diferencia de rentabilidad entre carteras de empresas pequeñas y grandes. HML mide la diferencia entre carteras con un cociente valor contable sobre valor de mercado alto y bajo, respectivamente. Cada exposición mide la sensibilidad al factor manteniendo constantes los demás. Los pesos de capital se fijan al construir la cartera.')
    table(['Modelo','N','R²','R² ajustado','AIC','BIC'], [[r.model,str(int(r.n_obs)),num(r.r_squared),num(r.adj_r_squared),num(r.aic, 2),num(r.bic, 2)] for _,r in comparison.iterrows()], [90,50,80,100,85,85], 'comparison', 'Comparación CAPM y FF3')
    ff_terms = ff_ols.set_index('term')
    ff_market_beta = ff_terms.loc['Mkt-RF', 'coefficient']
    paragraph(f'La beta de mercado estimada pasa de {num(portfolio_beta)} en el CAPM a {num(ff_market_beta)} '
              'en FF3, donde se estima manteniendo constantes SMB y HML. La diferencia describe el cambio de especificación '
              'sobre la misma muestra.')
    smb, hml = ff_terms.loc['SMB'], ff_terms.loc['HML']
    if smb.coefficient > 0 and hml.coefficient < 0 and min(smb.p_value, hml.p_value) >= .05:
        paragraph('Los signos estimados apuntan a una exposición positiva al diferencial de pequeñas frente a grandes y negativa al diferencial de valor. Ambos intervalos de confianza incluyen cero, por lo que la evidencia individual al 5 % es insuficiente para atribuir a la cartera una orientación por tamaño o estilo.')
    paragraph(f'Los valores p de SMB ({pval(smb.p_value)}) y HML ({pval(hml.p_value)}) corresponden a contrastes individuales. La comparación utiliza las mismas observaciones en ambos modelos.')
    delta = comparison.iloc[1].adj_r_squared - comparison.iloc[0].adj_r_squared
    change = 'sube' if delta > 0 else 'baja' if delta < 0 else 'se mantiene'
    paragraph(f'Al añadir SMB y HML, el R² ajustado {change}: pasa de {num(comparison.iloc[0].adj_r_squared)} en el CAPM a {num(comparison.iloc[1].adj_r_squared)} en FF3. Esta medida penaliza el número de regresores y describe el ajuste dentro de la muestra.')
    residual_df = count - 4  # Intercepto y tres factores en el modelo completo.
    restricted_r2, full_r2 = comparison.r_squared
    joint_f = ((full_r2 - restricted_r2) / 2) / ((1 - full_r2) / residual_df)
    joint_p = fisher_f.sf(joint_f, 2, residual_df)
    joint_result = 'se rechaza' if joint_p < .05 else 'no se rechaza'
    latex(r'El contraste conjunto evalúa \(H_0:\beta_{\mathrm{SMB}}=\beta_{\mathrm{HML}}=0\).')
    paragraph(f'El contraste da F(2, {residual_df}) = {num(joint_f)} y p = {pval(joint_p)}. Al 5 %, {joint_result} la hipótesis nula bajo los supuestos de la inferencia OLS convencional.')
    differences = [name for name in stats.index if (alpha.loc[name,'p_value'] < .05) != (hac_alpha.loc[name,'p_value'] < .05)]
    hac_summary = 'HAC cambia la clasificación nominal del alfa para ' + ', '.join(differences) + '.' if differences else 'HAC mantiene la clasificación nominal de los alfas CAPM al 5 %.'
    latex(r'La sensibilidad Newey–West \cite{nw} se recoge en las tablas~\ref{tab:hac-capm} y~\ref{tab:hac-ff3}.')
    paragraph(f'La estimación HAC usa {hac_lags(count)} retardos. {hac_summary}')
    if 'ACS' in alpha.index:
        paragraph(f'En ACS, el valor p pasa de {pval(alpha.loc["ACS","p_value"])} a {pval(hac_alpha.loc["ACS","p_value"])} y queda cerca del umbral. La muestra y la multiplicidad de contrastes limitan la inferencia.')
    page(); heading('Sensibilidad de la inferencia')
    paragraph(f'Los residuos mensuales pueden presentar heterocedasticidad o dependencia temporal. Como comprobación, se estima la covarianza HAC con ponderaciones de Bartlett y {hac_lags(count)} retardos. La corrección afecta a errores estándar, valores p e intervalos. Con {count} meses, la inferencia robusta sigue siendo aproximada y el contraste conjunto anterior conserva su alcance convencional.')
    table(['CAPM','p alfa OLS','p alfa HAC','IC95 HAC inf','IC95 HAC sup'], [[name,pval(alpha.loc[name,'p_value']),pval(hac_alpha.loc[name,'p_value']),pct(hac_alpha.loc[name,'ci_low']),pct(hac_alpha.loc[name,'ci_high'])] for name in stats.index], [130,80,80,100,100], 'hac-capm', 'Sensibilidad de los alfas CAPM (HAC)')
    paragraph('En FF3, el error estándar y el intervalo del alfa se expresan en porcentaje mensual.')
    table(['FF3 término','Error HAC','t HAC','p HAC','IC95 inferior','IC95 superior'], [[r.term,coef(r.term, r.std_error),num(r.t_stat),pval(r.p_value),coef(r.term, r.ci_low),coef(r.term, r.ci_high)] for _,r in ff_hac.iterrows()], [90,80,70,70,90,90], 'hac-ff3', 'Inferencia HAC de la cartera FF3')
    page(); heading('Anexo de coeficientes CAPM')
    paragraph('El porcentaje mensual facilita la comparación de los alfas, sus errores estándar e intervalos con las tablas del cuerpo. Las betas y su incertidumbre se expresan en unidades adimensionales.')
    table(['Activo y término','Coeficiente','Error est','t','p','IC95 inf','IC95 sup'], [[r.asset+' '+r.term,coef(r.term, r.coefficient),coef(r.term, r.std_error),num(r.t_stat),pval(r.p_value),coef(r.term, r.ci_low),coef(r.term, r.ci_high)] for _,r in ols.iterrows()], [128,65,65,52,52,64,64], 'capm-full', 'Coeficientes CAPM completos (OLS)')
    paragraph(f'Se estiman {n+1} CAPM y un FF3, todos con intercepto y {count} meses. Los errores y resultados HAC completos se conservan en CSV y Excel.')
    latex(r'La figura~\ref{fig:capm_scatter} muestra la dispersión de los excesos mensuales alrededor de cada recta estimada. El eje horizontal es común y la escala vertical varía entre paneles.')
    figure('capm_scatter_usd.png', 'Regresiones temporales del CAPM por activo.')
    page(); heading('Limitaciones y conclusiones')
    paragraph(
        f'La prima de mercado de EE. UU. tiene una capacidad explicativa distinta según el activo. '
        f'El CAPM recoge el {pct(alpha.loc[highest, "r_squared"])} de la variación mensual del exceso '
        f'de rentabilidad de {highest} y el {pct(alpha.loc[lowest, "r_squared"])} en {lowest}.'
    )
    if highest == 'Bolsa mundial' and lowest == 'Oro PPFB':
        paragraph(
            'El ajuste de IUSQ es coherente con que la renta variable mundial y la estadounidense '
            'compartan movimientos bursátiles. En el oro queda casi toda la variación por explicar. '
            'Los tipos reales y el dólar son canales plausibles, aunque estas regresiones solo estiman '
            'la relación con la prima bursátil.'
        )
    portfolio_p = alpha.loc['Cartera', 'p_value']
    ff_p = ff_terms.loc['alpha', 'p_value']
    alpha_summary = (
        'Ambas estimaciones son compatibles con un alfa nulo al 5 %.'
        if min(portfolio_p, ff_p) >= .05 else
        'Los valores p corresponden a contrastes individuales de cada alfa frente a cero.'
    )
    paragraph(
        f'La beta de la cartera es {num(portfolio_beta)}. Un aumento de un punto porcentual en la prima mensual '
        f'de mercado se asocia con un cambio estimado de {num(portfolio_beta, 2)} puntos porcentuales en el exceso '
        f'de rentabilidad de la cartera. El alfa mensual es {pct(alpha.loc["Cartera", "coefficient"])} con CAPM '
        f'(p = {pval(portfolio_p)}) y {pct(ff_terms.loc["alpha", "coefficient"])} con FF3 (p = {pval(ff_p)}). '
        f'{alpha_summary}'
    )
    capm_preferred = (comparison.iloc[0][['aic', 'bic']] < comparison.iloc[1][['aic', 'bic']]).all()
    criteria_summary = 'AIC y BIC también favorecen el CAPM.' if capm_preferred else ''
    model_summary = (
        'Para describir esta cartera en la muestra, la evidencia favorece el CAPM como especificación más sencilla.'
        if delta < 0 and capm_preferred and joint_p >= .05 else ''
    )
    paragraph(' '.join(filter(None, [
        f'Al incorporar tamaño y valor, el R² bruto pasa de {num(restricted_r2)} a {num(full_r2)} y el ajustado '
        f'pasa de {num(comparison.iloc[0].adj_r_squared)} a {num(comparison.iloc[1].adj_r_squared)}.',
        criteria_summary,
        f'Con p = {pval(joint_p)}, al 5 % {joint_result} que ambos coeficientes sean cero bajo los supuestos de OLS convencional.',
        model_summary,
    ])))
    paragraph(
        f'Las conclusiones corresponden a {count} meses y a una referencia bursátil estadounidense, '
        'que recoge de forma parcial los riesgos de tipos, divisas y materias primas. Los precios pueden '
        'revisarse y los cierres de los activos y del mercado de divisas ocurren a horas distintas.'
    )
    heading('Disponibilidad de datos y reproducibilidad')
    paragraph('El código de Python genera las estimaciones y las figuras. El libro complementario contiene los datos mensuales, los pesos, las fórmulas de conversión y rentabilidad, y los resultados de las regresiones exportados como valores. Una modificación de las entradas requiere volver a ejecutar el análisis en Python para actualizar las estimaciones y el informe.')
    latex(r'En el repositorio del trabajo se incluyen el código, el libro en \texttt{reports/} y las tablas en \texttt{reports/tables/}. La \href{https://github.com/jaimeeblancoo/beyond-beta/blob/main/docs/reviewer_guide.md}{guía de reproducción} distingue el recálculo desde los datos mensuales entregados (\texttt{python scripts/verify\_delivery.py}) de la regeneración a partir de las fuentes diarias y la copia original de factores, de custodia local.')
    heading('Referencias y fuentes')
    latex(r"""\begin{thebibliography}{9}
\bibitem{sharpe} Sharpe, W. F. (1964). Capital asset prices: A theory of market equilibrium under conditions of risk. \textit{The Journal of Finance}, 19(3), 425--442. \href{https://doi.org/10.1111/j.1540-6261.1964.tb02865.x}{DOI}.
\bibitem{ff} Fama, E. F., y French, K. R. (1993). Common risk factors in the returns on stocks and bonds. \textit{Journal of Financial Economics}, 33(1), 3--56. \href{https://doi.org/10.1016/0304-405X(93)90023-5}{DOI}.
\bibitem{nw} Newey, W. K., y West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. \textit{Econometrica}, 55(3), 703--708. \href{https://doi.org/10.2307/1913610}{DOI}.
\bibitem{factors} French, K. R. (2026). \textit{Description of Fama/French factors}. Data Library. Copia mensual CRSP 202609. \href{https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html}{Biblioteca de datos}.
\bibitem{yahoo} Yahoo Finance (2026). \textit{Historical data}. Series ACS.MC, PPFB.DE, NKE, RBLX, EUNH.DE, IUSQ.DE y EURUSD=X, obtenidas mediante yfinance. \href{https://finance.yahoo.com/}{Históricos}. \href{https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html}{Documentación de yfinance}.
\bibitem{ishares} BlackRock/iShares (2026). \textit{Fichas de productos}. iShares Physical Gold ETC, ISIN IE00B4ND3602, \href{https://www.ishares.com/gls-download/literature/fact-sheet/sgln-ishares-physical-gold-etc-fund-fact-sheet-en-de.pdf}{ficha PPFB}. iShares Core Euro Government Bond UCITS ETF, ISIN IE00B4WXJJ64: \href{https://www.ishares.com/gls-download/literature/fact-sheet/iega-ishares-core-govt-bond-ucits-etf-fund-fact-sheet-en-de.pdf}{Ficha EUNH}. iShares MSCI All Country World UCITS ETF, ISIN IE00B6R52259: \href{https://www.ishares.com/uk/individual/en/products/251850/ishares-msci-acwi-ucits-etf}{Ficha IUSQ}.
\end{thebibliography}""")
    summary = '# Parámetros y resultados de esta ejecución\n\n' + sample_text + '.\n\n' + strategy + '\n\n'
    summary += markdown_table(['Activo','Ticker','Divisa','Peso'], weights_rows)
    summary += f'\n\nInferencia principal OLS; sensibilidad HAC con {hac_lags(count)} retardos. Ejecución {run["run_id"]}.\n\n'
    methodology = (root / 'docs/methodology.md').read_text(encoding='utf-8') + '\n\n' + summary
    # Keep risk/return with descriptive evidence before the model estimates.
    start = next(i for i, item in enumerate(blocks) if item == ('heading', 'Rentabilidad y volatilidad'))
    end = next(i for i in range(start + 1, len(blocks)) if blocks[i][0] == 'heading')
    risk_blocks = blocks[start:end]
    del blocks[start:end]
    position = next(i for i, item in enumerate(blocks) if item == ('heading', 'Diversificación y contraste en euros'))
    blocks[position:position] = risk_blocks
    return blocks, subtitle, methodology


def generate_report(config, compile_pdf=True):
    run = validate_analysis(config); root = config['root']; directory = root / 'reports/report'
    directory.mkdir(parents=True, exist_ok=True)
    inputs = ['src/beyond_beta/report.py','src/beyond_beta/latex.py','templates/latex/preamble.tex','docs/methodology.md','docs/sources.md']
    before = artifact_hashes(root, inputs)
    blocks, subtitle, methodology = build_documents(config, run)
    run['stage']='report_building'
    write_json(root/'reports/run_manifest.json',run)
    if not compile_pdf:
        for name in ['informe','metodologia']:
            pdf=directory/f'{name}.pdf'
            if pdf.exists():
                archive=directory/'archive'/run['run_id'];archive.mkdir(parents=True,exist_ok=True)
                destination=archive/pdf.name
                if destination.exists():
                    from uuid import uuid4
                    destination=archive/f'{name}_{uuid4().hex}.pdf'
                pdf.replace(destination)
    for name, content in [('metodologia',methodology)]:
        (directory / f'{name}.md').write_text(content, encoding='utf-8')
    write_report(root, blocks, directory, subtitle, compile_pdf=compile_pdf)
    for name, title in [('metodologia','Metodología del análisis')]:
        write_markdown_document(root, directory / f'{name}.md', directory / f'{name}.tex', title, compile_pdf=compile_pdf)
    if before != artifact_hashes(root, inputs):
        raise ValueError('Una fuente del informe cambió durante su generación')
    outputs = [f'reports/report/{name}.{extension}' for name in ['informe','metodologia'] for extension in (['tex','pdf'] if compile_pdf else ['tex'])]
    outputs += ['reports/report/metodologia.md']
    run['report_pdf_compiled'] = compile_pdf
    record_report(config, run, inputs, outputs)
    print('Documentos LaTeX generados; PDF ' + ('compilados' if compile_pdf else 'no solicitados'), flush=True)
    return directory / ('informe.pdf' if compile_pdf else 'informe.tex')
