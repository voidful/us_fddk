import type { Metadata } from "next";
import AllocationCalculator from "./AllocationCalculator";
import FreshnessGuard from "./FreshnessGuard";
import data from "../data/trading-data.json";

export const metadata: Metadata = {
  title: "成長守門員｜美股 ETF 研究訊號",
  description: "20 年凍結回測、SPY／QQQ 比較、LIVE paper trade 與新手可讀的目標配置。",
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
  { name: "成長守門員", note: "研究候選", ...data.strategy.metrics },
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

export default function Home() {
  const pending = data.paper.pending_order !== null;
  const qqqWeight = data.strategy.current_target.QQQ;
  const shyWeight = data.strategy.current_target.SHY;
  return (
    <>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="回到頁首">
          <span className="brand-mark">G</span>
          <span>成長守門員 v2</span>
        </a>
        <nav aria-label="主要導覽">
          <a href="#allocation">配置</a>
          <a href="#evidence">證據</a>
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
            <div className="status-badge pending fresh-only"><span />資料有效 · 等待成交</div>
            <div className="status-badge expired stale-only"><span />訊號已停用</div>
            <h1 className="fresh-only">今天不用猜。<br />照規則，等下一個開盤。</h1>
            <h1 className="stale-only">資料已過期。<br />今天先不要照做。</h1>
            <p className="hero-lead fresh-only">
              系統已用 {data.data_through} 的月末收盤資料算出配置。最近波動越高，
              就自動降低 QQQ、增加 SHY；這筆訊號只在下一個新增交易日開盤模擬成交。
            </p>
            <p className="hero-lead stale-only">
              資料應在 {data.freshness.refresh_due_at_utc.replace("T", " ").replace("Z", " UTC")} 前更新，
              但目前仍只到 {data.data_through}。請先更新行情、paper 狀態與部署版本。
            </p>
            <div className="hero-actions">
              <a className="button primary fresh-only" href="#allocation">看我的配置</a>
              <a className="button danger stale-only" href="#risks">查看為何停止參考</a>
              <a className="button ghost" href="#evidence">先看證據</a>
            </div>
          </div>

          <article className="signal-card" aria-labelledby="today-title">
            <div className="signal-card-head">
              <div>
                <p>今天該做什麼</p>
                <h2 id="today-title" className="fresh-only">{pending ? "等待模擬成交" : "暫無待辦"}</h2>
                <h2 className="stale-only">資料過期，停止參考</h2>
              </div>
              <span className="clock" aria-hidden="true">↗</span>
            </div>
            <div className="fresh-only">
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
              <p>行情新增後，先核對成交明細；不是現在追價買進。</p>
            </div>
            </div>
            <div className="stale-only stale-signal">
              <strong>停止參考舊配置</strong>
              <p>舊權重已隱藏。請等資料契約、LIVE paper 與網站三者更新到同一個交易日後再查看。</p>
              <code>refresh due {data.freshness.refresh_due_at_utc}</code>
            </div>
          </article>
        </section>

        <section className="truth-strip" aria-label="證據狀態">
          <div><span className="check">✓</span><p><b>回測門檻通過</b><small>凍結 20 年資料</small></p></div>
          <div><span className="wait">!</span><p><b>統計尚未確認</b><small>NW t = {data.evidence.newey_west_t.toFixed(2)}，門檻 1.96</small></p></div>
          <div><span className="wait">→</span><p><b>LIVE 剛開始</b><small>{data.paper.forward_sessions} 個前瞻交易日 · {data.paper.transactions} 筆成交</small></p></div>
        </section>

        <section className="section wrap" id="allocation">
          <div className="section-heading split-heading">
            <div><p className="eyebrow">01 · CURRENT SIGNAL</p><h2>把百分比換成你看得懂的金額</h2></div>
            <p>輸入預算只做試算，不會下單、連券商或儲存資料。</p>
          </div>
          <div className="fresh-only"><AllocationCalculator allocations={targets} /></div>
          <div className="stale-only allocation-stale">
            <b>配置試算已停用</b>
            <p>過期資料不顯示目標金額，避免把舊訊號誤認成今天的行動建議。</p>
          </div>
          <div className="plain-note fresh-only">
            <b>一句話讀法</b>
            <p>{data.beginner.allocation_hint} 規則是「18% 目標波動 ÷ 最近 21 日 QQQ 波動」，上限 100%、不使用槓桿；集中度仍高，不能把它當低風險策略。</p>
          </div>
        </section>

        <section className="section contrast" id="evidence">
          <div className="wrap">
            <div className="section-heading light">
              <p className="eyebrow">02 · THE RECEIPT</p>
              <h2>它在這 20 年跑贏 SPY，<br />但沒有跑贏 QQQ。</h2>
              <p>這是更誠實也更有用的比較：候選提升了 SPY 的報酬與回撤，但放棄一部分 QQQ 的長期漲幅。</p>
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
              <article><span>相對 SPY 年化</span><strong>+{pct(data.evidence.cagr_difference_vs_spy, 2)}</strong><p>20 年單一起訖點</p></article>
              <article><span>回撤改善</span><strong>+{pct(data.evidence.drawdown_improvement_vs_spy, 2)}</strong><p>仍曾跌逾四成</p></article>
              <article><span>5 年滾動勝率</span><strong>{pct(data.evidence.rolling_five_year.win_fraction_vs_spy, 1)}</strong><p>{data.evidence.rolling_five_year.windows} 個月末視窗</p></article>
              <article className="caution"><span>最近 5 年相對 SPY</span><strong>{pct(data.evidence.rolling_five_year.latest_cagr_difference_vs_spy, 2)}</strong><p>不是每段都領先</p></article>
            </div>
          </div>
        </section>

        <section className="section wrap">
          <div className="section-heading split-heading">
            <div><p className="eyebrow">03 · PASS / NOT PROVEN</p><h2>通過的是歷史規則，不是未來保證</h2></div>
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
            <div><span>固定 80/20 政策 · 2012 至今</span><h3>{pct(data.evidence.fixed_post_2012.cagr, 2)} <small>vs SPY {pct(data.evidence.fixed_post_2012.spy_cagr, 2)}</small></h3></div>
            <p>年化領先 {pct(data.evidence.fixed_post_2012.cagr_difference_vs_spy, 2)}，但這個政策是在較廣泛探索後才凍結，仍不是純粹獨立樣本。</p>
          </article>
        </section>

        <section className="section paper-section" id="paper">
          <div className="wrap paper-grid">
            <div className="section-heading light">
              <p className="eyebrow">04 · FORWARD ONLY</p>
              <h2>Paper trade 不回填漂亮歷史</h2>
              <p>帳戶建立當天維持現金，只有快照新增後才會成交。這讓前瞻成績與回測清楚分開。</p>
            </div>
            <article className="account-card">
              <div className="account-top"><span>LIVE PAPER</span><i /></div>
              <strong>{money(data.paper.equity)}</strong>
              <small>截至 {data.paper.as_of}</small>
              <dl>
                <div><dt>現金</dt><dd>{money(data.paper.cash)}</dd></div>
                <div><dt>前瞻日數</dt><dd>{data.paper.forward_sessions}</dd></div>
                <div><dt>成交筆數</dt><dd>{data.paper.transactions}</dd></div>
                <div><dt>目前報酬</dt><dd>{pct(data.paper.return, 2)}</dd></div>
              </dl>
              <div className="queued"><span />訊號已排隊，等待下一個新增交易日</div>
            </article>
          </div>
        </section>

        <section className="section wrap" id="risks">
          <div className="section-heading"><p className="eyebrow">05 · READ BEFORE USE</p><h2>先知道最壞的事，再看最好看的數字</h2></div>
          <div className="risk-grid">
            {data.limitations.map((item, index) => <article key={item}><span>0{index + 1}</span><p>{item}</p></article>)}
          </div>
        </section>

        <section className="section wrap faq-section">
          <div className="section-heading"><p className="eyebrow">06 · BEGINNER FAQ</p><h2>常見問題</h2></div>
          <div className="faq-list">
            <details><summary>我現在可以照百分比買嗎？<span>＋</span></summary><p>頁面顯示的是等待 paper 模擬成交的研究訊號，不是即時買進指令。若自行實作，仍要評估風險承受度、稅務、匯率和券商成本。</p></details>
            <details><summary>既然 20 年贏 SPY，為什麼還說未確認？<span>＋</span></summary><p>同一批資料試過很多方法後，最好看的結果可能只是運氣。統計檢查與全新的前瞻交易紀錄仍不足，所以只稱「歷史候選」。</p></details>
            <details><summary>最大回撤 -36% 是什麼意思？<span>＋</span></summary><p>在回測最糟的一段，帳面價值曾從高點跌約 36%。10 萬美元可能一度只剩約 6.4 萬美元，而且回復時間未知。</p></details>
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
