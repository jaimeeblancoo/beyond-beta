from copy import deepcopy
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook
from beyond_beta.config import load_config
from beyond_beta.preparation import monthly_observations
from beyond_beta.portfolio import portfolio_returns
from beyond_beta.fama_french import fama_french
from beyond_beta.cli import analyze, main
from beyond_beta.download import download_prices,file_hash
from beyond_beta.report import generate_report,build_documents
from beyond_beta.provenance import validate_analysis,validate_report
from conftest import write_config


@pytest.mark.parametrize('weights',[[.4,.6],[.5,.5]])
def test_positive_weights(weights):
    assert portfolio_returns(pd.DataFrame([[.1,.2]]),weights).iloc[0]==pytest.approx(np.dot(weights,[.1,.2]))


@pytest.mark.parametrize('weights',[[-.5,1.5],[0,1],[float('inf'),0],[.4,.60001]])
def test_short_and_invalid_weights_rejected(weights):
    with pytest.raises(ValueError):portfolio_returns(pd.DataFrame([[.1,.2]]),weights)


@pytest.mark.parametrize('section,key,value',[
    ('assets','names',['A','A']),('assets','names',['A','Cartera']),('assets','tickers',['SYN1','SYN1']),
    ('assets','currencies',['EUR','GBP']),('assets','weights',[1]),
    ('inference','primary','HAC'),('inference','hac_rule','__import__("os")'),
    ('portfolio','rebalance','buy_and_hold'),('portfolio','costs',.01),('portfolio','taxes',.01),
    ('sample','expected_returns',0)])
def test_invalid_configuration(synthetic_project,section,key,value):
    root,parameters,path=synthetic_project;parameters[section][key]=value;write_config(path,parameters)
    with pytest.raises(ValueError):load_config(path)


def test_truncated_month_message():
    daily=pd.Series([100.],index=pd.to_datetime(['2021-01-01']))
    with pytest.raises(ValueError,match=r'SYN.*2021-01.*2021-01-01.*máximo 7'):
        monthly_observations(daily,pd.period_range('2021-01',periods=1,freq='M'),7,'SYN')


@pytest.mark.parametrize('month,date',[('2021-01','2021-01-29'),('2021-12','2021-12-30')])
def test_month_end_weekend_or_holiday_tolerance(month,date):
    prices,dates=monthly_observations(pd.Series([100.],index=pd.to_datetime([date])),pd.period_range(month,periods=1,freq='M'))
    assert str(dates.iloc[0].date())==date


def test_snapshot_reuse_also_rejects_truncated_month(synthetic_project):
    root,parameters,path=synthetic_project
    raw=root/'data/raw/SYN1.csv';frame=pd.read_csv(raw,index_col=0);frame.index=pd.to_datetime(frame.index)
    frame.index=pd.DatetimeIndex([date.replace(day=1) for date in frame.index]);frame.to_csv(raw)
    manifest_path=root/'data/raw/manifest.json';manifest=json.loads(manifest_path.read_text());manifest['SYN1']['sha256']=file_hash(raw);manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='SYN1.*distancia'):
        download_prices(load_config(path))


def test_insufficient_residual_degrees_of_freedom():
    index=pd.period_range('2021-01',periods=4,freq='M')
    factors=pd.DataFrame(np.eye(4),index=index,columns=['Mkt-RF','SMB','HML','RF'])
    with pytest.raises(ValueError,match='grados de libertad'):
        fama_french(pd.Series(np.arange(4),index=index),factors)


def test_alternative_config_full_cli_and_dynamic_excel(synthetic_project,monkeypatch,tmp_path):
    root,parameters,_=synthetic_project
    parameters['assets']['weights']=[.7,.3]
    alt=write_config(tmp_path/'elsewhere/custom.toml',parameters)
    monkeypatch.setattr('sys.argv',['beyond-beta','--config',str(alt),'analyze']);main()
    config=load_config(alt);run=validate_analysis(config)
    assert config['root']==root and run['config_sha256']==file_hash(alt)
    assert run['config_path']==str(alt.resolve()) and run['parameters']['assets']['weights']==[.7,.3]
    assert run['validation']['return_months']==24
    book=load_workbook(root/'reports/Resultados_Beyond_Beta.xlsx',data_only=False)
    assert book['Precios_USD'].max_row==26 and book['Rentabilidades_USD'].max_row==25
    assert book['Rentabilidades_USD']['D25'].data_type=='f'
    assert book['Pesos']['D2'].value==.7
    assert book.calculation.fullCalcOnLoad and load_workbook(root/'reports/Resultados_Beyond_Beta.xlsx',data_only=True)['Rentabilidades_USD']['D2'].value is None
    manual=root/'docs/methodology.md';manual.write_text(manual.read_text(encoding='utf-8')+'\n\nNota manual que se conserva.\n',encoding='utf-8');before=manual.read_bytes()
    monkeypatch.setattr('sys.argv',['beyond-beta','--config',str(alt),'report','--skip-pdf']);main()
    assert manual.read_bytes()==before
    text=(root/'reports/report/informe.tex').read_text(encoding='utf-8')
    assert '70,0000' in text and '3/10' in text and '24 rentabilidades' in text and 'equiponderada' not in text
    assert 'octubre de 2021 a septiembre de 2026' not in text
    report=validate_report(config)
    assert not report['report_pdf_compiled'] and not any(name.endswith('.pdf') for name in report['report_outputs'])


