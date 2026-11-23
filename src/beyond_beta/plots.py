from pathlib import Path
import numpy as np
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COLORS = ["#2563a6", "#c59625", "#637381", "#a14b78", "#3e8d79", "#925f36", "#162f45"]

def save(fig, path):
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)

def create_plots(frames, combined, factors, stats, capm_table, directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    colors=[COLORS[i] if i<len(COLORS) else plt.get_cmap('tab20')(i%20) for i in range(len(combined))]
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "axes.spines.top":False,
                        "axes.spines.right":False, "axes.grid":True, "grid.alpha":.18})
    initial = frames["prices_usd"].index[0].to_timestamp()
    fig, ax = plt.subplots(figsize=(9,4.5))
    for i, name in enumerate(combined):
        wealth = np.r_[100, 100*(1+combined[name]).cumprod()]
        dates = [initial, *combined.index.to_timestamp()]
        ax.plot(dates, wealth, label=name, color=colors[i], linestyle="--" if name=="Cartera" else "-", linewidth=2.3 if name=="Cartera" else 1.5)
    ax.set(title="Evolución de una inversión inicial de 100 USD", ylabel="Índice de riqueza", xlabel="Mes")
    ax.legend(ncol=3, loc="upper left", fontsize=11)
    save(fig,directory/"wealth_usd.png")
    corr = combined.corr()
    fig,ax=plt.subplots(figsize=(7.5,6))
    image=ax.imshow(corr, vmin=-1,vmax=1,cmap="RdBu_r")
    ax.set_xticks(range(len(corr)),corr.columns,rotation=35,ha="right")
    ax.set_yticks(range(len(corr)),corr.index); ax.grid(False)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j,i,f"{corr.iloc[i,j]:.2f}",ha="center",va="center",color="white" if abs(corr.iloc[i,j])>.65 else "black")
    fig.colorbar(image,ax=ax,shrink=.7,label="Correlación de rentabilidades mensuales USD")
    save(fig,directory/"correlations_usd.png")
    fig,ax=plt.subplots(figsize=(8,4.5))
    for i,name in enumerate(stats.index):
        ax.scatter(stats.loc[name,"vol_annual"]*100,stats.loc[name,"geometric_annual_return"]*100,color=colors[i],s=55)
        ax.annotate(name,(stats.loc[name,"vol_annual"]*100,stats.loc[name,"geometric_annual_return"]*100),xytext=(5,-12) if name=='Cartera' else (5,4),textcoords="offset points",fontsize=11)
    ax.set(title="Rentabilidad geométrica y volatilidad en USD",xlabel="Volatilidad anualizada (%)",ylabel="Rentabilidad anualizada geométrica (%)")
    save(fig,directory/"risk_return_usd.png")
    table=capm_table[capm_table.inference=="OLS"]
    beta=table[table.term=="Mkt-RF"].set_index("asset")
    alpha=table[table.term=="alpha"].set_index("asset")
    fig,ax=plt.subplots(figsize=(9,5))
    limits=np.array([min(0,beta.coefficient.min()-.2),beta.coefficient.max()+.2])
    ax.plot(limits,100*(factors.RF.mean()+limits*factors['Mkt-RF'].mean()),color="#162f45",label="SML: media RF + beta × media prima de mercado")
    for i,name in enumerate(combined):
        b=float(beta.loc[name,"coefficient"]); observed=combined[name].mean()*100
        required=(factors.RF.mean()+b*factors['Mkt-RF'].mean())*100
        significant=alpha.loc[name,"p_value"]<.05
        ax.scatter(b,observed,s=65,facecolor=colors[i] if significant else "white",edgecolor=colors[i],marker="o" if beta.loc[name,"p_value"]<.05 else "s")
        ax.plot([b,b],[required,observed],color=colors[i],linestyle=":",linewidth=1)
        offset=(10,-22) if name=='Cartera' else (10,15) if name=='Bolsa mundial' else (5,6 if i%2==0 else -12)
        ax.annotate(name,(b,observed),xytext=offset,textcoords="offset points",fontsize=11,
                    bbox={'facecolor':'white','edgecolor':'none','alpha':.85,'pad':1})
    ax.set(xlabel="Beta CAPM estimada",ylabel="Rentabilidad media mensual (%)")
    handles,labels=ax.get_legend_handles_labels()
    handles += [Line2D([],[],marker='o',linestyle='',color='gray',label='Relleno: alfa significativo al 5 %'),Line2D([],[],marker='s',linestyle='',markerfacecolor='white',color='gray',label='Cuadrado: beta no significativa al 5 %')]
    ax.legend(handles=handles, fontsize=9, loc='lower center', bbox_to_anchor=(.5, 1.01), frameon=False)
    save(fig,directory/"sml_usd.png")
    n=len(frames['returns_usd'].columns);cols=min(3,n);rows=math.ceil(n/cols)
    fig,axes=plt.subplots(rows,cols,figsize=(8,3.7*rows),sharex=True,squeeze=False)
    for ax in list(axes.flat)[n:]:ax.set_visible(False)
    for ax,name,color in zip(axes.flat,frames['returns_usd'],colors):
        x=factors['Mkt-RF']*100; y=(combined[name]-factors.RF)*100
        b=beta.loc[name,'coefficient']; a=alpha.loc[name,'coefficient']*100
        ax.scatter(x,y,color=color,s=13,alpha=.7); xx=np.array([x.min(),x.max()]);ax.plot(xx,a+b*xx,color='#162f45')
        ax.set(title=name,xlabel='Mkt-RF mensual (%)',ylabel='Exceso del activo (%)')
    fig.tight_layout();save(fig,directory/'capm_scatter_usd.png')
