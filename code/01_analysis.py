import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import *
from pathlib import Path
import pandas as pd, numpy as np, statsmodels.api as sm, json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
setup_font()
OUT=str(CHARTS)+'/'; NUM=str(OUTPUT)+'/'
df=pd.read_csv(TRAIN_CSV,index_col=0).drop(columns='id')
res={}
res['n']=len(df); res['sat_rate']=float((df.satisfaction=='satisfied').mean())
svc=['Inflight wifi service','Ease of Online booking','Online boarding','Seat comfort','Inflight entertainment','On-board service','Leg room service','Baggage handling','Checkin service','Inflight service','Cleanliness','Food and drink','Gate location','Departure/Arrival time convenient']
res['zero_share']={c:float((df[c]==0).mean()) for c in svc}
d=df.dropna(subset=['Arrival Delay in Minutes'])
m=sm.OLS(d['Arrival Delay in Minutes'],sm.add_constant(d[['Departure Delay in Minutes']])).fit()
na=df['Arrival Delay in Minutes'].isna()
df.loc[na,'Arrival Delay in Minutes']=m.predict(sm.add_constant(df.loc[na,['Departure Delay in Minutes']],has_constant='add'))
res['na_n']=int(na.sum())
q1,q3=df['Flight Distance'].quantile([.25,.75]); df['Flight Distance']=df['Flight Distance'].clip(q1-1.5*(q3-q1),q3+1.5*(q3-q1))
X=df.drop(columns='satisfaction'); y=(df.satisfaction=='satisfied').astype(int)
Xtr,Xva,ytr,yva=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
def prep(a,b):
    a=pd.get_dummies(a,drop_first=True);b=pd.get_dummies(b,drop_first=True);a,b=a.align(b,join='left',axis=1,fill_value=0)
    return sm.add_constant(a).astype(float),sm.add_constant(b).astype(float)
a,b=prep(Xtr,Xva); mb=sm.Logit(ytr,a).fit(disp=0); pb=mb.predict(b)
res['base']=(accuracy_score(yva,pb>=.5),roc_auc_score(yva,pb))
Xtr=Xtr.drop(columns='Arrival Delay in Minutes');Xva=Xva.drop(columns='Arrival Delay in Minutes')
def c1(x): return 'bad' if x<=1 else 'normal' if x<=3 else 'good'
def c2(x): return 'bad_or_normal' if x<=3 else 'good'
s1=["Food and drink","Leg room service","Checkin service","Cleanliness"]
s2=["Inflight wifi service","Ease of Online booking","Online boarding","Seat comfort","Inflight entertainment","On-board service","Baggage handling","Inflight service","Departure/Arrival time convenient"]
for D in (Xtr,Xva):
    for c in s1: D[c]=D[c].apply(c1)
    for c in s2: D[c]=D[c].apply(c2)
a2,b2=prep(Xtr,Xva); mf=sm.Logit(ytr,a2).fit(disp=0); pf=mf.predict(b2)
res['fe']=(accuracy_score(yva,pf>=.5),roc_auc_score(yva,pf))
ci=mf.conf_int(); t=pd.DataFrame({'OR':np.exp(mf.params),'lo':np.exp(ci[0]),'hi':np.exp(ci[1]),'p':mf.pvalues}).drop(index='const')
t.to_csv(NUM+'or_table.csv',encoding='utf-8-sig'); print(t.sort_values('OR',ascending=False).round(2).to_string())
def sim(cols):
    B=b2.copy()
    for c in cols: B[c]=1.0
    return mf.predict(B).mean()
