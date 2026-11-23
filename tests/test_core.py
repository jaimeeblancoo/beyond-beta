"""Pruebas sin red: todos los valores creados aquí son sintéticos."""
import numpy as np
import pandas as pd
import pytest
from beyond_beta.factors import read_factors,align_factors
from beyond_beta.preparation import monthly_observations,fx_at_dates,convert_prices,simple_returns
from beyond_beta.portfolio import portfolio_returns
from beyond_beta.descriptive import descriptive_statistics
from beyond_beta.capm import capm
from beyond_beta.fama_french import fama_french

def test_factor_monthly_block_percentage_and_annual_exclusion(tmp_path):
    path=tmp_path/'synthetic.csv'
    path.write_text('Synthetic test data\n,Mkt-RF,SMB,HML,RF\n202101,2.89,-1,3,0.22\n202102,1,2,3,0\n\n Annual Factors\n2021,100,200,300,400\n')
    frame=read_factors(path)
    assert len(frame)==2 and frame.index[-1]==pd.Period('2021-02','M')
    assert frame.iloc[0]['Mkt-RF']==pytest.approx(.0289)
    assert frame.iloc[0].RF==pytest.approx(.0022)

@pytest.mark.parametrize('rows',['202101,1,2,3,0\n202101,1,2,3,0','202102,1,2,3,0\n202101,1,2,3,0','202101,-99.99,2,3,0','202101,nan,2,3,0'])
def test_invalid_factors_rejected(tmp_path,rows):
    path=tmp_path/'synthetic.csv';path.write_text(',Mkt-RF,SMB,HML,RF\n'+rows)
    with pytest.raises(ValueError):read_factors(path)

def test_fx_uses_only_previous_observation_and_age():
    fx=pd.Series([1.1,1.2],index=pd.to_datetime(['2021-01-28','2021-02-01']))
    dates=pd.Series(pd.to_datetime(['2021-01-29']),index=pd.period_range('2021-01',periods=1,freq='M'))
    rates,selected,ages=fx_at_dates(fx,dates)
    assert rates.iloc[0]==1.1 and selected.iloc[0]==pd.Timestamp('2021-01-28') and ages.iloc[0]==1
    with pytest.raises(ValueError):fx_at_dates(fx,dates,max_age=0)
    with pytest.raises(ValueError):fx_at_dates(fx.iloc[1:],dates)

def test_price_conversion_and_returns_identity():
    index=pd.period_range('2021-01',periods=2,freq='M')
    prices=pd.Series([100,110],index=index);fx=pd.Series([1.2,1.3],index=index)
    usd=convert_prices(prices,fx,'EUR','USD')
    assert usd.tolist()==pytest.approx([120,143])
    assert convert_prices(usd,fx,'USD','EUR').tolist()==pytest.approx(prices.tolist())
    r=simple_returns(usd.to_frame('synthetic')).iloc[0,0]
    assert r==pytest.approx((1.1)*(1.3/1.2)-1)

def test_missing_month_and_price_rejected():
    frame=pd.DataFrame({'synthetic':[100,110]},index=pd.PeriodIndex(['2021-01','2021-03'],freq='M'))
    with pytest.raises(ValueError):simple_returns(frame)
    frame.index=pd.period_range('2021-01',periods=2,freq='M');frame.iloc[1,0]=np.nan
    with pytest.raises(ValueError):simple_returns(frame)

def test_monthly_last_and_absent_month():
    data=pd.Series([1,2,3],index=pd.to_datetime(['2021-01-15','2021-01-29','2021-02-26']))
    periods=pd.period_range('2021-01',periods=2,freq='M');prices,dates=monthly_observations(data,periods)
    assert prices.tolist()==[2,3] and dates.iloc[0]==pd.Timestamp('2021-01-29')
    with pytest.raises(ValueError):monthly_observations(data,pd.period_range('2021-01',periods=3,freq='M'))

def test_alignment_does_not_silently_drop_month():
    index=pd.period_range('2021-01',periods=3,freq='M')
    returns=pd.DataFrame({'synthetic':[.1,.2,.3]},index=index)
    factors=pd.DataFrame(np.zeros((3,4)),index=index,columns=['Mkt-RF','SMB','HML','RF'])
    assert align_factors(returns,factors).index.equals(index)
    with pytest.raises(ValueError):align_factors(returns,factors.drop(index[1]))

@pytest.mark.parametrize('weights',[[0,1],[.2,.2],[np.nan,1],[1]])
def test_invalid_weights(weights):
    with pytest.raises(ValueError):portfolio_returns(pd.DataFrame([[.1,.2]]),weights)

def test_portfolio_monthly_rebalance_and_drawdown_initial_peak():
    returns=pd.DataFrame({'synthetic_a':[-.2,.1],'synthetic_b':[.1,.2]})
    assert portfolio_returns(returns,[.5,.5]).tolist()==pytest.approx([-.05,.15])
    stats=descriptive_statistics(returns)
    assert stats.loc['synthetic_a','max_drawdown_monthly']==pytest.approx(-.2)
    assert stats.loc['synthetic_a','geometric_annual_return']==pytest.approx((.8*1.1)**6-1)

def test_known_capm_and_ff3_coefficients():
    rng=np.random.default_rng(37);index=pd.period_range('2000-01',periods=120,freq='M')
    factors=pd.DataFrame(rng.normal(0,.03,(120,4)),index=index,columns=['Mkt-RF','SMB','HML','RF'])
    factors['RF']=.002
    y=factors.RF+.004+1.2*factors['Mkt-RF']
    table,fit=capm(y,factors);coeff=table[table.inference=='OLS'].set_index('term').coefficient
    assert coeff['alpha']==pytest.approx(.004) and coeff['Mkt-RF']==pytest.approx(1.2)
    y=factors.RF+.003+1.1*factors['Mkt-RF']-.4*factors.SMB+.7*factors.HML
    table,fit=fama_french(y,factors);coeff=table[table.inference=='OLS'].set_index('term').coefficient
    assert coeff.tolist()==pytest.approx([.003,1.1,-.4,.7])
    assert fit.nobs==120 and len(fit.params)==4
