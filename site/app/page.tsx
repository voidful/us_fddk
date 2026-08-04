import type { Metadata } from "next";
import FreshnessGuard from "./FreshnessGuard";
import PaperAllocationLab from "./PaperAllocationLab";
import StrategyTabs from "./StrategyTabs";
import V25ForwardBoard from "./V25ForwardBoard";
import data from "../data/trading-data.json";
import shortResearch from "../data/short-term-research.json";
import frenchResearch from "../data/short-term-french-30-industry.json";
import priorReturnContract from "../data/short-term-french-prior-return-contract.json";
import priorReturnRepair from "../data/short-term-french-prior-return-schema-repair.json";
import formalBacktestReadiness from "../data/short-term-formal-backtest-readiness.json";
import localQuarantineIntake from "../data/short-term-local-quarantine-intake.json";
import authorizedDataHandoff from "../data/short-term-authorized-data-handoff.json";
import cizExecutionExtension from "../data/short-term-ciz-execution-extension.json";
import cizExecutionAccounting from "../data/short-term-ciz-execution-accounting.json";
import crspCizMapping from "../data/short-term-crsp-ciz-mapping.json";
import providerQualification from "../data/short-term-provider-qualification.json";
import pointInTimeReadiness from "../data/short-term-point-in-time-readiness.json";
import dailyMomentumRegime from "../data/short-term-daily-momentum-regime.json";
import sizeMomentumTiltResearch from "../data/short-term-french-size-momentum-tilt.json";
import sizePriorResearch from "../data/short-term-french-size-prior.json";

export const metadata: Metadata = {
  title: "美股雙策略研究｜長線穩定與短線高回報",
  description:
    "長線 ETF 分散策略與短線研究分頁呈列；短線第十八輪正式回測事前登記合成控制 18/18、十八項攻擊全拒收，真實就緒 1/18、正式回測仍為 0。",
};

const readerCapital = 1_000;
const latest = data.research_pipeline.growth_gold_diversification;
const pooled = latest.pooled;
const diagnostics = pooled.post_entry_diagnostics_not_used_for_frozen_gate;
const expanded = latest.expanded_comparison_not_used_for_frozen_gate;
const marketContext = expanded.market_context;
const paper = latest.paper;
const forward = paper.forward_evidence;

