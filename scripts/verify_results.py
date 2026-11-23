"""Comprobaciones numéricas independientes sobre los resultados locales guardados."""
import json
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from beyond_beta.config import load_config
from beyond_beta.preparation import prepare_prices
from beyond_beta.factors import read_factors, align_factors
from beyond_beta.download import file_hash
from beyond_beta.provenance import validate_analysis, write_json
import argparse

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='config/analysis.toml')
    parser.add_argument('--project-root',default=None)
    args=parser.parse_args()
    config=load_config(args.config,root=args.project_root);root=config['root']
    run=validate_analysis(config)
    frames=prepare_prices(config)
    factors=align_factors(frames['returns_usd'],read_factors(root/config['factors']['file']))
    combined=frames['returns_usd'].copy()
    combined['Cartera']=combined.to_numpy()@np.array(config['assets']['weights'])
    capm=pd.read_csv(root/'reports/tables/capm.csv');ff3=pd.read_csv(root/'reports/tables/ff3.csv')
    checks=0;max_error=0.
    def compare(actual,expected,tolerance=1e-10):
        nonlocal checks,max_error
        error=float(np.max(np.abs(np.asarray(actual)-np.asarray(expected))))
        if not np.isfinite(error) or error>tolerance:raise AssertionError(f'Diferencia {error}, límite {tolerance}')
        checks+=1;max_error=max(max_error,error)
    for name,columns,table in [(name,['Mkt-RF'],capm[capm.asset==name]) for name in combined]+[('Cartera',['Mkt-RF','SMB','HML'],ff3)]:
        x=np.column_stack([np.ones(len(factors)),factors[columns].to_numpy()]);y=(combined[name]-factors.RF).to_numpy()
        coefficients=np.linalg.lstsq(x,y,rcond=None)[0];residual=y-x@coefficients
        n,k=x.shape;bread=np.linalg.inv(x.T@x);rss=residual@residual
        covariance=(rss/(n-k))*bread;se=np.sqrt(np.diag(covariance));test=coefficients/se
        p=2*student_t.sf(np.abs(test),n-k);crit=student_t.ppf(.975,n-k)
        ols=table[table.inference=='OLS']
        for field,expected in [('coefficient',coefficients),('std_error',se),('t_stat',test),('p_value',p),('ci_low',coefficients-crit*se),('ci_high',coefficients+crit*se)]:compare(ols[field],expected)
        r2=1-rss/np.sum((y-y.mean())**2);compare(ols.r_squared,r2);compare(ols.adj_r_squared,1-(1-r2)*(n-1)/(n-k))
        lags=int(np.floor(4*(n/100)**(2/9)));scores=x*residual[:,None];meat=scores.T@scores
        for lag in range(1,lags+1):
            cross=scores[lag:].T@scores[:-lag];meat+=(1-lag/(lags+1))*(cross+cross.T)
        hac_cov=bread@meat@bread*n/(n-k)
        compare(table[table.inference=='HAC'].std_error,np.sqrt(np.diag(hac_cov)))
        if columns==['Mkt-RF']:compare(coefficients[0],combined[name].mean()-factors.RF.mean()-coefficients[1]*factors['Mkt-RF'].mean())
        if not (table.n_obs==len(factors)).all():raise AssertionError('Muestras distintas')
    for target in ['usd','eur']:
        saved=pd.read_csv(root/f'reports/tables/returns_{target}.csv',index_col=0)
        compare(saved.iloc[:,:len(config['assets']['names'])],frames[f'returns_{target}'])
        compare(saved.iloc[:,-1],frames[f'returns_{target}'].to_numpy()@np.array(config['assets']['weights']))
    output={'independent_numeric_checks':checks,'max_absolute_difference':max_error,
            'method':'Normal equations/lstsq, conventional covariance, Student t and manual Bartlett HAC',
            'common_months':len(factors),'regressions_with_intercept':len(combined.columns)+1,
            'run_id':run['run_id']}
    (root/'reports/numeric_validation.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    run['numeric_validation']={'path':'reports/numeric_validation.json','sha256':file_hash(root/'reports/numeric_validation.json')}
    write_json(root/'reports/run_manifest.json',run)
    print(json.dumps(output))

if __name__=='__main__':main()
