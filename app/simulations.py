from __future__ import annotations

from typing import Any
import pandas as pd


def _filter_years(df: pd.DataFrame, years: int | float | None):
    if df is None or df.empty or 'Close' not in df:
        return pd.DataFrame()
    data = df.dropna(subset=['Close']).copy()
    if data.empty:
        return data
    if years and years > 0:
        end = data.index.max()
        start = end - pd.DateOffset(years=int(years))
        data = data[data.index >= start]
    return data


def _date_str(value) -> str:
    try:
        return pd.Timestamp(value).strftime('%Y-%m-%d')
    except Exception:
        return '-'


def _max_drawdown(values: list[float]) -> float | None:
    if not values:
        return None
    peak = values[0]
    max_dd = 0.0
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, (value / peak - 1) * 100)
    return max_dd


def simulate_dca(df: pd.DataFrame, amount: float = 100_000, frequency: str = 'monthly', years: int = 3) -> dict[str, Any]:
    data = _filter_years(df, years)
    if data.empty:
        return {'available': False, 'summary': '가격 데이터가 부족합니다.'}
    close = data['Close'].dropna()
    if close.empty:
        return {'available': False, 'summary': '가격 데이터가 부족합니다.'}

    if frequency == 'weekly':
        buy_prices = close.resample('W').first().dropna()
        frequency_label = '매주'
    else:
        buy_prices = close.resample('MS').first().dropna()
        frequency_label = '매월'

    units = 0.0
    invested = 0.0
    for _, price in buy_prices.items():
        price = float(price)
        if price > 0:
            units += amount / price
            invested += amount

    current_price = float(close.iloc[-1])
    current_value = units * current_price
    profit = current_value - invested
    return_pct = (current_value / invested - 1) * 100 if invested else None
    avg_cost = invested / units if units else None

    running_units = 0.0
    buy_pointer = 0
    buys = list(buy_prices.items())
    values = []
    for date, price in close.items():
        while buy_pointer < len(buys) and buys[buy_pointer][0] <= date:
            bp = float(buys[buy_pointer][1])
            if bp > 0:
                running_units += amount / bp
            buy_pointer += 1
        values.append(running_units * float(price))

    return {
        'available': True,
        'frequency': frequency,
        'frequency_label': frequency_label,
        'years': years,
        'amount': amount,
        'buy_count': len(buy_prices),
        'invested': invested,
        'current_price': current_price,
        'current_value': current_value,
        'profit': profit,
        'return_pct': return_pct,
        'avg_cost': avg_cost,
        'max_drawdown': _max_drawdown(values),
        'start_date': _date_str(close.index[0]),
        'end_date': _date_str(close.index[-1]),
        'summary': f'{frequency_label} {amount:,.0f}원씩 {years}년 동안 투자했다면 현재 가치는 약 {current_value:,.0f}원입니다.',
    }


def simulate_peak_buy(df: pd.DataFrame, amount: float = 1_000_000, years: int = 5) -> dict[str, Any]:
    data = _filter_years(df, years)
    if data.empty:
        return {'available': False, 'summary': '가격 데이터가 부족합니다.'}
    close = data['Close'].dropna()
    peak_date = close.idxmax()
    peak_price = float(close.loc[peak_date])
    after_peak = close[close.index >= peak_date]
    current_price = float(close.iloc[-1])
    units = amount / peak_price if peak_price > 0 else 0
    current_value = units * current_price
    profit = current_value - amount
    return_pct = (current_value / amount - 1) * 100 if amount else None
    min_after = float(after_peak.min())
    min_date = after_peak.idxmin()
    max_loss_pct = (min_after / peak_price - 1) * 100 if peak_price else None
    max_loss_value = amount * (max_loss_pct / 100) if max_loss_pct is not None else None
    later = after_peak[(after_peak.index > peak_date) & (after_peak >= peak_price)]
    recovered = not later.empty
    recovery_date = later.index[0] if recovered else None
    recovery_days = (recovery_date - peak_date).days if recovered else None
    holding_days = (close.index[-1] - peak_date).days
    summary = f'최근 {years}년 고점에 투자했다면 현재 수익률은 {return_pct:.2f}%입니다.' if return_pct is not None else '계산할 수 없습니다.'
    return {
        'available': True,
        'years': years,
        'amount': amount,
        'peak_date': _date_str(peak_date),
        'peak_price': peak_price,
        'current_price': current_price,
        'current_value': current_value,
        'profit': profit,
        'return_pct': return_pct,
        'min_after_peak': min_after,
        'min_after_peak_date': _date_str(min_date),
        'max_loss_pct': max_loss_pct,
        'max_loss_value': max_loss_value,
        'recovered': recovered,
        'recovery_date': _date_str(recovery_date) if recovery_date is not None else None,
        'recovery_days': recovery_days,
        'holding_days': holding_days,
        'summary': summary,
    }


