from __future__ import annotations

import html
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from usfddk.engine import execute_rebalance
from usfddk.metrics import compute_metrics
from usfddk.models import MarketPanel

PASSIVE_BENCHMARK_KEY = "QQQ90_SHY10"

PAPER_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _weight_dict(target: pd.Series) -> dict[str, float]:
    clean = target.fillna(0.0).clip(lower=0.0)
    return {str(k): float(v) for k, v in clean.items() if float(v) > 1e-12}


def _new_state(
    *, mode: str, initial_cash: float, cost_bps: float, strategy_name: str
) -> dict[str, Any]:
    if mode not in {"live", "replay"}:
        raise ValueError("paper mode 必須是 live 或 replay")
    if initial_cash <= 0:
        raise ValueError("初始資金必須大於零")
    return {
        "schema_version": PAPER_SCHEMA_VERSION,
        "mode": mode,
        "strategy": str(strategy_name),
        "execution_clock": "signal at close t; rebalance at adjusted open t+1",
        "created_at": _now(),
        "updated_at": _now(),
        "initial_cash": float(initial_cash),
        "cash": float(initial_cash),
        "cost_bps": float(cost_bps),
        "as_of": None,
        "holdings": {},
        "pending_order": None,
        "order_history": [],
        "transactions": [],
        "equity_curve": [],
        "adjustment_rebases": [],
        "total_costs": 0.0,
        "snapshot_sha256": "",
    }


def _series_from_holdings(state: dict[str, Any], symbols: list[str]) -> pd.Series:
    raw = state.get("holdings", {})
    return pd.Series(
        {symbol: float(raw.get(symbol, {}).get("shares", 0.0)) for symbol in symbols},
        dtype=float,
    )


def _rebase_adjusted_holdings(
    state: dict[str, Any],
    panel: MarketPanel,
    shares: pd.Series,
    *,
    snapshot_sha256: str,
) -> pd.Series:
    """Preserve recorded market value when a vendor revises adjusted price history.

    Adjusted OHLC is a total-return unit, not a broker share price. Dividends, splits,
    and vendor repairs can change the adjusted close already stored for ``as_of``.
    Re-scaling units prevents that backward revision from becoming fake forward P&L.
    """
    holdings = state.get("holdings", {})
    unknown = set(holdings) - set(shares.index)
    if unknown:
        raise ValueError("paper 持倉不在目前策略代號中：" + ", ".join(sorted(unknown)))
    if not holdings:
        state.setdefault("adjustment_rebases", [])
        return shares

    as_of = pd.Timestamp(state["as_of"])
    revised_close = panel.close.loc[as_of, shares.index]
    events = state.setdefault("adjustment_rebases", [])
    prior_snapshot = str(state.get("snapshot_sha256", ""))
    for ticker, position in holdings.items():
        old_units = float(shares[ticker])
        if abs(old_units) <= 1e-12:
            continue
        old_price = float(position.get("last_price", float("nan")))
        new_price = float(revised_close[ticker])
        if not np.isfinite(old_price) or old_price <= 0:
            raise ValueError(f"{ticker} paper 缺少有效的既有調整後收盤價")
        if not np.isfinite(new_price) or new_price <= 0:
            raise ValueError(f"{ticker} 在 {as_of.date()} 缺少修訂後調整收盤價")
        if math.isclose(old_price, new_price, rel_tol=1e-10, abs_tol=1e-10):
            continue
        factor = old_price / new_price
        new_units = old_units * factor
        before_value = old_units * old_price
        after_value = new_units * new_price
        if not np.isfinite(new_units) or new_units <= 0:
            raise ValueError(f"{ticker} 調整後單位重基準無效：{new_units}")
        if not math.isclose(before_value, after_value, rel_tol=1e-12, abs_tol=1e-8):
            raise RuntimeError(f"{ticker} 單位重基準未保持市值")
        shares[ticker] = new_units
        events.append(
            {
                "detected_at": _now(),
                "as_of": as_of.strftime("%Y-%m-%d"),
                "ticker": str(ticker),
                "reason": "adjusted_price_history_revision",
                "old_adjusted_close": old_price,
                "new_adjusted_close": new_price,
                "unit_factor": factor,
                "units_before": old_units,
                "units_after": new_units,
                "market_value_before": before_value,
                "market_value_after": after_value,
                "snapshot_before": prior_snapshot,
                "snapshot_after": str(snapshot_sha256),
            }
        )
    return shares