base_rate=float(pf.mean()); res['pred_base']=base_rate
res['sim']={n:float(sim(c)-base_rate) for n,c in {'wifi':['Inflight wifi service_good'],'board':['Online boarding_good'],'checkin':['Checkin service_good'],'all3':['Inflight wifi service_good','Online boarding_good','Checkin service_good']}.items()}
res['actual_good_share']={c:float((df[c]>=4).mean()) for c in ['Inflight wifi service','Online boarding','Checkin service']}
print(res)
json.dump(res,open(NUM+'res.json','w',encoding='utf-8'),ensure_ascii=False,indent=1,default=float)
BL='#1F3A5F';OR='#E07B39';GR='#9AA5B1'
lab={'Inflight wifi service_good':'기내 와이파이 4점↑','Online boarding_good':'온라인 탑승 4점↑','Checkin service_good':'체크인 4점↑','Leg room service_good':'다리 공간 4점↑','Seat comfort_good':'좌석 편안함 4점↑','Baggage handling_good':'수하물 처리 4점↑','On-board service_good':'탑승 서비스 4점↑','Inflight service_good':'기내 서비스 4점↑','Inflight entertainment_good':'기내 엔터테인먼트 4점↑','Ease of Online booking_good':'온라인 예약 4점↑','Departure/Arrival time convenient_good':'출·도착 시간 편리 4점↑'}
tt=t.loc[list(lab)].sort_values('OR')
fig,ax=plt.subplots(figsize=(9,5.2))
ax.barh([lab[i] for i in tt.index],tt.OR,color=[OR if v>=2 else GR for v in tt.OR],height=.62)
ax.errorbar(tt.OR,range(len(tt)),xerr=[tt.OR-tt.lo,tt.hi-tt.OR],fmt='none',ecolor='#333',capsize=3,lw=1)
for i,v in enumerate(tt.OR): ax.text(tt.hi.iloc[i]+.12,i,f'{v:.1f}배',va='center',fontsize=11,fontweight='bold')
ax.axvline(1,color='#333',lw=1); ax.set_xlim(0,tt.hi.max()+1.2); ax.set_xlabel('만족 오즈비 (95% 신뢰구간)')
for s in ['top','right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT+'odds_ratio.png',dpi=200); plt.close()
fig,axs=plt.subplots(1,3,figsize=(11,3.6),sharey=True)
for ax,c,tl in zip(axs,['Type of Travel','Customer Type','Class'],['여행 목적','고객 유형','좌석 등급']):
    g=(df.groupby(c)['satisfaction'].apply(lambda s:(s=='satisfied').mean())*100).sort_values()
    ax.bar(g.index.str.replace(' Travel','').str.replace(' Customer',''),g.values,color=BL)
    for i,v in enumerate(g.values): ax.text(i,v+1.5,f'{v:.0f}%',ha='center',fontweight='bold')
    ax.set_title(tl); ax.set_ylim(0,100)
    for s in ['top','right']: ax.spines[s].set_visible(False)
axs[0].set_ylabel('만족 비율 (%)'); plt.tight_layout(); plt.savefig(OUT+'segments.png',dpi=200); plt.close()
fig,ax=plt.subplots(figsize=(6,3.8))
g=df[df['Inflight wifi service']>0].groupby('Inflight wifi service')['satisfaction'].apply(lambda s:(s=='satisfied').mean()*100)
ax.bar(g.index.astype(str),g.values,color=[GR]*3+[OR]*2)
for i,v in enumerate(g.values): ax.text(i,v+1.5,f'{v:.0f}%',ha='center',fontweight='bold')
ax.set_xlabel('와이파이 점수 (0점 제외)'); ax.set_ylabel('만족 비율 (%)'); ax.set_ylim(0,100)
for s in ['top','right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT+'wifi.png',dpi=200); plt.close()
fig,ax=plt.subplots(figsize=(5,3.6)); x=np.arange(2);w=.35
bv=[res['base'][0]*100,res['base'][1]*100]; fv=[res['fe'][0]*100,res['fe'][1]*100]
ax.bar(x-w/2,bv,w,color=GR,label='Baseline');ax.bar(x+w/2,fv,w,color=OR,label='구간화 적용')
for i in range(2):
    ax.text(i-w/2,bv[i]+.3,f'{bv[i]:.1f}',ha='center');ax.text(i+w/2,fv[i]+.3,f'{fv[i]:.1f}',ha='center',fontweight='bold')
ax.set_xticks(x);ax.set_xticklabels(['Accuracy (%)','AUC (×100)']);ax.set_ylim(80,100);ax.legend(frameon=False,loc='upper left')
for s in ['top','right']: ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(OUT+'model.png',dpi=200); plt.close()
