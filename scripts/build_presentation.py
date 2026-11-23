"""Presentación académica Beamer desde una ejecución íntegra, sin descargas."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

from scipy.stats import f as fisher_f

from beyond_beta.config import load_config, hac_lags
from beyond_beta.download import file_hash
from beyond_beta.factors import read_factors, align_factors
from beyond_beta.latex import compile_tex, tex_escape
from beyond_beta.provenance import validate_report, artifact_hashes, write_json
from beyond_beta.report import span

COLORS = ['#2868A6', '#B38023', '#875597', '#B55158', '#458875', '#6C778A']
NAVY = '#183650'
SOURCES = ['scripts/build_presentation.py', 'templates/beamer/presentation.tex',
           'templates/latex/preamble.tex', 'src/beyond_beta/latex.py']
TABLES = ['returns_usd', 'descriptive_usd', 'capm', 'ff3', 'comparison', 'correlations']


def decimal(value, digits=2):
    return f'{value:.{digits}f}'.replace('.', ',')


def percentage(value):
    return decimal(value * 100) + ' %'


def probability(value):
    return '<0,0001' if value < .0001 else decimal(value, 4)


def sml_coordinates(returns, factors, beta):
    """SML en medias aritméticas; la diferencia es alfa con intercepto."""
    expected = factors['RF'].mean() + beta * factors['Mkt-RF'].mean()
    realized = returns.mean().reindex(beta.index)
    return expected, realized


def replace_tokens(text, values, latex=False):
    def substitute(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f'Falta contenido para {key}')
        value = str(values[key])
        return value if key.endswith('_ROWS') or not latex else tex_escape(value)
    return re.sub(r'@@([A-Z0-9_]+)@@', substitute, text)


def input_state(config):
    run = validate_report(config)
    paths = SOURCES + [f'reports/tables/{name}.csv' for name in TABLES]
    paths += ['reports/run_manifest.json', config['factors']['file']]
    return {'run_id': run['run_id'], 'files': artifact_hashes(config['root'], paths),
            'config_path': str(config['config_path']), 'config_sha256': file_hash(config['config_path'])}


def validate_presentation(config):
    folder = config['root'] / 'reports/presentation'
    manifest = json.loads((folder/'presentation_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('stage') != 'complete' or manifest['inputs'] != input_state(config):
        raise ValueError('Presentación incompleta o entradas de otra ejecución')
    for path, digest in manifest['outputs'].items():
        if file_hash(config['root']/path) != digest:
            raise ValueError(f'Entregable de presentación alterado: {path}')
    return manifest


def load_results(config):
    folder = config['root']/'reports/tables'
    data = {name: pd.read_csv(folder/f'{name}.csv', index_col=0 if name in
            {'returns_usd', 'descriptive_usd', 'correlations'} else None) for name in TABLES}
    data['returns_usd'].index = pd.PeriodIndex(data['returns_usd'].index, freq='M')
    data['factors'] = align_factors(data['returns_usd'], read_factors(config['root']/config['factors']['file']))
    data['alpha'] = data['capm'].query("inference == 'OLS' and term == 'alpha'").set_index('asset')
    data['beta'] = data['capm'].query("inference == 'OLS' and term == 'Mkt-RF'").set_index('asset')
    data['ff_ols'] = data['ff3'].query("inference == 'OLS'").set_index('term')
    data['ff_hac'] = data['ff3'].query("inference == 'HAC'").set_index('term')
    data['hac_alpha'] = data['capm'].query("inference == 'HAC' and term == 'alpha'").set_index('asset')
    expected, realized = sml_coordinates(data['returns_usd'], data['factors'], data['beta']['coefficient'])
    if not np.allclose(realized-expected, data['alpha']['coefficient'], atol=1e-12, rtol=0):
        raise ValueError('La SML no coincide con los alfas de las tablas')
    return data


def create_figures(config, data, folder):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 20,
        'axes.labelsize': 21, 'xtick.labelsize': 18, 'ytick.labelsize': 18,
        'legend.fontsize': 17, 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'axes.spines.top': False, 'axes.spines.right': False, 'axes.labelcolor': NAVY,
        'text.color': NAVY, 'axes.edgecolor': '#A3ADB6', 'figure.facecolor': 'white'})
    folder.mkdir(parents=True, exist_ok=True)
    names = config['assets']['names']; colors = dict(zip(names, COLORS)); colors['Cartera'] = NAVY
    returns = data['returns_usd']; periods = pd.period_range(config['sample']['price_start'], config['sample']['price_end'], freq='M')
    wealth = pd.DataFrame(np.vstack([np.ones(len(returns.columns)), (1+returns).cumprod().to_numpy()])*100,
                          index=periods.to_timestamp('M'), columns=returns.columns)
    outputs = []
    def save(fig, name):
        path = folder/f'{name}.pdf'; fig.savefig(path, bbox_inches='tight', metadata={'Creator':'Beyond Beta'}); plt.close(fig)
        outputs.append(path)
    fig, ax = plt.subplots(figsize=(13, 4.8), layout='constrained')
    for name in wealth:
        ax.plot(wealth.index, wealth[name], label=name, color=colors[name],
                linewidth=3.6 if name=='Cartera' else 2.1, linestyle='--' if name=='Cartera' else '-')
    ax.set_ylabel('Riqueza en USD (base 100)'); ax.grid(axis='y', alpha=.15)
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.legend(ncol=4, loc='upper left', frameon=False, bbox_to_anchor=(0,1.24))
    save(fig, 'wealth')
    stats = data['descriptive_usd']
    fig, ax = plt.subplots(figsize=(12.5,4.7), layout='constrained')
    offsets = {'ACS':(8,3), 'Oro PPFB':(8,3), 'Nike':(8,-5), 'Roblox':(-75,8),
               'Bonos euro':(8,-8), 'Bolsa mundial':(8,8), 'Cartera':(10,-15)}
    for name, row in stats.iterrows():
        ax.scatter(row.vol_annual*100, row.geometric_annual_return*100, color=colors[name], s=150,
                   marker='D' if name=='Cartera' else 'o', zorder=3)
        ax.annotate(name, (row.vol_annual*100, row.geometric_annual_return*100),
                    xytext=offsets.get(name,(8,7)), textcoords='offset points', fontsize=18)
    ax.axhline(0,color='#A3ADB6',linewidth=1); ax.set(xlabel='Volatilidad anualizada (%)', ylabel='Rentabilidad geométrica (%)')
    ax.set_xlim(0,stats.vol_annual.max()*115); ax.margins(y=.2); ax.grid(alpha=.12)
    save(fig,'risk_return')
    fig, axes = plt.subplots(1,2,figsize=(13,4.8),layout='constrained',sharey=True)
    for ax, table, title, scale in [(axes[0],data['alpha'],'Alfa (% mensual)',100),
                                     (axes[1],data['beta'],'Beta',1)]:
        for i,name in enumerate(names):
            row=table.loc[name]
            ax.errorbar(row.coefficient*scale,i,xerr=np.array([[row.coefficient-row.ci_low],[row.ci_high-row.coefficient]])*scale,
                        fmt='o',color=colors[name],capsize=5,markersize=9,linewidth=2.5)
        ax.axvline(0,color='#A3ADB6',linestyle='--');ax.set_xlabel(title);ax.grid(axis='x',alpha=.15)
        ax.set_yticks(range(len(names)),names)
    axes[0].invert_yaxis();save(fig,'capm_intervals')
    fig, ax = plt.subplots(figsize=(12.5,4.8),layout='constrained')
    beta=data['beta']['coefficient'].loc[names];factors=data['factors']
    expected,realized=sml_coordinates(returns[names],factors,beta)
    x=np.linspace(min(0,float(beta.min())-.1),max(1,float(beta.max())+.15),100)
    ax.plot(x,(factors.RF.mean()+x*factors['Mkt-RF'].mean())*100,color=NAVY,linewidth=2,label='SML virtual')
    for name in names:
        significant=data['alpha'].loc[name,'p_value']<.05
        ax.vlines(beta[name],expected[name]*100,realized[name]*100,color=colors[name],linestyle=':',linewidth=2)
        ax.scatter(beta[name],realized[name]*100,s=170,edgecolors=colors[name],
                   facecolors=colors[name] if significant else 'white',linewidths=2,
                   marker='s' if data['beta'].loc[name,'p_value']>=.05 else 'o',zorder=3)
        ax.annotate(name,(beta[name],realized[name]*100),xytext=(9,6),textcoords='offset points',fontsize=18)
    ax.set(xlabel='Beta CAPM estimada',ylabel='Media mensual (%)');ax.grid(alpha=.12)
    ax.set_xlim(x.min()-.06,x.max()+.15);ax.margins(y=.2);save(fig,'sml')
    drawdown=wealth.Cartera/wealth.Cartera.cummax()-1
    fig,ax=plt.subplots(figsize=(9,4.4),layout='constrained')
    ax.fill_between(drawdown.index,drawdown,0,color=NAVY,alpha=.16);ax.plot(drawdown.index,drawdown,color=NAVY,linewidth=2.8)
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.set_ylabel('Caída desde el máximo')
    ax.xaxis.set_major_locator(mdates.YearLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'));ax.grid(axis='y',alpha=.15)
    save(fig,'drawdown')
    fig,ax=plt.subplots(figsize=(8.3,4.6),layout='constrained')
    ff=data['ff_ols'].loc[['Mkt-RF','SMB','HML']]
    for i,(term,row) in enumerate(ff.iterrows()):
        ax.errorbar(row.coefficient,i,xerr=np.array([[row.coefficient-row.ci_low],[row.ci_high-row.coefficient]]),
                    fmt='o',color=NAVY,capsize=6,linewidth=3,markersize=10)
    ax.set_yticks(range(3),['Mkt-RF','SMB','HML']);ax.invert_yaxis();ax.axvline(0,color='#A3ADB6',linestyle='--')
    ax.set_xlabel('Exposición e IC95% (OLS)');ax.grid(axis='x',alpha=.15);save(fig,'ff3_exposures')
    fig,ax=plt.subplots(figsize=(8,5.2),layout='constrained')
    corr=data['correlations'].loc[names,names]
    im=ax.pcolormesh(corr.to_numpy(),vmin=-1,vmax=1,cmap='BrBG',edgecolors='white',linewidth=.6)
    ax.set_aspect('equal');ax.invert_yaxis()
    short=[name.replace('Bolsa mundial','Mundial').replace('Bonos euro','Bonos').replace('Oro PPFB','Oro') for name in names]
    ax.set_xticks(np.arange(len(names))+.5,short,rotation=35,ha='right');ax.set_yticks(np.arange(len(names))+.5,short)
    for i in range(len(names)):
        for j in range(len(names)):ax.text(j+.5,i+.5,decimal(corr.iloc[i,j]),ha='center',va='center',fontsize=16,color='white' if abs(corr.iloc[i,j])>.65 else NAVY)
    colorbar=fig.colorbar(im,ax=ax,shrink=.8);colorbar.solids.set_rasterized(False)
    save(fig,'correlations')
    return outputs


def content_values(config, run, data):
    names=config['assets']['names'];sample=config['sample'];a=data['alpha'];b=data['beta'];ff=data['ff_ols'];hac=data['hac_alpha']
    stats=data['descriptive_usd'];p=stats.loc['Cartera'];comparison=data['comparison'].set_index('model')
    positive=[n for n in names if a.loc[n,'coefficient']>0 and a.loc[n,'p_value']<.05]
    negative=[n for n in names if a.loc[n,'coefficient']<0 and a.loc[n,'p_value']<.05]
    significant=positive+negative
    alpha_summary='Alfa significativo: '+(', '.join(significant) if significant else 'ninguno')+'.'
    worsens=comparison.loc['FF3','adj_r_squared']<comparison.loc['CAPM','adj_r_squared']
    changed=[n for n in names+['Cartera'] if (a.loc[n,'p_value']<.05)!=(hac.loc[n,'p_value']<.05)]
    equal=np.ptp(config['assets']['weights'])<1e-12
    weights='1/6 por activo' if equal else ', '.join(percentage(w) for w in config['assets']['weights'])
    residual_df = len(data['returns_usd']) - 4
    capm_r2, ff_r2 = comparison.loc[['CAPM','FF3'], 'r_squared']
    joint_f = ((ff_r2 - capm_r2) / 2) / ((1 - ff_r2) / residual_df)
    weighted_beta = np.dot(config['assets']['weights'], b.loc[names, 'coefficient'])
    def rows(table):return '\n'.join(' & '.join(row)+r' \\' for row in table)
    values={'NPRICES':sample['expected_prices'],'NRETURNS':sample['expected_returns'],
        'PRICEWINDOW':span(pd.period_range(sample['price_start'],sample['price_end'],freq='M')),
        'RETURNWINDOW':span(data['returns_usd'].index),'CAGR':percentage(p.geometric_annual_return),
        'CUMULATIVE':percentage(p.cumulative_return),'VOL':percentage(p.vol_annual),'DRAWDOWN':percentage(p.max_drawdown_monthly),
        'PORTFOLIO':'Cartera equiponderada' if equal else 'Cartera con pesos configurados','WEIGHTS_SHORT':weights,
        'FF_TITLE':'FF3 no mejora el R² ajustado' if worsens else 'FF3 eleva el R² ajustado',
        'CAPM_ADJ':decimal(comparison.loc['CAPM','adj_r_squared'],4),'FF_ADJ':decimal(comparison.loc['FF3','adj_r_squared'],4),
        'CAPM_R2':decimal(comparison.loc['CAPM','r_squared'],4),'FF_R2':decimal(comparison.loc['FF3','r_squared'],4),
        'FF_ALPHA':percentage(ff.loc['alpha','coefficient']),'FF_P':probability(ff.loc['alpha','p_value']),
        'FACTOR_FINDING':'SMB y HML: evidencia individual insuficiente al 5 %' if (ff.loc[['SMB','HML'],'p_value']>=.05).all() else 'Contrastes individuales de SMB y HML en A3',
        'CONCLUSION_TITLE':'En esta cartera, FF3 aporta poco ajuste' if worsens else 'El ajuste de FF3 en esta muestra',
        'CONCLUSION_ALPHA':alpha_summary+' El contraste depende del modelo de referencia.',
        'CONCLUSION_FF':'FF3 eleva R², pero reduce R² ajustado. No encontramos alfa de cartera significativo.' if worsens and ff.loc['alpha','p_value']>=.05 else 'La comparación de modelos exige considerar ajuste e incertidumbre.',
        'ALPHA_SUMMARY':alpha_summary,'LAGS':hac_lags(len(data['returns_usd'])),
        'HAC_FINDING':'No cambia qué alfas son significativos al 5 %.' if not changed else 'Cambia la clasificación para: '+', '.join(changed)+'.',
        'FX_TOLERANCE':sample['max_fx_age_days'],'FX_ACTUAL':run['validation']['max_fx_age_days'],
        'FACTOR_SOURCE':config['factors']['source'],'RUN_ID':run['run_id'],
        'ACS_ALPHA':percentage(a.loc['ACS','coefficient']),'NIKE_ALPHA':percentage(a.loc['Nike','coefficient']),
        'BONDS_ALPHA':percentage(a.loc['Bonos euro','coefficient']),
        'GOLD_BETA':decimal(b.loc['Oro PPFB','coefficient'],3),'WORLD_BETA':decimal(b.loc['Bolsa mundial','coefficient'],3),
        'ROBLOX_VOL':percentage(stats.loc['Roblox','vol_annual']),
        'ROBLOX_CAGR':percentage(stats.loc['Roblox','geometric_annual_return']),
        'ACS_CUMULATIVE':percentage(stats.loc['ACS','cumulative_return']),
        'NIKE_CUMULATIVE':percentage(stats.loc['Nike','cumulative_return']),
        'PORTFOLIO_BETA':decimal(b.loc['Cartera','coefficient'],4),
        'WEIGHTED_BETA':decimal(weighted_beta,4), 'FF_DF':residual_df,
        'FF_F':decimal(joint_f,4), 'FF_JOINT_P':probability(fisher_f.sf(joint_f,2,residual_df)),
        'FF_MARKET':decimal(ff.loc['Mkt-RF','coefficient'],4),
        'CORR_GOLD_NIKE':decimal(data['correlations'].loc['Oro PPFB','Nike'],3)}
    values['CAPM_ROWS']=rows([[tex_escape(n),decimal(a.loc[n,'coefficient']*100),probability(a.loc[n,'p_value']),
        decimal(b.loc[n,'coefficient'],3),probability(b.loc[n,'p_value']),decimal(a.loc[n,'r_squared'],3)] for n in names])
    values['HAC_ROWS']=rows([[tex_escape(n),probability(a.loc[n,'p_value']),probability(hac.loc[n,'p_value']),
        '['+decimal(hac.loc[n,'ci_low']*100)+'; '+decimal(hac.loc[n,'ci_high']*100)+']'] for n in names+['Cartera']])
    values['FF_ROWS']=rows([[tex_escape(term),decimal(row.coefficient*(100 if term=='alpha' else 1),3),probability(row.p_value),
        '['+decimal(row.ci_low*(100 if term=='alpha' else 1),3)+'; '+decimal(row.ci_high*(100 if term=='alpha' else 1),3)+']',
        probability(data['ff_hac'].loc[term,'p_value'])] for term,row in ff.iterrows()])
    values['COMPARISON_ROWS']=rows([[name,decimal(row.r_squared,4),decimal(row.adj_r_squared,4),decimal(row.aic),decimal(row.bic)] for name,row in comparison.iterrows()])
    return values


def generate(config):
    # The academic narrative is specific to the approved universe, not arbitrary tickers.
    expected=['ACS.MC','PPFB.DE','NKE','RBLX','EUNH.DE','IUSQ.DE']
    expected_names=['ACS','Oro PPFB','Nike','Roblox','Bonos euro','Bolsa mundial']
    if config['assets']['tickers'] != expected or config['assets']['names'] != expected_names:
        raise ValueError('Esta presentación requiere el universo académico de seis activos y sus nombres documentados')
    run=validate_report(config);before=input_state(config);data=load_results(config)
    folder=config['root']/'reports/presentation';folder.mkdir(parents=True,exist_ok=True)
    manifest={'stage':'building','created_at':datetime.now(timezone.utc).isoformat(),
              'inputs':before,'main_slides':10,'backup_slides':6}
    manifest_path=folder/'presentation_manifest.json';write_json(manifest_path,manifest)
    outputs=create_figures(config,data,folder/'figures');values=content_values(config,run,data)
    template=config['root']/'templates/beamer/presentation.tex'
    tex=folder/'Presentacion_Beyond_Beta.tex'
    tex.write_text(replace_tokens(template.read_text(encoding='utf-8'),values,latex=True),encoding='utf-8')
    outputs.extend([tex,compile_tex(tex)])
    if input_state(config)!=before:raise ValueError('Las entradas cambiaron durante la generación')
    manifest.update(stage='complete', outputs=artifact_hashes(config['root'], [p.relative_to(config['root']) for p in outputs]))
    write_json(manifest_path,manifest);validate_presentation(config)
    print(json.dumps({k:manifest[k] for k in ['stage','main_slides','backup_slides']}))



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config/analysis.toml');parser.add_argument('--project-root')
    parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    config=load_config(args.config,root=args.project_root)
    if args.verify:
        manifest=validate_presentation(config);print('Presentación íntegra, ejecución '+manifest['inputs']['run_id'])
    else:generate(config)


if __name__=='__main__':main()