def _queue_order(state: dict[str, Any], day: pd.Timestamp, target: pd.Series) -> None:
    weights = _weight_dict(target)
    order = {
        "signal_date": day.strftime("%Y-%m-%d"),
        "queued_at": day.strftime("%Y-%m-%d"),
        "execute_after": day.strftime("%Y-%m-%d"),
        "target_weights": weights,
        "status": "pending",
    }
    state["pending_order"] = order


def _record_execution(
    state: dict[str, Any],
    *,
    day: pd.Timestamp,
    prices: pd.Series,
    old_shares: pd.Series,
    new_shares: pd.Series,
    traded_dollars: pd.Series,
    turnover: float,
    cost: float,
) -> None:
    pending = dict(state["pending_order"])
    total_traded = float(traded_dollars.abs().sum())
    for ticker, dollars in traded_dollars.items():
        if abs(float(dollars)) <= 1e-8:
            continue
        allocation = abs(float(dollars)) / total_traded if total_traded > 0 else 0.0
        delta = float(new_shares[ticker] - old_shares[ticker])
        state["transactions"].append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "signal_date": pending["signal_date"],
                "ticker": str(ticker),
                "side": "BUY" if delta > 0 else "SELL",
                "shares": abs(delta),
                "price": float(prices[ticker]),
                "notional": abs(float(dollars)),
                "cost": float(cost * allocation),
            }
        )
    pending.update(
        {
            "status": "filled",
            "filled_at": day.strftime("%Y-%m-%d"),
            "turnover": float(turnover),
            "cost": float(cost),
        }
    )
    state["order_history"].append(pending)
    state["pending_order"] = None


def _append_mark(
    state: dict[str, Any],
    *,
    day: pd.Timestamp,
    shares: pd.Series,
    close_prices: pd.Series,
    turnover: float,
    cost: float,
) -> None:
    equity = float(state["cash"] + (shares * close_prices.reindex(shares.index).fillna(0.0)).sum())
    if not np.isfinite(equity) or equity <= 0:
        raise RuntimeError(f"{day.date()} paper 權益無效：{equity}")
    previous_peak = max(
        [float(row["equity"]) for row in state["equity_curve"]] + [equity]
    )
    state["equity_curve"].append(
        {
            "date": day.strftime("%Y-%m-%d"),
            "equity": equity,
            "cash": float(state["cash"]),
            "turnover": float(turnover),
            "cost": float(cost),
            "drawdown": float(equity / previous_peak - 1.0),
        }
    )