def _drawdown_periods(close: pd.Series, threshold: float) -> list[dict[str, Any]]:
    running_peak = close.cummax()
    drawdown = (close / running_peak - 1) * 100
    periods = []
    in_period = False
    start = None
    trough_date = None
    trough_dd = 0.0
    for date, dd in drawdown.items():
        dd = float(dd)
        if not in_period and dd <= threshold:
            in_period = True
            start = date
            trough_date = date
            trough_dd = dd
        elif in_period:
            if dd < trough_dd:
                trough_dd = dd
                trough_date = date
            if dd >= -0.1:
                periods.append({'start': start, 'end': date, 'trough_date': trough_date, 'trough_dd': trough_dd, 'duration_days': (date - start).days, 'recovered': True})
                in_period = False
    if in_period and start is not None:
        end = drawdown.index[-1]
        periods.append({'start': start, 'end': end, 'trough_date': trough_date, 'trough_dd': trough_dd, 'duration_days': (end - start).days, 'recovered': False})
    return periods


def simulate_bear_survival(df: pd.DataFrame, years: int = 5) -> dict[str, Any]:
    data = _filter_years(df, years)
    if data.empty:
        return {'available': False, 'summary': '가격 데이터가 부족합니다.'}
    close = data['Close'].dropna()
    running_peak = close.cummax()
    current_dd = float((close.iloc[-1] / running_peak.iloc[-1] - 1) * 100)
    max_dd = float(((close / running_peak - 1) * 100).min())
    stats = []
    for threshold in [-10, -20, -30, -50]:
        periods = _drawdown_periods(close, threshold)
        durations = [p['duration_days'] for p in periods]
        depths = [p['trough_dd'] for p in periods]
        stats.append({'threshold': threshold, 'count': len(periods), 'recovered_count': sum(1 for p in periods if p['recovered']), 'avg_duration': sum(durations)/len(durations) if durations else None, 'max_duration': max(durations) if durations else None, 'avg_depth': sum(depths)/len(depths) if depths else None, 'max_depth': min(depths) if depths else None})
    if current_dd <= -30:
        label = '깊은 하락장 구간'
    elif current_dd <= -20:
        label = '약세장 구간'
    elif current_dd <= -10:
        label = '조정 구간'
    else:
        label = '고점 부근 또는 일반 변동 구간'
    return {'available': True, 'years': years, 'start_date': _date_str(close.index[0]), 'end_date': _date_str(close.index[-1]), 'current_drawdown': current_dd, 'max_drawdown': max_dd, 'label': label, 'stats': stats, 'summary': f'최근 {years}년 기준 현재 위치는 {label}에 가깝습니다.'}


def months_to_target(target: float, initial: float, monthly: float, annual_rate: float, max_months: int = 1200) -> dict[str, Any]:
    monthly_rate = (1 + annual_rate / 100) ** (1 / 12) - 1
    value = initial
    if value >= target:
        return {'annual_rate': annual_rate, 'months': 0, 'years': 0, 'final_value': value, 'total_contribution': initial, 'available': True}
    for month in range(1, max_months + 1):
        value = value * (1 + monthly_rate) + monthly
        if value >= target:
            return {'annual_rate': annual_rate, 'months': month, 'years': month / 12, 'final_value': value, 'total_contribution': initial + monthly * month, 'available': True}
    return {'annual_rate': annual_rate, 'months': None, 'years': None, 'final_value': value, 'total_contribution': initial + monthly * max_months, 'available': False}


def simulate_target_goal(target: float = 100_000_000, initial: float = 5_000_000, monthly: float = 300_000, custom_rate: float = 12) -> dict[str, Any]:
    rates = [5, 10, 20]
    if custom_rate not in rates:
        rates.append(custom_rate)
    return {'target': target, 'initial': initial, 'monthly': monthly, 'custom_rate': custom_rate, 'scenarios': [months_to_target(target, initial, monthly, rate) for rate in rates], 'summary': '미래 수익률은 예측이 아니라 가정입니다. 시나리오로만 참고하세요.'}


def parse_symbols_and_weights(symbols: str, weights: str):
    symbol_list = [x.strip().upper() for x in symbols.split(',') if x.strip()] or ['BTC-USD', 'QQQ', 'GLD']
    weight_list = []
    for x in weights.split(','):
        try:
            weight_list.append(float(x.strip()))
        except Exception:
            pass
    if len(weight_list) != len(symbol_list):
        weight_list = [100 / len(symbol_list)] * len(symbol_list)
    total = sum(weight_list) or 100
    normalized = [w / total for w in weight_list]
    return symbol_list, weight_list, normalized
