import type { Metadata } from "next";
import AllocationCalculator from "./AllocationCalculator";
import FreshnessGuard from "./FreshnessGuard";
import data from "../data/trading-data.json";

export const metadata: Metadata = {
  title: "成長守門員 v2｜美股 ETF 研究訊號",
  description: "20 年凍結回測、SPY／QQQ／被動 90/10 比較、LIVE paper trade 與新手可讀的風險判讀。",
};

const labels: Record<string, { name: string; role: string }> = {
  QQQ: { name: "NASDAQ 100", role: "成長引擎" },
  SHY: { name: "1–3 年美國公債", role: "防守現金替代" },
  SPY: { name: "S&P 500", role: "大型股分散" },
  VNQ: { name: "美國 REIT", role: "不動產分散" },
  EFA: { name: "已開發市場", role: "區域分散" },
  IWM: { name: "美國小型股", role: "規模分散" },
  DBC: { name: "廣泛商品", role: "通膨分散" },
  EEM: { name: "新興市場", role: "區域分散" },
};

const pct = (value: number, digits = 1) =>
  new Intl.NumberFormat("zh-TW", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

const money = (value: number) =>
  new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const targets = Object.entries(data.strategy.current_target)
  .map(([ticker, weight]) => ({
    ticker,
    weight,
    name: labels[ticker]?.name ?? ticker,
    role: labels[ticker]?.role ?? "分散部位",
  }))
  .sort((a, b) => b.weight - a.weight);

const benchmarks = [
  { name: "成長守門員 v2", note: "Paper-only", ...data.strategy.metrics },
  { name: "被動 90/10", note: "曝險控制", ...data.benchmarks.QQQ90_SHY10 },
  { name: "SPY", note: "必須跨過的基準", ...data.benchmarks.SPY },
  { name: "QQQ", note: "更積極的成長基準", ...data.benchmarks.QQQ },
];

const gateLabels: Record<string, string> = {
  full_cagr_at_least_spy_plus_3pp: "全期年化至少領先 SPY 3%",
  sharpe_above_spy: "風險調整報酬高於 SPY",
  drawdown_improvement_at_least_15pp: "最大回撤至少改善 15%",
  both_ten_year_halves_beat_spy: "前後兩個十年都領先",
  rolling_five_year_win_rate_at_least_90pct: "5 年滾動勝率至少 90%",
  latest_five_year_window_beats_spy: "最近 5 年仍領先",
  still_beats_spy_at_100bps: "成本提高到 100 bps 仍領先",
  fixed_policy_2012_beats_spy: "固定政策 2012 至今仍領先",
  improves_incumbent_cagr_and_drawdown: "報酬與回撤都改善 v1",
  average_qqq_weight_no_more_than_90pct: "歷史平均 QQQ 不超過 90%",
};

const exposureGateLabels: Record<string, string> = {
  full_cagr_above_passive_90_10: "20 年 CAGR 高於被動 90/10",
  sharpe_above_passive_90_10: "Sharpe 高於被動 90/10",
  drawdown_improvement_at_least_10pp_vs_passive_90_10: "最大回撤至少改善 10%",
  both_ten_year_halves_beat_passive_90_10: "前後兩個十年都領先",
  rolling_five_year_win_rate_vs_passive_at_least_75pct: "5 年滾動勝率至少 75%",
  still_beats_passive_90_10_at_25bps: "成本提高到 25 bps 仍領先",
  positive_average_daily_active_return_vs_passive_90_10: "平均每日超額報酬為正",
};

export default function Home() {
  const pending = data.paper.pending_order !== null;
  const invested = data.paper.status === "invested";
  const forward = data.paper.forward_evidence;
  const readiness = data.readiness;
  const canShowReferenceAllocation = readiness.allocation_visible === true;
  const qqqWeight = data.strategy.current_target.QQQ;
  const shyWeight = data.strategy.current_target.SHY;
  const challenger = data.research_pipeline.challengers.v3;
  const challengerProxy = challenger.proxy_validation;
  const challengerPaper = challenger.paper;
  const crossMarket = data.research_pipeline.cross_market;
  const styleRotation = data.research_pipeline.style_rotation;
  const threeClock = data.research_pipeline.three_clock;
  const industryTilt = data.research_pipeline.industry_tilt;
  const relativeGrowth = data.research_pipeline.relative_growth;
  const alwaysInvested = data.research_pipeline.always_invested;
  const lowTurnover = data.research_pipeline.low_turnover;
  const hierarchicalDefense = data.research_pipeline.hierarchical_defense;
  const confirmedGrowth = data.research_pipeline.confirmed_relative_growth;
  const confirmedR1000 = confirmedGrowth.datasets.russell_1000;
  const confirmedR2000 = confirmedGrowth.datasets.russell_2000;
  const confirmedEafe = confirmedGrowth.datasets.eafe;
  return (
    <>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="回到頁首">
          <span className="brand-mark">G</span>
          <span>成長守門員 v2</span>
        </a>
        <nav aria-label="主要導覽">
          <a href="#allocation">今日決定</a>
          <a href="#evidence">證據</a>
          <a href="#challenger">v3 研究</a>
          <a href="#paper">Paper</a>
          <a href="#risks">風險</a>
        </nav>
        <FreshnessGuard
          dataThrough={data.data_through}
          refreshDueAtUtc={data.freshness.refresh_due_at_utc}
        />
      </header>

      <main id="top">
        <section className="hero wrap">
          <div className="hero-copy">
            <p className="eyebrow">20 年凍結研究 · LIVE PAPER</p>
            <div className="status-badge pending fresh-only"><span />資料有效 · {canShowReferenceAllocation ? (pending ? "等待成交" : invested ? "照規則持有中" : "維持現金") : "實金訊號關閉"}</div>
            <div className="status-badge expired stale-only"><span />訊號已停用</div>
            <h1 className="fresh-only">今天不下單。<br />超額報酬尚未證實。</h1>
            <h1 className="stale-only">資料已過期。<br />今天先不要照做。</h1>
            <p className="hero-lead fresh-only">
              {!canShowReferenceAllocation
                ? <>v2 在 20 年回測勝過 SPY，但對相近成長曝險的被動 90% QQQ／10% SHY，後十年、滾動一致性與成本壓力都沒有通過。配置只供 Paper 驗證，不是實金下單指令。</>
                : pending
                ? <>系統已用 {data.data_through} 的月末收盤資料算出配置。最近波動越高，就自動降低 QQQ、增加 SHY；這筆訊號只在下一個新增交易日開盤模擬成交。</>
                : invested
                ? <>Paper 帳戶已按規則持有。現在不需要追價或手動換倉；系統會在下一個完整月末重新計算配置。</>
                : <>目前沒有可執行的月末訊號，Paper 帳戶維持現金；不要為了交易而交易。</>}
            </p>
            <p className="hero-lead stale-only">
              資料應在 {data.freshness.refresh_due_at_utc.replace("T", " ").replace("Z", " UTC")} 前更新，
              但目前仍只到 {data.data_through}。請先更新行情、paper 狀態與部署版本。
            </p>
            <div className="hero-actions">
              <a className="button primary fresh-only" href={canShowReferenceAllocation ? "#allocation" : "#readiness"}>{canShowReferenceAllocation ? "看我的配置" : "查看還缺什麼"}</a>
              <a className="button danger stale-only" href="#risks">查看為何停止參考</a>
              <a className="button ghost" href="#evidence">先看證據</a>
            </div>
          </div>

          <article className="signal-card" aria-labelledby="today-title">
            <div className="signal-card-head">
              <div>
                <p>今天該做什麼</p>
                <h2 id="today-title" className="fresh-only">{canShowReferenceAllocation ? (pending ? "等待模擬成交" : invested ? "照規則持有" : "維持現金") : "不建立實金部位"}</h2>
                <h2 className="stale-only">資料過期，停止參考</h2>
              </div>
              <span className="clock" aria-hidden="true">↗</span>
            </div>
            {canShowReferenceAllocation ? <div className="fresh-only">
            <div className="donut-row">
              <div
                className="donut"
                style={{ background: `conic-gradient(var(--forest) 0 ${qqqWeight * 100}%, var(--gold) ${qqqWeight * 100}% 100%)` }}
                role="img"
                aria-label={`目標配置：QQQ ${pct(qqqWeight)}，SHY ${pct(shyWeight)}`}
              >
                <div><strong>{pct(qqqWeight, 0)}</strong><span>QQQ</span></div>
              </div>
              <div className="donut-legend">
                <div><i className="qqq" /><span>QQQ 成長曝險</span><b>{pct(qqqWeight)}</b></div>
                <div><i className="shy" /><span>SHY 防守準備</span><b>{pct(shyWeight)}</b></div>
              </div>
            </div>
            <div className="next-step">
              <span>下一步</span>
              <p>{pending ? "行情新增後，先核對成交明細；不是現在追價買進。" : invested ? "等待下一個月末訊號；期間不因新聞或情緒自行換倉。" : "等待完整月末訊號，沒有訊號就不建立部位。"}</p>
            </div>
            </div> : <div className="fresh-only signal-stop">
              <strong>今日實金動作：0</strong>
              <p>系統仍會記錄 Paper 結果，但不顯示可照抄的 ETF 百分比或金額。</p>
              <ul>
                <li><span>未通過</span>相近曝險的被動 90/10 基準</li>
                <li><span>未通過</span>多重搜尋後的統計確認</li>
                <li><span>等待中</span>{forward.forward_sessions} / {forward.minimum_sessions} 個前瞻交易日</li>
              </ul>
              <a href="#paper">只查看 Paper 觀察紀錄 →</a>
            </div>}
            <div className="stale-only stale-signal">
              <strong>停止參考舊配置</strong>
              <p>舊權重已隱藏。請等資料契約、LIVE paper 與網站三者更新到同一個交易日後再查看。</p>
              <code>refresh due {data.freshness.refresh_due_at_utc}</code>
            </div>
          </article>
        </section>

        <section className="truth-strip" aria-label="證據狀態">
          <div><span className="check">✓</span><p><b>回測門檻通過</b><small>凍結 20 年資料</small></p></div>
          <div><span className={data.evidence.exposure_control_passed ? "check" : "wait"}>{data.evidence.exposure_control_passed ? "✓" : "!"}</span><p><b>{data.evidence.exposure_control_passed ? "曝險控制通過" : "曝險控制未通過"}</b><small>對照被動 90/10</small></p></div>
          <div><span className="wait">!</span><p><b>統計尚未確認</b><small>NW t = {data.evidence.newey_west_t.toFixed(2)}，門檻 1.96</small></p></div>
          <div><span className={data.evidence.live_confirmed ? "check" : "wait"}>{data.evidence.live_confirmed ? "✓" : "→"}</span><p><b>{data.evidence.live_confirmed ? "LIVE 門檻通過" : "LIVE 累積中"}</b><small>{forward.forward_sessions} / {forward.minimum_sessions} 日 · {forward.filled_rebalances} / {forward.minimum_filled_rebalances} 次換倉</small></p></div>
        </section>

        <section className="readiness-section wrap" id="readiness" aria-labelledby="readiness-title">
          <div className="readiness-head">
            <div>
              <p className="eyebrow">REAL-MONEY READINESS</p>
              <h2 id="readiness-title" className="fresh-only">資料可安全發布，<br />不等於可以實金參考。</h2>
              <h2 className="stale-only">資料已過期，<br />Paper 與實金都停止參考。</h2>
            </div>
            <div className={readiness.trade_ready ? "readiness-verdict ready" : "readiness-verdict blocked"}>
              <span className="fresh-only">{readiness.trade_ready ? "實金參考已開放" : "實金參考未開放"}</span>
              <span className="stale-only">資料過期，停止參考</span>
              <strong className="fresh-only">{readiness.passed_gate_count} / {readiness.required_gate_count}</strong>
              <strong className="stale-only">STOP</strong>
              <small className="fresh-only">所有門檻必須同時通過</small>
              <small className="stale-only">更新與完整性檢查完成前維持關閉</small>
            </div>
          </div>
          <div className="readiness-grid">
            <article>
              <span>01 · 歷史與公平基準</span>
              <strong>{data.evidence.historical_gate_passed ? "SPY 歷史通過" : "歷史未通過"}</strong>
              <p>公平 90/10：{data.evidence.exposure_control_passed ? "通過" : "失敗"}；搜尋懲罰後統計：{data.evidence.statistically_confirmed ? "通過" : "失敗"}。歷史回測只能決定是否值得前瞻觀察。</p>
            </article>
            <article>
              <span>02 · 不可回填的等待期</span>
              <strong>{forward.forward_sessions} / {forward.minimum_sessions} 日</strong>
              <p>還缺 {forward.remaining_sessions} 個前瞻交易日、{forward.remaining_filled_rebalances} 次完成換倉。未滿樣本前，報酬與回撤門檻一律鎖定為未通過。</p>
            </article>
            <article>
              <span>03 · 最終升級條件</span>
              <strong>{readiness.trade_ready ? "全部通過" : "維持 Paper-only"}</strong>
              <p>扣成本後必須為正、同時勝 SPY 與被動 90/10，且最大回撤不比兩者深；資料過期或任何帳戶漂移都立即停止參考。</p>
            </article>
          </div>
          <p className="readiness-note fresh-only"><b>今天的明確決定：</b>{readiness.trade_ready ? "已通過完整合約，才可顯示參考交易配置。" : "只允許查看研究與 Paper 進度；主配置不是實金下單指令。"}</p>
          <p className="readiness-note stale-only"><b>今天的明確決定：</b>停止使用所有舊配置；等待新快照、Paper 與網站重新通過一致性檢查。</p>
        </section>

        <section className="section wrap" id="allocation">
          <div className="section-heading split-heading">
            <div><p className="eyebrow">01 · TODAY’S DECISION</p><h2>{canShowReferenceAllocation ? "已開放的參考配置" : "目前沒有實金配置"}</h2></div>
            <p>{canShowReferenceAllocation ? "只有完整門檻通過後，才會顯示可換算的參考權重。" : "Paper 仍在背景觀察；為避免新手把研究結果誤認成指令，百分比與金額試算維持關閉。"}</p>
          </div>
          {canShowReferenceAllocation ? <div className="fresh-only"><AllocationCalculator allocations={targets} /></div> : <div className="fresh-only allocation-stale">
            <b>實金配置鎖定中</b>
            <p>目前只通過 {readiness.passed_gate_count} / {readiness.required_gate_count} 道上線門檻。今天的清楚做法是不依這套策略建立新部位。</p>
          </div>}
          <div className="stale-only allocation-stale">
            <b>配置試算已停用</b>
            <p>過期資料不顯示目標金額，避免把舊訊號誤認成今天的行動建議。</p>
          </div>
          {canShowReferenceAllocation && <div className="plain-note fresh-only">
            <b>一句話讀法</b>
            <p>{data.beginner.allocation_hint} 規則是「18% 目標波動 ÷ 最近 21 日 QQQ 波動」，上限 100%、不使用槓桿。</p>
          </div>}
        </section>

        <section className="section contrast" id="evidence">
          <div className="wrap">
            <div className="section-heading light">
              <p className="eyebrow">02 · THE RECEIPT</p>
              <h2>它跑贏 SPY，<br />但只略贏被動 90/10。</h2>
              <p>加入相近 QQQ 曝險的簡單被動組合後，真正能歸因於波動管理的報酬優勢很小，而且跨期間不穩定。</p>
            </div>
            <div className="comparison-grid">
              {benchmarks.map((row, index) => (
                <article className={`comparison-card ${index === 0 ? "featured" : ""}`} key={row.name}>
                  <div><h3>{row.name}</h3><span>{row.note}</span></div>
                  <dl>
                    <div><dt>20 年年化</dt><dd>{pct(row.cagr, 2)}</dd></div>
                    <div><dt>Sharpe</dt><dd>{row.sharpe.toFixed(2)}</dd></div>
                    <div><dt>最大回撤</dt><dd>{pct(row.max_drawdown, 2)}</dd></div>
                  </dl>
                </article>
              ))}
            </div>
            <div className="evidence-numbers">
              <article><span>相對被動 90/10 年化</span><strong>+{pct(data.evidence.cagr_difference_vs_passive_90_10, 2)}</strong><p>只看 20 年單一起訖點</p></article>
              <article><span>相對 90/10 回撤改善</span><strong>+{pct(data.evidence.drawdown_improvement_vs_passive_90_10, 2)}</strong><p>降風險效果明顯</p></article>
              <article><span>5 年滾動勝率</span><strong>{pct(data.evidence.rolling_five_year_vs_passive_90_10.win_fraction, 1)}</strong><p>門檻 75%，實際接近擲硬幣</p></article>
              <article className="caution"><span>後十年相對 90/10</span><strong>{pct(data.evidence.second_ten_year_cagr_difference_vs_passive_90_10, 2)}</strong><p>未能跨時期維持領先</p></article>
            </div>
          </div>
        </section>

        <section className="section wrap" id="exposure-control">
          <div className="section-heading split-heading">
            <div><p className="eyebrow">03 · EXPOSURE CONTROL</p><h2>真正難的基準：不用預測的 90/10</h2></div>
            <p>被動 90% QQQ／10% SHY 每月末再平衡。這項稽核是在 v2 選定後補上，因此只算反證，不冒充預先註冊。</p>
          </div>
          <div className="gate-layout">
            <div className="gate-list">
              {Object.entries(data.evidence.exposure_control_gates).map(([key, passed]) => (
                <div key={key}><span className={passed ? "gate-pass" : "gate-fail"}>{passed ? "通過" : "失敗"}</span><p>{exposureGateLabels[key] ?? key}</p></div>
              ))}
            </div>
            <article className="stat-card">
              <span>最重要的新反證</span>
              <h3>降回撤，不等於穩健超額</h3>
              <p>全期 CAGR 仍略高 {pct(data.evidence.cagr_difference_vs_passive_90_10, 2)}，但每日超額報酬年化平均為 {pct(data.evidence.active_return_vs_passive_90_10.annualized_mean, 2)}，NW t 只有 {data.evidence.active_return_vs_passive_90_10.newey_west_t.toFixed(2)}。</p>
              <p>成本提高到 25 bps 後，年化差轉為 {pct(data.evidence.cost_25bps_cagr_difference_vs_passive_90_10, 2)}；所以不能只看最好看的單一起訖 CAGR。</p>
              <div className="verdict">目前結論：保留 Paper 追蹤，不升級成實金參考策略。</div>
            </article>
          </div>
        </section>

        <section className="section challenger-section" id="challenger">
          <div className="wrap">
            <div className="section-heading light split-heading">
              <div><p className="eyebrow">04 · CHALLENGER AUDIT</p><h2>v3 在 20 年贏 QQQ，<br />為什麼還不能上線？</h2></div>
              <p>因為單一起訖點可以很好看，真正的考題是：換成相近曝險、更早年代和全新前瞻交易後，優勢還在不在。</p>
            </div>

            <div className="challenger-scorecards">
              <article>
                <span>2006–2026 · 近期 20 年</span>
                <strong>{pct(challenger.metrics.cagr, 2)}</strong>
                <p>QQQ 為 {pct(challenger.qqq_metrics.cagr, 2)}；v3 年化領先 {pct(challenger.cagr_difference_vs_qqq, 2)}，最大回撤改善 {pct(challenger.drawdown_improvement_vs_qqq, 2)}。</p>
              </article>
              <article>
                <span>96% QQQ／4% SHY · 公平基準</span>
                <strong>{challenger.matched_control_passed ? "通過" : "未通過"}</strong>
                <p>v3 年化 {pct(challenger.metrics.cagr, 2)}，固定曝險組合 {pct(challenger.matched_96_4_metrics.cagr, 2)}；這一層不是失敗原因。</p>
              </article>
              <article className="failed">
                <span>1986–2006 · 更早期代理</span>
                <strong>{pct(challengerProxy.rolling_five_year_win_fraction, 1)}</strong>
                <p>有效 5 年滾動勝率，門檻 60%。雖然全期領先 {pct(challengerProxy.cagr_difference_vs_ndx, 2)}，前十年卻落後 {pct(Math.abs(challengerProxy.ten_year_cagr_differences.first), 2)}。</p>
              </article>
              <article className="failed">
                <span>搜尋運氣懲罰 · 6,100 次</span>
                <strong>{pct(challenger.deflated_sharpe_probability, 3)}</strong>
                <p>Deflated Sharpe 機率；每日超額報酬的 Newey–West t 值只有 {challenger.active_return_newey_west.t_stat.toFixed(2)}，尚未達統計確認。</p>
              </article>
            </div>

            <div className="cross-market-audit">
              <div className="cross-market-head">
                <div><span>1989–2006 · 五市場事前凍結</span><h3>只有 {crossMarket.counts.full_cagr} / 5 完整期勝出，機制未能泛化</h3></div>
                <strong>{crossMarket.passed ? "通過" : "未通過"}</strong>
              </div>
              <p>在看結果前固定美、英、德、日、港與七道門檻。只有德國 DAX 的完整期 CAGR 勝出；不能拿單一成功掩蓋四個失敗市場。</p>
              <div className="cross-market-grid">
                {Object.entries(crossMarket.markets).map(([ticker, item]) => (
                  <article className={item.cagr_difference > 0 ? "passed" : "failed"} key={ticker}>
                    <span>{item.market} · {item.index}</span>
                    <strong>{pct(item.cagr_difference, 2)}</strong>
                    <p>相對買進持有 CAGR；5 年滾動勝率 {pct(item.rolling_five_year_win_fraction, 1)}</p>
                  </article>
                ))}
              </div>
              <div className="cross-market-stats">
                <span>50 bps 仍勝出 <b>{crossMarket.counts.cost_50bps} / 5</b></span>
                <span>滾動達標 <b>{crossMarket.counts.rolling_60pct} / 5</b></span>
                <span>等權主動報酬 <b>{pct(crossMarket.pooled_active_return.annualized, 2)}</b></span>
                <span>Newey–West t <b>{crossMarket.pooled_active_return.newey_west_t.toFixed(2)}</b></span>
              </div>
            </div>

            <div className="style-rotation-audit">
              <div className="cross-market-head">
                <div><span>2006–2026 · v4 股權風格輪動</span><h3>回撤較淺，但 14 道門檻只過 {styleRotation.passed_gate_count} 道</h3></div>
                <strong>{styleRotation.historical_gate_passed ? "通過" : "不建立 Paper"}</strong>
              </div>
              <p>這次在下載資料前固定 IWF、IWD、IJR 的 12–1 月動量與兩個 50% 槽位。結果不能只看較淺回撤：長期報酬、成本、後十年、五年滾動和統計證據都沒有一起過關。</p>
              <div className="style-rotation-grid">
                <article>
                  <span>策略 / SPY 年化</span>
                  <strong>{pct(styleRotation.strategy_metrics.cagr, 2)} / {pct(styleRotation.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>策略落後 {pct(Math.abs(styleRotation.comparisons.market.cagr_difference), 2)}</p>
                </article>
                <article className="passed">
                  <span>策略 / SPY 最大回撤</span>
                  <strong>{pct(styleRotation.strategy_metrics.max_drawdown, 1)} / {pct(styleRotation.benchmark_metrics.market.max_drawdown, 1)}</strong>
                  <p>回撤改善 {pct(styleRotation.comparisons.market.drawdown_improvement, 1)}</p>
                </article>
                <article className="failed">
                  <span>相對 SPY · 五年滾動勝率</span>
                  <strong>{pct(styleRotation.rolling_five_year.market.win_fraction, 1)}</strong>
                  <p>事前門檻 70%；NW t = {styleRotation.comparisons.market.newey_west_t.toFixed(2)}</p>
                </article>
                <article className="failed">
                  <span>50 bps · 相對 SPY 年化</span>
                  <strong>{pct(styleRotation.cost_50bps.market.cagr_difference, 2)}</strong>
                  <p>較高成本下明顯落後</p>
                </article>
              </div>
              <div className="proxy-data-failure">
                <b>舊代理資料門檻失敗</b>
                <p>`^RLG`、`^RLV` 在凍結來源只從 2002-09-30 開始，1996 起算前暖機都是 0；協議禁止事後換代號，所以六道舊代理門檻全部關閉。</p>
              </div>
            </div>

            <div className="three-clock-audit">
              <div className="cross-market-head">
                <div><span>1986–2026 · v5 三時鐘等權集成</span><h3>近期幾乎追平 QQQ，為何仍不開 Paper？</h3></div>
                <strong>{threeClock.passed_gate_count} / {threeClock.required_gate_count} 道 · 不建立 Paper</strong>
              </div>
              <p>固定持有、波動管理、趨勢確認各占 1/3，不搜尋袖套比例。2006–2026 的單一起訖點很好看，但舊年代的滾動穩定性和五市場泛化直接失敗，因此不能把近期成功當成可上線訊號。</p>
              <div className="three-clock-grid">
                <article className="passed">
                  <span>策略 / QQQ 年化</span>
                  <strong>{pct(threeClock.main.strategy_metrics.cagr, 2)} / {pct(threeClock.main.benchmark_metrics.opportunity.cagr, 2)}</strong>
                  <p>近期只領先 {pct(threeClock.main.comparisons.opportunity.cagr_difference, 2)}</p>
                </article>
                <article className="passed">
                  <span>策略 / QQQ 最大回撤</span>
                  <strong>{pct(threeClock.main.strategy_metrics.max_drawdown, 1)} / {pct(threeClock.main.benchmark_metrics.opportunity.max_drawdown, 1)}</strong>
                  <p>回撤改善 {pct(threeClock.main.comparisons.opportunity.drawdown_improvement, 1)}</p>
                </article>
                <article className="failed">
                  <span>公平 95/5 · 統計證據</span>
                  <strong>t {threeClock.main.comparisons.matched_95_5.newey_west_t.toFixed(2)}</strong>
                  <p>搜尋懲罰後機率 {pct(threeClock.main.comparisons.matched_95_5.deflated_sharpe_probability, 3)}</p>
                </article>
                <article className="failed">
                  <span>1986–2006 · 五年滾動</span>
                  <strong>{pct(threeClock.proxy.rolling_five_year.market.win_fraction, 1)}</strong>
                  <p>對舊 Nasdaq-100 的中位年化差 {pct(threeClock.proxy.rolling_five_year.market.median_cagr_difference, 2)}</p>
                </article>
                <article className="failed">
                  <span>五市場完整期</span>
                  <strong>{threeClock.cross_market.counts.full_cagr_beats_both} / 5</strong>
                  <p>50 bps 後同勝兩基準：{threeClock.cross_market.counts.cost_50bps_beats_both} / 5</p>
                </article>
                <article className="failed">
                  <span>22 道事前門檻</span>
                  <strong>{threeClock.passed_gate_count} / {threeClock.required_gate_count}</strong>
                  <p>需全數通過才可建立 Paper</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>研究配置，不是主訊號</b>
                <p>最新研究權重為 QQQ {pct(threeClock.main.current_target.QQQ, 1)}、SHY {pct(threeClock.main.current_target.SHY, 1)}。這裡不提供金額試算，也不建立 Paper 帳戶，避免把失敗研究誤當成今日下單建議。</p>
              </div>
            </div>

            <div className="industry-tilt-audit">
              <div className="cross-market-head">
                <div><span>1927–2026 · v6 產業動能核心傾斜</span><h3>長期代理支持，為何可交易主期仍淘汰？</h3></div>
                <strong>{industryTilt.passed_gate_count} / {industryTilt.required_gate_count} 道 · 不建立 Paper</strong>
              </div>
              <p>新資料下載前先固定 50% SPY 核心與三個產業動能槽位。1927–2005 的官方產業代理顯示機制曾有效，但真正可交易的 2006–2026 ETF 主期同時落後 SPY 與每月相同股票曝險的公平對照；實務結果優先。</p>
              <div className="industry-tilt-grid">
                <article className="failed">
                  <span>ETF 主期 · 策略 / SPY 年化</span>
                  <strong>{pct(industryTilt.main.strategy_metrics.cagr, 2)} / {pct(industryTilt.main.benchmark_metrics.spy.cagr, 2)}</strong>
                  <p>策略落後 {pct(Math.abs(industryTilt.main.comparisons.spy.cagr_difference), 2)}</p>
                </article>
                <article className="failed">
                  <span>ETF 主期 · 策略 / matched 年化</span>
                  <strong>{pct(industryTilt.main.strategy_metrics.cagr, 2)} / {pct(industryTilt.main.benchmark_metrics.matched.cagr, 2)}</strong>
                  <p>同總權益曝險下，選產業沒有增加淨報酬</p>
                </article>
                <article className="passed">
                  <span>ETF 主期 · 策略 / SPY 最大回撤</span>
                  <strong>{pct(industryTilt.main.strategy_metrics.max_drawdown, 1)} / {pct(industryTilt.main.benchmark_metrics.spy.max_drawdown, 1)}</strong>
                  <p>回撤較淺，但不能補足報酬失敗</p>
                </article>
                <article className="failed">
                  <span>五年滾動 · 對 SPY / matched</span>
                  <strong>{pct(industryTilt.main.rolling_five_year.spy.win_fraction, 1)} / {pct(industryTilt.main.rolling_five_year.matched.win_fraction, 1)}</strong>
                  <p>兩者都必須至少 60%</p>
                </article>
                <article className="passed">
                  <span>1927–2005 代理 · 策略 / 市場</span>
                  <strong>{pct(industryTilt.proxy.strategy_metrics.cagr, 2)} / {pct(industryTilt.proxy.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>七個完整十年有 {industryTilt.proxy.decade_wins} 個同勝兩基準</p>
                </article>
                <article className="failed">
                  <span>同曝險主動報酬 · 統計證據</span>
                  <strong>t {industryTilt.main.comparisons.matched.newey_west_t.toFixed(2)}</strong>
                  <p>搜尋懲罰後機率 {pct(industryTilt.main.comparisons.matched.deflated_sharpe_probability, 3)}</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>負結果已封存</b>
                <p>歷史規則最後算出的配置是 {Object.entries(industryTilt.main.current_target).map(([ticker, weight]) => `${ticker} ${pct(weight, 1)}`).join("、")}；但 22 道只過 {industryTilt.passed_gate_count} 道，因此不可照單、不提供金額試算，也不建立 Paper 帳戶。</p>
              </div>
            </div>

            <div className="industry-tilt-audit">
              <div className="cross-market-head">
                <div><span>1973–2026 · v10–v12 階層式三態</span><h3>回撤改善了，為什麼仍不能當成跑贏 ETF 策略？</h3></div>
                <strong>{hierarchicalDefense.paper_entry_passed_gate_count} / {hierarchicalDefense.paper_entry_required_gate_count} 道入口 · Paper 指令鎖定</strong>
              </div>
              <p>規則永久保留 60% 核心，剩下 40% 依序判斷：成長強且在 200 日線上就放 QQQ；否則 SPY 在 200 日線上就回到 SPY；兩者都不成立才放 SHY。v10 的 Yahoo DJIA 沒資料、v11 的 S&amp;P 官方檔唯一一次下載回覆 403，兩次都在計算前封存；v12 沒有偷換來源，只用三段既有凍結資料第一次計算同一規則。</p>
              <div className="industry-tilt-grid">
                <article className="failed">
                  <span>ETF 主期 · 策略 / SPY 年化</span>
                  <strong>{pct(hierarchicalDefense.main.strategy_metrics.cagr, 2)} / {pct(hierarchicalDefense.main.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>年化落後 {pct(Math.abs(hierarchicalDefense.main.comparison.cagr_difference), 2)}，第一道門直接失敗</p>
                </article>
                <article className="passed">
                  <span>ETF 主期 · 策略 / SPY 最大回撤</span>
                  <strong>{pct(hierarchicalDefense.main.strategy_metrics.max_drawdown, 1)} / {pct(hierarchicalDefense.main.benchmark_metrics.market.max_drawdown, 1)}</strong>
                  <p>回撤改善 {pct(hierarchicalDefense.main.comparison.drawdown_improvement, 1)}，但降風險不等於有超額</p>
                </article>
                <article className="failed">
                  <span>50 bps 成本 · 相對 SPY 年化</span>
                  <strong>{pct(hierarchicalDefense.main.cost_50bps_cagr_difference, 2)}</strong>
                  <p>58 次完成切換後，成本壓力明顯落後</p>
                </article>
                <article className="failed">
                  <span>ETF 主期 · 前十年 / 後十年年化差</span>
                  <strong>{pct(hierarchicalDefense.main.fixed_halves.first.cagr_difference, 2)} / {pct(hierarchicalDefense.main.fixed_halves.second.cagr_difference, 2)}</strong>
                  <p>後十年落後，五年滾動勝率僅 {pct(hierarchicalDefense.main.rolling_five_year.win_fraction, 1)}</p>
                </article>
                <article className="failed">
                  <span>外部期 · 前半 / 後半年化差</span>
                  <strong>{pct(hierarchicalDefense.external.fixed_halves.first.cagr_difference, 2)} / {pct(hierarchicalDefense.external.fixed_halves.second.cagr_difference, 2)}</strong>
                  <p>1973–1980 有效，1981–1988 又轉為落後</p>
                </article>
                <article className="failed">
                  <span>主期 / 舊代理 / 外部 · NW t</span>
                  <strong>{hierarchicalDefense.main.comparison.newey_west_t.toFixed(2)} / {hierarchicalDefense.old_proxy.comparison.newey_west_t.toFixed(2)} / {hierarchicalDefense.external.comparison.newey_west_t.toFixed(2)}</strong>
                  <p>三段都未達 1.96；6,109 次搜尋後 DSR 也全失敗</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>最新歷史狀態不是今天的下單訊號</b>
                <p>最後完整月末判斷為 {Object.entries(hierarchicalDefense.main.current_policy_allocation).filter(([, weight]) => weight > 0).map(([ticker, weight]) => `${ticker} ${pct(weight, 1)}`).join("、")}；241 個月末中 growth／core／defense 分別為 {hierarchicalDefense.main.signals.state_month_counts.growth}／{hierarchicalDefense.main.signals.state_month_counts.core}／{hierarchicalDefense.main.signals.state_month_counts.defense} 個月。因 Paper 入口只過 {hierarchicalDefense.paper_entry_passed_gate_count}/{hierarchicalDefense.paper_entry_required_gate_count}，網站不提供金額試算，`paper update --strategy v12` 也會讀收據後拒絕建帳戶。</p>
              </div>
            </div>

            <div className="industry-tilt-audit v13-audit">
              <div className="cross-market-head">
                <div><span>2006–2026 · v13 規則先鎖定、再下載新 ETF</span><h3>已知年代看起來進步，真正的新資料答應了嗎？</h3></div>
                <strong>{confirmedGrowth.economic_passed_gate_count} / {confirmedGrowth.economic_required_gate_count} 道新資料經濟門檻 · 不建立 Paper</strong>
              </div>
              <p>v13 用連續兩個月確認降低假切換；成長成立時是 40% 核心／60% 成長，成長關閉且核心也轉弱時才放 30% 短債。這套規則先在既有年代探索，之後才把參數與淘汰條件寫死，再第一次下載大中型、小型與海外三組 ETF。這一段比「舊回測變漂亮」更重要。</p>
              <div className="industry-tilt-grid">
                <article className="failed">
                  <span>Russell 1000 · 策略 / IWB 年化</span>
                  <strong>{pct(confirmedR1000.strategy_metrics.cagr, 2)} / {pct(confirmedR1000.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>回撤較淺，但 20 年長期報酬仍少 {pct(Math.abs(confirmedR1000.comparison.cagr_difference), 2)}</p>
                </article>
                <article className="failed">
                  <span>Russell 1000 · 50 bps / 五年勝率</span>
                  <strong>{pct(confirmedR1000.cost_50bps_cagr_difference, 2)} / {pct(confirmedR1000.rolling_five_year.win_fraction, 1)}</strong>
                  <p>成本與跨起點一致性都未通過</p>
                </article>
                <article className="failed">
                  <span>Russell 2000 · 策略 / IWM 年化</span>
                  <strong>{pct(confirmedR2000.strategy_metrics.cagr, 2)} / {pct(confirmedR2000.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>小型成長替代核心沒有產生穩健超額</p>
                </article>
                <article className="failed">
                  <span>Russell 2000 · 50 bps / 五年勝率</span>
                  <strong>{pct(confirmedR2000.cost_50bps_cagr_difference, 2)} / {pct(confirmedR2000.rolling_five_year.win_fraction, 1)}</strong>
                  <p>前後十年也都沒有領先</p>
                </article>
                <article className="failed">
                  <span>EAFE · 固定起點前暖機</span>
                  <strong>{confirmedEafe.warmup_common_sessions} / {confirmedEafe.required_warmup_sessions} 日</strong>
                  <p>少 5 日；不事後延後起點或替換 ETF</p>
                </article>
                <article className="failed">
                  <span>新資料 / 完整性 / 統計</span>
                  <strong>{confirmedGrowth.economic_passed_gate_count}/{confirmedGrowth.economic_required_gate_count} · {confirmedGrowth.data_passed_gate_count}/{confirmedGrowth.data_required_gate_count} · {confirmedGrowth.statistical_passed_gate_count}/{confirmedGrowth.statistical_required_gate_count}</strong>
                  <p>三層都沒有同時通過，研究在 Paper 前停止</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>新手結論：少跌不等於有能力跑贏</b>
                <p>Russell 1000 組的最大回撤確實較 IWB 淺，但 CAGR 反而較低；如果只挑回撤卡片，就會得出錯誤的「策略成功」。v13 沒有交易帳戶、沒有可照抄百分比，也不會因這次失敗再調 40/60、70/30 或確認月數。</p>
              </div>
            </div>

            <div className="industry-tilt-audit">
              <div className="cross-market-head">
                <div><span>1989–2026 · v7 相對成長衛星</span><h3>降低 SPY 回撤，為何仍不是已證實 alpha？</h3></div>
                <strong>{relativeGrowth.passed_gate_count} / {relativeGrowth.required_gate_count} 道 · 不建立 Paper</strong>
              </div>
              <p>永久保留 50% SPY；只有 QQQ 的 12–1 動能領先 SPY、且仍在 200 日均線上時，另一半才持有 QQQ，否則放 SHY。公平 matched 對照每月維持完全相同的股票比例，卻不選 QQQ，藉此把「少持股票」的政策效果和「選成長股」的 alpha 分開。</p>
              <div className="industry-tilt-grid">
                <article className="failed">
                  <span>ETF 主期 · 策略 / SPY 年化</span>
                  <strong>{pct(relativeGrowth.main.strategy_metrics.cagr, 2)} / {pct(relativeGrowth.main.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>20 年策略仍落後 SPY {pct(Math.abs(relativeGrowth.main.comparisons.market.cagr_difference), 2)}</p>
                </article>
                <article className="passed">
                  <span>ETF 主期 · 策略 / matched 年化</span>
                  <strong>{pct(relativeGrowth.main.strategy_metrics.cagr, 2)} / {pct(relativeGrowth.main.benchmark_metrics.matched.cagr, 2)}</strong>
                  <p>QQQ 選擇效果為正，但證據沒有同時跨過 SPY</p>
                </article>
                <article className="passed">
                  <span>ETF 主期 · 策略 / SPY 最大回撤</span>
                  <strong>{pct(relativeGrowth.main.strategy_metrics.max_drawdown, 1)} / {pct(relativeGrowth.main.benchmark_metrics.market.max_drawdown, 1)}</strong>
                  <p>風險政策有緩衝，但策略回撤比 matched 深</p>
                </article>
                <article className="failed">
                  <span>五年滾動 · 對 SPY / matched</span>
                  <strong>{pct(relativeGrowth.main.rolling_five_year.market.win_fraction, 1)} / {pct(relativeGrowth.main.rolling_five_year.matched.win_fraction, 1)}</strong>
                  <p>對 SPY 未達事前 60% 門檻</p>
                </article>
                <article className="passed">
                  <span>1989–2006 代理 · 策略 / 市場</span>
                  <strong>{pct(relativeGrowth.proxy.strategy_metrics.cagr, 2)} / {pct(relativeGrowth.proxy.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>全期略勝，但前半期落後，且回撤比 matched 深</p>
                </article>
                <article className="failed">
                  <span>ETF 主期 · 對 SPY / matched NW t</span>
                  <strong>{relativeGrowth.main.comparisons.market.newey_west_t.toFixed(2)} / {relativeGrowth.main.comparisons.matched.newey_west_t.toFixed(2)}</strong>
                  <p>兩者都必須至少 1.96；不能只挑接近通過的一邊</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>政策值得理解，不代表可以照單</b>
                <p>歷史規則最後算出的配置是 {Object.entries(relativeGrowth.main.current_target).map(([ticker, weight]) => `${ticker} ${pct(weight, 1)}`).join("、")}；這只是淘汰研究的最後狀態。19 道只過 {relativeGrowth.passed_gate_count} 道，因此不提供金額試算、不建立 Paper，也不把降低回撤寫成保證跑贏。</p>
              </div>
            </div>

            <div className="industry-tilt-audit">
              <div className="cross-market-head">
                <div><span>1989–2026 · v8 永遠持股相對成長</span><h3>20 年真的勝 SPY，為何還是不能開 Paper？</h3></div>
                <strong>{alwaysInvested.paper_entry_passed_gate_count} / {alwaysInvested.paper_entry_required_gate_count} 道入口 · 不建立 Paper</strong>
              </div>
              <p>v8 把 v7 的 SHY 防守完全拿掉：每一天都是 100% 股票，50% 固定 SPY，另一半只在 QQQ 相對強勢時換成 QQQ。這次主期確實跑贏 SPY，但事前規定成本壓力與舊期尾部風險也要通過，不能只挑漂亮的 CAGR。</p>
              <div className="industry-tilt-grid">
                <article className="passed">
                  <span>ETF 主期 · 策略 / SPY 年化</span>
                  <strong>{pct(alwaysInvested.main.strategy_metrics.cagr, 2)} / {pct(alwaysInvested.main.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>同樣 100% 股票曝險，年化領先 {pct(alwaysInvested.main.comparison.cagr_difference, 2)}</p>
                </article>
                <article className="passed">
                  <span>ETF 主期 · 五年滾動勝率</span>
                  <strong>{pct(alwaysInvested.main.rolling_five_year.win_fraction, 1)}</strong>
                  <p>前後十年也都勝 SPY</p>
                </article>
                <article className="failed">
                  <span>50 bps 成本 · 相對 SPY 年化</span>
                  <strong>{pct(alwaysInvested.main.cost_50bps_cagr_difference, 2)}</strong>
                  <p>月末再平衡的換手成本把優勢完全吃掉</p>
                </article>
                <article className="failed">
                  <span>舊代理 · 策略 / 市場最大回撤</span>
                  <strong>{pct(alwaysInvested.proxy.strategy_metrics.max_drawdown, 1)} / {pct(alwaysInvested.proxy.benchmark_metrics.market.max_drawdown, 1)}</strong>
                  <p>策略深 {pct(Math.abs(alwaysInvested.proxy.comparison.drawdown_difference), 1)}，超過事前容許 5%</p>
                </article>
                <article className="failed">
                  <span>主期 / 代理 · NW t</span>
                  <strong>{alwaysInvested.main.comparison.newey_west_t.toFixed(2)} / {alwaysInvested.proxy.comparison.newey_west_t.toFixed(2)}</strong>
                  <p>兩段都未達 1.96</p>
                </article>
                <article className="failed">
                  <span>6,105 次搜尋懲罰 · 主期 / 代理</span>
                  <strong>{pct(alwaysInvested.global_dsr_promotion_sensitivity.main_probability, 2)} / {pct(alwaysInvested.global_dsr_promotion_sensitivity.proxy_probability, 2)}</strong>
                  <p>選擇偏誤尚未排除</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>最接近目標，不等於通過</b>
                <p>最後歷史配置是 {Object.entries(alwaysInvested.main.current_target).map(([ticker, weight]) => `${ticker} ${pct(weight, 1)}`).join("、")}；但 Paper 入口仍有兩道失敗，因此不顯示金額試算、不建立帳戶。下一步應取得真正新增的資料，不是依這次結果改成本或放寬回撤門檻。</p>
              </div>
            </div>

            <div className="industry-tilt-audit">
              <div className="cross-market-head">
                <div><span>1973–2026 · v9 低換手＋下載前未見外部期</span><h3>少交易、三段全期都勝，為什麼仍被淘汰？</h3></div>
                <strong>{lowTurnover.paper_entry_passed_gate_count} / {lowTurnover.paper_entry_required_gate_count} 道入口 · 不建立 Paper</strong>
              </div>
              <p>v9 把成長槽位從 50% 降到 40%，而且每月只判斷狀態；只有「開啟／關閉」真的改變時才交易。第三段 1973–1988 Nasdaq Composite／S&amp;P 500 是在代號、期間與資料契約鎖定後才首次下載，專門檢查規則是否只適合近代科技行情。</p>
              <div className="industry-tilt-grid">
                <article className="passed">
                  <span>ETF 主期 · 策略 / SPY 年化</span>
                  <strong>{pct(lowTurnover.main.strategy_metrics.cagr, 2)} / {pct(lowTurnover.main.benchmark_metrics.market.cagr, 2)}</strong>
                  <p>同樣 100% 股票，年化領先 {pct(lowTurnover.main.comparison.cagr_difference, 2)}</p>
                </article>
                <article className="passed">
                  <span>每月判斷 / 完成切換</span>
                  <strong>{lowTurnover.main.signals.completed_month_ends_in_formal_period} / {lowTurnover.main.signals.completed_executions_in_formal_period}</strong>
                  <p>狀態不變不交易；年換手仍為 {pct(lowTurnover.main.strategy_metrics.turnover, 1)}</p>
                </article>
                <article className="failed">
                  <span>50 bps 成本 · 相對 SPY 年化</span>
                  <strong>{pct(lowTurnover.main.cost_50bps_cagr_difference, 3)}</strong>
                  <p>只剩微幅正差，未達事前要求的 0.10%</p>
                </article>
                <article className="failed">
                  <span>舊代理 · 策略 / 市場最大回撤</span>
                  <strong>{pct(lowTurnover.old_proxy.strategy_metrics.max_drawdown, 1)} / {pct(lowTurnover.old_proxy.benchmark_metrics.market.max_drawdown, 1)}</strong>
                  <p>策略多跌 {pct(Math.abs(lowTurnover.old_proxy.comparison.drawdown_difference), 1)}，超過容許 5%</p>
                </article>
                <article className="failed">
                  <span>全新外部期 · 前半 / 後半年化差</span>
                  <strong>{pct(lowTurnover.external.fixed_halves.first.cagr_difference, 2)} / {pct(lowTurnover.external.fixed_halves.second.cagr_difference, 2)}</strong>
                  <p>全期雖勝，固定後半期仍落後市場</p>
                </article>
                <article className="failed">
                  <span>主期 / 舊代理 / 外部 · NW t</span>
                  <strong>{lowTurnover.main.comparison.newey_west_t.toFixed(2)} / {lowTurnover.old_proxy.comparison.newey_west_t.toFixed(2)} / {lowTurnover.external.comparison.newey_west_t.toFixed(2)}</strong>
                  <p>三段都未達 1.96；6,106 次搜尋偏誤也未排除</p>
                </article>
              </div>
              <div className="research-target-warning">
                <b>政策狀態不等於今天的下單建議</b>
                <p>最後月末的研究狀態是 {Object.entries(lowTurnover.main.current_policy_allocation).filter(([, weight]) => weight > 0).map(([ticker, weight]) => `${ticker} ${pct(weight, 1)}`).join("、")}；但這是被三道入口淘汰的歷史政策狀態。網站不提供金額試算，Paper 指令也會讀取 20/23 守門收據並拒絕建帳戶。</p>
              </div>
            </div>

            <div className="challenger-flow" aria-label="v3 升級關卡">
              <article className={challenger.historical_gate_passed && challenger.matched_control_passed ? "passed" : "failed"}>
                <span>1</span><div><b>近期歷史與公平基準</b><p>{challenger.historical_gate_passed && challenger.matched_control_passed ? "通過" : "失敗"}</p></div>
              </article>
              <i aria-hidden="true">→</i>
              <article className={challengerProxy.passed ? "passed" : "failed"}>
                <span>2</span><div><b>更早期不重疊代理</b><p>{challengerProxy.passed ? "通過" : "失敗：滾動穩定性不足"}</p></div>
              </article>
              <i aria-hidden="true">→</i>
              <article className={crossMarket.passed ? "passed" : "failed"}>
                <span>3</span><div><b>五市場機制驗證</b><p>{crossMarket.passed ? "通過" : `失敗：完整期僅 ${crossMarket.counts.full_cagr}/5 勝出`}</p></div>
              </article>
            </div>

            <div className="challenger-verdict">
              <div><span>研究決定</span><strong>不替換 v2；v3 留在隔離 Paper</strong></div>
              <p>v3 已建立獨立的 10 萬美元 Paper 帳戶，目前累積 {challengerPaper.forward_sessions} / 252 個前瞻交易日與 {challengerPaper.transactions} 筆成交；{challengerPaper.pending_order ? "現在只排隊等待第一筆模擬成交" : "目前尚無待成交委託"}。舊 Nasdaq-100 代理與下載前凍結的五市場測試都失敗，因此獨立 Paper 驗證只用來觀察實作，不會把策略救回實金候選。每次發布前也會核對日期、快照、權益與委託，任何漂移都拒絕更新網站。</p>
            </div>
          </div>
        </section>

        <section className="section wrap">
          <div className="section-heading split-heading">
            <div><p className="eyebrow">05 · PASS / NOT PROVEN</p><h2>通過 SPY，不代表通過公平基準</h2></div>
            <p>策略搜尋會放大運氣。因此除了績效，我們也保留沒有通過的統計檢查。</p>
          </div>
          <div className="gate-layout">
            <div className="gate-list">
              {Object.entries(data.evidence.historical_gates).map(([key, passed]) => (
                <div key={key}><span className={passed ? "gate-pass" : "gate-fail"}>{passed ? "通過" : "失敗"}</span><p>{gateLabels[key] ?? key}</p></div>
              ))}
            </div>
            <article className="stat-card">
              <span>最重要的未通過項目</span>
              <h3>超額報酬還不夠確定</h3>
              <div className="stat-meter"><i style={{ width: `${Math.min(data.evidence.newey_west_t / 1.96, 1) * 100}%` }} /></div>
              <p>Newey–West t 值 {data.evidence.newey_west_t.toFixed(2)}，低於 95% 常用門檻 1.96。</p>
              <p>考慮約 6,014 次研究搜尋後，Deflated Sharpe 機率只有 {pct(data.evidence.deflated_sharpe_probability, 2)}。</p>
              <div className="verdict">所以：可 paper 追蹤，不可宣稱穩定獲利。</div>
            </article>
          </div>
          <article className="period-card">
            <div><span>固定 18% 目標波動政策 · 2012 至今</span><h3>{pct(data.evidence.fixed_post_2012.cagr, 2)} <small>vs SPY {pct(data.evidence.fixed_post_2012.spy_cagr, 2)}</small></h3></div>
            <p>年化領先 {pct(data.evidence.fixed_post_2012.cagr_difference_vs_spy, 2)}，但這個政策是在較廣泛探索後才凍結，仍不是純粹獨立樣本。</p>
          </article>
        </section>

        <section className="section paper-section" id="paper">
          <div className="wrap paper-grid">
            <div className="section-heading light">
              <p className="eyebrow">06 · FORWARD ONLY</p>
              <h2>Paper trade 不回填漂亮歷史</h2>
              <p>主策略、SPY、QQQ 與被動 90/10 都從同一天現金起跑、使用同一成本與下一開盤成交。至少累積 252 個交易日、6 次換倉，且同時跑贏 SPY 與被動 90/10、回撤不更深，才標成 LIVE 通過。除息或拆股造成調整價格回溯時，只重基準總報酬單位，不回寫既有損益。</p>
            </div>
            <article className="account-card">
              <div className="account-top"><span>LIVE PAPER</span><i /></div>
              <strong>{money(data.paper.equity)}</strong>
              <small>截至 {data.paper.as_of}</small>
              <dl>
                <div><dt>現金</dt><dd>{money(data.paper.cash)}</dd></div>
                <div><dt>前瞻日數</dt><dd>{data.paper.forward_sessions}</dd></div>
                <div><dt>成交筆數</dt><dd>{data.paper.transactions}</dd></div>
                <div><dt>完成換倉</dt><dd>{data.paper.filled_rebalances}</dd></div>
                <div><dt>價格重基準</dt><dd>{data.paper.adjustment_rebases}</dd></div>
                <div><dt>v2 前瞻報酬</dt><dd>{pct(data.paper.return, 2)}</dd></div>
                <div><dt>SPY 同期</dt><dd>{pct(forward.benchmarks.SPY.return, 2)}</dd></div>
                <div><dt>QQQ 同期</dt><dd>{pct(forward.benchmarks.QQQ.return, 2)}</dd></div>
                <div><dt>被動 90/10 同期</dt><dd>{pct(forward.benchmarks.QQQ90_SHY10.return, 2)}</dd></div>
              </dl>
              <div className="queued"><span />{pending ? "訊號已排隊，等待下一個新增交易日" : invested ? "目前持有中，等待下一個月末重算" : "目前維持現金，等待有效月末訊號"}</div>
            </article>
          </div>
        </section>

        <section className="section wrap" id="risks">
          <div className="section-heading"><p className="eyebrow">07 · READ BEFORE USE</p><h2>先知道最壞的事，再看最好看的數字</h2></div>
          <div className="risk-grid">
            {data.limitations.map((item, index) => <article key={item}><span>0{index + 1}</span><p>{item}</p></article>)}
          </div>
        </section>

        <section className="section wrap faq-section">
          <div className="section-heading"><p className="eyebrow">08 · BEGINNER FAQ</p><h2>常見問題</h2></div>
          <div className="faq-list">
            <details><summary>我現在可以照百分比買嗎？<span>＋</span></summary><p>頁面顯示的是等待 paper 模擬成交的研究訊號，不是即時買進指令。若自行實作，仍要評估風險承受度、稅務、匯率和券商成本。</p></details>
            <details><summary>為什麼資料檢查通過，還是不能下單？<span>＋</span></summary><p>資料檢查通過只代表日期、快照、Paper 帳戶、基準和網站彼此一致，沒有表示策略已證實。實金參考另外要求 {readiness.required_gate_count} 道門檻全過；目前只有 {readiness.passed_gate_count} 道，決定仍是 Paper-only。</p></details>
            <details><summary>既然 20 年贏 SPY，為什麼還說未確認？<span>＋</span></summary><p>同一批資料試過很多方法後，最好看的結果可能只是運氣。統計檢查與全新的前瞻交易紀錄仍不足，所以只稱「歷史候選」。</p></details>
            <details><summary>為什麼要再比被動 90/10？<span>＋</span></summary><p>v2 平均持有接近九成 QQQ，只比 SPY 可能把科技股曝險誤認成策略能力。90/10 不預測波動、只固定再平衡，是更公平的曝險控制；目前 v2 沒有穩定跨過它。</p></details>
            <details><summary>v3 回測贏 QQQ，為什麼不用？<span>＋</span></summary><p>近期 2006–2026 看起來漂亮，但不重疊的 1986–2006 Nasdaq-100 代理期，5 年滾動勝率只有 {pct(challengerProxy.rolling_five_year_win_fraction, 1)}；下載前固定的美、英、德、日、港測試也只有 {crossMarket.counts.full_cagr}/5 完整期勝出。這代表優勢依賴特定市場與年代，先留在獨立 Paper，不取代主訊號。</p></details>
            <details><summary>v4 回撤較淺，為什麼連 Paper 都不開？<span>＋</span></summary><p>因為事前規定 14 道門檻要全部通過，實際只有 {styleRotation.passed_gate_count} 道。策略 20 年 CAGR 落後 SPY、後十年與 50 bps 成本失敗，五年滾動勝率只有 {pct(styleRotation.rolling_five_year.market.win_fraction, 1)}；舊代理資料也不足。只改善回撤不能補足報酬與泛化證據。</p></details>
            <details><summary>v5 幾乎追平 QQQ，為什麼還是不開 Paper？<span>＋</span></summary><p>近期 20 年只看 CAGR，v5 是 {pct(threeClock.main.strategy_metrics.cagr, 2)}、QQQ 是 {pct(threeClock.main.benchmark_metrics.opportunity.cagr, 2)}，而且回撤較淺；但更早 1986–2006 的 5 年滾動勝率只有 {pct(threeClock.proxy.rolling_five_year.market.win_fraction, 1)}，五市場完整期只有 {threeClock.cross_market.counts.full_cagr_beats_both}/5 同時勝過買進持有與公平基準。事前 22 道門檻只過 {threeClock.passed_gate_count} 道，因此研究到此停止，不開 Paper。</p></details>
            <details><summary>v6 長期代理有效，為什麼還是淘汰？<span>＋</span></summary><p>代理資料能說明產業動能在 1927–2005 曾有作用，卻不是可以直接下單的 ETF。真正可交易的 2006–2026 主期，策略年化 {pct(industryTilt.main.strategy_metrics.cagr, 2)}，低於 SPY {pct(industryTilt.main.benchmark_metrics.spy.cagr, 2)}，也低於同月相同股票曝險的 matched {pct(industryTilt.main.benchmark_metrics.matched.cagr, 2)}。22 道只過 {industryTilt.passed_gate_count} 道，所以依事前規則淘汰、不調參救援。</p></details>
            <details><summary>v7 回撤比 SPY 淺，為什麼仍不建立 Paper？<span>＋</span></summary><p>因為風險較低可能只是少持股票，不代表 QQQ 選擇有穩健 alpha。v7 主期年化 {pct(relativeGrowth.main.strategy_metrics.cagr, 2)}，低於 SPY {pct(relativeGrowth.main.benchmark_metrics.market.cagr, 2)}；相對 SPY 的五年滾動勝率只有 {pct(relativeGrowth.main.rolling_five_year.market.win_fraction, 1)}，NW t 為 {relativeGrowth.main.comparisons.market.newey_west_t.toFixed(2)}。舊代理前半期也落後市場。19 道只過 {relativeGrowth.passed_gate_count} 道，所以封存負結果、不調參、不開 Paper。</p></details>
            <details><summary>v8 已經連續兩段都跑贏市場，為什麼還是不開 Paper？<span>＋</span></summary><p>因為「全期勝出」不是唯一條件。v8 主期年化 {pct(alwaysInvested.main.strategy_metrics.cagr, 2)}，確實高於 SPY {pct(alwaysInvested.main.benchmark_metrics.market.cagr, 2)}，舊代理也勝出；但 50 bps 成本後主期略輸 SPY，舊代理最大回撤比市場深 {pct(Math.abs(alwaysInvested.proxy.comparison.drawdown_difference), 1)}，而兩段 NW t 都未達 1.96。事前 16 道 Paper 入口只過 {alwaysInvested.paper_entry_passed_gate_count} 道，所以不能用結果出來後再放寬規格。</p></details>
            <details><summary>v9 已減少交易，為什麼成本門檻還是失敗？<span>＋</span></summary><p>因為一次從 100% SPY 切到 60% SPY／40% QQQ，再切回來，仍會買賣相當多部位。主期 {lowTurnover.main.signals.completed_month_ends_in_formal_period} 個月末只完成 {lowTurnover.main.signals.completed_executions_in_formal_period} 次切換，但年換手仍約 {pct(lowTurnover.main.strategy_metrics.turnover, 1)}；50 bps 後只領先 SPY {pct(lowTurnover.main.cost_50bps_cagr_difference, 3)}，低於事前 0.10% 門檻。加上舊期回撤與全新外部期後半失敗，23 道只過 {lowTurnover.paper_entry_passed_gate_count} 道，因此仍不開 Paper。</p></details>
            <details><summary>v12 已把回撤壓低，為什麼仍不值得 Paper？<span>＋</span></summary><p>主期最大回撤從 SPY 的 {pct(hierarchicalDefense.main.benchmark_metrics.market.max_drawdown, 1)} 改善到 {pct(hierarchicalDefense.main.strategy_metrics.max_drawdown, 1)}，但 CAGR 也從 {pct(hierarchicalDefense.main.benchmark_metrics.market.cagr, 2)} 降到 {pct(hierarchicalDefense.main.strategy_metrics.cagr, 2)}；50 bps 成本後年化再落後 {pct(Math.abs(hierarchicalDefense.main.cost_50bps_cagr_difference), 2)}，後十年與外部期後半都沒跑贏。它是有用的風險控制負結果，不是穩健 alpha，所以事前 23 道入口只過 {hierarchicalDefense.paper_entry_passed_gate_count} 道，Paper 指令必須拒絕。</p></details>
            <details><summary>v13 交易更少、舊年代更好，為什麼還是淘汰？<span>＋</span></summary><p>因為降低換手是在已知資料上找到的改善，不是獨立證據。規則鎖定後才下載的 Russell 1000 組，策略年化 {pct(confirmedR1000.strategy_metrics.cagr, 2)} 低於 IWB {pct(confirmedR1000.benchmark_metrics.market.cagr, 2)}；Russell 2000 組也以 {pct(confirmedR2000.strategy_metrics.cagr, 2)} 落後 IWM {pct(confirmedR2000.benchmark_metrics.market.cagr, 2)}。新資料 30 道只過 {confirmedGrowth.economic_passed_gate_count} 道，所以不能用既有年代的漂亮結果覆蓋真正的新反證。</p></details>
            <details><summary>最大回撤 -36% 是什麼意思？<span>＋</span></summary><p>在回測最糟的一段，帳面價值曾從高點跌約 36%。10 萬美元可能一度只剩約 6.4 萬美元，而且回復時間未知。</p></details>
            <details><summary>為什麼除息後 Paper 單位數可能改變？<span>＋</span></summary><p>Paper 使用可連續計算總報酬的調整單位，不是券商實際股數。若除息、拆股或供應商修訂讓舊的調整價格改變，系統會等比例調整單位數、保持當時市值不變，既有成交和損益不會被重寫。</p></details>
            <details><summary>訊號多久變一次？<span>＋</span></summary><p>每個月最後一個交易日收盤後重新計算；有新訊號時，只在下一個交易日開盤模擬調整。</p></details>
          </div>
        </section>
      </main>

      <footer>
        <div className="wrap footer-grid">
          <div><span className="brand-mark">G</span><p><b>成長守門員 v2</b><br />規則比預測重要，證據比故事重要。</p></div>
          <div><p>{data.disclaimer}</p><code>快照 {data.snapshot_sha256.slice(0, 12)}…</code></div>
        </div>
      </footer>
    </>
  );
}