def update_paper_state(
    panel: MarketPanel,
    target_signals: pd.DataFrame,
    *,
    state: dict[str, Any] | None = None,
    mode: str = "live",
    replay_from: str | None = None,
    initial_cash: float = 100_000.0,
    cost_bps: float = 10.0,
    snapshot_sha256: str = "",
    strategy_name: str = "ETF 雙動量",
) -> dict[str, Any]:
    """Create or advance a fractional-share paper account using unseen bars only.

    Live initialization starts in cash at the current close and queues the latest
    completed monthly signal for the next *future* bar. Replay is deliberately marked
    as historical and is never presented as forward evidence.
    """
    symbols = [str(x) for x in target_signals.columns if x in panel.close.columns]
    if not symbols:
        raise ValueError("paper strategy 與行情沒有共同代號")
    signals = target_signals.reindex(index=panel.close.index, columns=symbols)
    created = state is None
    if created:
        if replay_from:
            mode = "replay"
        state = _new_state(
            mode=mode,
            initial_cash=initial_cash,
            cost_bps=cost_bps,
            strategy_name=strategy_name,
        )
    assert state is not None
    if int(state.get("schema_version", -1)) != PAPER_SCHEMA_VERSION:
        raise ValueError("不支援的 paper state schema")
    if float(state["cost_bps"]) != float(cost_bps):
        raise ValueError("成交成本與既有 paper 帳戶不一致")
    if str(state.get("strategy")) != str(strategy_name):
        raise ValueError("策略與既有 paper 帳戶不一致；請使用新的 state 路徑")

    index = panel.close.index
    if created and state["mode"] == "live":
        day = pd.Timestamp(index[-1])
        state["as_of"] = day.strftime("%Y-%m-%d")
        state["started_at"] = day.strftime("%Y-%m-%d")
        shares = pd.Series(0.0, index=symbols)
        _append_mark(
            state,
            day=day,
            shares=shares,
            close_prices=panel.close.loc[day, symbols],
            turnover=0.0,
            cost=0.0,
        )
        completed = signals.loc[:day].dropna(how="all")
        if len(completed):
            _queue_order(state, day, completed.iloc[-1])
            state["pending_order"]["signal_date"] = pd.Timestamp(
                completed.index[-1]
            ).strftime("%Y-%m-%d")
        days = pd.DatetimeIndex([])
    else:
        if created:
            start = pd.Timestamp(replay_from).normalize() if replay_from else pd.Timestamp(index[0])
            days = index[index >= start]
            if not len(days):
                raise ValueError("replay 起點晚於資料截止日")
            state["started_at"] = pd.Timestamp(days[0]).strftime("%Y-%m-%d")
            prior = signals.loc[signals.index < days[0]].dropna(how="all")
            if len(prior):
                _queue_order(state, pd.Timestamp(prior.index[-1]), prior.iloc[-1])
        else:
            as_of = pd.Timestamp(state["as_of"])
            if panel.end < as_of:
                raise ValueError("行情截止日早於 paper 帳戶進度，拒絕時間倒退")
            days = index[index > as_of]

        shares = _series_from_holdings(state, symbols)
        if not created:
            shares = _rebase_adjusted_holdings(
                state,
                panel,
                shares,
                snapshot_sha256=snapshot_sha256,
            )
        for day in days:
            day = pd.Timestamp(day)
            day_open = panel.open.loc[day, symbols]
            day_close = panel.close.loc[day, symbols]
            held = shares != 0
            if bool(day_open[held].isna().any()) or bool(day_close[held].isna().any()):
                missing = list(day_open.index[held & (day_open.isna() | day_close.isna())])
                raise ValueError(f"{day.date()} paper 持倉遇到缺價：{missing}")
            turnover = 0.0
            cost = 0.0
            pending = state.get("pending_order")
            if pending and day > pd.Timestamp(pending["execute_after"]):
                target = pd.Series(pending["target_weights"], dtype=float).reindex(
                    symbols, fill_value=0.0
                )
                old_shares = shares.copy()
                try:
                    shares, cash, turnover, cost, traded = execute_rebalance(
                        shares,
                        float(state["cash"]),
                        day_open,
                        target,
                        cost_bps=float(state["cost_bps"]),
                    )
                except ValueError as exc:
                    raise ValueError(f"{day.date()} paper 成交失敗：{exc}") from exc
                state["cash"] = float(cash)
                state["total_costs"] = float(state["total_costs"] + cost)
                _record_execution(
                    state,
                    day=day,
                    prices=day_open,
                    old_shares=old_shares,
                    new_shares=shares,
                    traded_dollars=traded,
                    turnover=turnover,
                    cost=cost,
                )
            _append_mark(
                state,
                day=day,
                shares=shares,
                close_prices=day_close,
                turnover=turnover,
                cost=cost,
            )
            signal = signals.loc[day]
            if signal.notna().any():
                _queue_order(state, day, signal)
            state["as_of"] = day.strftime("%Y-%m-%d")

    holdings: dict[str, dict[str, float]] = {}
    close_day = pd.Timestamp(state["as_of"])
    last_close = panel.close.loc[close_day, symbols]
    for ticker, quantity in shares.items():
        if abs(float(quantity)) <= 1e-12:
            continue
        market_value = float(quantity * last_close[ticker])
        holdings[str(ticker)] = {
            "shares": float(quantity),
            "last_price": float(last_close[ticker]),
            "market_value": market_value,
        }
    state["holdings"] = holdings
    state["updated_at"] = _now()
    state["snapshot_sha256"] = str(snapshot_sha256)
    return state


def paper_metrics(state: dict[str, Any]) -> dict[str, float]:
    rows = state.get("equity_curve", [])
    if not rows:
        return {"equity": float(state["cash"]), "pnl": 0.0, "return": 0.0, "max_drawdown": 0.0}
    frame = pd.DataFrame(rows)
    frame.index = pd.to_datetime(frame["date"])
    equity = frame["equity"].astype(float)
    returns = equity.pct_change(fill_method=None).fillna(0.0)
    turnover = frame["turnover"].astype(float)
    metrics = compute_metrics(equity, returns, turnover)
    current = float(equity.iloc[-1])
    return {
        **metrics,
        "equity": current,
        "pnl": current - float(state["initial_cash"]),
        "return": current / float(state["initial_cash"]) - 1.0,
    }


