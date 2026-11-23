import argparse
import json
import pandas as pd
from .config import load_config
from .download import download_prices, download_official_factors, file_hash
from .factors import read_factors, align_factors
from .preparation import prepare_prices
from .portfolio import portfolio_returns
from .descriptive import descriptive_statistics
from .capm import capm
from .fama_french import fama_french
from .provenance import source_hashes, begin_analysis, finish_analysis, validate_report

def validate_source(config):
    path=config['root']/config['factors']['file']
    if not path.exists():raise FileNotFoundError(f'Falta la copia del profesor: {path.name}')
    if file_hash(path).lower()!=config['factors']['sha256'].lower():raise ValueError('El fichero de factores no coincide con la versión fijada')
    return path

def prepare(config):
    source_hashes(config)
    source=validate_source(config)
    manifest=json.loads((config['root']/'data/raw/manifest.json').read_text(encoding='utf-8'))
    for ticker in config['assets']['tickers']+['EURUSD=X']:
        path=config['root']/f"data/raw/{ticker.replace('=','_')}.csv"
        if file_hash(path)!=manifest[ticker]['sha256']:raise ValueError(f'Fuente local alterada: {ticker}')
    frames=prepare_prices(config)
    factors=align_factors(frames['returns_usd'],read_factors(source))
    if len(factors)!=config['sample']['expected_returns']:raise ValueError(f"No hay exactamente {config['sample']['expected_returns']} meses comunes")
    processed=config['root']/'data/processed';processed.mkdir(parents=True,exist_ok=True)
    for name,frame in {**frames,'factors_usd':factors}.items():frame.to_csv(processed/f'{name}.csv',index=name!='observations')
    validation={'price_months':len(frames['prices_usd']),'return_months':len(factors),'assets':len(config['assets']['tickers']),
      'price_start':str(frames['prices_usd'].index[0]),'price_end':str(frames['prices_usd'].index[-1]),
      'return_start':str(factors.index[0]),'return_end':str(factors.index[-1]),
      'missing_values':int(sum(df.isna().sum().sum() for df in frames.values())),
      'max_fx_age_days':int(frames['observations'].fx_age_days.max()),'factor_sha256':file_hash(source),
      'weights_sum':float(sum(config['assets']['weights'])),'currency':config['sample']['currency'],
      'max_month_end_age_days':config['sample']['max_month_end_age_days']}
    (processed/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation,ensure_ascii=False),flush=True)
    return frames,factors,validation

def analyze(config):
    frames,factors,validation=prepare(config)
    run=begin_analysis(config,validation)
    combined=frames['returns_usd'].copy();combined['Cartera']=portfolio_returns(combined,config['assets']['weights'])
    combined_eur=frames['returns_eur'].copy();combined_eur['Cartera']=portfolio_returns(combined_eur,config['assets']['weights'])
    records=[];fits={}
    for name in combined:
        table,fit=capm(combined[name],factors);table.insert(0,'asset',name);records.append(table);fits[name]=fit
    capm_table=pd.concat(records,ignore_index=True)
    ff3_table,ff3_fit=fama_french(combined['Cartera'],factors);ff3_table.insert(0,'asset','Cartera')
    comparison=pd.DataFrame([{'model':name,'n_obs':int(fit.nobs),'r_squared':float(fit.rsquared),
       'adj_r_squared':float(fit.rsquared_adj),'aic':float(fit.aic),'bic':float(fit.bic)} for name,fit in [('CAPM',fits['Cartera']),('FF3',ff3_fit)]])
    tables={'descriptive_usd':descriptive_statistics(combined),'descriptive_eur':descriptive_statistics(combined_eur),
        'capm':capm_table,'ff3':ff3_table,'comparison':comparison,'correlations':combined.corr()}
    output=config['root']/'reports/tables';output.mkdir(parents=True,exist_ok=True)
    for name,table in tables.items():table.to_csv(output/f'{name}.csv',index=name.startswith('descriptive') or name=='correlations')
    combined.to_csv(output/'returns_usd.csv');combined_eur.to_csv(output/'returns_eur.csv')
    from .plots import create_plots
    from .export import write_workbook
    create_plots(frames,combined,factors,tables['descriptive_usd'],capm_table,config['root']/'reports/figures')
    workbook=write_workbook(config,frames,factors,combined,combined_eur['Cartera'],tables)
    finish_analysis(config,run)
    print(f'Análisis local completado: {workbook.name}',flush=True)
    return frames,factors,combined,tables,validation

def main():
    parser=argparse.ArgumentParser(description='Análisis histórico académico CAPM y Fama-French')
    parser.add_argument('--config',default='config/analysis.toml')
    parser.add_argument('--project-root',default=None,help='Raíz del proyecto; independiente de la ubicación del TOML')
    parser.add_argument('command',choices=['download','prepare','analyze','report','all','download-official-factors','verify-artifacts'])
    parser.add_argument('--refresh',action='store_true',help='Archiva la fuente antes de actualizar precios')
    parser.add_argument('--skip-pdf',action='store_true',help='Genera fuentes LaTeX sin compilar (revisión sin MiKTeX)')
    args=parser.parse_args();config=load_config(args.config,root=args.project_root)
    if args.refresh and args.command not in {'download','all'}:parser.error('--refresh solo se admite en download/all')
    if args.skip_pdf and args.command not in {'report','all'}:parser.error('--skip-pdf solo se admite en report/all')
    if args.command=='download':download_prices(config,args.refresh)
    elif args.command=='download-official-factors':print(download_official_factors(config))
    elif args.command=='prepare':prepare(config)
    elif args.command=='analyze':analyze(config)
    elif args.command=='report':
        from .report import generate_report
        generate_report(config,compile_pdf=not args.skip_pdf)
    elif args.command=='verify-artifacts':
        run=validate_report(config);print(f"Artefactos íntegros de la ejecución {run['run_id']}")
    elif args.command=='all':
        download_prices(config,args.refresh);analyze(config)
        from .report import generate_report
        generate_report(config,compile_pdf=not args.skip_pdf)

if __name__=='__main__':main()