const pct = (value: number, digits = 1) =>
  new Intl.NumberFormat("zh-HK", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

const money = (value: number) =>
  new Intl.NumberFormat("zh-HK", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const pp = (value: number, digits = 2) =>
  `${value >= 0 ? "+" : ""}${(value * 100).toFixed(digits)} 個百分點`;

const multiple = (value: number, digits = 2) => value.toFixed(digits);

const shortDate = (value: string) => value.replaceAll("-", "/");

const comparisonRows = [
  { label: "長線穩定候選", detail: "80% 大型成長股／20% 黃金", metrics: pooled.strategy_metrics },
  { label: "SPY", detail: "美國大型股市場基準", metrics: pooled.spy_metrics },
  { label: "純成長 ETF", detail: "三路徑大型成長股彙總", metrics: pooled.growth_metrics },
  { label: "公平持倉比率基準", detail: "80% 成長股／20% SHY", metrics: pooled.matched_metrics },
];

const pathLabels: Record<string, string> = {
  vanguard: "Vanguard",
  ishares: "iShares",
  state_street: "State Street",
};

const productPaths = Object.entries(latest.paths).map(([key, value]) => ({
  key,
  provider: pathLabels[key] ?? key,
  pair: `${value.implementation.growth}／${value.implementation.gold}`,
  ...value,
}));

const bootstrap = diagnostics.paired_moving_block_bootstrap.benchmarks;
const expandedBaselines = expanded.formal_baselines;
const stockComparisons = expanded.individual_stock_diagnostics.stocks;
const baselineByKey = Object.fromEntries(expandedBaselines.map((row) => [row.key, row]));
const qqqBaseline = baselineByKey.QQQ;
const nvdaDiagnostic = stockComparisons.find((row) => row.symbol === "NVDA")!;
const amdDiagnostic = stockComparisons.find((row) => row.symbol === "AMD")!;
const sectorLabels: Record<string, string> = {
  "Information Technology": "資訊科技",
  "Consumer Discretionary": "非必需消費",
  Communication: "通訊服務",
  Financials: "金融",
  "Health Care": "醫療保健",
  Energy: "能源",
};
const identityGateNames = [
  "all_accounts_live_and_same_start",
  "all_accounts_same_as_of",
  "all_accounts_same_snapshot",
  "all_accounts_same_cost_and_cash",
  "all_accounts_same_session_path",
  "all_accounts_same_execution_clock",
  "all_accounts_same_order_path",
  "all_accounts_same_fill_counts",
  "zero_integrity_violations",
] as const;
const paperIntegrity = identityGateNames.every((key) => forward.gates[key] === true);
const realMoneyLocked = !latest.real_money_signal_display_allowed;
const shortCandidate = shortResearch.frozen_candidate;
const shortBaselines = shortResearch.baselines;
const shortComparison = shortResearch.comparison_vs_qqq;
const shortTranslation = shortResearch.taiwan_reference_translation_ablation.results;
const shortSignal = shortResearch.taiwan_reference_signal_layer_diagnostic;
const shortSignalPrimary = shortSignal.horizons["20"];
const shortCostRows = [
  { label: "10 bps", metrics: shortCandidate.cost_sensitivity["10_bps"] },
  { label: "25 bps", metrics: shortCandidate.cost_sensitivity["25_bps"] },
  { label: "50 bps", metrics: shortCandidate.cost_sensitivity["50_bps"] },
];
const shortTranslationRows = [
  { key: "tw_v85_weekly", label: "20 日動量＋60 日趨勢", metrics: shortTranslation.tw_v85_weekly },
  { key: "tw_v85_weekly_spy_regime", label: "再加 SPY 市場環境", metrics: shortTranslation.tw_v85_weekly_spy_regime },
  { key: "tw_v85_weekly_spy_regime_corr", label: "再加相關性濾網", metrics: shortTranslation.tw_v85_weekly_spy_regime_corr },
];
const shortSignalRows = [
  { label: "5 日", result: shortSignal.horizons["5"] },
  { label: "10 日", result: shortSignal.horizons["10"] },
  { label: "20 日（主要）", result: shortSignal.horizons["20"] },
];
const shortEconomicPassed = Object.values(shortResearch.economic_and_statistical_gates).filter(Boolean).length;
const shortDataPassed = Object.values(shortResearch.data_gates).filter(Boolean).length;
const formalReadinessControl = formalBacktestReadiness.synthetic_control;
const formalReadinessAttackRows = formalBacktestReadiness.attacks;
const formalBaselineLabels: Record<string, { label: string; detail: string }> = {
  QQQ_buy_hold: { label: "QQQ 買入持有", detail: "主要高回報機會成本" },
  SPY_buy_hold: { label: "SPY 買入持有", detail: "廣泛大型股市場基準" },
  pit_eligible_equal_weight_monthly: { label: "逐期合資格池月度等權", detail: "分開選股排序與投資範圍回報" },
  first_top10_equal_then_drift: { label: "首輪 Top-10 等權後漂移", detail: "只買第一個正式訊號十股，不再主動輪選" },
};
const formalBaselineRows = formalReadinessControl.baselines.map((key) => ({
  key,
  ...(formalBaselineLabels[key] ?? { label: key, detail: "凍結 baseline" }),
}));
const pointInTimeGateLabels: Record<string, string> = {
  "01_authorized_provider": "合法授權及供應商產品",
  "02_manifest_and_file_set": "Manifest 與精確檔案集合",
  "03_hash_and_row_receipts": "原始檔 SHA-256 及列數",
  "04_preregistration_order": "協議早於首次數據匯入",
  "05_security_master": "永久證券主檔",
  "06_identifier_history": "歷史代號無重疊或歧義",
  "07_membership_availability": "成分公布時間無前視",
  "08_membership_intervals": "成分區間完整且不重疊",
  "09_fixed_20_year_calendar": "固定 20 年正式交易日",
  "10_daily_member_count": "每日成分數 495–510",
  "11_member_price_coverage": "在籍價格／停牌覆蓋",
  "12_market_data_validity": "OHLCV 及總回報因子",
  "13_raw_price_policy": "原始價與調整用途分離",
  "14_corporate_actions": "公司行動唯一且可對數",
  "15_outcome_coverage": "每段成分資格有 outcome",
  "16_permanent_exit_economics": "永久退出經濟回報完整",
  "17_no_post_exit_prices": "退出後沒有幽靈價格",
  "18_point_in_time_classifications": "歷史行業分類當時可知",
  "19_share_class_dedup_capability": "同公司股份類別可去重",
  "20_execution_clock": "t 收市訊號／t+1 開市成交",
};
const pointInTimeGateRows = Object.entries(pointInTimeReadiness.gates).map(([key, gate]) => ({
  key,
  number: key.slice(0, 2),
  label: pointInTimeGateLabels[key] ?? key,
  passed: gate.passed,
  detail: gate.detail,
}));
const pointInTimeGroupCount = (first: number, last: number) => {
  const rows = pointInTimeGateRows.slice(first - 1, last);
  return `${rows.filter((row) => row.passed).length}/${rows.length}`;
};
const providerRows = providerQualification.providers;
const providerQualifiedCount = providerRows.filter((row) => row.contract_passed).length;
const localIntakeAttackRows = localQuarantineIntake.attacks;
const handoffAttackRows = authorizedDataHandoff.attacks;
const extensionAttackRows = cizExecutionExtension.attacks;
const executionAttackRows = cizExecutionAccounting.attacks;
const cizAttackRows = crspCizMapping.attacks;
const providerCapabilityRows = [
  { key: "05_security_master", label: "永久證券／公司 ID" },
  { key: "06_identifier_history", label: "歷史代號及上市地" },
  { key: "07_membership_availability", label: "成分公布時間" },
  { key: "08_membership_intervals", label: "歷史 S&P 500 成分" },
  { key: "12_market_data_validity", label: "Raw OHLCV／總回報" },
  { key: "14_corporate_actions", label: "公司行動明細" },
  { key: "16_permanent_exit_economics", label: "退市／收購經濟回報" },
  { key: "18_point_in_time_classifications", label: "歷史行業分類" },
  { key: "19_share_class_dedup_capability", label: "股份類別去重" },
  { key: "20_execution_clock", label: "t 收市／t+1 開市" },
] as const;
const providerStatusLabels: Record<string, string> = {
  documented: "明確",
  partial: "部分",
  not_documented: "未見",
  unresolved_login_required: "需登入",
  not_applicable_until_import: "待匯入",
};
const frenchCandidate = frenchResearch.frozen_candidate;
const frenchPrimary = frenchResearch.primary_external_period;
const frenchRecent = frenchResearch.recent_confirmation_period;
const frenchPrimaryEvent = frenchPrimary.fixed_20_day_event;
const frenchRecentEvent = frenchRecent.fixed_20_day_event;
const frenchPrimaryMarket = frenchPrimary.comparisons.market;
const frenchPrimaryEqual = frenchPrimary.comparisons.industry_monthly_equal;
const frenchRecentMarket = frenchRecent.comparisons.market;
const frenchRecentEqual = frenchRecent.comparisons.industry_monthly_equal;
const frenchCostRows = ["10_bps", "25_bps", "50_bps"].map((key) => ({
  label: key.replace("_", " "),
  metrics: frenchCandidate.cost_sensitivity_full_history[key as keyof typeof frenchCandidate.cost_sensitivity_full_history],
}));
const frenchPrimaryRows = [
  { label: "6–1 行業動量 Top-3", detail: "唯一凍結候選 · 10 bps", metrics: frenchPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF", metrics: frenchPrimary.baseline_metrics.market },
  { label: "30 行業月度等權", detail: "不排序、每月回復等權", metrics: frenchPrimary.baseline_metrics.industry_monthly_equal },
  { label: "30 行業起點等權後漂移", detail: "不排序、不再輪替", metrics: frenchPrimary.baseline_metrics.industry_start_equal_then_drift },
];
const frenchRecentRows = [
  { label: "6–1 行業動量 Top-3", detail: "唯一凍結候選 · 10 bps", metrics: frenchRecent.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF", metrics: frenchRecent.baseline_metrics.market },
  { label: "30 行業月度等權", detail: "不排序、每月回復等權", metrics: frenchRecent.baseline_metrics.industry_monthly_equal },
  { label: "30 行業起點等權後漂移", detail: "不排序、不再輪替", metrics: frenchRecent.baseline_metrics.industry_start_equal_then_drift },
];
const frenchStressRows = [
  { label: "1973–1974 石油危機", result: frenchResearch.stress_periods["1973_1974"] },
  { label: "1987 股災", result: frenchResearch.stress_periods["1987_crash"] },
  { label: "2000–2002 科網泡沫", result: frenchResearch.stress_periods.dotcom },
  { label: "2008–2009 金融海嘯", result: frenchResearch.stress_periods.gfc },
  { label: "2020 新冠衝擊", result: frenchResearch.stress_periods.covid_2020 },
  { label: "2022 加息衝擊", result: frenchResearch.stress_periods.rate_shock_2022 },
];
const priorRepairCandidate = priorReturnRepair.frozen_candidate;
const priorRepairPrimary = priorReturnRepair.primary_external_period;
const priorRepairRecent = priorReturnRepair.recent_confirmation_period;
const priorRepairRecentMarket = priorRepairRecent.comparisons.market;
const priorRepairRecentEqual = priorRepairRecent.comparisons.decile_equal;
const priorRepairPrimaryRows = [
  { label: "VW Hi PRIOR 1–1", detail: "唯一凍結候選 · 每月完整換倉 · 10 bps", metrics: priorRepairPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: priorRepairPrimary.baseline_metrics.market },
  { label: "VW 十分位等權", detail: "同一 short-term 母體 · 每月等權", metrics: priorRepairPrimary.baseline_metrics.decile_equal },
  { label: "VW Lo PRIOR 1–1", detail: "短期反轉對照 · 每月完整換倉", metrics: priorRepairPrimary.baseline_metrics.lo_prior_1_0 },
  { label: "VW Hi PRIOR 12–2", detail: "較慢橫斷面動量 · 每月完整換倉", metrics: priorRepairPrimary.baseline_metrics.long_momentum_hi_12_2 },
];
const priorRepairRecentRows = [
  { label: "VW Hi PRIOR 1–1", detail: "唯一凍結候選 · 每月完整換倉 · 10 bps", metrics: priorRepairRecent.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: priorRepairRecent.baseline_metrics.market },
  { label: "VW 十分位等權", detail: "同一 short-term 母體 · 每月等權", metrics: priorRepairRecent.baseline_metrics.decile_equal },
  { label: "VW Lo PRIOR 1–1", detail: "短期反轉對照 · 每月完整換倉", metrics: priorRepairRecent.baseline_metrics.lo_prior_1_0 },
  { label: "VW Hi PRIOR 12–2", detail: "較慢橫斷面動量 · 每月完整換倉", metrics: priorRepairRecent.baseline_metrics.long_momentum_hi_12_2 },
];
const priorRepairSensitivityRows = [
  { label: "VW Hi PRIOR 1–1", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_hi_prior_1_0 },
  { label: "VW Top-2", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_top_2 },
  { label: "VW Top-3", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_top_3 },
  { label: "VW 線性全池傾斜", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_linear_tilt },
  { label: "VW 平方全池傾斜", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.vw_square_tilt },
  { label: "EW Hi PRIOR 1–1", metrics: priorReturnRepair.sensitivity_full_history_metrics_10bps.ew_hi_prior_1_0 },
];
const priorRepairStressRows = [
  { label: "1973–1974 石油危機", result: priorReturnRepair.stress_periods["1973_1974"] },
  { label: "1987 股災", result: priorReturnRepair.stress_periods["1987_crash"] },
  { label: "2000–2002 科網泡沫", result: priorReturnRepair.stress_periods.dotcom },
  { label: "2008–2009 金融海嘯", result: priorReturnRepair.stress_periods.gfc },
  { label: "2020 新冠衝擊", result: priorReturnRepair.stress_periods.covid_2020 },
  { label: "2022 加息衝擊", result: priorReturnRepair.stress_periods.rate_shock_2022 },
];
const sizePriorPrimary = sizePriorResearch.primary_external_period;
const sizePriorRecent = sizePriorResearch.recent_confirmation_period;
const sizePriorRecentMarket = sizePriorRecent.comparisons.market;
const sizePriorRecentBigEqual = sizePriorRecent.comparisons.big_row_equal;
const sizePriorPrimaryRows = [
  { label: "Big Hi PRIOR 1–1", detail: "唯一凍結候選 · 大型股短窗贏家 · 10 bps", metrics: sizePriorPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizePriorPrimary.baseline_metrics.market },
  { label: "大型股 prior 等權", detail: "同一 Size 5 母體 · 五組每月等權", metrics: sizePriorPrimary.baseline_metrics.big_row_equal },
  { label: "全 25 cells 等權", detail: "五個 size × 五個 prior", metrics: sizePriorPrimary.baseline_metrics.all_25_equal },
  { label: "Big Lo PRIOR", detail: "大型股短窗輸家 · 反方向控制", metrics: sizePriorPrimary.baseline_metrics.big_lo_prior },
  { label: "Hi PRIOR 12–2", detail: "長窗動量控制", metrics: sizePriorPrimary.baseline_metrics.long_momentum_hi_12_2 },
];
const sizePriorRecentRows = [
  { label: "Big Hi PRIOR 1–1", detail: "唯一凍結候選 · 大型股短窗贏家 · 10 bps", metrics: sizePriorRecent.candidate_metrics, featured: true },
  { label: "QQQ", detail: "實際產品機會成本 · 買入持有", metrics: sizePriorRecent.baseline_metrics.QQQ },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizePriorRecent.baseline_metrics.market },
  { label: "大型股 prior 等權", detail: "同一 Size 5 母體 · 五組每月等權", metrics: sizePriorRecent.baseline_metrics.big_row_equal },
  { label: "全 25 cells 等權", detail: "五個 size × 五個 prior", metrics: sizePriorRecent.baseline_metrics.all_25_equal },
  { label: "Big Lo PRIOR", detail: "大型股短窗輸家 · 反方向控制", metrics: sizePriorRecent.baseline_metrics.big_lo_prior },
  { label: "Hi PRIOR 12–2", detail: "長窗動量控制", metrics: sizePriorRecent.baseline_metrics.long_momentum_hi_12_2 },
];
const sizeMomentumPrimary = sizeMomentumTiltResearch.primary_external_period;
const sizeMomentumRecent = sizeMomentumTiltResearch.recent_confirmation_period;
const sizeMomentumRecentMarket = sizeMomentumRecent.comparisons.market;
const sizeMomentumRecentEqual = sizeMomentumRecent.comparisons.all_25_equal;
const sizeMomentumPrimaryRows = [
  { label: "全池線性動量傾斜", detail: "五個 size 各 20% · prior 權重 1:2:3:4:5 · 10 bps", metrics: sizeMomentumPrimary.candidate_metrics, featured: true },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizeMomentumPrimary.baseline_metrics.market },
  { label: "全 25 cells 等權", detail: "同一母體 · 每月回復等權", metrics: sizeMomentumPrimary.baseline_metrics.all_25_equal },
  { label: "每個 size 的 Prior 4–5", detail: "較集中 Top 2 對照", metrics: sizeMomentumPrimary.baseline_metrics.top2 },
  { label: "每個 size 的 Prior 5", detail: "最集中 Top 1 對照", metrics: sizeMomentumPrimary.baseline_metrics.top1 },
  { label: "Prior 1–1 短窗線性傾斜", detail: "同一權重規則的負控制", metrics: sizeMomentumPrimary.baseline_metrics.short_window_linear_tilt },
];
const sizeMomentumRecentRows = [
  { label: "全池線性動量傾斜", detail: "五個 size 各 20% · prior 權重 1:2:3:4:5 · 10 bps", metrics: sizeMomentumRecent.candidate_metrics, featured: true },
  { label: "QQQ", detail: "實際產品機會成本 · 買入持有", metrics: sizeMomentumRecent.baseline_metrics.QQQ },
  { label: "SPY", detail: "實際廣泛市場 ETF · 買入持有", metrics: sizeMomentumRecent.baseline_metrics.SPY },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: sizeMomentumRecent.baseline_metrics.market },
  { label: "全 25 cells 等權", detail: "同一母體 · 每月回復等權", metrics: sizeMomentumRecent.baseline_metrics.all_25_equal },
  { label: "每個 size 的 Prior 4–5", detail: "較集中 Top 2 對照", metrics: sizeMomentumRecent.baseline_metrics.top2 },
  { label: "每個 size 的 Prior 5", detail: "最集中 Top 1 對照", metrics: sizeMomentumRecent.baseline_metrics.top1 },
  { label: "Prior 1–1 短窗線性傾斜", detail: "同一權重規則的負控制", metrics: sizeMomentumRecent.baseline_metrics.short_window_linear_tilt },
];
const sizeMomentumFrontierRows = [
  { label: "等權", result: sizeMomentumTiltResearch.concentration_frontier.equal },
  { label: "線性 1:2:3:4:5", result: sizeMomentumTiltResearch.concentration_frontier.linear },
  { label: "平方 1:4:9:16:25", result: sizeMomentumTiltResearch.concentration_frontier.squared },
  { label: "只持 Prior 4–5", result: sizeMomentumTiltResearch.concentration_frontier.top2 },
  { label: "只持 Prior 5", result: sizeMomentumTiltResearch.concentration_frontier.top1 },
];
const dailyRecent = dailyMomentumRegime.recent;
const dailyEarly = dailyMomentumRegime.early;
const dailyRepair = dailyMomentumRegime.repair_diagnostic;
const dailyRecentRows = [
  { label: "四證據環境共振", detail: "唯一凍結候選 · 5% 學術拖累 · 10 bps", metrics: dailyRecent.candidate, featured: true },
  { label: "QQQ", detail: "實際 Nasdaq-100 ETF · 買入持有", metrics: dailyRecent.qqq },
  { label: "SPY", detail: "實際美國大型股 ETF · 買入持有", metrics: dailyRecent.spy },
  { label: "French 美國市場", detail: "Mkt-RF + RF · 買入持有", metrics: dailyRecent.market },
  { label: "永久 Hi PRIOR", detail: "相同 5% 拖累 · 不做環境減倉", metrics: dailyRecent.raw_hi_prior },
  { label: "相同持倉比率 French 市場", detail: "相同 0／50／100% 持倉時序", metrics: dailyRecent.matched_market_exposure },
];
const dailyCostRows = dailyRecent.cost_and_drag_grid.filter((row) =>
  (row.annual_drag === 0.02 || row.annual_drag === 0.05 || row.annual_drag === 0.1)
  && (row.overlay_cost_bps === 10 || row.overlay_cost_bps === 50)
);
const dailyStressRows = [
  { label: "金融海嘯", result: dailyMomentumRegime.stress_periods_recent.global_financial_crisis },
  { label: "新冠急跌", result: dailyMomentumRegime.stress_periods_recent.covid_crash },
  { label: "2022 加息衝擊", result: dailyMomentumRegime.stress_periods_recent.rate_shock_2022 },
];

export default function Home() {
  return (
    <>
      <header className="site-header">
        <div className="wrap nav-shell">
          <a className="brand" href="#top" aria-label="返回報告頂部">
            <span>US FDDK</span>
            <b>美股策略研究室</b>
          </a>
          <nav aria-label="報告導覽">
            <a href="#strategy-tabs">兩條策略</a>
            <a href="#strategy-evidence">研究證據</a>
            <a href="#paper">Paper 狀態</a>
          </nav>
          <FreshnessGuard
            dataThrough={data.data_through}
            refreshDueAtUtc={data.freshness.refresh_due_at_utc}
          />
        </div>
      </header>

      <main id="top">
        <StrategyTabs>
        <div id="long-term" data-strategy-panel="stable">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">LONG-TERM STABILITY · v25</span>
              <span className="status-chip warning"><i /> PAPER ONLY</span>
            </div>
            <h1>長線穩定<br />80% 美國大型成長股＋20% 黃金</h1>
            <p className="hero-lead">
              目標是保留增長、降低波幅與大型跌幅，不是追逐最高 CAGR。20 年歷史入口及三家實際 ETF 產品路徑全部通過；最新前瞻樣本仍是
              <strong> {forward.forward_sessions}/{forward.minimum_sessions} 個交易日</strong>，因此今日實金動作維持
              <strong> US$0</strong>。
            </p>
            <div className="hero-actions">
              <a className="primary-button" href="#backtest">查看完整回測</a>
              <a className="secondary-button" href="#paper">查看 Paper 進度</a>
            </div>
          </div>
          <aside className="decision-card" aria-label="最新策略決策摘要">
            <div className="decision-head">
              <span>長線策略摘要</span>
              <b>{realMoneyLocked ? "實金配置鎖定" : "參考配置開放"}</b>
            </div>
            <div className="capital-number"><small>讀者示例本金</small><strong>{money(readerCapital)}</strong></div>
            <div className="allocation-split" aria-label="Paper 目標配置">
              <div className="growth" style={{ width: "80%" }}><b>VUG</b><span>80% · {money(800)}</span></div>
              <div className="gold" style={{ width: "20%" }}><b>GLD</b><span>20%</span></div>
            </div>
            <dl className="decision-list">
              <div><dt>Paper 目標</dt><dd>VUG {money(800)}／GLD {money(200)}</dd></div>
              <div><dt>下一步</dt><dd>{paper.pending_order ? "等待下一交易日開市模擬成交" : "等待下次月末檢查"}</dd></div>
              <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
            </dl>
            <p>US$1,000 只作比例示例；正式 Paper 三個模擬組合仍以 US$100,000 公平起跑。</p>
          </aside>
        </section>

        <section className="truth-strip">
          <div className="wrap truth-grid">
            <article><span>長線策略年率化回報</span><strong>{pct(pooled.strategy_metrics.cagr, 2)}</strong><small>SPY {pct(pooled.spy_metrics.cagr, 2)}</small></article>
            <article><span>QQQ 年率化回報</span><strong>{pct(qqqBaseline.metrics.cagr, 2)}</strong><small>高回報，但跌幅較深</small></article>
            <article><span>最大跌幅</span><strong>{pct(pooled.strategy_metrics.max_drawdown, 1)}</strong><small>SPY {pct(pooled.spy_metrics.max_drawdown, 1)}</small></article>
            <article><span>產品路徑</span><strong>3 / 3</strong><small>每條 12 / 12 門檻</small></article>
            <article><span>前瞻 Paper</span><strong>{forward.forward_sessions} / {forward.minimum_sessions}</strong><small>{paper.status === "awaiting_fill" ? "首筆仍待成交" : "已開始累積"}</small></article>
          </div>
        </section>

        <section className="section wrap" id="market">
          <div className="section-heading">
            <div><span>MARKET STATUS</span><h2>目前市場與策略狀況</h2></div>
            <p>只用最新凍結快照和前瞻狀態判讀，不把歷史回測當成今日即時訊號。</p>
          </div>
          <div className="market-grid">
            <article className="market-verdict">
              <span>截至 {shortDate(data.data_through)}</span>
              <h3>近期五年仍領先 SPY，組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}</h3>
              <p>
                最新五年窗的年率化回報較 SPY 高 {pp(diagnostics.rolling_five_year_entry_timing_risk.SPY.latest_window.cagr_difference)}，
                較純成長高 {pp(diagnostics.rolling_five_year_entry_timing_risk.growth.latest_window.cagr_difference)}。
                但全 20 年純成長 CAGR 仍高 {pp(Math.abs(pooled.tradeoff_vs_growth.cagr_difference))}；這套配置追求的是較高 Sharpe 及較淺最大跌幅，不是每段市況都要成為最高回報組合。
              </p>
              <div className="market-badges">
                <span>固定 80/20</span><span>每月檢查</span><span>不預測升跌</span><span>不使用槓桿</span>
              </div>
            </article>
            <div className="market-status-list">
              <article><span>數據狀態</span><strong>{paperIntegrity ? "完整性通過" : "暫停參考"}</strong><p>最新交易日 {data.freshness.last_session}；下一預期交易日 {data.freshness.next_expected_session}。</p></article>
              <article><span>當前風險</span><strong>{pct(diagnostics.portfolio_underwater.current_drawdown, 1)}</strong><p>這是回測組合相對自身歷史高位的距離，不是未來跌幅預測。</p></article>
              <article><span>最長復原期</span><strong>{diagnostics.portfolio_underwater.max_underwater_months} 個月</strong><p>最深一段由 {diagnostics.portfolio_underwater.deepest_episode.peak} 高位開始，至 {diagnostics.portfolio_underwater.deepest_episode.recovery} 才復原。</p></article>
              <article><span>今日可執行狀態</span><strong className="danger-text">Paper-only</strong><p>待成交指令不等於成交；實金配置仍鎖定。</p></article>
            </div>
          </div>
        </section>

        <section className="section wrap" id="backtest">
          <div className="section-heading">
            <div><span>20-YEAR BACKTEST</span><h2>同期間、同成本口徑的核心比較</h2></div>
            <p>{pooled.period.start_equity_date} 至 {pooled.period.end}，共 {pooled.period.months} 個月；回報包含經調整價格，換手成本在策略中扣除。</p>
          </div>
          <div className="metric-table-wrap">
            <table className="metric-table">
              <thead><tr><th>組合</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th><th>平均月度換手</th></tr></thead>
              <tbody>
                {comparisonRows.map((row, index) => (
                  <tr className={index === 0 ? "featured-row" : ""} key={row.label}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th>
                    <td>{pct(row.metrics.cagr, 2)}</td>
                    <td>{row.metrics.sharpe.toFixed(2)}</td>
                    <td>{pct(row.metrics.volatility, 1)}</td>
                    <td>{pct(row.metrics.max_drawdown, 1)}</td>
                    <td>{pct(row.metrics.turnover, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="tradeoff-grid">
            <article><span>對 SPY</span><strong>{pp(pooled.strategy_metrics.cagr - pooled.spy_metrics.cagr)}</strong><p>年率化回報優勢；最大跌幅改善 {pp(Math.abs(pooled.spy_metrics.max_drawdown) - Math.abs(pooled.strategy_metrics.max_drawdown))}。</p></article>
            <article><span>對純成長</span><strong>{pp(pooled.tradeoff_vs_growth.cagr_difference)}</strong><p>放棄少量年率化回報，換取 Sharpe +{pooled.tradeoff_vs_growth.sharpe_difference.toFixed(2)}、最大跌幅改善 {pp(pooled.tradeoff_vs_growth.drawdown_improvement)}。</p></article>
            <article><span>對公平基準</span><strong>{pp(pooled.strategy_metrics.cagr - pooled.matched_metrics.cagr)}</strong><p>同樣 80% 股票持倉比率，以黃金取代 SHY 後的年率化差異。</p></article>
          </div>

          <div className="subsection-heading">
            <div><span>PRODUCT SENSITIVITY</span><h3>三家實際 ETF 產品路徑</h3></div>
            <p>不只測單一 VUG／GLD 組合；同一 80/20 定義跨 Vanguard、iShares、State Street 重跑。</p>
          </div>
          <div className="metric-table-wrap">
            <table className="metric-table compact-table">
              <thead><tr><th>產品路徑</th><th>實際 ETF</th><th>年率化回報</th><th>Sharpe</th><th>最大跌幅</th><th>50 bps 後對 SPY</th><th>5 年窗勝 SPY</th><th>入口</th></tr></thead>
              <tbody>
                {productPaths.map((path) => (
                  <tr key={path.key}>
                    <th><b>{path.provider}</b><span>{path.period.months} 個月</span></th>
                    <td>{path.pair}</td>
                    <td>{pct(path.strategy_metrics.cagr, 2)}</td>
                    <td>{path.strategy_metrics.sharpe.toFixed(2)}</td>
                    <td>{pct(path.strategy_metrics.max_drawdown, 1)}</td>
                    <td>{pp(path.cost_50bps_cagr_difference_vs_spy)}</td>
                    <td>{pct(path.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</td>
                    <td><span className="pass-pill">{path.passed_gate_count}/{path.required_gate_count}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="section comparison-section" id="strategy-evidence">
          <div className="wrap">
            <div className="section-heading">
              <div><span>EXPANDED COMPARISON LAB</span><h2>更多 baseline，不迴避輸贏</h2></div>
              <p>同一 20 年、同一經調整價格及 10 bps 成本。這一層只作通過後診斷，不更改凍結策略或 Paper 門檻。</p>
            </div>

            <div className="context-grid" aria-label="研究快照市場狀況指標">
              <article>
                <span>大型股市場廣度</span>
                <strong>{pct(marketContext.current_watchlist_above_200d_fraction, 1)}</strong>
                <p>{marketContext.current_watchlist_count} 隻現時大型股高於 200 天平均線；高於 50 天為 {pct(marketContext.current_watchlist_above_50d_fraction, 1)}。</p>
              </article>
              <article>
                <span>SPY 12 個月</span>
                <strong>{pct(marketContext.spy_return_12m, 1)}</strong>
                <p>高於 200 天平均線 {pct(marketContext.spy_distance_from_200d_average, 1)}；只描述 {marketContext.as_of} 快照。</p>
              </article>
              <article>
                <span>21 天實現波幅</span>
                <strong>{pct(marketContext.spy_realized_volatility_21d, 1)}</strong>
                <p>位於近五年 {pct(marketContext.spy_realized_volatility_21d_five_year_percentile, 0)} 分位，並非波幅預測。</p>
              </article>
              <article>
                <span>VIX 收市</span>
                <strong>{marketContext.vix_close.toFixed(2)}</strong>
                <p>近五年 {pct(marketContext.vix_five_year_percentile, 0)} 分位；不參與 80/20 買賣規則。</p>
              </article>
              <article>
                <span>成長股相對 SPY</span>
                <strong className={marketContext.vug_relative_return_vs_spy_12m < 0 ? "negative-number" : ""}>{pp(marketContext.vug_relative_return_vs_spy_12m)}</strong>
                <p>12 個月 VUG {pct(marketContext.vug_return_12m, 1)}，SPY {pct(marketContext.spy_return_12m, 1)}。</p>
              </article>
              <article>
                <span>VUG／GLD 相關性</span>
                <strong>{marketContext.vug_gold_correlation_252d.toFixed(2)}</strong>
                <p>252 日相關性；近 63 日升至 {marketContext.vug_gold_correlation_63d.toFixed(2)}，短期分散效用有所減弱。</p>
              </article>
            </div>

            <div className="subsection-heading baseline-heading">
              <div><span>FORMAL BASELINES</span><h3>九組同口徑配置矩陣</h3></div>
              <p>超額 Sharpe 以 SHY 月回報作現金代理；「策略五年窗勝率」是最新策略在 181 個滾動窗口勝過該列的比例。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table expanded-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>Sortino</th><th>最大跌幅</th><th>Beta</th><th>策略五年窗勝率</th><th>NW t</th></tr></thead>
                <tbody>
                  {expandedBaselines.map((row) => (
                    <tr className={row.key === "candidate" ? "featured-row" : ""} key={row.key}>
                      <th><b>{row.label}</b><span>{row.detail}</span></th>
                      <td>{pct(row.metrics.cagr, 2)}</td>
                      <td>{multiple(row.excess_sharpe_vs_shy)}</td>
                      <td>{multiple(row.metrics.sortino)}</td>
                      <td>{pct(row.metrics.max_drawdown, 1)}</td>
                      <td>{multiple(row.beta_to_spy)}</td>
                      <td>{row.candidate_rolling_five_year_win_fraction === null ? "—" : pct(row.candidate_rolling_five_year_win_fraction, 1)}</td>
                      <td>{row.candidate_active_newey_west_t === null ? "—" : row.candidate_active_newey_west_t.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="baseline-findings">
              <article><span>高回報 baseline</span><strong>{pp(baselineByKey.candidate.metrics.cagr - baselineByKey.QQQ.metrics.cagr)}</strong><p>長線策略的 CAGR 低於 QQQ，五年窗只有 {pct(baselineByKey.QQQ.candidate_rolling_five_year_win_fraction, 1)} 勝出。</p></article>
              <article><span>同黃金比重控制</span><strong>{pp(baselineByKey["80_SPY_20_GLD"].candidate_cagr_difference)}</strong><p>成長股選擇相對 80% SPY／20% GLD 的 NW t 只有 {baselineByKey["80_SPY_20_GLD"].candidate_active_newey_west_t.toFixed(2)}。</p></article>
              <article><span>重新平衡測試</span><strong>{pp(baselineByKey["80_VUG_20_GLD_DRIFT"].candidate_cagr_difference)}</strong><p>每月重新平衡 CAGR 略高，但最大跌幅反而深 {pp(Math.abs(baselineByKey.candidate.metrics.max_drawdown - baselineByKey["80_VUG_20_GLD_DRIFT"].metrics.max_drawdown))}。</p></article>
            </div>

            <div className="baseline-source-links" aria-label="ETF 官方產品定義">
              <span>官方產品定義</span>
              {Object.entries(expanded.official_product_sources).map(([ticker, href]) => (
                <a href={href} target="_blank" rel="noreferrer" key={ticker}>{ticker}</a>
              ))}
            </div>
          </div>
        </section>

        <section className="section wrap" id="tests">
          <div className="section-heading">
            <div><span>ROBUSTNESS &amp; STATISTICS</span><h2>不是只看漂亮 CAGR</h2></div>
            <p>成本、固定十年分段、181 個滾動五年窗、統計檢定及 30,000 次配對區塊重抽樣都完整呈列。</p>
          </div>
          <div className="test-matrix">
            <article className="test-card passed">
              <div><span>01 · 歷史入口</span><b>通過</b></div>
              <strong>{pooled.passed_gate_count}/{pooled.required_gate_count}</strong>
              <p>三條產品路徑各 12/12；數據契約 {latest.data_passed_gate_count}/{latest.data_required_gate_count}。</p>
            </article>
            <article className="test-card passed">
              <div><span>02 · 成本壓力</span><b>通過</b></div>
              <strong>{pp(pooled.cost_50bps_cagr_difference_vs_spy)}</strong>
              <p>把單邊成本假設提高至 50 bps 後，年率化回報仍領先 SPY。</p>
            </article>
            <article className="test-card passed">
              <div><span>03 · 固定十年分段</span><b>兩段皆正</b></div>
              <strong>{pp(pooled.fixed_halves_vs_spy.first.cagr_difference)}</strong>
              <p>前十年對 SPY；後十年仍有 {pp(pooled.fixed_halves_vs_spy.second.cagr_difference)}。</p>
            </article>
            <article className="test-card mixed">
              <div><span>04 · 滾動五年</span><b>有時序風險</b></div>
              <strong>{pct(pooled.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</strong>
              <p>{pooled.rolling_five_year_vs_spy.windows} 個窗口勝 SPY 的比例；最差年率化落後 {pp(pooled.rolling_five_year_vs_spy.worst_cagr_difference)}。</p>
            </article>
            <article className="test-card mixed">
              <div><span>05 · 統計顯著</span><b>對 SPY 未確認</b></div>
              <strong>t = {pooled.statistics_vs_spy.newey_west_t.toFixed(2)}</strong>
              <p>對公平持倉比率基準 t = {pooled.statistics_vs_matched.newey_west_t.toFixed(2)}；不能把兩者混為一談。</p>
            </article>
            <article className="test-card failed">
              <div><span>06 · 多重搜尋校正</span><b>警示</b></div>
              <strong>{pct(pooled.statistics_vs_spy.global_deflated_sharpe_probability, 1)}</strong>
              <p>全專案 {latest.global_search_trials.toLocaleString("zh-HK")} 次搜尋後的 Deflated Sharpe 機率很低，故只准 Paper。</p>
            </article>
          </div>

          <div className="robust-grid">
            <article className="rolling-panel">
              <div className="panel-title"><span>181 個滾動五年窗</span><h3>進場時間會改變體驗</h3></div>
              <div className="rolling-rows">
                <div><span>勝 SPY</span><div><i style={{ width: `${pooled.rolling_five_year_vs_spy.cagr_win_fraction * 100}%` }} /></div><b>{pct(pooled.rolling_five_year_vs_spy.cagr_win_fraction, 1)}</b></div>
                <div><span>勝公平基準</span><div><i style={{ width: `${diagnostics.rolling_five_year_entry_timing_risk.matched.winning_window_fraction * 100}%` }} /></div><b>{pct(diagnostics.rolling_five_year_entry_timing_risk.matched.winning_window_fraction, 1)}</b></div>
                <div><span>勝純成長</span><div><i className="gold-bar" style={{ width: `${pooled.rolling_five_year_vs_growth.cagr_win_fraction * 100}%` }} /></div><b>{pct(pooled.rolling_five_year_vs_growth.cagr_win_fraction, 1)}</b></div>
              </div>
              <p>結論：策略相對 SPY 及公平基準較有一致性，但大多數五年窗不會跑贏 100% 純成長；黃金的角色是分散風險。</p>
            </article>
            <article className="bootstrap-panel">
              <div className="panel-title"><span>12 個月區塊 · 10,000 次</span><h3>配對移動區塊重抽樣</h3></div>
              <dl>
                <div><dt>回報高於 SPY</dt><dd>{pct(bootstrap.SPY["12"].probability_cagr_above, 1)}</dd></div>
                <div><dt>回報高於且最大跌幅不差於 SPY</dt><dd>{pct(bootstrap.SPY["12"].probability_cagr_above_and_drawdown_not_worse, 1)}</dd></div>
                <div><dt>回報高於公平基準</dt><dd>{pct(bootstrap.matched["12"].probability_cagr_above, 1)}</dd></div>
                <div><dt>回報高於純成長</dt><dd>{pct(bootstrap.growth["12"].probability_cagr_above, 1)}</dd></div>
              </dl>
              <p>這是對歷史月份順序的敏感度診斷，不是未來勝率，也沒有用來改寫凍結入口。</p>
            </article>
          </div>

          <div className="risk-panel">
            <div><span>HISTORICAL STRESS</span><h3>最差歷史壓力並不溫和</h3></div>
            <dl>
              <div><dt>最深跌幅</dt><dd>{pct(diagnostics.portfolio_underwater.deepest_episode.drawdown, 1)}</dd></div>
              <div><dt>高位</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.peak}</dd></div>
              <div><dt>谷底</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.trough}</dd></div>
              <div><dt>復原</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.recovery}</dd></div>
              <div><dt>水底期</dt><dd>{diagnostics.portfolio_underwater.deepest_episode.underwater_months} 個月</dd></div>
            </dl>
            <p>即使歷史最大跌幅比 SPY 淺，投資者仍可能面對超過三成跌幅和接近三年的復原期。黃金不是本金保障。</p>
          </div>
        </section>

        <section className="section wrap" id="paper">
          <div className="section-heading">
            <div><span>FORWARD PAPER TRADING</span><h2>歷史通過，前瞻證據由零開始</h2></div>
            <p>候選、SPY 與公平持倉比率基準同日起跑；不把 20 年回測接到 LIVE 圖，也不回填成交。</p>
          </div>
          <V25ForwardBoard paper={paper} integrity={paperIntegrity} />
          <PaperAllocationLab paperOnly={!latest.trade_ready} />
        </section>

        <section className="section wrap report-notes" id="notes">
          <div className="section-heading">
            <div><span>READING NOTES</span><h2>專業判讀與限制</h2></div>
            <p>報告保留支持證據與反證，避免只挑勝出的欄位。</p>
          </div>
          <div className="note-grid">
            <article><span>結論</span><h3>歷史上合格，前瞻仍未確認</h3><p>20 年三產品路徑及 pooled 入口通過，足以建立隔離 Paper；{forward.forward_sessions}/{forward.minimum_sessions} 個新增交易日不足以顯示實金參考。</p></article>
            <article><span>最重要反證</span><h3>對 SPY 的 NW t 只有 {pooled.statistics_vs_spy.newey_west_t.toFixed(2)}</h3><p>歷史年率化優勢存在，但統計證據未達常用 1.96 門檻；多重搜尋校正亦偏弱。</p></article>
            <article><span>數據邊界</span><h3>Yahoo Finance／yfinance 研究快照</h3><p>使用經調整 OHLCV 並保存 SHA-256 快照；上游不是交易所官方行情，可能回溯修訂。</p></article>
            <article><span>成本邊界</span><h3>回測不等於個人實際成交</h3><p>未涵蓋個人稅務、匯率、碎股限制、券商佣金差異、市場衝擊及即市買賣差價。</p></article>
          </div>
          <div className="source-line">
            <span>研究快照</span><code>{data.research_snapshot_sha256}</code>
            <span>v25 協議</span><code>{latest.protocol_sha256}</code>
            <a href="https://github.com/appr1ciat1/tst_wocker" target="_blank" rel="noreferrer">報告層次參考</a>
            <a href="https://github.com/voidful/us_fddk" target="_blank" rel="noreferrer">研究程式與完整證據</a>
          </div>
        </section>

        <section className="section wrap faq-section">
          <div className="section-heading">
            <div><span>QUICK ANSWERS</span><h2>四個關鍵問題</h2></div>
          </div>
          <div className="faq-list">
            <details open><summary>長線穩定策略現在可以用實金嗎？</summary><p>不可以。歷史回測通過只准建立 Paper。前瞻仍是 {forward.forward_sessions}/{forward.minimum_sessions} 個新增交易日、{forward.filled_rebalances}/{forward.minimum_filled_rebalances} 次完成重新平衡，實金動作為 US$0。</p></details>
            <details><summary>為甚麼同時比較 SPY、純成長和公平持倉比率基準？</summary><p>SPY 回答是否勝過廣泛市場；純成長回答黃金是否犧牲上行；80% 成長／20% SHY 回答黃金是否只靠降低股票持倉比率製造較淺跌幅。三者缺一不可。</p></details>
            <details><summary>目前市場判讀是買入還是避險？</summary><p>此策略沒有短線看好或看淡訊號，只在每個完整月末把比例拉回 80/20。最新五年窗仍領先 SPY，但組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}，不能解讀為保證反彈。</p></details>
            <details><summary>US$1,000 應該如何理解？</summary><p>US$800 VUG／US$200 GLD 是瀏覽器內的 Paper 比例示例，不是落盤指令。正式前瞻比較仍以 US$100,000 同起點、相同成本及相同交易日序列運作。</p></details>
          </div>
        </section>
        </div>

        <div id="short-term" data-strategy-panel="aggressive">
          <section className="hero aggressive-hero wrap">
            <div className="hero-copy">
              <div className="eyebrow-row">
                <span className="eyebrow">SHORT-TERM RETURN RESEARCH · FORMAL BACKTEST PREREGISTRATION · ROUND 18</span>
                <span className="status-chip research"><i /> 尚未啟動 PAPER</span>
              </div>
              <h1>短線高回報<br />先鎖規則才看結果</h1>
              <p className="hero-lead">
                真實與合成分開；第十八輪在任何正式策略成績出現前，把風險免費日回報、四個公平 baseline、下一開市成交、公司行動單次入賬、6,208 次 DSR 懲罰及四路 PBO 全部凍結。合成就緒控制通過 <strong>{formalReadinessControl.gate_summary.passed}/{formalReadinessControl.gate_summary.total}</strong>，十八項 RF 缺日／單位、run ID、baseline、成本、統計及來源冒充攻擊 <strong>{formalBacktestReadiness.attack_summary.rejected}/{formalBacktestReadiness.attack_summary.total} 全部拒收</strong>。
                <strong>真實正式就緒只有 {formalBacktestReadiness.actual_formal_readiness.passed}/{formalBacktestReadiness.actual_formal_readiness.total}，provider 匯入 {formalBacktestReadiness.actual_local_intake.passed}/{formalBacktestReadiness.actual_local_intake.total}、逐股數據 {formalBacktestReadiness.actual_point_in_time_readiness.passed}/{formalBacktestReadiness.actual_point_in_time_readiness.total}，正式 20 年逐股回測仍是 0 次；短線 Paper、持倉及實金動作均為 US$0</strong>。第十輪 {dailyRepair.passed}/{dailyRepair.required} 負結果及候選近期 CAGR {pct(dailyRecent.candidate.cagr, 2)} 對 QQQ {pct(dailyRecent.qqq.cagr, 2)} 繼續保留。
              </p>
              <div className="hero-actions">
                <a className="primary-button aggressive-button" href="#formal-backtest-readiness">查看正式就緒 1/18</a>
                <a className="primary-button aggressive-button" href="#local-quarantine-intake">查看隔離匯入 1/16</a>
                <a className="primary-button aggressive-button" href="#authorized-data-handoff">查看授權交接 1/12</a>
                <a className="primary-button aggressive-button" href="#ciz-execution-extension">查看 extension 16/16</a>
                <a className="secondary-button" href="#ciz-execution-accounting">查看退出會計 8/12</a>
                <a className="secondary-button" href="#crsp-ciz-mapping">查看 CIZ 映射</a>
                <a className="secondary-button" href="#provider-qualification">查看四條數據路徑</a>
                <a className="secondary-button" href="#daily-momentum-regime">查看第十輪 27/48</a>
                <a className="secondary-button" href="#point-in-time-readiness">查看 1/20 數據閘門</a>
              </div>
            </div>
            <aside className="decision-card aggressive-card" aria-label="短線高回報研究摘要">
              <div className="decision-head">
                <span>最新研究決策</span>
                <b>正式就緒 {formalBacktestReadiness.actual_formal_readiness.passed}/{formalBacktestReadiness.actual_formal_readiness.total} · strategy run 0</b>
              </div>
              <div className="capital-number"><small>讀者示例本金</small><strong>{money(readerCapital)}</strong></div>
              <div className="research-lock" aria-label="短線策略尚未開放配置">
                <span>目前短線配置</span><strong>US$0</strong><small>正式結果 0 · 就緒 1/18 · Paper 保持全現金</small>
              </div>
              <dl className="decision-list">
                <div><dt>正式就緒控制</dt><dd>{formalReadinessControl.gate_summary.passed}/{formalReadinessControl.gate_summary.total} · 只限合成</dd></div>
                <div><dt>就緒攻擊</dt><dd>{formalBacktestReadiness.attack_summary.rejected}/{formalBacktestReadiness.attack_summary.total} · 全部拒收</dd></div>
                <div><dt>超額統計</dt><dd>US 1M T-bill RF · 真實包未到</dd></div>
                <div><dt>隔離匯入控制</dt><dd>{localQuarantineIntake.synthetic_gate_summary.passed}/{localQuarantineIntake.synthetic_gate_summary.total} · 只限合成</dd></div>
                <div><dt>匯入攻擊</dt><dd>{localQuarantineIntake.attack_summary.rejected}/{localQuarantineIntake.attack_summary.total} · 全部拒收</dd></div>
                <div><dt>合成文件控制</dt><dd>{authorizedDataHandoff.synthetic_gate_summary.passed}/{authorizedDataHandoff.synthetic_gate_summary.total} · 只驗證格式</dd></div>
                <div><dt>供應商聯絡</dt><dd>0 · 回覆 0 · 樣本 0</dd></div>
                <div><dt>Extension 攻擊</dt><dd>{cizExecutionExtension.attack_summary.rejected}/{cizExecutionExtension.attack_summary.total} · 全部拒收</dd></div>
                <div><dt>真實數據入口</dt><dd>{pointInTimeReadiness.gate_summary.passed}/{pointInTimeReadiness.gate_summary.total} · 尚未授權匯入</dd></div>
                <div><dt>最新機制結果</dt><dd>第十輪 {dailyRepair.passed}/{dailyRepair.required} · 失敗</dd></div>
                <div><dt>近期機會成本</dt><dd>候選 {pct(dailyRecent.candidate.cagr, 2)}／QQQ {pct(dailyRecent.qqq.cagr, 2)}</dd></div>
                <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
              </dl>
              <p>US$1,000 複利數字只解釋歷史尺度，不包括通脹、稅項及真實買賣差價，亦不是預測。</p>
            </aside>
          </section>

          <section className="truth-strip aggressive-truth">
            <div className="wrap truth-grid">
              <article><span>正式回測就緒</span><strong>{formalBacktestReadiness.actual_formal_readiness.passed}/{formalBacktestReadiness.actual_formal_readiness.total}</strong><small>只通過事前凍結</small></article>
              <article><span>正式合成控制</span><strong>{formalReadinessControl.gate_summary.passed}/{formalReadinessControl.gate_summary.total}</strong><small>不是策略回報通過</small></article>
              <article><span>真實隔離匯入</span><strong>{localQuarantineIntake.actual_local_intake.passed}/{localQuarantineIntake.actual_local_intake.total}</strong><small>只通過事前凍結</small></article>
              <article><span>真實文件交接</span><strong>{authorizedDataHandoff.actual_document_handoff.passed}/{authorizedDataHandoff.actual_document_handoff.total}</strong><small>只通過事前凍結</small></article>
              <article><span>Extension 合成控制</span><strong>{cizExecutionExtension.gate_summary.passed}/{cizExecutionExtension.gate_summary.total}</strong><small>不是供應商數據通過</small></article>
              <article><span>執行會計閘門</span><strong>{cizExecutionAccounting.gate_summary.passed}/{cizExecutionAccounting.gate_summary.total}</strong><small>舊八份賬本仍缺四項</small></article>
              <article><span>CIZ 映射控制</span><strong>{crspCizMapping.synthetic_control.gates_passed}/{crspCizMapping.synthetic_control.gates_total}</strong><small>必要但不足以執行</small></article>
              <article><span>逐股數據閘門</span><strong>{pointInTimeReadiness.gate_summary.passed}/{pointInTimeReadiness.gate_summary.total}</strong><small>只通過事前凍結</small></article>
              <article><span>第十輪總門檻</span><strong>{dailyRepair.passed}/{dailyRepair.required}</strong><small>近期只過 {dailyRepair.recent_passed}/{dailyRepair.recent_required}</small></article>
              <article><span>正式逐股回測</span><strong>未運行</strong><small>不以現時成分倒推</small></article>
              <article><span>短線 Paper</span><strong>未啟動</strong><small>實金及 Paper 均為 0</small></article>
            </div>
          </section>

          <section className="section wrap" id="formal-backtest-readiness">
            <div className="section-heading">
              <div><span>FORMAL BACKTEST READINESS · ROUND 18</span><h2>合成就緒 18/18、攻擊 18/18；真實正式就緒仍只有 1/18</h2></div>
              <p>這一輪不試新參數、不產生成績；先把正式 20 年逐股回測的 RF、baseline、會計、統計及一次性 run ID 鎖死，避免看到結果後移動龍門。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>QQQ／SPY 不等於風險免費；超額統計不能再用 0 或 SHY 偷代</h3>
                <p>{formalBacktestReadiness.gap_closed.risk_free_proxy} 正式 RF 必須與 XNYS 交易日一對一、以 decimal simple daily return 表示，來源、版本、授權、列數及 SHA-256 全部對數。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>合成控制／攻擊</span><strong>{formalReadinessControl.gate_summary.passed}/{formalReadinessControl.gate_summary.total} · {formalBacktestReadiness.attack_summary.rejected}/{formalBacktestReadiness.attack_summary.total}</strong><p>只證明壞 RF、改規則或來源冒充會失敗關閉。</p></article>
                <article><span>真實決策</span><strong>就緒 {formalBacktestReadiness.actual_formal_readiness.passed}/{formalBacktestReadiness.actual_formal_readiness.total} · 回測 {formalBacktestReadiness.strategy_run_count}</strong><p>provider package 及真實 RF 均未收到；Paper 全現金。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOUR FAIR BASELINES</span><h3>四個比較對手在正式結果前定義清楚</h3></div>
              <p>所有路徑同一交易日、US$1,000、下一日 raw open、公司行動及 10／25／50 bps；候選不能只挑較弱的 QQQ 比。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第十八輪四個正式 baseline">
              {formalBaselineRows.map((row, index) => (
                <article className="passed" key={row.key}><span>{String(index + 1).padStart(2, "0")}</span><b>{row.label}</b><strong>{index < 2 ? "買入持有" : index === 2 ? "月度等權" : "只買一次"}</strong><p>{row.detail}</p></article>
              ))}
            </div>
            <div className="comparison-caveat"><b>漂移 baseline 已消除歧義：</b><p>{formalBacktestReadiness.gap_closed.drift_baseline} 若公司退出，仍按退市／現金／換股條款只結算一次，現金退出款不假設賺取 RF。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ACCOUNTING &amp; STATISTICS</span><h3>US$1,000、下一開市、6,208 trials 及四路 PBO 不可事後改</h3></div>
              <p>組合中的零碎現金固定 0% 回報；RF 只用於風險免費超額 Sharpe、PSR／DSR，QQQ 補位仍是風險資產。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>正式顯示本金</span><strong>US$1,000</strong><p>容許碎股以隔離資金規模影響；不代表實金落盤金額。</p></article>
              <article><span>成交／成本</span><strong>t+1 raw open · 10／25／50 bps</strong><p>三個成本情境完整重跑，不以 CAGR 事後近似。</p></article>
              <article><span>超額回報基準</span><strong>US 1M T-bill daily RF</strong><p>真實 provider RF 尚未收到；合成短表沒有市場證據。</p></article>
              <article><span>全專案 DSR</span><strong>{formalReadinessControl.global_search_trials.toLocaleString("zh-HK")} trials</strong><p>成功、失敗及未升級路徑全計入，不把首次正式 run 重設為 1。</p></article>
              <article><span>PBO</span><strong>{formalReadinessControl.pbo_paths} 路 · 10 段 CSCV</strong><p>綜合 Top-10 加三個既有台股直譯消融；不以勝出者換掉正式候選。</p></article>
              <article><span>一次性執行</span><strong>immutable run ID</strong><p>綁定 intake、ledger、execution、RF、政策及協議 SHA-256；同一組輸入只准一次。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FORMAL READINESS GATES</span><h3>十八道事前控制逐項呈列</h3></div>
              <p>合成 18/18 只驗證程式形狀；真實仍是 1/18，正式策略結果及選股名單都沒有生成。</p>
            </div>
            <div className="point-in-time-gate-list">
              {formalReadinessControl.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十八項 RF、run ID、baseline、成本及決策錯誤全數拒收</h3></div>
              <p>每次只改一個語義條件並對準指定 error code，避免普通 hash 錯誤掩蓋真正會計或統計問題。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {formalReadinessAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>只在合法 provider package 與同步一個月國庫券 RF 都到位後，運行一次固定正式回測</b></div>
              <p>{formalBacktestReadiness.next_action} 任何經濟或統計門檻失敗即封存，不改權重、窗口、持股數或成本救援；全部通過亦只准由全現金開始前瞻 Paper。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FORMAL_BACKTEST_READINESS_REPORT.md" target="_blank" rel="noreferrer">第十八輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FORMAL_BACKTEST_PREREGISTRATION.md" target="_blank" rel="noreferrer">一次性事前登記</a><a href="https://github.com/voidful/us_fddk/blob/main/scripts/validate_short_term_formal_backtest_readiness.py" target="_blank" rel="noreferrer">只讀正式入口</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_formal_backtest_readiness_validation.json" target="_blank" rel="noreferrer">機器收據</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html" target="_blank" rel="noreferrer">一個月國庫券 RF 定義</a></div>
            </div>
          </section>

          <section className="section wrap" id="local-quarantine-intake">
            <div className="section-heading">
              <div><span>LOCAL QUARANTINE INTAKE · ROUND 17</span><h2>合成匯入 16/16、攻擊 16/16；真實匯入仍只有 1/16</h2></div>
              <p>收到授權文件與細樣本後，必須先分辨真實／合成來源，再在 repository 外完成原子轉換、20/20 點時稽核及 16/16 execution 稽核；本輪仍沒有任何供應商輸入。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>舊 bridge 的 synthetic 標示不能直接承接真實供應商包</h3>
                <p>{localQuarantineIntake.gap_closed.finding} 新 bridge 另立 provider status，沒有修改第十五輪程式、報告或 16/16 收據。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>合成匯入／攻擊</span><strong>{localQuarantineIntake.synthetic_gate_summary.passed}/{localQuarantineIntake.synthetic_gate_summary.total} · {localQuarantineIntake.attack_summary.rejected}/{localQuarantineIntake.attack_summary.total}</strong><p>只證明模式、路徑、數據及權限錯誤會被拒收。</p></article>
                <article><span>真實決策</span><strong>provider run {localQuarantineIntake.provider_mode_run_count} · 回測 0</strong><p>四個外部絕對路徑仍未提供；不掃描、不猜測、不建立 Paper。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EXPLICIT SOURCE MODES</span><h3>真實與合成 status 不可互換</h3></div>
              <p>下游程式可由 manifest 直接辨認來源，不再把工程控制誤當市場證據。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第十七輪來源及隔離控制">
              <article className="passed"><span>01</span><b>合成控制</b><strong>synthetic_local…</strong><p>只供固定 harness；不能授權正式回測。</p></article>
              <article className="passed"><span>02</span><b>授權供應商</b><strong>authorized_provider…</strong><p>只有真實文件、數據 20/20 及 extension 16/16 才可產生。</p></article>
              <article className="passed"><span>03</span><b>本地隔離</b><strong>0700／0600</strong><p>目錄及檔案 owner-only；原始列不進 Git 或 Action artifact。</p></article>
              <article className="passed"><span>04</span><b>原子輸出</b><strong>staging → rename</strong><p>目的地必須全新；失敗時不留下半套 package。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>LOCAL INTAKE GATES</span><h3>十六道匯入控制逐項呈列</h3></div>
              <p>合成 16/16 不提高真實匯入 1/16；provider 16/16 亦只准另一步運行一次凍結正式回測。</p>
            </div>
            <div className="point-in-time-gate-list">
              {localQuarantineIntake.synthetic_gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十六項路徑、來源、數據及權限錯誤全數拒收</h3></div>
              <p>包括 repo 內路徑、symlink、synthetic 冒充 provider、身份不符、授權 false、前視成分、QQQ 缺日及 world-readable 輸出。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {localIntakeAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>只在使用者明確提供四個外部絕對路徑後運行 provider mode</b></div>
              <p>即使真實匯入 16/16，程式亦不自動跑策略、不調參、不回填成交及不建立 Paper；只會產生可供一次固定正式回測的 owner-only package。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_LOCAL_QUARANTINE_INTAKE_REPORT.md" target="_blank" rel="noreferrer">第十七輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_LOCAL_QUARANTINE_INTAKE_PROTOCOL.md" target="_blank" rel="noreferrer">事前匯入協議</a><a href="https://github.com/voidful/us_fddk/blob/main/scripts/validate_short_term_local_quarantine_intake.py" target="_blank" rel="noreferrer">本地 CLI</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_local_quarantine_intake_validation.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="authorized-data-handoff">
            <div className="section-heading">
              <div><span>AUTHORIZED DATA HANDOFF · ROUND 16</span><h2>合成文件 12/12、攻擊 12/12；真實文件只有 1/12</h2></div>
              <p>把「需要甚麼數據」收窄成可直接交付的固定請求。這一輪只核對公開官方文件及本地驗證器，沒有登入、購買、聯絡供應商或取得市場列。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>請求已準備好；供應商能力及授權仍未證實</h3>
                <p>固定 Request ID、協議雜湊、20 年區間、十份輸入及 QQQ／SPY 同步基準。公開目錄名稱只作登入後確認候選，不當成訂閱、能力或數據通過。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>本地合成控制</span><strong>{authorizedDataHandoff.synthetic_gate_summary.passed}/{authorizedDataHandoff.synthetic_gate_summary.total} · 攻擊 {authorizedDataHandoff.attack_summary.rejected}/{authorizedDataHandoff.attack_summary.total}</strong><p>證明文件驗證器會按指定錯誤關門。</p></article>
                <article><span>真實狀態</span><strong>文件 {authorizedDataHandoff.actual_document_handoff.passed}/{authorizedDataHandoff.actual_document_handoff.total} · 數據 {authorizedDataHandoff.actual_point_in_time_readiness.passed}/{authorizedDataHandoff.actual_point_in_time_readiness.total}</strong><p>供應商聯絡 0、文件回覆 0、合法樣本 0、正式回測 0。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED REQUEST</span><h3>同一產品、時段、欄位與成交時鐘</h3></div>
              <p>避免看到供應商 export 後才刪難處理欄位、縮短時段或改基準。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第十六輪固定數據請求">
              <article className="passed"><span>01</span><b>固定正式期</b><strong>{authorizedDataHandoff.coverage.formal_start} → {authorizedDataHandoff.coverage.formal_end}</strong><p>由 {authorizedDataHandoff.coverage.buffer_start} 起留至少 {authorizedDataHandoff.coverage.minimum_pre_signal_sessions} 個訊號前 session。</p></article>
              <article className="passed"><span>02</span><b>十份輸入</b><strong>{authorizedDataHandoff.source_file_count} 份</strong><p>五份 CIZ，加成分公布、公司行動、退出條款及日曆證據層。</p></article>
              <article className="passed"><span>03</span><b>產品候選</b><strong>{authorizedDataHandoff.provider_products_to_confirm.map((row) => row.product_code).join("／")}</strong><p>Monthly 是公開更新套裝標示；不推論只有月線。</p></article>
              <article className="passed"><span>04</span><b>公平基準</b><strong>QQQ／SPY</strong><p>同一交易日、raw open、總回報因子及來源記錄 ID。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>DOCUMENT GATES</span><h3>十二道文件控制逐項呈列</h3></div>
              <p>12/12 只准供應商文件進入細樣本交付；不提高真實 1/20，不啟動回測或 Paper。</p>
            </div>
            <div className="point-in-time-gate-list">
              {authorizedDataHandoff.synthetic_gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十二項文件錯誤，全數以指定代碼拒收</h3></div>
              <p>每次攻擊重新計算 response SHA-256，只保留一項 schema、授權、時間或數據能力錯誤。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {handoffAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>OFFICIAL DOCUMENT CHECK</span><h3>公開名稱可核對；完整 data dictionary 仍要登入</h3></div>
              <p>以下全是一手官方頁，只支持「候選名稱」及 CIZ 現行格式，不支持已訂閱或可完整交付的結論。</p>
            </div>
            <div className="data-source-grid">
              {authorizedDataHandoff.official_findings.map((finding) => (
                <article key={finding.id}>
                  <span>{finding.status.replaceAll("_", " ")}</span>
                  <h3>{finding.detail}</h3>
                  <a href={finding.url} target="_blank" rel="noreferrer">查看官方文件</a>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>先取得使用者授權，再發送固定請求</b></div>
              <p>供應商文件 12/12 後，只收本地隔離細樣本，再依次運行細樣本驗收、真實數據 20/20、extension 16/16 及一次固定策略回測。任何一層失敗都不改規則、不刪退出樣本、不開短線 Paper。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_AUTHORIZED_DATA_HANDOFF.md" target="_blank" rel="noreferrer">第十六輪完整交接文件</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_AUTHORIZED_DATA_HANDOFF_PROTOCOL.md" target="_blank" rel="noreferrer">事前交接協議</a><a href="https://github.com/voidful/us_fddk/blob/main/schemas/short_term_authorized_data_response.schema.json" target="_blank" rel="noreferrer">回覆 JSON Schema</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_authorized_data_handoff.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="ciz-execution-extension">
            <div className="section-heading">
              <div><span>CIZ EXECUTION EXTENSION · ROUND 15</span><h2>合成 extension 16/16、攻擊 16/16；真實逐股數據仍是 1/20</h2></div>
              <p>第十四輪找到四項不能靠舊賬本回答的問題。本輪沒有改寫舊 adapter，而是新增四份可雜湊、可重建的 execution 數據表，逐項證明 bridge 會拒絕缺日、雙重計算、不同步基準及同日成交。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>四項 schema 缺口已封口；市場證據仍未到位</h3>
                <p>合成控制保留 dividend pay-date、至少 252 日訊號歷史、移除日至下一重新平衡 open 的完整價格，以及 QQQ／SPY 同步行情。這是工程可執行性，不是策略回報或供應商通過。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>合成控制／攻擊</span><strong>{cizExecutionExtension.gate_summary.passed}/{cizExecutionExtension.gate_summary.total} · {cizExecutionExtension.attack_summary.rejected}/{cizExecutionExtension.attack_summary.total}</strong><p>十六道全過、十六項全拒收；每次攻擊均重算上游收據。</p></article>
                <article><span>正式決策</span><strong>回測 0 · US$0</strong><p>合法樣本仍是 0；短線 Paper 保持全現金，不展示個股名單。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOUR CLOSED SCHEMA GAPS</span><h3>每項都有可核對日期、計數或價格路徑</h3></div>
              <p>以下全部是合成控制，數字只描述測試 fixture；不會加入回測表現或變成買賣訊號。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第十五輪四項 execution extension 控制">
              <article className="passed"><span>01</span><b>派息付款日</b><strong>{cizExecutionExtension.control_examples.dividend.ex_date} → {cizExecutionExtension.control_examples.dividend.pay_date}</strong><p>Ex-date 建立應收；pay-date 才成為可交易現金。</p></article>
              <article className="passed"><span>02</span><b>訊號前歷史</b><strong>{cizExecutionExtension.control_examples.minimum_return_sessions}／252</strong><p>正成交量亦有 {cizExecutionExtension.control_examples.minimum_positive_volume_sessions} 個 session，門檻為 20。</p></article>
              <article className="passed"><span>03</span><b>移除後成交路徑</b><strong>{cizExecutionExtension.control_examples.removal.observed_sessions}/{cizExecutionExtension.control_examples.removal.required_sessions} sessions</strong><p>{cizExecutionExtension.control_examples.removal.membership_effective_to} 移除，{cizExecutionExtension.control_examples.removal.execution_session} open 才退出。</p></article>
              <article className="passed"><span>04</span><b>公平基準同步</b><strong>{cizExecutionExtension.synthetic_counts.benchmark_rows} 列</strong><p>QQQ／SPY 使用相同交易日、raw open、總回報及凍結成本。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIVE HASHED OUTPUTS</span><h3>原八份賬本不改；execution 層獨立對數</h3></div>
              <p>Bridge 把每個關鍵判斷寫成可重建檔案，不把新欄位塞回舊 manifest 或事後改寫第十三輪證據。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第十五輪 execution extension 輸出">
              <article className="passed"><span>01</span><b>cash_entitlements</b><strong>{cizExecutionExtension.synthetic_counts.cash_entitlements} 行</strong><p>公告、除息、付款及現金可用日分欄。</p></article>
              <article className="passed"><span>02</span><b>signal_eligibility</b><strong>{cizExecutionExtension.synthetic_counts.signal_eligibility_rows} 行</strong><p>每個月末、每個永久 ID 的回報與流動性計數。</p></article>
              <article className="passed"><span>03</span><b>removal_windows</b><strong>{cizExecutionExtension.synthetic_counts.removal_execution_windows} 行</strong><p>移除日至下一訊號後開市的完整路徑。</p></article>
              <article className="passed"><span>04–05</span><b>benchmark＋manifest</b><strong>QQQ／SPY</strong><p>行情與 base／overlay／策略／輸出 SHA-256 一併鎖定。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN CONTROL CONTRACT</span><h3>十六道 extension 閘門逐項呈列</h3></div>
              <p>16/16 只代表合成 bridge 可重現；真實供應商包仍須另行跑 20 道 point-in-time 閘門。</p>
            </div>
            <div className="point-in-time-gate-list">
              {cizExecutionExtension.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十六項單一錯誤，全數以指定代碼停止</h3></div>
              <p>缺付款日、251 日歷史、19 日成交量、移除後缺價、QQQ／SPY 不同步、成本漂移及同日 open 全部直接拒收。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {extensionAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>只索取合法細樣本，不以合成 16/16 先跑策略</b></div>
              <p>真實包須同時提供 CIZ point-in-time／退出列、DisPayDt、研究期前 252 日候選歷史及同步 QQQ／SPY raw open。真實 20/20 與 extension 16/16 都通過後，才可按凍結 v1 運行一次正式回測。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CIZ_EXECUTION_EXTENSION_REPORT.md" target="_blank" rel="noreferrer">第十五輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CIZ_EXECUTION_EXTENSION_PROTOCOL.md" target="_blank" rel="noreferrer">事前 extension 協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_ciz_execution_extension_validation.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="ciz-execution-accounting">
            <div className="section-heading">
              <div><span>CIZ EXECUTION ACCOUNTING · ROUND 14</span><h2>退出會計 8/12；十項攻擊全拒收，四項正式輸入仍缺</h2></div>
              <p>20/20 賬本只證明數據形狀完整。本輪再問一次：若真的持有股份，退市、收購、派息、拆細及成分移除能否按下一開市時鐘準確結算，而且不重複計回報？</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>退市沒有雙計，但正式引擎仍不可運行</h3>
                <p>最後持倉值 100、DelRet −50% 時，正確終端值是 {cizExecutionAccounting.accounting_controls.delisting_terminal_value_once.toFixed(0)}；adapter 沒有把 DelDlyDt storage row 再計一次。現金收購、換股、拆細與分拆亦通過唯一結算控制。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>固定攻擊</span><strong>{cizExecutionAccounting.attack_summary.rejected}/{cizExecutionAccounting.attack_summary.total}</strong><p>雙計、早收股息、缺歷史、缺 benchmark 及同日成交全部拒收。</p></article>
                <article><span>正式決策</span><strong>回測 0 · US$0</strong><p>四項缺口未補；Paper 維持全現金，不顯示選股名單。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>ONCE-ONLY ACCOUNTING</span><h3>五個固定例子，經濟價值沒有憑空增加或消失</h3></div>
              <p>這些是合成算術控制，不是策略回報；用途是防止未來正式數據在退出或公司行動時重複入賬。</p>
            </div>
            <div className="point-in-time-groups" aria-label="退出與公司行動會計控制">
              <article className="passed"><span>01</span><b>退市 −50%</b><strong>100 → {cizExecutionAccounting.accounting_controls.delisting_terminal_value_once.toFixed(0)}</strong><p>DelRet 只由 outcome 結算一次。</p></article>
              <article className="passed"><span>02</span><b>現金收購</b><strong>2 × 50 = {cizExecutionAccounting.accounting_controls.cash_exit_terminal_value.toFixed(0)}</strong><p>缺 DelRet 時只用可追溯每股現金代價。</p></article>
              <article className="passed"><span>03</span><b>換股收購</b><strong>4 × 0.5 = {cizExecutionAccounting.accounting_controls.stock_exit_successor_shares.toFixed(0)} 股</strong><p>舊股消失，successor 持股只建立一次。</p></article>
              <article className="passed"><span>04</span><b>2-for-1 拆細</b><strong>100 → {cizExecutionAccounting.accounting_controls.split_after_value.toFixed(0)}</strong><p>股數倍增、價格減半，不當成額外 +100% 回報。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FORMAL ENGINE GATES</span><h3>十二道閘門逐項呈列，不用 20/20 headline 掩蓋缺口</h3></div>
              <p>未通過項目會直接阻止正式 20 年回測；合成映射、程式綠燈或品牌文件都不能代替。</p>
            </div>
            <div className="point-in-time-gate-list">
              {cizExecutionAccounting.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十項會計與成交攻擊，全數以指定代碼停止</h3></div>
              <p>攻擊通過只代表 auditor 能辨認錯誤；不會把 8/12 包裝成正式引擎完成。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {executionAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 15 FOLLOW-UP</span><b>四項 extension 已在合成控制封口；真實數據仍未通過</b></div>
              <p>第十五輪已把 dividend pay-date、每股訊號前 252 日、移除後至下一重新平衡 open，以及同步 QQQ／SPY／QQQ 補位行情寫成獨立合約；本輪 8/12 歷史結果不被事後改寫。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CIZ_EXECUTION_ACCOUNTING_REPORT.md" target="_blank" rel="noreferrer">第十四輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CIZ_EXECUTION_ACCOUNTING_PROTOCOL.md" target="_blank" rel="noreferrer">事前會計協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_ciz_execution_accounting_validation.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="crsp-ciz-mapping">
            <div className="section-heading">
              <div><span>CRSP CIZ MAPPING · ROUND 13</span><h2>映射 20/20、攻擊 12/12 拒收；真實數據仍是 1/20</h2></div>
              <p>只接受現行 CIZ Flat File Format 2.0；公開欄位未能證明的公布時間、可用時間及缺失退出代價必須另有 evidence overlay，轉換器不會自行推算補洞。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>成分生效日不是公布時間；退市儲存日不是退出日</h3>
                <p>CIZ 的 MbrStartDt／MbrEndDt 只作在籍區間；DelistingDt 保留為最後價格日，DelDlyDt 只核對退市回報在日檔的儲存日。缺少 announcement、security-info KnownAt 或退出經濟條款即停止。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>合成 CIZ → 八份賬本</span><strong>{crspCizMapping.synthetic_control.gates_passed}/{crspCizMapping.synthetic_control.gates_total}</strong><p>不含供應商原始列；只證明凍結映射可通過下游稽核。</p></article>
                <article><span>真實狀態</span><strong>{crspCizMapping.actual_point_in_time_readiness.passed}/{crspCizMapping.actual_point_in_time_readiness.total} · US$0</strong><p>合法樣本 0、正式回測 0、Paper 0；沒有因合成測試升格。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIELD POLICY</span><h3>直接、派生、外加、禁止推算四層分開</h3></div>
              <p>永久 ID、raw OHLCV 及有效區間可按官方欄位轉換；公布／可用時間及缺失退市代價只能由可追溯外加證據補足。</p>
            </div>
            <div className="point-in-time-groups" aria-label="CIZ 欄位映射四層政策">
              <article className="passed"><span>01</span><b>官方直接欄位</b><strong>可映射</strong><p>PERMNO／PERMCO、raw OHLCV、membership 起訖及 DelRet。</p></article>
              <article className="passed"><span>02</span><b>決定性派生</b><strong>可重現</strong><p>inclusive end 轉 half-open；總回報因子固定為 1 + DlyRet。</p></article>
              <article><span>03</span><b>外加證據</b><strong>必須提供</strong><p>成分 announced_at、security-info KnownAt、公司行動及缺失退出代價。</p></article>
              <article><span>04</span><b>禁止推算</b><strong>拒收</strong><p>現時 ticker 倒填、adjusted 價當 raw、DelRet 補 0、DelDlyDt 當退出日。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>十二種單一錯誤，全數在指定閘門被擋下</h3></div>
              <p>每次都重算列數與 SHA-256，再核對指定 error code；不是用「檔案被改」一個泛化錯誤掩蓋語義。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {cizAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>只向 CRSP／WRDS 索取合法 schema、細樣本及授權條款</b></div>
              <p>小樣本必須同時提供 membership announcement、security-info availability、公司行動正規化及缺失退出代價四類 evidence overlay；任何一類缺失都不會用 effective date 或匯出日代替。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CRSP_CIZ_MAPPING_REPORT.md" target="_blank" rel="noreferrer">第十三輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CRSP_CIZ_MAPPING_PROTOCOL.md" target="_blank" rel="noreferrer">事前映射協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_crsp_ciz_mapping_validation.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="provider-qualification">
            <div className="section-heading">
              <div><span>PROVIDER QUALIFICATION · ROUND 11</span><h2>四條數據路徑：沒有一條可單獨通過</h2></div>
              <p>先按同一套 20 道合約審查官方文件，再決定是否值得索取樣本。文件有欄位只代表可查詢，不代表真實數據已到手或閘門通過。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict provider-verdict">
                <span>最新研究判斷</span>
                <h3>CRSP／WRDS 只適合先索取正式樣本</h3>
                <p>官方文件明確支持 10/20、部分支持 2/20，但未見 S&amp;P 500 成分公布時間，部分 delisting return 亦可能缺失。未取得授權、細樣本、雜湊及逐列稽核前，CRSP 仍不是 20/20。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>供應商預審</span><strong>{providerQualifiedCount}/{providerRows.length}</strong><p>四條路徑本地驗證全部為 false；不能將產品文件當成回測數據。</p></article>
                <article><span>實際研究入口</span><strong>1/20 · US$0</strong><p>正式逐股回測 0 次、Paper 0 成交、持倉 0；全部保持關閉。</p></article>
              </div>
            </div>

            <div className="provider-grid" aria-label="四條數據來源資格摘要">
              {providerRows.map((row) => (
                <article className={row.first_enquiry ? "first-enquiry" : undefined} key={row.id}>
                  <div className="provider-card-head"><span>{row.first_enquiry ? "FIRST ENQUIRY" : "SUPPLEMENT ONLY"}</span><b>{row.name}</b></div>
                  <strong>{row.status_counts.documented}/20 明確 · {row.status_counts.partial}/20 部分</strong>
                  <p>{row.role}</p>
                  <ul>{row.hard_blockers.slice(0, 2).map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>
                  <small>{row.first_enquiry ? "下一步：索取 data dictionary、細樣本及授權條款；仍未通過。" : row.next_action}</small>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CAPABILITY MATRIX</span><h3>十項核心能力：明確不等於通過</h3></div>
              <p>「需登入」不假定訂閱後一定存在；「待匯入」只能靠真實列數、雜湊、覆蓋率及正反稽核回答。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table provider-table">
                <thead><tr><th>核心能力</th>{providerRows.map((row) => <th key={row.id}>{row.name}</th>)}</tr></thead>
                <tbody>{providerCapabilityRows.map((capability) => (
                  <tr key={capability.key}><th><b>{capability.label}</b></th>{providerRows.map((row) => {
                    const status = row.selected_gates[capability.key].status;
                    return <td key={row.id}><span className={`provider-status ${status}`}>{providerStatusLabels[status]}</span></td>;
                  })}</tr>
                ))}</tbody>
              </table>
            </div>
            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>先向 CRSP／WRDS 問五個可判定問題，不先買結論</b></div>
              <p>確認成分公告時間、缺失 delisting return、20 年 OHLCV／停牌覆蓋、歷史分類可知時間及本地研究授權。只有合法數據包跑過 20/20，才按既有 v1 原樣正式回測一次。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_QUALIFICATION_REPORT.md" target="_blank" rel="noreferrer">第十一輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_QUALIFICATION_PROTOCOL.md" target="_blank" rel="noreferrer">事前協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_provider_qualification.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="daily-momentum-regime">
            <div className="section-heading">
              <div><span>DAILY MOMENTUM REGIME · ROUND 10</span><h2>危機減倉有效，但近期回報幾乎消失</h2></div>
              <p>唯一候選、訊號延遲一日、5% 學術實作拖累、10／25／50 bps、早期／近期、固定 baseline 及 48 道門檻均在結果前鎖定。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>早期 {pct(dailyEarly.candidate.cagr, 2)}，近期只餘 {pct(dailyRecent.candidate.cagr, 2)}</h3>
                <p>候選早期勝 French 市場，但 1985–2006 已轉為落後；近期兩個固定十年都輸 QQQ，204 個滾動三年窗只有 {pct(dailyRecent.rolling_three_year.cagr_win_fraction, 1)} 勝出。這是跨世代失效，不是單一危機或起點問題。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>原始數據合約</span><strong>{dailyMomentumRegime.original_data_contract.passed}/{dailyMomentumRegime.original_data_contract.required}</strong><p>官方 marker 比映射多一個 Average；原輪在策略計算前停止，失敗收據保留。</p></article>
                <article><span>Schema repair</span><strong>非獨立 · {dailyRepair.passed}/{dailyRepair.required}</strong><p>只精確修正 marker，不重下載或改門檻；因已看見原始 schema，不能冒充首次未見證據。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT 20 YEARS · FAIR BASELINES</span><h3>QQQ、SPY、原始動量與相同持倉比率全部列出</h3></div>
              <p>French Hi PRIOR 是 CRSP-based 學術組合而非可買 ETF；US$1,000 只量度歷史複利尺度，不是預測。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>每年換手</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{dailyRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.annual_turnover, 1)}×</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, STABILITY & STATISTICS</span><h3>低成本假設亦救不到近期結果</h3></div>
              <p>成本表同時改變年度學術拖累與每日持倉轉換成本；所有組合仍沿用同一訊號。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>年度學術拖累</th><th>轉倉成本</th><th>近期 CAGR</th><th>最大跌幅</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{dailyCostRows.map((row) => (
                  <tr key={`${row.annual_drag}-${row.overlay_cost_bps}`}>
                    <th><b>{pct(row.annual_drag, 0)}</b><span>事前固定敏感度</span></th><td>{row.overlay_cost_bps} bps</td><td>{pct(row.metrics.cagr, 2)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="short-evidence-grid">
              <article><span>兩個固定十年</span><strong>{pp(dailyRecent.first_half.cagr_difference)}／{pp(dailyRecent.second_half.cagr_difference)}</strong><p>均為候選相對 QQQ 的 CAGR 差，沒有用單一完整期掩蓋後半失效。</p></article>
              <article><span>相對 QQQ 統計</span><strong>NW t {dailyRecent.newey_west_vs_qqq.t_stat.toFixed(2)}</strong><p>PSR {pct(dailyRecent.psr_vs_qqq, 2)}；經 6,208 次全專案搜尋校正後 DSR 幾乎為零。</p></article>
              <article><span>平均持倉比率／每年換手</span><strong>{pct(dailyRecent.exposure.average, 1)}／{multiple(dailyRecent.candidate.annual_turnover, 1)}×</strong><p>只准 0／50／100%，不借款、不沽空；高換手令 25／50 bps 結果快速惡化。</p></article>
              <article><span>近期三因子 alpha</span><strong>{pct(dailyRecent.factor_regression.annualized_alpha, 2)}</strong><p>市場 beta {multiple(dailyRecent.factor_regression.market_beta)}；負 alpha 反駁「純粹因低 beta 才落後」的解釋。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS CHECK</span><h3>跌幅較淺，不等於值得犧牲二十年升幅</h3></div>
              <p>三段危機只作固定壓力測試；不以事後危機日期改變候選訊號。</p>
            </div>
            <div className="context-grid">
              {dailyStressRows.map((row) => (
                <article key={row.label}><span>{row.label}</span><strong>{pct(row.result.candidate.max_drawdown, 1)}</strong><p>候選最大跌幅；QQQ 為 {pct(row.result.qqq.max_drawdown, 1)}。風控有作用，但不能抵銷長期回報缺口。</p></article>
              ))}
            </div>
            <div className="comparison-caveat"><b>最新決策：</b><p>第十輪 27/48 失敗，參數不救援；Paper、持倉及實金動作均為 US$0。下一個正式逐股研究仍須先把 point-in-time／退市賬本由 1/20 提升至 20/20，再按已凍結 v1 原樣運行。</p></div>
          </section>

          <section className="section wrap" id="point-in-time-readiness">
            <div className="section-heading">
              <div><span>DATA INTEGRITY GATE · ROUND 9</span><h2>逐股數據就緒度：1/20，先堵住存活者偏差</h2></div>
              <p>選股規則完全不變；本輪只回答數據是否足以進行可信的 20 年逐股回測。沒有供應商數據時失敗關閉，不拼接現時名單與殘缺價格。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>驗證器已能拒絕壞數據；真實供應商數據仍未到位</h3>
                <p>合格合成賬本可通過 20/20；檔案被改、成分事後才知、ticker 重疊、永久退出缺回報或退出後仍有價格時都會拒收。這只證明硬閘門有效，不是市場數據或策略成功。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>唯一已通過</span><strong>事前凍結 1/1</strong><p>數據合約、manifest schema 及既有個股 v1 規則 SHA-256 全部吻合。</p></article>
                <article><span>資金界線</span><strong>全現金 · US$0</strong><p>正式回測 0 次、Paper 0 成交、持倉 0；不回填歷史交易。</p></article>
              </div>
            </div>

            <div className="point-in-time-groups" aria-label="逐股數據四組閘門摘要">
              <article><span>01</span><b>供應商與數據包</b><strong>{pointInTimeGroupCount(1, 3)}</strong><p>授權、manifest、八份檔案雜湊仍待真實數據。</p></article>
              <article className="passed"><span>02</span><b>事前凍結順序</b><strong>{pointInTimeGroupCount(4, 4)}</strong><p>先鎖規則及 schema，後來的數據不能改門檻。</p></article>
              <article><span>03</span><b>逐股歷史賬本</b><strong>{pointInTimeGroupCount(5, 19)}</strong><p>永久 ID、成分、價格、退出、公司行動及行業全數待驗。</p></article>
              <article><span>04</span><b>D+1 成交時鐘</b><strong>{pointInTimeGroupCount(20, 20)}</strong><p>schema 已固定；真實交易日與開收市價仍待接入。</p></article>
            </div>

            <details className="point-in-time-details">
              <summary>展開全部 20 道數據閘門</summary>
              <div className="point-in-time-gate-list">
                {pointInTimeGateRows.map((row) => (
                  <article className={row.passed ? "passed" : "blocked"} key={row.key}>
                    <span>{row.number}</span><div><b>{row.label}</b><p>{row.detail}</p></div><strong>{row.passed ? "通過" : "未驗證"}</strong>
                  </article>
                ))}
              </div>
            </details>

            <div className="subsection-heading stock-heading">
              <div><span>FAIL-CLOSED TESTS</span><h3>十二種固定攻擊加一個完整控制包</h3></div>
              <p>第十三輪把 CIZ 生效／公布時間、raw／adjusted 價及退市事件／儲存日期分開；第十四輪再證明 20/20 賬本不足以直接執行，仍須退出會計 12/12。</p>
            </div>
            <div className="test-matrix point-in-time-tests">
              <article className="test-card"><div><span>完整合成賬本</span><b className="positive-number">20/20</b></div><p>永久 ID、成分、價格、分類及 outcome 一致時才放行。</p></article>
              <article className="test-card"><div><span>CSV 被改動</span><b className="negative-number">拒收</b></div><p>SHA-256 或列數與 manifest 不符即停止。</p></article>
              <article className="test-card"><div><span>事後成分</span><b className="negative-number">拒收</b></div><p>公布時間晚於生效日，視為前視數據。</p></article>
              <article className="test-card"><div><span>Ticker 重疊</span><b className="negative-number">拒收</b></div><p>同日代號／交易所指向兩個永久 ID 即停止。</p></article>
              <article className="test-card"><div><span>退出缺回報</span><b className="negative-number">拒收</b></div><p>退市、破產或收購沒有完整經濟代價即停止。</p></article>
              <article className="test-card"><div><span>幽靈價格</span><b className="negative-number">拒收</b></div><p>最後交易日後仍有價格，視為前向填補或 ID 錯配。</p></article>
            </div>
            <div className="data-source-decision">
              <div><span>NEXT VALID ACTION</span><b>只接受數據擁有人合法提供的本地 point-in-time／退市轉換包</b></div>
              <p>數據包須固定覆蓋 2006-08-01–2026-07-31、每日 495–510 隻成分及至少 99.5% 在籍價格／停牌記錄。數據 20/20 後仍要通過第十四輪執行會計 12/12，才可按既有 v1 規則重跑一次；兩者都不自動開 Paper。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_POINT_IN_TIME_READINESS_REPORT.md" target="_blank" rel="noreferrer">第九輪就緒度報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_POINT_IN_TIME_LEDGER_CONTRACT.md" target="_blank" rel="noreferrer">凍結數據合約</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_point_in_time_readiness.json" target="_blank" rel="noreferrer">機器收據</a></div>
            </div>
          </section>

          <section className="section wrap" id="size-momentum-tilt-diagnostic">
            <div className="section-heading">
              <div><span>FIRST-SEEN FULL-POOL VALIDATION · ROUND 8</span><h2>全池動量傾斜：數據 10/10，經濟只過 23/48</h2></div>
              <p>25 cells、1:2:3:4:5 權重、等權／集中度／短窗負控制、QQQ／SPY、10／25／50 bps、30 路 PBO 及 48 道門檻都在首次下載前凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>排名傾斜早期有效；近期仍輸市場、SPY 及 QQQ</h3>
                <p>主要期候選較市場高 {pp(sizeMomentumPrimary.candidate_metrics.cagr - sizeMomentumPrimary.baseline_metrics.market.cagr)}，較全池等權高 {pp(sizeMomentumPrimary.candidate_metrics.cagr - sizeMomentumPrimary.baseline_metrics.all_25_equal.cagr)}；近期只較等權高 {pp(sizeMomentumRecent.candidate_metrics.cagr - sizeMomentumRecent.baseline_metrics.all_25_equal.cagr)}，卻較市場低 {pp(sizeMomentumRecent.candidate_metrics.cagr - sizeMomentumRecent.baseline_metrics.market.cagr)}、較 QQQ 低 {pp(sizeMomentumRecent.candidate_metrics.cagr - sizeMomentumRecent.baseline_metrics.QQQ.cagr)}。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>門檻分解</span><strong>{sizeMomentumTiltResearch.gate_breakdown.data} · {sizeMomentumTiltResearch.gate_breakdown.primary} · {sizeMomentumTiltResearch.gate_breakdown.recent}</strong><p>近期只有四項通過；所有市場、成本、統計及 PBO 門檻均失敗。</p></article>
                <article><span>資金界線</span><strong>首次未見 · US$0</strong><p>French cells 只驗證機制，不是可買證券；不輸出股票名單、不建立 Paper。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>早期：分散傾斜勝市場與等權，仍輸集中組合</h3></div>
              <p>候選固定保留全部 25 cells；Top 2／Top 1 只作集中度 baseline，不可在看到結果後取代候選。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizeMomentumPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>分散與回報取捨：</b><p>線性傾斜只保留 Top 1 CAGR 的 {pct(sizeMomentumPrimary.candidate_metrics.cagr / sizeMomentumPrimary.baseline_metrics.top1.cagr, 1)}，未達 80% 門檻；但最大跌幅亦由 Top 1 的 {pct(sizeMomentumPrimary.baseline_metrics.top1.max_drawdown, 1)} 加深至 {pct(sizeMomentumPrimary.candidate_metrics.max_drawdown, 1)}，沒有換來更佳風險調整回報。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期：只輕微勝等權，市場及 QQQ 機會成本更高</h3></div>
              <p>所有路徑沿用相同凍結規則；QQQ／SPY 只在共同可用的近期產品史比較。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizeMomentumRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>兩段都輸市場：</b><p>2006–2015 較市場 {pp(sizeMomentumRecent.fixed_splits["2006_to_2015"].edge_vs_market)}；2016–2026 更落後 {pp(sizeMomentumRecent.fixed_splits["2016_to_end"].edge_vs_market)}。近期 60 月窗口勝市場只有 {pct(sizeMomentumRecent.rolling_60m_vs_market.cagr_win_fraction, 1)}。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>CONCENTRATION FRONTIER</span><h3>早期集中度有回報，近期則幾乎攤平</h3></div>
              <p>逐級比較等權、線性、平方、Top 2及 Top 1；不只展示候選與最弱 baseline。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>集中度</th><th>主要期 CAGR</th><th>主要期 Sharpe</th><th>主要期最大跌幅</th><th>近期 CAGR</th><th>近期 Sharpe</th><th>近期最大跌幅</th></tr></thead>
                <tbody>{sizeMomentumFrontierRows.map((row) => <tr key={row.label}><th><b>{row.label}</b><span>相同 25 cells 與 10 bps</span></th><td>{pct(row.result.primary.cagr, 2)}</td><td>{multiple(row.result.primary.excess_sharpe)}</td><td>{pct(row.result.primary.max_drawdown, 1)}</td><td>{pct(row.result.recent.cagr, 2)}</td><td>{multiple(row.result.recent.excess_sharpe)}</td><td>{pct(row.result.recent.max_drawdown, 1)}</td></tr>)}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIOR-RANK MONOTONICITY</span><h3>排名訊號仍有殘餘，最高五分位已不再領先</h3></div>
              <p>每個 prior 五分位跨五個 size 等權；主要期單調上升，近期由第三五分位開始轉平。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>Prior 12–2 五分位</th><th>主要期 CAGR</th><th>主要期最大跌幅</th><th>近期 CAGR</th><th>近期最大跌幅</th></tr></thead>
                <tbody>{sizeMomentumTiltResearch.prior_rank_diagnostic.primary.map((row, index) => {
                  const recent = sizeMomentumTiltResearch.prior_rank_diagnostic.recent[index];
                  return <tr key={row.prior_rank}><th><b>Prior {row.prior_rank}</b><span>由輸家至贏家</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{pct(recent.metrics.cagr, 2)}</td><td>{pct(recent.metrics.max_drawdown, 1)}</td></tr>;
                })}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>高換手成本與現代樣本推翻升格</h3></div>
              <p>每月完整重組是保守共同口徑；真實逐股成本未知，所以不能把 10 bps 當保證。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本</span><dl><div><dt>10 bps</dt><dd>{pct(sizeMomentumTiltResearch.frozen_candidate.cost_sensitivity_full_history["10_bps"].cagr, 2)}</dd></div><div><dt>25 bps</dt><dd>{pct(sizeMomentumTiltResearch.frozen_candidate.cost_sensitivity_full_history["25_bps"].cagr, 2)}</dd></div><div><dt>50 bps</dt><dd>{pct(sizeMomentumTiltResearch.frozen_candidate.cost_sensitivity_full_history["50_bps"].cagr, 2)}</dd></div></dl><p>近期 50 bps CAGR 更跌至 {pct(sizeMomentumRecent.candidate_50bps_metrics.cagr, 2)}。</p></article>
              <article><span>近期成本 break-even</span><strong>市場 {sizeMomentumRecent.cost_break_even_vs_baselines.market.one_way_bps.toFixed(2)} · 全池等權 {sizeMomentumRecent.cost_break_even_vs_baselines.all_25_equal.one_way_bps.toFixed(2)} bps</strong><p>對市場已是 0；對等權亦遠低於 50 bps 門檻。</p></article>
              <article><span>近期 60 月勝率</span><strong>市場 {pct(sizeMomentumRecent.rolling_60m_vs_market.cagr_win_fraction, 1)} · 等權 {pct(sizeMomentumRecent.rolling_60m_vs_all_25_equal.cagr_win_fraction, 1)}</strong><p>能穩定勝較弱的等權，不能勝正式市場 baseline。</p></article>
              <article><span>近期主動統計</span><strong>NW t {sizeMomentumRecentMarket.newey_west.t_stat.toFixed(2)}／{sizeMomentumRecentEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／全池等權；PSR {pct(sizeMomentumRecentMarket.active_probabilistic_sharpe.probability, 2)}／{pct(sizeMomentumRecentEqual.active_probabilistic_sharpe.probability, 2)}。</p></article>
              <article><span>DSR 與 PBO</span><strong>DSR {pct(sizeMomentumRecentMarket.active_global_deflated_sharpe.probability, 6)} · PBO {pct(sizeMomentumTiltResearch.pbo.recent.pbo, 1)}</strong><p>6,204 次搜尋校正後接近零；30 路近期 PBO 超過 20% 上限。</p></article>
              <article><span>因子解釋</span><strong>Alpha {pct(sizeMomentumTiltResearch.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(sizeMomentumTiltResearch.factor_regression_full_history.market_beta)}、SMB beta {multiple(sizeMomentumTiltResearch.factor_regression_full_history.smb_beta)}、MOM beta {multiple(sizeMomentumTiltResearch.factor_regression_full_history.mom_beta)}、R² {pct(sizeMomentumTiltResearch.factor_regression_full_history.r_squared, 1)}。</p></article>
            </div>

            <div className="data-source-decision">
              <div><span>DECISION BOUNDARY</span><b>排名機制有殘餘，不等於可交易高回報策略</b></div>
              <p>數據 10/10，但經濟只有 13/38。近二十年落後市場、SPY及 QQQ；50 bps 後轉負；French cells 亦沒有逐股名單、退市／收購、公司行動、流動性及 bid-ask spread。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_size_momentum_tilt_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_12_2.html" target="_blank" rel="noreferrer">官方方法</a></div>
            </div>
          </section>

          <section className="section wrap" id="size-prior-diagnostic">
            <div className="section-heading">
              <div><span>FIRST-SEEN SIZE-CONDITIONED VALIDATION · ROUND 7</span><h2>大型股短窗贏家：數據 10/10，經濟只過 14/44</h2></div>
              <p>唯一候選、25 cells、成本、時期、QQQ／SPY 與同母體基準、17＋17 道門檻及 6,175 次搜尋校正在首次官方下載前已凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>大型股隔離後仍跑輸市場；近期更大幅落後 QQQ</h3>
                <p>主要期候選較市場低 {pp(sizePriorPrimary.candidate_metrics.cagr - sizePriorPrimary.baseline_metrics.market.cagr)}；近期較市場低 {pp(sizePriorRecent.candidate_metrics.cagr - sizePriorRecent.baseline_metrics.market.cagr)}，較 QQQ 低 {pp(sizePriorRecent.candidate_metrics.cagr - sizePriorRecent.baseline_metrics.QQQ.cagr)}。不是由小型股污染就能解釋或救援。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>門檻分解</span><strong>{sizePriorResearch.gate_breakdown.data} · {sizePriorResearch.gate_breakdown.primary} · {sizePriorResearch.gate_breakdown.recent}</strong><p>主要期只過 PBO；近期只過全池等權、Big Lo 及最大跌幅限制。</p></article>
                <article><span>證據與資金界線</span><strong>首次未見 · US$0</strong><p>數據合約有效，但 French cells 不是證券；Paper、選股名單及實金均維持關閉。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>長歷史：短窗贏家落後所有主要回報基準</h3></div>
              <p>所有每月重組路徑以相同 10 bps 單邊成本處理；French 市場只扣首次買入成本。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizePriorPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>兩半一致失敗：</b><p>1963–1984 較市場低 {pp(sizePriorPrimary.fixed_splits["1963_to_1984"].edge_vs_market)}，1985–2005 低 {pp(sizePriorPrimary.fixed_splits["1985_to_2005"].edge_vs_market)}；60 月窗勝市場只有 {pct(sizePriorPrimary.rolling_60m_vs_market.cagr_win_fraction, 1)}。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期：只勝弱基準，QQQ 明顯較好</h3></div>
              <p>QQQ／SPY 使用既有經調整產品價格快照，只作 2006 後機會成本；沒有用現時成份股回推歷史。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{sizePriorRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>Regime 不穩定：</b><p>2006–2015 候選只得 {pct(sizePriorRecent.fixed_splits["2006_to_2015"].candidate_cagr, 2)}，較市場低 {pp(sizePriorRecent.fixed_splits["2006_to_2015"].edge_vs_market)}；2016 後才較市場高 {pp(sizePriorRecent.fixed_splits["2016_to_end"].edge_vs_market)}。後段反彈不能覆蓋固定前段。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>SIZE × DIRECTION</span><h3>早期五個 size 全部是反轉；近期才轉為部分延續</h3></div>
              <p>Hi−Lo 為同一 size 贏家 CAGR 減輸家 CAGR。這是機制拆解，不是事後改買最好的 size。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>Size 五分位</th><th>1963–2005 Hi−Lo</th><th>2006–2026 Hi−Lo</th><th>近期 Hi CAGR</th><th>近期 Hi 最大跌幅</th></tr></thead>
                <tbody>{sizePriorResearch.size_direction_diagnostic.recent.map((row, index) => (
                  <tr key={row.size_quintile}><th><b>Size {row.size_quintile}</b><span>{row.size_quintile === 5 ? "大型股" : "由小至大"}</span></th><td>{pp(sizePriorResearch.size_direction_diagnostic.primary[index].high_minus_low_cagr)}</td><td>{pp(row.high_minus_low_cagr)}</td><td>{pct(row.high_prior_cagr, 2)}</td><td>{pct(row.high_prior_max_drawdown, 1)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本容忍度不足，統計沒有確認</h3></div>
              <p>Newey–West 固定月度 lag 3；PSR／DSR 以每年 12 期計算；PBO family 包括全部 25 cells 及事前大型股傾斜。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本</span><dl><div><dt>10 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["10_bps"].cagr, 2)}</dd></div><div><dt>25 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["25_bps"].cagr, 2)}</dd></div><div><dt>50 bps</dt><dd>{pct(sizePriorResearch.frozen_candidate.cost_sensitivity_full_history["50_bps"].cagr, 2)}</dd></div></dl><p>年換手約 {multiple(sizePriorResearch.frozen_candidate.full_history_metrics_10bps.annual_turnover)}x；完整換倉成本是重要反證。</p></article>
              <article><span>近期成本 break-even</span><strong>市場 {sizePriorRecent.cost_break_even_vs_baselines.market.one_way_bps.toFixed(2)} · 大型股等權 {sizePriorRecent.cost_break_even_vs_baselines.big_row_equal.one_way_bps.toFixed(2)} bps</strong><p>凍結門檻為 50 bps；兩者都遠低於要求。</p></article>
              <article><span>近期 60 月勝率</span><strong>市場 {pct(sizePriorRecent.rolling_60m_vs_market.cagr_win_fraction, 1)} · 大型股等權 {pct(sizePriorRecent.rolling_60m_vs_big_row_equal.cagr_win_fraction, 1)}</strong><p>相對市場中位 CAGR 差 {pp(sizePriorRecent.rolling_60m_vs_market.median_cagr_difference)}。</p></article>
              <article><span>近期主動統計</span><strong>NW t {sizePriorRecentMarket.newey_west.t_stat.toFixed(2)}／{sizePriorRecentBigEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／大型股等權；PSR {pct(sizePriorRecentMarket.active_probabilistic_sharpe.probability, 2)}／{pct(sizePriorRecentBigEqual.active_probabilistic_sharpe.probability, 2)}。</p></article>
              <article><span>DSR 與 PBO</span><strong>DSR {pct(sizePriorRecentMarket.active_global_deflated_sharpe.probability, 4)} · PBO {pct(sizePriorResearch.pbo.recent.pbo, 1)}</strong><p>6,175 次搜尋校正後不足；近期 PBO 高於 20% 上限。</p></article>
              <article><span>五因子解釋</span><strong>Alpha {pct(sizePriorResearch.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(sizePriorResearch.factor_regression_full_history.market_beta)}、ST_Rev beta {multiple(sizePriorResearch.factor_regression_full_history.short_term_reversal_beta)}、R² {pct(sizePriorResearch.factor_regression_full_history.r_squared, 1)}。</p></article>
            </div>

            <div className="data-source-decision">
              <div><span>DECISION BOUNDARY</span><b>首次數據 10/10，但經濟只有 14/44</b></div>
              <p>這輪比現時成份股倒推更可靠，仍只到機制層；近期 50 bps 後 CAGR 為 {pct(sizePriorRecent.candidate_50bps_metrics.cagr, 2)}。沒有逐股 point-in-time 成分、退市／收購回報、公司行動、流動性及精確成交成本，所以不建立短線 Paper，不輸出股票名單。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_size_prior_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_25_port_form_sz_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div>
            </div>
          </section>

          <section className="section wrap" id="prior-return-contract">
            <div className="section-heading">
              <div><span>LATEST DATA-CONTRACT ATTEMPT · ROUND 6</span><h2>美股一個月贏家延續測試：6/8，計算前停止</h2></div>
              <p>主要候選、成本、短期反轉／同池等權／12–2 動量／市場 baseline，以及 38 道學術門檻已在五個新 ZIP 首次下載前凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>數據契約判斷</span>
                <h3>原檔標題不符凍結映射，沒有計算任何回報</h3>
                <p>short-term 原檔寫成 <code>{priorReturnContract.observed_monthly_markers.short_term_prior_1_0[0]}</code>；long-term 原檔則是 <code>{priorReturnContract.observed_monthly_markers.long_term_prior_12_2[0]}</code>。兩者都不等於事前固定的 <code>{priorReturnContract.expected_value_weighted_monthly_marker}</code>，所以沒有用寬鬆 parser 跨過。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>完整性檢查</span><strong>{priorReturnContract.passed_check_count}/{priorReturnContract.required_check_count}</strong><p>五個 SHA-256、CSV member、equal-weighted 表及因素 header 通過；兩個 value-weighted 表段標記失敗。</p></article>
                <article><span>策略與資金狀態</span><strong>未計算 · US$0</strong><p>沒有 CAGR、Sharpe、PBO、選股名單、Paper 或實金落盤；亦不重下載同一發布版。</p></article>
              </div>
            </div>
            <div className="comparison-caveat"><b>這不是策略負結果：</b><p>它只證明下載前映射與官方 CSV schema 不相容，不能據此說美股短窗動量有效或無效。修改 marker 後重用同一批已見原檔，也不能再聲稱獨立 first-seen 經濟驗證。</p></div>
            <div className="protocol-link"><span>第六輪凍結與失敗證據</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_PROTOCOL.md" target="_blank" rel="noreferrer">事前協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_DATA_FAILURE.md" target="_blank" rel="noreferrer">完整失敗紀錄</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_prior_return_data_receipt.json" target="_blank" rel="noreferrer">機器收據</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_port_form_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div></div>
          </section>

          <section className="section wrap" id="prior-return-diagnostic">
            <div className="section-heading">
              <div><span>SCHEMA-INFORMED ENGINEERING DIAGNOSTIC · ROUND 6B</span><h2>短窗贏家策略：工程 8/8，經濟只過 11/38</h2></div>
              <p>只使用原五份 SHA-256 快照；兩個精確 marker 的 repair 協議在任何策略數字前提交。經濟候選、四個 baseline、成本、時期及 6,150 次搜尋校正全部不變。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>短窗贏家延續被市場、同池基準與長窗動量擊敗</h3>
                <p>主要期只過 {priorRepairPrimary.passed_gate_count}/15，近期只過 {priorRepairRecent.passed_gate_count}/15。近期候選雖較短窗輸家高 {pp(priorRepairRecent.candidate_metrics.cagr - priorRepairRecent.baseline_metrics.lo_prior_1_0.cagr)}，仍較市場低 {pp(priorRepairRecent.candidate_metrics.cagr - priorRepairRecent.baseline_metrics.market.cagr)}，最大跌幅達 {pct(priorRepairRecent.candidate_metrics.max_drawdown, 1)}。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>門檻分解</span><strong>{priorReturnRepair.gate_breakdown.data} · {priorReturnRepair.gate_breakdown.primary} · {priorReturnRepair.gate_breakdown.recent}</strong><p>數據工程全過；主要期只過 PBO，近期只過短窗輸家及最大跌幅兩項。</p></article>
                <article><span>證據與資金界線</span><strong>非獨立 · US$0</strong><p>原 6/8 收據不被覆蓋；`independent_first_seen_evidence=false`，Paper 及實金均維持關閉。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>早期完整期：零成本也未能追上四個基準</h3></div>
              <p>所有需每月輪替的投資組合使用相同 10 bps 單邊成本；每月假設完整沽出及買入。這是保守共同口徑，不是假裝知道逐股真實換手。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>兩半都失敗：</b><p>1963–1984 候選 CAGR {pct(priorRepairPrimary.fixed_splits["1963_to_1984"].candidate_cagr, 2)}，較市場低 {pp(priorRepairPrimary.fixed_splits["1963_to_1984"].edge_vs_market)}；1985–2005 候選 CAGR {pct(priorRepairPrimary.fixed_splits["1985_to_2005"].candidate_cagr, 2)}，較市場低 {pp(priorRepairPrimary.fixed_splits["1985_to_2005"].edge_vs_market)}。候選在零交易成本下仍落後全部四個基準。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期改善，但市場及 12–2 贏家仍更好</h3></div>
              <p>不能只展示 2016 後反彈；2006–2015 與 2016–2026 兩段固定結果同時列出。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>分段不穩定：</b><p>2006–2015 候選 CAGR {pct(priorRepairRecent.fixed_splits["2006_to_2015"].candidate_cagr, 2)}，較市場低 {pp(priorRepairRecent.fixed_splits["2006_to_2015"].edge_vs_market)}；2016–2026 才較市場高 {pp(priorRepairRecent.fixed_splits["2016_to_end"].edge_vs_market)}。後段成功不能抵銷固定前段失敗。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本容忍度很低，統計沒有確認</h3></div>
              <p>Newey–West 使用月度回報、固定三個月 lag；Sharpe／PSR／DSR 按每年 12 期，DSR 保留全專案 6,150 次搜尋懲罰。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本</span><dl><div><dt>10 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["10_bps"].cagr, 2)} CAGR</dd></div><div><dt>25 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["25_bps"].cagr, 2)} CAGR</dd></div><div><dt>50 bps</dt><dd>{pct(priorRepairCandidate.cost_sensitivity_full_history["50_bps"].cagr, 2)} CAGR</dd></div></dl><p>假設年換手 {multiple(priorRepairCandidate.full_history_metrics_10bps.annual_turnover)}x；50 bps 後 US$1,000 只餘 {money(priorRepairCandidate.cost_sensitivity_full_history["50_bps"].hypothetical_1000_usd_end)}。</p></article>
              <article><span>近期成本 break-even</span><strong>市場 {priorRepairRecent.cost_break_even_vs_baselines.market.one_way_bps.toFixed(2)} · 12–2 贏家 {priorRepairRecent.cost_break_even_vs_baselines.long_momentum_hi_12_2.one_way_bps.toFixed(2)} bps</strong><p>這是每月單邊上限；凍結主測 10 bps 已超出兩者。對十分位等權及短窗輸家則為 {priorRepairRecent.cost_break_even_vs_baselines.decile_equal.one_way_bps.toFixed(2)}／{priorRepairRecent.cost_break_even_vs_baselines.lo_prior_1_0.one_way_bps.toFixed(2)} bps。</p></article>
              <article><span>60 月滾動勝率</span><strong>市場 {pct(priorRepairRecent.rolling_60m_vs_market.cagr_win_fraction, 1)} · 等權 {pct(priorRepairRecent.rolling_60m_vs_decile_equal.cagr_win_fraction, 1)}</strong><p>合格線是 60%；中位 CAGR 差分別為 {pp(priorRepairRecent.rolling_60m_vs_market.median_cagr_difference)}／{pp(priorRepairRecent.rolling_60m_vs_decile_equal.median_cagr_difference)}。</p></article>
              <article><span>近期主動統計</span><strong>NW t {priorRepairRecentMarket.newey_west.t_stat.toFixed(2)}／{priorRepairRecentEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／十分位等權；PSR {pct(priorRepairRecentMarket.active_probabilistic_sharpe.probability, 2)}／{pct(priorRepairRecentEqual.active_probabilistic_sharpe.probability, 2)}，均未達 95%。</p></article>
              <article><span>DSR 與 PBO</span><strong>DSR {pct(priorRepairRecentMarket.active_global_deflated_sharpe.probability, 3)} · PBO {pct(priorReturnRepair.pbo.recent.pbo, 1)}</strong><p>6,150 次搜尋校正後幾乎沒有證據；六路近期 PBO 高於 20% 上限。</p></article>
              <article><span>五因子解釋</span><strong>Alpha {pct(priorReturnRepair.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(priorReturnRepair.factor_regression_full_history.market_beta)}、ST_Rev beta {multiple(priorReturnRepair.factor_regression_full_history.short_term_reversal_beta)}、R² {pct(priorReturnRepair.factor_regression_full_history.r_squared, 1)}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PREDECLARED SENSITIVITY SET</span><h3>六條路徑全部保留，不事後換冠軍</h3></div>
              <p>線性傾斜是事後看到的六路最高值，仍低於全歷史市場；它只能作敏感度，不能取代唯一主要候選。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>事前路徑</th><th>全歷史年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>US$1,000 期末值</th></tr></thead>
                <tbody>{priorRepairSensitivityRows.map((row, index) => (
                  <tr key={row.label} className={index === 0 ? "featured-row" : undefined}><th><b>{row.label}</b><span>{index === 0 ? "唯一主要候選" : "敏感度／PBO 路徑"}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{money(row.metrics.hypothetical_1000_usd_end)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS TESTS</span><h3>2020 勝出，不能掩蓋五段較差尾部表現</h3></div>
              <p>固定危機期全部展示；個別上升段不會取代完整期、成本、統計與最大跌幅門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>壓力期</th><th>候選回報</th><th>市場回報</th><th>十分位等權</th><th>12–2 贏家</th><th>候選最大跌幅</th></tr></thead>
                <tbody>{priorRepairStressRows.map((row) => <tr key={row.label}><th><b>{row.label}</b><span>固定壓力窗口</span></th><td>{pct(row.result.candidate.return, 1)}</td><td>{pct(row.result.market.return, 1)}</td><td>{pct(row.result.decile_equal.return, 1)}</td><td>{pct(row.result.long_momentum_hi_12_2.return, 1)}</td><td>{pct(row.result.candidate.max_drawdown, 1)}</td></tr>)}</tbody>
              </table>
            </div>

            <div className="data-source-decision">
              <div><span>DECISION BOUNDARY</span><b>原 6/8 失敗與本次 11/38 工程診斷同時保留</b></div>
              <p>本次只證明精確 parser 可重現同一已見 schema 快照的負經濟結果。沒有逐股 point-in-time 成分、退市／收購回報、公司行動、精確換手及已授權供應商，所以不能產生股票名單、Paper 或落盤指令。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_PROTOCOL.md" target="_blank" rel="noreferrer">repair 協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_MAPPING.md" target="_blank" rel="noreferrer">精確映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_prior_return_schema_repair_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_10_port_form_pr_1_0.html" target="_blank" rel="noreferrer">官方方法</a></div>
            </div>
          </section>

          <section className="section wrap" id="aggressive-evidence">
            <div className="section-heading">
              <div><span>PREVIOUS FIRST-SEEN EXTERNAL VALIDATION</span><h2>French 30 行業逾 63 年驗證：早期有效，近期不足</h2></div>
              <p>原始共同期 1926–2026；正式候選從 {shortDate(frenchPrimary.start)} 起計。規則、數據映射、成本及 33 道門檻在首次下載 30 行業 ZIP 前已凍結。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>最新研究判斷</span>
                <h3>有歷史行業動量，不等於近期可穩健賺取超額</h3>
                <p>主要外部期較市場高 {pp(frenchPrimary.candidate_metrics.cagr - frenchPrimary.baseline_metrics.market.cagr)}，20 日事件亦 5/5；但近期只高 {pp(frenchRecent.candidate_metrics.cagr - frenchRecent.baseline_metrics.market.cagr)}，2006–2015 更落後市場，近期主動 NW t 只有 {frenchRecentMarket.newey_west.t_stat.toFixed(2)}。因此整體判定失敗。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>數據與凍結順序</span><strong>{frenchResearch.gate_breakdown.data}</strong><p>官方 ZIP、雜湊、30 欄、缺值及訊號 t／回報 t+1 全部通過。</p></article>
                <article><span>雙時期硬門檻</span><strong>{frenchResearch.gate_breakdown.primary} · {frenchResearch.gate_breakdown.recent}</strong><p>近期只過最大跌幅及對行業等權的五年滾動一致性。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRIMARY EXTERNAL PERIOD · 1963–2005</span><h3>完整早期樣本：候選勝出，但仍未過全部門檻</h3></div>
              <p>同一官方快照、同一日期、10 bps 單邊成本；Sharpe 全部以每日回報減 RF 計算。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>{frenchPrimaryRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{multiple(row.metrics.annual_turnover)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>US$1,000 歷史尺度：</b><p>1963 年投入候選的理論期末值為 {money(frenchPrimary.candidate_metrics.hypothetical_1000_usd_end)}，市場為 {money(frenchPrimary.baseline_metrics.market.hypothetical_1000_usd_end)}。這是 42 年名義複利、未計通脹與稅項；不能當成未來金額預測。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>RECENT CONFIRMATION · 2006–2026</span><h3>近期樣本：回報略高，證據強度大幅下降</h3></div>
              <p>不能用 1963–2005 的漂亮結果掩蓋近期失敗；近期獨立再用同一 13 道門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>{frenchRecentRows.map((row) => (
                  <tr key={row.label} className={row.featured ? "featured-row" : undefined}>
                    <th><b>{row.label}</b><span>{row.detail}</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.excess_sharpe)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.calmar)}</td><td>{multiple(row.metrics.annual_turnover)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>US$1,000 歷史尺度：</b><p>2006 年起候選的理論期末值為 {money(frenchRecent.candidate_metrics.hypothetical_1000_usd_end)}，市場為 {money(frenchRecent.baseline_metrics.market.hypothetical_1000_usd_end)}；候選最大跌幅 {pct(frenchRecent.candidate_metrics.max_drawdown, 1)}，並非低風險捷徑。</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; STATISTICS</span><h3>成本、分段、PBO 與因子解釋</h3></div>
              <p>Top-3 是唯一候選；Top-2／5 只作敏感度及 CSCV PBO，不因 Top-2 全期回報較高便換冠軍。</p>
            </div>
            <div className="short-evidence-grid">
              <article><span>全歷史成本敏感度</span><dl>{frenchCostRows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{pct(row.metrics.cagr, 2)} CAGR</dd></div>)}</dl><p>每年雙邊換手約 {multiple(frenchCandidate.full_history_metrics.annual_turnover)}x；50 bps 把全期 CAGR 壓至 {pct(frenchCandidate.cost_sensitivity_full_history["50_bps"].cagr, 2)}。</p></article>
              <article><span>固定近期分段</span><strong>{pp(frenchRecent.fixed_splits["2006_to_2015"].edge_vs_market)}／{pp(frenchRecent.fixed_splits["2016_to_end"].edge_vs_market)}</strong><p>2006–2015／2016–2026 對市場；第一段落後，不能用第二段反彈掩蓋。</p></article>
              <article><span>五年滾動勝率</span><strong>市場 {pct(frenchRecent.rolling_five_year_vs_market.cagr_win_fraction, 1)} · 等權 {pct(frenchRecent.rolling_five_year_vs_industry_monthly_equal.cagr_win_fraction, 1)}</strong><p>近期 185 個窗口；對市場未達 60%，最差落後 {pp(frenchRecent.rolling_five_year_vs_market.worst_cagr_difference)}。</p></article>
              <article><span>主動統計</span><strong>早期 t {frenchPrimaryMarket.newey_west.t_stat.toFixed(2)}／{frenchPrimaryEqual.newey_west.t_stat.toFixed(2)}</strong><p>對市場／行業等權；近期跌至 {frenchRecentMarket.newey_west.t_stat.toFixed(2)}／{frenchRecentEqual.newey_west.t_stat.toFixed(2)}。近期對市場 DSR 只有 {pct(frenchRecentMarket.active_global_deflated_sharpe.probability, 2)}。</p></article>
              <article><span>CSCV 過度配適</span><strong>{pct(frenchResearch.pbo.primary.pbo, 1)}／{pct(frenchResearch.pbo.recent.pbo, 1)}</strong><p>主要／近期 PBO，遠高於 20% 上限；Top-2、3、5 的相對排序不穩定。</p></article>
              <article><span>四因子解釋</span><strong>Alpha {pct(frenchResearch.factor_regression_full_history.annualized_alpha, 2)}</strong><p>市場 beta {multiple(frenchResearch.factor_regression_full_history.market_beta)}、Mom beta {multiple(frenchResearch.factor_regression_full_history.mom_beta)}、R² {pct(frenchResearch.factor_regression_full_history.r_squared, 1)}；全歷史 alpha 為負。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED 20-DAY SIGNAL</span><h3>早期 5/5，近期只 3/5</h3></div>
              <p>每週以同一 6–1 排名選 Top-3，下一交易日開始持有 20 日，每個事件扣來回 20 bps；重疊事件用 NW lag 4 及固定區塊重抽樣。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table signal-diagnostic-table">
                <thead><tr><th>時期</th><th>事件</th><th>Top-3 平均淨回報</th><th>30 行業等權</th><th>配對差</th><th>勝出率</th><th>NW t</th><th>Bootstrap 95% 區間</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>1963–2005</b><span>主要外部期 · 5/5</span></th><td>{frenchPrimaryEvent.events}</td><td>{pct(frenchPrimaryEvent.selected_mean_return, 2)}</td><td>{pct(frenchPrimaryEvent.industry_equal_mean_return, 2)}</td><td>{pp(frenchPrimaryEvent.mean_difference_vs_industry_equal)}</td><td>{pct(frenchPrimaryEvent.paired_win_fraction, 1)}</td><td>{frenchPrimaryEvent.newey_west.t_stat.toFixed(2)}</td><td>{pp(frenchPrimaryEvent.moving_block_bootstrap.low)} 至 {pp(frenchPrimaryEvent.moving_block_bootstrap.high)}</td></tr>
                  <tr><th><b>2006–2026</b><span>近期確認期 · 3/5</span></th><td>{frenchRecentEvent.events}</td><td>{pct(frenchRecentEvent.selected_mean_return, 2)}</td><td>{pct(frenchRecentEvent.industry_equal_mean_return, 2)}</td><td>{pp(frenchRecentEvent.mean_difference_vs_industry_equal)}</td><td>{pct(frenchRecentEvent.paired_win_fraction, 1)}</td><td>{frenchRecentEvent.newey_west.t_stat.toFixed(2)}</td><td>{pp(frenchRecentEvent.moving_block_bootstrap.low)} 至 {pp(frenchRecentEvent.moving_block_bootstrap.high)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS TESTS</span><h3>六段壓力期：上行較高，尾部風險仍大</h3></div>
              <p>危機表只描述固定規則的實際歷史表現，不用個別危機勝出代替全套門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>壓力期</th><th>候選回報</th><th>市場回報</th><th>行業等權回報</th><th>候選最大跌幅</th><th>候選最差單日</th></tr></thead>
                <tbody>{frenchStressRows.map((row) => <tr key={row.label}><th><b>{row.label}</b><span>固定歷史窗口</span></th><td>{pct(row.result.candidate.return, 1)}</td><td>{pct(row.result.market.return, 1)}</td><td>{pct(row.result.industry_monthly_equal.return, 1)}</td><td>{pct(row.result.candidate.max_drawdown, 1)}</td><td>{pct(row.result.candidate.worst_day, 1)}</td></tr>)}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>最新決策：</b><p>保留早期正面與近期負面證據，不改 6–1、Top-3、20 日、成本或起訖日救援。French 組合不是可買賣產品，短線 Paper 仍等候合格逐股 point-in-time 成分與退市回報；實金及 Paper 動作均為 US$0。</p></div>
            <div className="protocol-link"><span>最新研究協議、數據映射與失敗證據</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_MOMENTUM_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_30_industry_validation.json" target="_blank" rel="noreferrer">完整 JSON</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_INDUSTRY_DATA_FAILURE.md" target="_blank" rel="noreferrer">49 行業數據失敗</a></div></div>
          </section>

          <section className="section wrap" id="aggressive-sandbox">
            <div className="section-heading">
              <div><span>PRIOR STOCK SANDBOX</span><h2>較早大型股沙盒：表面跑贏也未證明輪選</h2></div>
              <p>{shortResearch.period.start} 至 {shortResearch.period.end}；月末訊號、下一開市執行、主要單邊成本 10 bps。</p>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict">
                <span>目前研究判斷</span>
                <h3>較 QQQ 高 {pp(shortComparison.cagr_difference)}，但較同股池漂移低 {pp(shortCandidate.metrics.cagr - shortBaselines.current_cohort_start_equal_then_drift.cagr)}</h3>
                <p>候選只比「現時完整股池每月等權」高 {pp(shortCandidate.metrics.cagr - shortBaselines.current_cohort_monthly_equal_weight.cagr)}，卻輸給起點等權後不再選股。這表示漂亮回報很可能主要來自今日仍然成功的公司，而非輪選規則。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>候選最大跌幅</span><strong>{pct(shortCandidate.metrics.max_drawdown, 1)}</strong><p>新冠急跌段達 {pct(shortResearch.stress_periods.covid_crash.results.frozen_candidate.return, 1)}，比 QQQ 的 {pct(shortResearch.stress_periods.covid_crash.results.QQQ.return, 1)} 更差。</p></article>
                <article><span>數據／經濟門檻</span><strong>{shortDataPassed}/7 · {shortEconomicPassed}/13</strong><p>逐期成分、退市回報、歷史行業及公司行動賬本仍未完成。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>HARD BASELINES</span><h3>候選、QQQ、SPY 與同股池控制</h3></div>
              <p>同一凍結快照、同一起訖日及相同 10 bps 口徑；同股池兩列亦有偏差，但能檢查輪選是否勝過更簡單做法。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>策略／baseline</th><th>年率化回報</th><th>Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Calmar</th><th>每年換手</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>綜合動量輪選沙盒</b><span>現時 2026 股池倒推 · 不可投資</span></th><td>{pct(shortCandidate.metrics.cagr, 2)}</td><td>{multiple(shortCandidate.metrics.sharpe)}</td><td>{pct(shortCandidate.metrics.volatility, 1)}</td><td>{pct(shortCandidate.metrics.max_drawdown, 1)}</td><td>{multiple(shortCandidate.metrics.calmar)}</td><td>{multiple(shortCandidate.metrics.turnover)}x</td></tr>
                  <tr><th><b>QQQ 買入持有</b><span>正式高回報機會成本</span></th><td>{pct(shortBaselines.QQQ.cagr, 2)}</td><td>{multiple(shortBaselines.QQQ.sharpe)}</td><td>{pct(shortBaselines.QQQ.volatility, 1)}</td><td>{pct(shortBaselines.QQQ.max_drawdown, 1)}</td><td>{multiple(shortBaselines.QQQ.calmar)}</td><td>{multiple(shortBaselines.QQQ.turnover)}x</td></tr>
                  <tr><th><b>SPY 買入持有</b><span>廣泛大型股市場</span></th><td>{pct(shortBaselines.SPY.cagr, 2)}</td><td>{multiple(shortBaselines.SPY.sharpe)}</td><td>{pct(shortBaselines.SPY.volatility, 1)}</td><td>{pct(shortBaselines.SPY.max_drawdown, 1)}</td><td>{multiple(shortBaselines.SPY.calmar)}</td><td>{multiple(shortBaselines.SPY.turnover)}x</td></tr>
                  <tr><th><b>現時完整股池等權</b><span>每月重新平衡 · 有偏差</span></th><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.cagr, 2)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.sharpe)}</td><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.volatility, 1)}</td><td>{pct(shortBaselines.current_cohort_monthly_equal_weight.max_drawdown, 1)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.calmar)}</td><td>{multiple(shortBaselines.current_cohort_monthly_equal_weight.turnover)}x</td></tr>
                  <tr><th><b>現時完整股池漂移</b><span>起點等權後不再選股 · 有偏差</span></th><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.cagr, 2)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.sharpe)}</td><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.volatility, 1)}</td><td>{pct(shortBaselines.current_cohort_start_equal_then_drift.max_drawdown, 1)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.calmar)}</td><td>{multiple(shortBaselines.current_cohort_start_equal_then_drift.turnover)}x</td></tr>
                </tbody>
              </table>
            </div>
            <div className="comparison-caveat">
              <b>為何 21.52% 仍不開 Paper：</b>
              <p>現時名單不知道 2006 年當時可買什麼，也漏掉退市、被收購及失敗公司；同股池漂移更達 {pct(shortBaselines.current_cohort_start_equal_then_drift.cagr, 2)}。這個沙盒只說明假說值得以合格數據重測，不代表可賺取相同回報。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, WINDOWS &amp; CRISES</span><h3>高成本、固定分段與壓力期</h3></div>
              <p>成本沒有立即消滅表面回報，但危機及統計檢驗顯示風險遠未解決。</p>
            </div>
            <div className="short-evidence-grid">
              <article>
                <span>成本敏感度</span>
                <dl>{shortCostRows.map((row) => <div key={row.label}><dt>{row.label}</dt><dd>{pct(row.metrics.cagr, 2)} CAGR</dd></div>)}</dl>
                <p>50 bps 後仍較 QQQ 高 {pp(shortCandidate.cost_sensitivity["50_bps"].cagr - shortBaselines.QQQ.cagr)}，但數據偏差沒有因成本測試而消失。</p>
              </article>
              <article>
                <span>固定十年分段</span>
                <strong>{pp(shortResearch.fixed_halves_vs_qqq.first.cagr_difference)}／{pp(shortResearch.fixed_halves_vs_qqq.second.cagr_difference)}</strong>
                <p>前十年／後十年對 QQQ；滾動三年 {pct(shortResearch.rolling_three_year_vs_qqq.cagr_win_fraction, 1)} 勝出，最差仍落後 {pp(shortResearch.rolling_three_year_vs_qqq.worst_cagr_difference)}。</p>
              </article>
              <article>
                <span>統計與搜尋校正</span>
                <strong>t {shortComparison.active_newey_west.t_stat.toFixed(2)} · DSR {pct(shortComparison.active_global_deflated_sharpe.probability, 1)}</strong>
                <p>未校正 PSR {pct(shortComparison.active_probabilistic_sharpe.probability, 1)}，但 {shortResearch.global_search_trials.toLocaleString("zh-HK")} 次搜尋後失效；四版本 PBO {pct(shortResearch.pbo_across_four_current_cohort_variants.pbo, 1)}。</p>
              </article>
              <article>
                <span>三段壓力期</span>
                <strong>{pct(shortResearch.stress_periods.global_financial_crisis.results.frozen_candidate.return, 1)} · {pct(shortResearch.stress_periods.covid_crash.results.frozen_candidate.return, 1)} · {pct(shortResearch.stress_periods.rate_hike_2022.results.frozen_candidate.return, 1)}</strong>
                <p>金融海嘯／新冠急跌／2022。2022 防守較佳，不能掩蓋新冠段比 QQQ 多跌逾 11 個百分點。</p>
              </article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>TAIWAN-TO-U.S. ABLATION</span><h3>台股短窗規則直譯：三版均未勝 QQQ</h3></div>
              <p>只逐層測 20 日動量、60 日趨勢、SPY 環境與相關性濾網；不搬用台股槓桿、止蝕、止賺或 headline 回報。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table">
                <thead><tr><th>直譯版本</th><th>年率化回報</th><th>Sharpe</th><th>最大跌幅</th><th>每年換手</th><th>對 QQQ</th></tr></thead>
                <tbody>{shortTranslationRows.map((row) => (
                  <tr key={row.key}><th><b>{row.label}</b><span>每週 Top-7 · 現時股池沙盒</span></th><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.metrics.sharpe)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.metrics.turnover)}x</td><td className="negative-number">{pp(row.metrics.cagr - shortBaselines.QQQ.cagr)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="subsection-heading stock-heading">
              <div><span>SIGNAL-LAYER DIAGNOSTIC</span><h3>拆走止賺止蝕後，20 日排序有正差</h3></div>
              <p>協議在首次計算前提交；每週訊號於下一開市進場，固定持有，所有事件組合扣來回 20 bps。這只回答訊號層問題，不是可落盤策略。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table short-result-table signal-diagnostic-table">
                <thead><tr><th>固定持有期</th><th>事件</th><th>Top-7 平均淨回報</th><th>合資格池等權</th><th>配對差</th><th>NW t</th><th>Bootstrap 95% 區間</th></tr></thead>
                <tbody>{shortSignalRows.map((row) => {
                  const comparison = row.result.comparisons.eligible_equal;
                  const bootstrapRange = row.result.moving_block_bootstrap_mean_difference_vs_eligible_equal;
                  return (
                    <tr key={row.label} className={row.result.holding_sessions === 20 ? "featured-row" : undefined}>
                      <th><b>{row.label}</b><span>每週 Top-7 · 固定離場</span></th>
                      <td>{row.result.events}</td>
                      <td>{pct(row.result.net_return_summary.top7_mean, 2)}</td>
                      <td>{pct(row.result.net_return_summary.eligible_equal_mean, 2)}</td>
                      <td>{pp(comparison.mean_difference)}</td>
                      <td>{comparison.newey_west.t_stat.toFixed(2)}</td>
                      <td>{pp(bootstrapRange.low)} 至 {pp(bootstrapRange.high)}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
            <div className="signal-diagnostic-verdict">
              <div><span>20 日主要診斷</span><strong>{shortSignal.passed_primary_gate_count}/{shortSignal.required_primary_gate_count} 表面通過</strong></div>
              <p>Top-7 每個 20 日事件平均較當日合資格池高 {pp(shortSignalPrimary.comparisons.eligible_equal.mean_difference)}，NW t {shortSignalPrimary.comparisons.eligible_equal.newey_west.t_stat.toFixed(2)}，配對勝率 {pct(shortSignalPrimary.comparisons.eligible_equal.win_fraction, 1)}；前後十年平均差為 {pp(shortSignalPrimary.fixed_halves_vs_eligible_equal.first.mean_difference)}／{pp(shortSignalPrimary.fixed_halves_vs_eligible_equal.second.mean_difference)}。但樣本仍用今日成功公司倒推，不能據此買入或開 Paper。</p>
            </div>
            <div className="reference-projects">
              <a href="https://github.com/appr1ciat1/tst_wocker" target="_blank" rel="noreferrer"><b>tst_wocker</b><span>橫斷面動量／市場環境</span></a>
              <a href="https://github.com/appr1ciat1/tw-block-warrant" target="_blank" rel="noreferrer"><b>tw-block-warrant</b><span>研究與每日訊號分層</span></a>
              <a href="https://github.com/appr1ciat1/tst_wocker_filter_lab" target="_blank" rel="noreferrer"><b>filter_lab</b><span>凍結快照／負結果／池 baseline</span></a>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>INDIVIDUAL STOCK RISK DIAGNOSTICS</span><h3>12 隻現時大型股的完整 20 年比較</h3></div>
              <p>這是倖存者偏差診斷，只量化個股上行及崩跌範圍；這些公司不能反推成 2006 年選股名單。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table stock-table">
                <thead><tr><th>個股</th><th>行業</th><th>年率化回報</th><th>超額 Sharpe</th><th>波幅</th><th>最大跌幅</th><th>Beta</th><th>長線策略五年窗勝率</th></tr></thead>
                <tbody>{stockComparisons.map((row) => (
                  <tr key={row.symbol}><th><b>{row.symbol}</b><span>{row.name}</span></th><td>{sectorLabels[row.sector] ?? row.sector}</td><td>{pct(row.metrics.cagr, 2)}</td><td>{multiple(row.excess_sharpe_vs_shy)}</td><td>{pct(row.metrics.volatility, 1)}</td><td>{pct(row.metrics.max_drawdown, 1)}</td><td>{multiple(row.beta_to_spy)}</td><td>{pct(row.candidate_rolling_five_year_win_fraction, 1)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="comparison-caveat"><b>不能直接照表買入：</b><p>NVDA 年率化回報達 {pct(nvdaDiagnostic.metrics.cagr, 1)}，但最大跌幅亦達 {pct(nvdaDiagnostic.metrics.max_drawdown, 1)}；AMD 更曾達 {pct(amdDiagnostic.metrics.max_drawdown, 1)}。今日仍在大型股名單本身已包含未來資訊。</p></div>
          </section>

          <section className="section aggressive-method" id="aggressive-gates">
            <div className="wrap">
              <div className="section-heading">
                <div><span>GATE-BY-GATE DECISION</span><h2>最新全池動量傾斜驗證只過 {sizeMomentumTiltResearch.passed_gate_count} / {sizeMomentumTiltResearch.required_gate_count} 道</h2></div>
                <p>首次數據 10/10，主要外部期 9/19，近期確認期 4/19。上一輪 first-seen 14/44、schema-informed 11/38及 French 30 的 17/33 仍完整保留。</p>
              </div>
              <div className="signal-formula" aria-label="最新外部驗證凍結規格">
                <article><span>5 × 5</span><b>Size 與 12–2 prior</b><p>五個 size 各 20%，避免回報只由某一 size 主導。</p></article>
                <article><span>1:2:3:4:5</span><b>全池固定傾斜</b><p>保留全部 25 cells；集中路徑只作 baseline。</p></article>
                <article><span>MONTHLY</span><b>完整重新平衡</b><p>缺乏逐股換手，保守假設每月完整沽出再買入。</p></article>
                <article><span>10 bps</span><b>主要單邊成本</b><p>另測 25／50 bps；成本不能在看到負結果後刪除。</p></article>
              </div>

              <div className="short-gate-grid">
                <article className="waiting"><span>01</span><div><b>首次數據契約</b><strong>{sizeMomentumTiltResearch.gate_breakdown.data} 通過</strong><p>官方 ZIP、SHA-256、兩個 25 欄月表、1963–2026 完整月份及形成時序全部通過。</p></div></article>
                <article className="failed"><span>02</span><div><b>主要外部期</b><strong>{sizeMomentumTiltResearch.gate_breakdown.primary}</strong><p>候選 CAGR {pct(sizeMomentumPrimary.candidate_metrics.cagr, 2)} 勝市場，但未保留集中組合 80% 回報，成本及 DSR 失敗。</p></div></article>
                <article className="failed"><span>03</span><div><b>近期確認期</b><strong>{sizeMomentumTiltResearch.gate_breakdown.recent}</strong><p>候選 {pct(sizeMomentumRecent.candidate_metrics.cagr, 2)}，QQQ {pct(sizeMomentumRecent.baseline_metrics.QQQ.cagr, 2)}；只穩定勝全池等權。</p></div></article>
                <article className="failed"><span>04</span><div><b>成本與固定分段</b><strong>失敗</strong><p>近期 50 bps CAGR {pct(sizeMomentumRecent.candidate_50bps_metrics.cagr, 2)}；兩個固定近期分段都落後市場。</p></div></article>
                <article className="failed"><span>05</span><div><b>NW、DSR 與 PBO</b><strong>失敗</strong><p>近期市場 NW t {sizeMomentumRecentMarket.newey_west.t_stat.toFixed(2)}；DSR {pct(sizeMomentumRecentMarket.active_global_deflated_sharpe.probability, 6)}；PBO {pct(sizeMomentumTiltResearch.pbo.recent.pbo, 1)}。</p></div></article>
                <article className="failed"><span>06</span><div><b>逐股數據與前瞻 Paper</b><strong>未啟動</strong><p>French cells 不是證券，亦沒有逐股 point-in-time／退市賬本；即使 48/48 亦不能直接落盤。</p></div></article>
              </div>
              <div className="data-source-decision">
                <div><span>EVIDENCE LADDER</span><b>full-pool 23/48、first-seen 14/44、schema-informed 11/38、French 30 的 17/33 及原始失敗同時保留</b></div>
                <p>最新 25 cells 顯示長窗排名較短窗可靠，但近期仍輸市場及 QQQ；上一輪大型股隔離與 repair 亦未通過；French 30 只有早期優勢；49 行業在 1971-03-11 缺值停止。沒有一條可取代逐股 point-in-time 賬本。</p>
                <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">最新 23/48 報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_PRIOR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">上一輪 14/44</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_PRIOR_RETURN_SCHEMA_REPAIR_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">schema-informed 11/38</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_30_INDUSTRY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">French 30 的 17/33</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_INDUSTRY_DATA_FAILURE.md" target="_blank" rel="noreferrer">49 行業失敗</a></div>
              </div>
              <p className="aggressive-final-decision"><b>目前決策：</b>12–2 全池排名傾斜比短窗版本可靠，但近期、成本、相對市場、統計及可交易性仍未通過，QQQ 亦明顯較好。不開短線 Paper。下一步只接受已授權逐股 point-in-time 成分、退市／收購、公司行動、流動性及精確成本，另立協議後由全現金開始。實金及 Paper 動作均為 US$0。</p>
              <div className="protocol-link"><span>最新證據完整保留 · 23/48 負結果優先</span><div><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">最新報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_PROTOCOL.md" target="_blank" rel="noreferrer">凍結協議</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_FRENCH_SIZE_MOMENTUM_TILT_DATA_MAPPING.md" target="_blank" rel="noreferrer">數據映射</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_french_size_momentum_tilt_validation.json" target="_blank" rel="noreferrer">完整結果</a></div></div>
            </div>
          </section>
        </div>
        </StrategyTabs>
      </main>

      <footer>
        <div className="wrap footer-grid">
          <div><b>US FDDK</b><p>長線穩定與短線高回報兩條獨立研究線。</p></div>
          <div><span>最新數據</span><b>{data.data_through}</b></div>
          <div><span>公開狀態</span><b>Research + Paper-only</b></div>
          <div><span>免責聲明</span><p>歷史表現不保證未來結果；本頁不構成投資建議或實金落盤指令。</p></div>
        </div>
      </footer>
    </>
  );
}