def forward_paper_evidence(
    strategy_state: dict[str, Any],
    benchmark_states: dict[str, dict[str, Any]],
    *,
    minimum_sessions: int = 252,
    minimum_filled_rebalances: int = 6,
) -> dict[str, Any]:
    """Evaluate forward-only promotion gates against synchronized ETF paper accounts."""
    if minimum_sessions <= 0 or minimum_filled_rebalances <= 0:
        raise ValueError("LIVE 門檻必須大於零")
    missing = {"SPY", "QQQ", PASSIVE_BENCHMARK_KEY} - set(benchmark_states)
    if missing:
        raise ValueError("缺少 LIVE benchmark：" + ", ".join(sorted(missing)))
    if strategy_state.get("mode") != "live":
        raise ValueError("主策略必須是 LIVE paper")

    identity_fields = ("mode", "started_at", "as_of", "snapshot_sha256")
    for ticker, state in benchmark_states.items():
        mismatched = [
            field
            for field in identity_fields
            if str(state.get(field)) != str(strategy_state.get(field))
        ]
        if mismatched:
            raise ValueError(f"{ticker} benchmark 與主策略不同步：{', '.join(mismatched)}")
        if float(state.get("initial_cash", 0.0)) != float(
            strategy_state.get("initial_cash", 0.0)
        ):
            raise ValueError(f"{ticker} benchmark 初始資金與主策略不同")
        if float(state.get("cost_bps", 0.0)) != float(strategy_state.get("cost_bps", 0.0)):
            raise ValueError(f"{ticker} benchmark 成本與主策略不同")

    strategy_metrics = paper_metrics(strategy_state)
    benchmark_metrics = {
        ticker: paper_metrics(state) for ticker, state in benchmark_states.items()
    }
    forward_sessions = max(len(strategy_state.get("equity_curve", [])) - 1, 0)
    filled_rebalances = sum(
        str(order.get("status")) == "filled"
        for order in strategy_state.get("order_history", [])
    )
    sample_ready = (
        forward_sessions >= minimum_sessions
        and filled_rebalances >= minimum_filled_rebalances
    )
    gates = {
        "at_least_252_forward_sessions": forward_sessions >= minimum_sessions,
        "at_least_6_filled_rebalances": (
            filled_rebalances >= minimum_filled_rebalances
        ),
        "positive_return_after_costs": (
            sample_ready and strategy_metrics["return"] > 0.0
        ),
        "beats_spy_total_return": (
            sample_ready
            and strategy_metrics["return"] > benchmark_metrics["SPY"]["return"]
        ),
        "beats_passive_90_10_total_return": (
            sample_ready
            and strategy_metrics["return"]
            > benchmark_metrics[PASSIVE_BENCHMARK_KEY]["return"]
        ),
        "max_drawdown_no_worse_than_spy": (
            sample_ready
            and strategy_metrics["max_drawdown"]
            >= benchmark_metrics["SPY"]["max_drawdown"]
        ),
        "max_drawdown_no_worse_than_passive_90_10": (
            sample_ready
            and strategy_metrics["max_drawdown"]
            >= benchmark_metrics[PASSIVE_BENCHMARK_KEY]["max_drawdown"]
        ),
    }
    return {
        "minimum_sessions": int(minimum_sessions),
        "minimum_filled_rebalances": int(minimum_filled_rebalances),
        "forward_sessions": int(forward_sessions),
        "filled_rebalances": int(filled_rebalances),
        "remaining_sessions": int(max(minimum_sessions - forward_sessions, 0)),
        "remaining_filled_rebalances": int(
            max(minimum_filled_rebalances - filled_rebalances, 0)
        ),
        "strategy": {
            "return": float(strategy_metrics["return"]),
            "max_drawdown": float(strategy_metrics["max_drawdown"]),
            "equity": float(strategy_metrics["equity"]),
        },
        "benchmarks": {
            ticker: {
                "return": float(metrics["return"]),
                "max_drawdown": float(metrics["max_drawdown"]),
                "equity": float(metrics["equity"]),
            }
            for ticker, metrics in benchmark_metrics.items()
        },
        "return_difference_vs_spy": float(
            strategy_metrics["return"] - benchmark_metrics["SPY"]["return"]
        ),
        "return_difference_vs_passive_90_10": float(
            strategy_metrics["return"]
            - benchmark_metrics[PASSIVE_BENCHMARK_KEY]["return"]
        ),
        "gates": gates,
        "live_confirmed": all(gates.values()),
    }


