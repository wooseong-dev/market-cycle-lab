from __future__ import annotations
from functools import lru_cache
import hashlib
import numpy as np
import pandas as pd
import yfinance as yf

def _fallback_history(symbol, years=5):
    days=years*365; end=pd.Timestamp.utcnow().normalize(); idx=pd.date_range(end=end, periods=days, freq='D')
    seed=int(hashlib.sha256(symbol.encode()).hexdigest()[:8],16); rng=np.random.default_rng(seed)
    base={'BTC-USD':42000,'ETH-USD':2400,'SOL-USD':120,'SPY':450,'QQQ':380,'GLD':190,'CL=F':75,'DX-Y.NYB':103}.get(symbol,100)
    drift=0.00025 if 'USD' in symbol or symbol in ['SPY','QQQ'] else 0.00008
    vol=0.035 if 'USD' in symbol else 0.012
    returns=rng.normal(drift,vol,size=days); wave=np.sin(np.linspace(0,18,days))*0.003
    prices=base*np.exp(np.cumsum(returns+wave))
    return pd.DataFrame({'Close':prices}, index=idx)

@lru_cache(maxsize=64)
def get_history(symbol, period='5y'):
    try:
        df=yf.download(symbol, period=period, interval='1d', auto_adjust=True, progress=False, threads=False)
        if df is None or df.empty: return _fallback_history(symbol), True
        if isinstance(df.columns, pd.MultiIndex): df.columns=[c[0] for c in df.columns]
        if 'Close' not in df.columns: return _fallback_history(symbol), True
        df=df[['Close']].dropna(); df.index=pd.to_datetime(df.index)
        if df.empty: return _fallback_history(symbol), True
        return df, False
    except Exception:
        return _fallback_history(symbol), True