@pytest.mark.parametrize('name',['reports/tables/capm.csv','reports/figures/sml_usd.png'])
def test_report_rejects_tampered_consumed_artifacts(synthetic_project,name):
    _,_,path=synthetic_project;config=load_config(path);analyze(config)
    target=config['root']/name;target.write_bytes(target.read_bytes()+b'alteration')
    with pytest.raises(ValueError,match='Artefacto alterado'):
        generate_report(config,compile_pdf=False)


def test_no_mixing_runs_or_extra_csv(synthetic_project):
    root,parameters,path=synthetic_project;config=load_config(path);analyze(config)
    previous=(root/'reports/tables/returns_usd.csv').read_bytes();first=validate_analysis(config)['run_id']
    (root/'reports/tables/obsolete.csv').write_text('not part of this run',encoding='utf-8')
    assert 'reports/tables/obsolete.csv' not in validate_analysis(config)['analysis_outputs']
    parameters['assets']['weights']=[.2,.8];write_config(path,parameters);config=load_config(path)
    with pytest.raises(ValueError,match='configuración efectiva'):generate_report(config,compile_pdf=False)
    analyze(config);assert validate_analysis(config)['run_id']!=first
    (root/'reports/tables/returns_usd.csv').write_bytes(previous)
    with pytest.raises(ValueError,match='Artefacto alterado'):generate_report(config,compile_pdf=False)


def test_raw_or_provenance_change_is_not_assigned_to_old_results(synthetic_project):
    root,_,path=synthetic_project;config=load_config(path);analyze(config)
    raw=root/'data/raw/SYN1.csv';raw.write_bytes(raw.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='Snapshot'):generate_report(config,compile_pdf=False)


def test_failed_analysis_cannot_publish_previous_manifest(synthetic_project,monkeypatch):
    _,_,path=synthetic_project;config=load_config(path);analyze(config)
    def fail(*args,**kwargs):raise RuntimeError('Synthetic staged failure')
    monkeypatch.setattr('beyond_beta.plots.create_plots',fail)
    with pytest.raises(RuntimeError):analyze(config)
    with pytest.raises(ValueError,match='ejecución completa'):generate_report(config,compile_pdf=False)


def test_updated_raw_manifest_still_cannot_relabel_old_results(synthetic_project):
    root,_,path=synthetic_project;config=load_config(path);analyze(config)
    raw=root/'data/raw/SYN1.csv';frame=pd.read_csv(raw,index_col=0);frame.iloc[-1,0]*=1.01;frame.to_csv(raw)
    manifest_path=root/'data/raw/manifest.json';manifest=json.loads(manifest_path.read_text());manifest['SYN1']['sha256']=file_hash(raw);manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='entradas o su procedencia cambiaron'):generate_report(config,compile_pdf=False)


def test_failed_report_is_not_marked_complete(synthetic_project,monkeypatch):
    _,_,path=synthetic_project;config=load_config(path);analyze(config);generate_report(config,compile_pdf=False)
    def fail(*args,**kwargs):raise RuntimeError('Synthetic compiler failure')
    monkeypatch.setattr('beyond_beta.report.write_report',fail)
    with pytest.raises(RuntimeError):generate_report(config,compile_pdf=False)
    with pytest.raises(ValueError,match='Informe no completado'):validate_report(config)


def test_identical_config_at_another_path_is_not_misattributed(synthetic_project,tmp_path):
    root,parameters,path=synthetic_project;config=load_config(path);analyze(config)
    alternate=write_config(tmp_path/'another.toml',parameters)
    with pytest.raises(ValueError,match='configuración efectiva'):
        generate_report(load_config(alternate),compile_pdf=False)


def test_source_only_report_archives_existing_pdf(synthetic_project):
    root,_,path=synthetic_project;config=load_config(path);analyze(config)
    folder=root/'reports/report';folder.mkdir();(folder/'informe.pdf').write_bytes(b'Synthetic previous PDF placeholder')
    generate_report(config,compile_pdf=False)
    assert not (folder/'informe.pdf').exists()
    assert list((folder/'archive').rglob('informe.pdf'))


def test_plots_cover_more_assets_than_original_palette(tmp_path,monkeypatch):
    from beyond_beta.plots import create_plots
    from beyond_beta.descriptive import descriptive_statistics
    rng=np.random.default_rng(9);index=pd.period_range('2020-02',periods=24,freq='M')
    returns=pd.DataFrame(rng.normal(.005,.03,(24,8)),index=index,columns=[f'Activo {i}' for i in range(8)])
    combined=returns.copy();combined['Cartera']=returns.mean(axis=1)
    factors=pd.DataFrame({'Mkt-RF':rng.normal(.005,.02,24),'RF':.001},index=index)
    capm_table=pd.DataFrame([{'asset':name,'term':term,'inference':'OLS','coefficient':.1 if term=='alpha' else .5,'p_value':.1} for name in combined for term in ['alpha','Mkt-RF']])
    captured={}
    def capture(fig,path):
        captured[Path(path).name]=sum(ax.get_visible() for ax in fig.axes)
        import matplotlib.pyplot as plt
        plt.close(fig)
    monkeypatch.setattr('beyond_beta.plots.save',capture)
    create_plots({'returns_usd':returns,'prices_usd':pd.DataFrame(index=pd.period_range('2020-01',periods=25,freq='M'))},combined,factors,descriptive_statistics(combined),capm_table,tmp_path)
    assert captured['capm_scatter_usd.png']==8