def write_paper_state(path: str | Path, state: dict[str, Any]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )
    temporary.replace(destination)
    return destination


def load_paper_state(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _paper_equity_svg(state: dict[str, Any], width: int = 980, height: int = 260) -> str:
    rows = state.get("equity_curve", [])
    if len(rows) < 2:
        return '<div class="empty">前瞻帳戶剛建立；有新交易日後開始繪製權益曲線。</div>'
    dates = pd.to_datetime([row["date"] for row in rows])
    values = np.asarray([float(row["equity"]) for row in rows])
    pad_l, pad_r, pad_t, pad_b = 70, 20, 18, 34
    chart_w, chart_h = width - pad_l - pad_r, height - pad_t - pad_b
    y0, y1 = float(values.min()), float(values.max())
    if math.isclose(y0, y1):
        y0 *= 0.99
        y1 *= 1.01
    points = []
    for idx, value in enumerate(values):
        x = pad_l + idx / max(len(values) - 1, 1) * chart_w
        y = pad_t + (y1 - value) / max(y1 - y0, 1e-12) * chart_h
        points.append((x, y))
    path = " ".join(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points))
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="paper account equity">'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{height-pad_b}" class="grid"/>'
        f'<line x1="{pad_l}" y1="{height-pad_b}" x2="{width-pad_r}" y2="{height-pad_b}" class="grid"/>'
        f'<path d="{path}" fill="none" stroke="#61d3a5" stroke-width="2.5"/>'
        f'<text x="{pad_l-8}" y="{pad_t+4}" text-anchor="end" class="axis">{html.escape(_money(y1))}</text>'
        f'<text x="{pad_l-8}" y="{height-pad_b+4}" text-anchor="end" class="axis">{html.escape(_money(y0))}</text>'
        f'<text x="{pad_l}" y="{height-9}" class="axis">{dates[0].date()}</text>'
        f'<text x="{width-pad_r}" y="{height-9}" text-anchor="end" class="axis">{dates[-1].date()}</text>'
        "</svg>"
    )


