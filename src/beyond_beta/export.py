"""Excel de revisión; las estimaciones se calculan en Python y se exportan como valores."""
import json
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties

def write_workbook(config, frames, factors, combined, portfolio_eur, tables):
    root=config['root']; output=root/'reports/Resultados_Beyond_Beta.xlsx'; output.parent.mkdir(exist_ok=True)
    weights=pd.DataFrame({'Activo':config['assets']['names'],'Ticker':config['assets']['tickers'],
                          'Divisa original':config['assets']['currencies'],'Peso':config['assets']['weights']})
    def dated(df):
        df=df.copy()
        if isinstance(df.index,pd.PeriodIndex):df.index=df.index.to_timestamp(how='end').normalize();df.index.name='Mes'
        return df
    with pd.ExcelWriter(output,engine='openpyxl',datetime_format='DD/MM/YYYY') as writer:
        for key,sheet in [('descriptive_usd','Descriptivos_USD'),('descriptive_eur','Descriptivos_EUR'),('capm','CAPM'),('ff3','FF3_cartera'),('comparison','Comparacion_modelos'),('correlations','Correlaciones_USD')]:
            tables[key].to_excel(writer,sheet_name=sheet,index=key.startswith('descriptive') or key=='correlations')
        for key,sheet in [('prices_original','Precios_originales'),('prices_usd','Precios_USD'),('prices_eur','Precios_EUR'),('returns_usd','Rentabilidades_USD'),('returns_eur','Rentabilidades_EUR')]:
            dated(frames[key]).to_excel(writer,sheet_name=sheet)
        dated(factors).to_excel(writer,sheet_name='Factores_USD')
        frames['observations'].to_excel(writer,sheet_name='Fechas_y_FX',index=False)
        weights.to_excel(writer,sheet_name='Pesos',index=False)
        manifest=json.loads((root/'data/raw/manifest.json').read_text(encoding='utf-8'))
        source_rows=[{'ticker':t,**manifest[t]} for t in config['assets']['tickers']+['EURUSD=X']]
        source_rows.append({'ticker':'FF3','name':config['factors']['source'],'url':config['factors']['url'],'sha256':config['factors']['sha256'],'field':'Mensual; porcentajes divididos por 100'})
        pd.DataFrame(source_rows).to_excel(writer,sheet_name='Fuentes',index=False)
        # Native formulas make FX, returns, and portfolio weights reviewable.
        n=len(config['assets']['names']); count=len(frames['prices_usd'])
        for j,currency in enumerate(config['assets']['currencies']):
            col=get_column_letter(j+2)
            for i in range(count):
                row=i+2; obsrow=j*count+i+2
                for target in ['USD','EUR']:
                    original=f"'Precios_originales'!{col}{row}"; fx=f"'Fechas_y_FX'!G{obsrow}"
                    formula=f'={original}' if currency==target else f'={original}{"*" if target=="USD" else "/"}{fx}'
                    writer.book[f'Precios_{target}'].cell(row,j+2,formula)
                for target in ['USD','EUR']:
                    if i>0:
                        writer.book[f'Rentabilidades_{target}'].cell(i+1,j+2,f"='Precios_{target}'!{col}{row}/'Precios_{target}'!{col}{row-1}-1")
        for target in ['USD','EUR']:
            sheet=writer.book[f'Rentabilidades_{target}'];sheet.cell(1,n+2,'Cartera')
            for i in range(len(frames[f'returns_{target.lower()}'])):
                row=i+2;terms=[f"{get_column_letter(j+2)}{row}*'Pesos'!$D${j+2}" for j in range(n)]
                sheet.cell(row,n+2,'='+ '+'.join(terms))
        for sheet in writer.book.worksheets:
            sheet.sheet_view.showGridLines=False;sheet.freeze_panes='B2';sheet.auto_filter.ref=sheet.dimensions
            for cell in sheet[1]:
                cell.fill=PatternFill('solid',fgColor='243B53');cell.font=Font(name='Calibri',size=11,color='FFFFFF',bold=True);cell.alignment=Alignment(horizontal='center')
            sheet.row_dimensions[1].height=30
            for row in sheet.iter_rows(min_row=2):
                for cell in row:
                    cell.font=Font(name='Calibri',size=11,color='111111')
                    if isinstance(cell.value,(pd.Timestamp,__import__('datetime').datetime)):cell.number_format='dd/mm/yyyy'
                    elif cell.data_type=='f' or isinstance(cell.value,(int,float)):
                        cell.number_format='0.0000'
                    if cell.data_type=='f':cell.font=Font(name='Calibri',size=11,color='008000')
                    if sheet.title.startswith('Rentabilidades') and cell.column>1:cell.number_format='0.00%;(0.00%);0.00%'
                    if sheet.title.startswith('Descriptivos') and cell.column>1:cell.number_format='0.00%;(0.00%);0.00%'
            for column in sheet.columns:
                width=max(len(str(cell.value or '')) if cell.data_type!='f' else 16 for cell in column)
                sheet.column_dimensions[column[0].column_letter].width=min(65,max(18,width+2))
            if sheet.title=='Fechas_y_FX':sheet.column_dimensions['G'].width=20
        labels={'cumulative_return':'Acumulada','geometric_annual_return':'Geométrica anual','mean_monthly':'Media mensual',
          'vol_monthly':'Volatilidad mensual','vol_annual':'Volatilidad anual','max_drawdown_monthly':'Máxima caída mensual',
          'asset':'Activo','term':'Término','inference':'Inferencia','coefficient':'Coeficiente','std_error':'Error estándar',
          't_stat':'Estadístico t','p_value':'Valor p','ci_low':'IC95 inferior','ci_high':'IC95 superior',
          'r_squared':'R²','adj_r_squared':'R² ajustado','n_obs':'N meses','hac_lags':'Retardos HAC',
          'model':'Modelo','month':'Mes','currency':'Divisa','price_date':'Fecha precio','fx_date':'Fecha FX',
          'fx_age_days':'Antigüedad FX días','USD_per_EUR':'USD por EUR','name':'Nombre','downloaded_at':'Descarga UTC',
          'provider':'Proveedor','url':'URL','field':'Campo','sha256':'SHA256','daily_start':'Inicio diario','daily_end':'Fin diario'}
        for sheet in writer.book.worksheets:
            for cell in sheet[1]:
                previous=cell.value
                if previous in ['n_obs','hac_lags','fx_age_days']:
                    for row in sheet.iter_rows(min_row=2,min_col=cell.column,max_col=cell.column):row[0].number_format='0'
                elif previous=='p_value':
                    for row in sheet.iter_rows(min_row=2,min_col=cell.column,max_col=cell.column):row[0].number_format='0.0000E+00'
                elif previous in ['coefficient','std_error','ci_low','ci_high']:
                    for row in sheet.iter_rows(min_row=2,min_col=cell.column,max_col=cell.column):row[0].number_format='0.000000'
                if previous in labels:cell.value=labels[previous]
                sheet.column_dimensions[cell.column_letter].width=max(sheet.column_dimensions[cell.column_letter].width,min(28,len(str(cell.value or ''))+3))
        for row in writer.book['Factores_USD'].iter_rows(min_row=2,min_col=2):
            for cell in row:cell.number_format='0.00%;(0.00%);0.00%'
        writer.book['Pesos'].column_dimensions['D'].width=18
        for row in writer.book['Pesos'].iter_rows(min_row=2,min_col=4,max_col=4):row[0].number_format='0.00%'
        writer.book.properties.creator='Alonso Castro Freibott, Pablo Caonabo Crespo de la Cruz, Carlos Segovia Domínguez y Jaime Blanco González'
        writer.book.properties.lastModifiedBy=writer.book.properties.creator
        writer.book.calculation=CalcProperties(calcId=0,fullCalcOnLoad=True,forceFullCalc=True,calcMode='auto')
    return output
