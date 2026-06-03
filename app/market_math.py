from __future__ import annotations
from datetime import timedelta
import math
import pandas as pd
import numpy as np

def pct(a,b):
    if a is None or b in (None,0) or pd.isna(a) or pd.isna(b): return None
    return (a/b-1)*100

def safe_float(v):
    try:
        if v is None or pd.isna(v): return None
        return float(v)
    except Exception: return None

def nearest_price(df: pd.DataFrame, target_date) -> tuple[float | None, str | None]:
    if df.empty:
        return None, None

    data = df.copy()

    # index timezone 제거
    index_naive = pd.to_datetime(data.index).tz_localize(None)
    target = pd.Timestamp(target_date).tz_localize(None)

    # TimedeltaIndex는 .abs()가 안 되는 환경이 있어서 numpy로 처리
    diffs = np.abs((index_naive - target).days)

    nearest_pos = int(np.argmin(diffs))
    row = data.iloc[nearest_pos]

    return safe_float(row["Close"]), data.index[nearest_pos].strftime("%Y-%m-%d")

def drawdown_periods(close, threshold_pct=0.0):
    if close.empty: return []
    dd=(close/close.cummax()-1)*100
    periods=[]; in_p=False; start=None; trough=None; trough_dd=0.0
    for dt,val in dd.items():
        cond=val < threshold_pct
        if cond and not in_p:
            in_p=True; start=dt; trough=dt; trough_dd=val
        if in_p and val < trough_dd:
            trough_dd=val; trough=dt
        if in_p and not cond:
            periods.append({'start':start,'end':dt,'trough':trough,'duration_days':(dt-start).days,'max_drawdown_pct':float(trough_dd)})
            in_p=False
    if in_p:
        end=close.index[-1]
        periods.append({'start':start,'end':None,'trough':trough,'duration_days':(end-start).days,'max_drawdown_pct':float(trough_dd)})
    return periods

def calculate_metrics(df):
    if df.empty or 'Close' not in df: return None
    df=df.dropna(subset=['Close']).copy()
    if df.empty: return None
    close=df['Close']
    current=safe_float(close.iloc[-1]); current_date=close.index[-1].strftime('%Y-%m-%d')
    ath=safe_float(close.max()); ath_date=close.idxmax().strftime('%Y-%m-%d')
    target=close.index[-1].tz_localize(None)-timedelta(days=365)
    one_y, one_y_date = nearest_price(df,target)
    dd=(close/close.cummax()-1)*100
    below=drawdown_periods(close,0.0); bear=drawdown_periods(close,-20.0)
    completed=[p for p in below if p['end'] is not None]
    avg_d=sum(p['duration_days'] for p in completed)/len(completed) if completed else 0
    max_d=max([p['duration_days'] for p in below], default=0)
    current_period=below[-1] if below and below[-1]['end'] is None else None
    current_days=current_period['duration_days'] if current_period else 0
    vol=None
    if len(close)>90:
        vol=safe_float(close.pct_change().dropna().tail(90).std()*math.sqrt(365)*100)
    current_dd=safe_float(dd.iloc[-1]); one_change=pct(current,one_y)
    risk=50
    if current_dd is not None: risk += min(abs(current_dd),50)*0.6
    if vol is not None: risk += min(vol,100)*0.25
    if one_change is not None and (one_change>50 or one_change<-30): risk += 8
    risk=max(0,min(100,round(risk)))
    if current_dd is not None and current_dd > -5:
        label='Near High'; desc='전고점 부근입니다. 추세는 강하지만 기대가 많이 반영됐을 수 있습니다.'
    elif current_dd is not None and current_dd > -20:
        label='Cooling'; desc='일반 조정 구간입니다. 과열이 식는 과정인지 구조 변화인지 구분해야 합니다.'
    elif current_dd is not None and current_dd > -50:
        label='Deep Drawdown'; desc='깊은 하락 구간입니다. 평균 회복 기간과 유동성 환경을 함께 봐야 합니다.'
    else:
        label='Capitulation Zone'; desc='극단적 하락 구간입니다. 반등 가능성과 추가 붕괴 리스크가 동시에 커집니다.'
    return {'current_price':current,'current_date':current_date,'ath_price':ath,'ath_date':ath_date,'ath_drawdown':pct(current,ath),'current_drawdown':current_dd,'one_year_price':one_y,'one_year_date':one_y_date,'one_year_change':one_change,'total_return':pct(current,safe_float(close.iloc[0])),'max_drawdown':safe_float(dd.min()),'current_dd_days':current_days,'avg_dd_duration':avg_d,'max_dd_duration':max_d,'bear_period_count':len(bear),'volatility_90d':vol,'risk_score':risk,'cycle_label':label,'cycle_desc_ko':desc}

def to_chart_points(df, limit=420):
    if df.empty: return []
    data=df.dropna(subset=['Close']).copy()
    if len(data)>limit:
        data=data.iloc[::max(1,len(data)//limit)]
    return [{'date':idx.strftime('%Y-%m-%d'),'close':round(float(row['Close']),4)} for idx,row in data.iterrows()]