def build_paper_report(
    destination: str | Path,
    *,
    state: dict[str, Any],
    panel: MarketPanel,
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = paper_metrics(state)
    mode = str(state["mode"])
    mode_label = "LIVE 前瞻帳戶" if mode == "live" else "REPLAY 歷史回放"
    mode_note = (
        "只會用帳戶建立後新增的行情推進；這是前瞻紀錄，但仍不是券商成交。"
        if mode == "live"
        else "使用已知歷史資料驗證流程；不得當成樣本外或真實前瞻績效。"
    )
    as_of = str(state["as_of"])
    equity = float(metrics["equity"])
    holdings = state.get("holdings", {})
    total_value = max(equity, 1e-12)
    pending = state.get("pending_order")
    target = pending.get("target_weights", {}) if pending else {}
    position_rows = []
    symbols = sorted(set(holdings) | set(target))
    for ticker in symbols:
        item = holdings.get(ticker, {})
        market_value = float(item.get("market_value", 0.0))
        weight = market_value / total_value
        target_weight = float(target.get(ticker, 0.0))
        position_rows.append(
            f"<tr><th>{html.escape(ticker)}</th><td>{float(item.get('shares', 0.0)):,.4f}</td>"
            f"<td>{_money(float(item.get('last_price', 0.0))) if item else '—'}</td>"
            f"<td>{_money(market_value)}</td><td>{_pct(weight)}</td><td>{_pct(target_weight)}</td>"
            f'<td class="{"good" if abs(weight-target_weight) < .02 else "warntext"}">{_pct(weight-target_weight)}</td></tr>'
        )
    if not position_rows:
        position_rows.append('<tr><td colspan="7">目前全數現金，等待下一個可成交交易日。</td></tr>')
    transactions = []
    for item in reversed(state.get("transactions", [])[-30:]):
        transactions.append(
            f"<tr><td>{html.escape(item['date'])}</td><td>{html.escape(item['ticker'])}</td>"
            f'<td class="{"good" if item["side"] == "BUY" else "warntext"}">{html.escape(item["side"])}</td>'
            f"<td>{float(item['shares']):,.4f}</td><td>{_money(float(item['price']))}</td>"
            f"<td>{_money(float(item['notional']))}</td><td>{_money(float(item['cost']))}</td></tr>"
        )
    if not transactions:
        transactions.append('<tr><td colspan="7">尚無成交；第一筆委託不會回填成過去已成交。</td></tr>')
    rebase_rows = []
    for item in reversed(state.get("adjustment_rebases", [])[-30:]):
        rebase_rows.append(
            f"<tr><td>{html.escape(str(item['detected_at']))}</td>"
            f"<td>{html.escape(str(item['as_of']))}</td>"
            f"<td>{html.escape(str(item['ticker']))}</td>"
            f"<td>{_money(float(item['old_adjusted_close']))}</td>"
            f"<td>{_money(float(item['new_adjusted_close']))}</td>"
            f"<td>{float(item['unit_factor']):,.8f}×</td>"
            f"<td>{_money(float(item['market_value_before']))}</td>"
            f"<td>{_money(float(item['market_value_after']))}</td></tr>"
        )
    if not rebase_rows:
        rebase_rows.append(
            '<tr><td colspan="8">尚無調整後價格回溯修訂；持倉單位未重基準。</td></tr>'
        )
    pending_rows = []
    if pending:
        for ticker, weight in pending["target_weights"].items():
            pending_rows.append(
                f"<tr><th>{html.escape(ticker)}</th><td>{_pct(float(weight))}</td>"
                f"<td>{_money(equity * float(weight))}</td></tr>"
            )
    else:
        pending_rows.append('<tr><td colspan="3">目前沒有待成交委託。</td></tr>')
    css = """
    :root{--bg:#08131f;--panel:#122132;--line:#294057;--text:#edf4fa;--muted:#9eb0c1;--green:#61d3a5;--gold:#ffbd69;--red:#ff7f7f}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#17334b,#08131f 55%);color:var(--text);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,"PingFang TC","Noto Sans TC",sans-serif}main{max-width:1120px;margin:auto;padding:34px 22px 72px}header{display:flex;justify-content:space-between;gap:24px;align-items:end}h1{font-size:clamp(34px,6vw,58px);line-height:1.05;margin:8px 0 12px}h2{margin:0 0 12px}a{color:var(--green)}.eyebrow{color:var(--green);font-weight:800;letter-spacing:.12em}.lead,.fine{color:var(--muted)}.badge{padding:10px 14px;border:1px solid var(--green);color:var(--green);border-radius:999px;font-weight:800;white-space:nowrap}.replay{border-color:var(--gold);color:var(--gold)}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}.kpi,.panel{background:rgba(18,33,50,.94);border:1px solid var(--line);border-radius:16px}.kpi{padding:16px}.kpi span{display:block;color:var(--muted);font-size:12px}.kpi strong{font-size:25px}.panel{padding:20px;margin-top:14px;overflow:hidden}.notice{border-left:4px solid var(--gold);background:#292214;padding:13px 15px;border-radius:8px}.good{color:var(--green)}.bad{color:var(--red)}.warntext{color:var(--gold)}table{width:100%;border-collapse:collapse;min-width:690px}.table-wrap{overflow:auto}th,td{text-align:right;padding:10px;border-bottom:1px solid var(--line);white-space:nowrap}th:first-child,td:first-child{text-align:left}thead th{color:var(--muted);font-size:12px}.grid{stroke:#294057}.axis{fill:#9eb0c1;font-size:11px}svg{width:100%;height:auto}.empty{padding:50px 16px;text-align:center;color:var(--muted)}.hash{font:12px ui-monospace,SFMono-Regular,monospace;word-break:break-all}.footer{color:var(--muted);font-size:12px;margin-top:22px}@media(max-width:760px){header{display:block}.badge{display:inline-block;margin-top:10px}.grid4{grid-template-columns:1fr 1fr}main{padding:24px 13px 56px}.panel{padding:15px}}@media(max-width:430px){.grid4{grid-template-columns:1fr}}
    """
    strategy_name = html.escape(str(state.get("strategy", "—")))
    content = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>US FDDK Paper Trade</title><style>{css}</style></head><body><main>
    <header><div><div class="eyebrow">PERSISTENT PAPER ACCOUNT</div><h1>模擬交易帳戶</h1><p class="lead"><b>{strategy_name}</b>｜同一套月末訊號、下一交易日開盤時鐘與成交成本；帳戶保存現金、總報酬單位、委託、成交與逐日權益，不把回測偷偷當成實盤。</p><p><a href="report.html">← 回到 20 年研究報表</a></p></div><div class="badge {'replay' if mode == 'replay' else ''}">{mode_label}</div></header>
    <p class="notice">{html.escape(mode_note)}</p>
    <section class="grid4"><div class="kpi"><span>帳戶權益</span><strong>{_money(equity)}</strong></div><div class="kpi"><span>累積損益</span><strong class="{'good' if metrics['pnl'] >= 0 else 'bad'}">{_money(float(metrics['pnl']))}</strong></div><div class="kpi"><span>累積報酬</span><strong>{_pct(float(metrics['return']))}</strong></div><div class="kpi"><span>最大回撤</span><strong>{_pct(float(metrics['max_drawdown']))}</strong></div></section>
    <section class="panel"><h2>帳戶權益</h2>{_paper_equity_svg(state)}<p class="fine">起始 {html.escape(str(state.get('started_at', '—')))}｜截至 {html.escape(as_of)}｜現金 {_money(float(state['cash']))}｜累積成本 {_money(float(state['total_costs']))}｜成交 {len(state.get('transactions', []))} 筆｜單位重基準 {len(state.get('adjustment_rebases', []))} 筆</p></section>
    <section class="panel"><h2>持倉與目標漂移</h2><p class="fine">單位數與價格採總報酬調整口徑，不是券商實際股數；遇到除息、拆股或供應商修訂時會重基準單位並保持既有市值不變。</p><div class="table-wrap"><table><thead><tr><th>代號</th><th>總報酬單位</th><th>調整後收盤</th><th>市值</th><th>目前權重</th><th>待成交目標</th><th>偏差</th></tr></thead><tbody>{''.join(position_rows)}</tbody></table></div></section>
    <section class="panel"><h2>待成交委託</h2><p class="fine">{'訊號日 '+html.escape(pending['signal_date'])+'；只會在 '+html.escape(pending['execute_after'])+' 之後第一個新增交易日開盤成交。' if pending else '月末收盤後才會產生下一張委託。'}</p><div class="table-wrap"><table><thead><tr><th>代號</th><th>目標權重</th><th>依目前權益估算</th></tr></thead><tbody>{''.join(pending_rows)}</tbody></table></div></section>
    <section class="panel"><h2>成交明細</h2><div class="table-wrap"><table><thead><tr><th>日期</th><th>代號</th><th>方向</th><th>成交單位</th><th>調整後開盤</th><th>名目金額</th><th>成本</th></tr></thead><tbody>{''.join(transactions)}</tbody></table></div></section>
    <section class="panel"><h2>調整後價格重基準收據</h2><p class="fine">供應商若回溯改寫既有日期的調整後收盤，系統只縮放總報酬單位以保持該日已記錄市值；既有權益曲線與成交不會被回寫。</p><div class="table-wrap"><table><thead><tr><th>偵測時間</th><th>帳戶日期</th><th>代號</th><th>舊調整收盤</th><th>新調整收盤</th><th>單位倍數</th><th>重基準前市值</th><th>重基準後市值</th></tr></thead><tbody>{''.join(rebase_rows)}</tbody></table></div></section>
    <section class="panel"><h2>稽核收據</h2><p>策略：{strategy_name}<br>模式：{mode.upper()}<br>成本：{float(state['cost_bps']):g} bps／雙邊換手<br>價格口徑：調整後 OHLC 總報酬單位；歷史修訂只重基準單位、不回寫既有 P&amp;L<br>資料截止：{panel.end.date()}<br>快照 SHA-256：<span class="hash">{html.escape(str(state.get('snapshot_sha256', '')))}</span></p></section>
    <p class="footer">模擬交易不會送單到券商；總報酬單位也不是可直接下單的券商股數。未含稅務、點差、滑價、市場衝擊與資金限制；僅供研究與教育。</p>
    </main></body></html>"""
    path.write_text(content, encoding="utf-8")
    return path
