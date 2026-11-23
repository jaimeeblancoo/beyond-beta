"""Fixtures sintéticas aisladas; todas las pruebas bloquean peticiones de red."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import tomllib
import urllib.request
import numpy as np
import pandas as pd
import pytest
from beyond_beta.config import load_config
from beyond_beta.download import file_hash

PROJECT = Path(__file__).resolve().parents[1]


def write_config(path, parameters):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines=[]
    for section,values in parameters.items():
        lines.append(f'[{section}]')
        lines.extend(f'{key} = {json.dumps(value,ensure_ascii=False)}' for key,value in values.items())
        lines.append('')
    path.write_text('\n'.join(lines),encoding='utf-8')
    return path


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError('Las pruebas no permiten peticiones de red')
    monkeypatch.setattr(socket.socket,'connect',blocked)
    monkeypatch.setattr(urllib.request,'urlopen',blocked)
    import requests
    from curl_cffi import requests as curl_requests
    monkeypatch.setattr(requests.sessions.Session,'request',blocked)
    monkeypatch.setattr(curl_requests.Session,'request',blocked)


@pytest.fixture
def synthetic_project(tmp_path, monkeypatch):
    root=tmp_path/'project';root.mkdir()
    shutil.copy2(PROJECT/'pyproject.toml',root/'pyproject.toml')
    shutil.copytree(PROJECT/'src',root/'src',ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    shutil.copytree(PROJECT/'templates',root/'templates')
    (root/'docs').mkdir()
    for name in ['methodology.md','sources.md']:
        shutil.copy2(PROJECT/'docs'/name,root/'docs'/name)
    with (PROJECT/'config/analysis.toml').open('rb') as handle:parameters=tomllib.load(handle)
    parameters=deepcopy(parameters)
    sample=parameters['sample'];sample.update(price_start='2020-01',price_end='2022-01',expected_prices=25,expected_returns=24)
    parameters['assets']={'tickers':['SYN1','SYN2'],'names':['Sintético A','Sintético B'],'currencies':['EUR','USD'],'weights':[.4,.6]}
    raw=root/'data/raw';raw.mkdir(parents=True)
    rng=np.random.default_rng(2026);periods=pd.period_range('2020-01','2022-01',freq='M')
    dates=pd.DatetimeIndex([pd.offsets.BDay().rollback(month.end_time.normalize()) for month in periods])
    factors=pd.DataFrame(rng.normal(0,.03,(24,4)),index=periods[1:],columns=['Mkt-RF','SMB','HML','RF']);factors['RF']=.001
    factor_path=raw/'F-F_Research_Data_Factors.csv'
    factor_path.write_text('Synthetic test data only\n,Mkt-RF,SMB,HML,RF\n'+'\n'.join(str(month).replace('-','')+','+','.join(str(value*100) for value in row) for month,row in zip(factors.index,factors.to_numpy()))+'\n\n Annual data\n2020,1,2,3,4\n',encoding='utf-8')
    parameters['factors']['sha256']=file_hash(factor_path)
    parameters['factors']['source']='Datos sintéticos exclusivos de pruebas'
    manifest={}
    for ticker,currency in [('SYN1','EUR'),('SYN2','USD'),('EURUSD=X','USD')]:
        field='Close' if ticker=='EURUSD=X' else 'Adj Close'
        values=1.1+np.arange(25)*.001 if ticker=='EURUSD=X' else 100*np.cumprod(np.r_[1,1+rng.normal(.008,.03,24)])
        path=raw/f"{ticker.replace('=','_')}.csv";pd.DataFrame({field:values},index=dates).to_csv(path,index_label='Date')
        manifest[ticker]={'currency':currency,'field':field,'sha256':file_hash(path),'name':ticker,'provider':'Synthetic test fixture','url':'synthetic://test-only'}
    (raw/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
    config_path=write_config(root/'config/analysis.toml',parameters)
    monkeypatch.chdir(root)
    return root,parameters,config_path
