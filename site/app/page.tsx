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
import survivorshipStress from "../data/short-term-survivorship-contamination.json";
import temporalTailRobustness from "../data/short-term-temporal-tail-robustness.json";
import baselineMultiplicity from "../data/short-term-baseline-multiplicity.json";
import correlationCrowding from "../data/short-term-correlation-crowding.json";
import commonRiskResidual from "../data/short-term-common-risk-residual.json";
import rankMonotonicityPlacebo from "../data/short-term-rank-monotonicity-placebo.json";
import reversalVolatilityAttribution from "../data/short-term-reversal-volatility-attribution.json";
import calendarCapitalAccounting from "../data/short-term-calendar-capital-accounting.json";
import qqqReplacementOverlay from "../data/short-term-qqq-replacement-overlay.json";
import multiWindowResonance from "../data/short-term-multi-window-resonance.json";
import disclosureReadiness from "../data/short-term-disclosure-readiness.json";
import providerGapClosure from "../data/short-term-provider-gap-closure.json";
import providerGapSourceProbe from "../data/short-term-provider-gap-source-probe.json";
import providerConvergence from "../data/short-term-provider-convergence.json";
import providerGuideProbe from "../data/short-term-provider-guide-probe.json";
import riskFreeStaging from "../data/short-term-risk-free-staging.json";
import riskFreeSourceProbe from "../data/short-term-risk-free-source-probe.json";
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
    "長線 ETF 分散策略與短線研究分頁呈列；美國議員與企業內部人公開披露 Phase 1 只過 2/20 數據就緒門檻，動態選擇停用，Paper 維持全現金。",
};

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
  "Consumer Staples": "必需消費",
  Communication: "通訊服務",
  Financials: "金融",
  "Health Care": "醫療保健",
  Industrials: "工業",
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
const realMoneyReady =
  data.readiness.trade_ready === true &&
  data.readiness.allocation_visible === true &&
  data.readiness.passed_gate_count === 11 &&
  data.readiness.required_gate_count === 11;
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
const survivorshipPrimary = survivorshipStress.primary_cell;
const survivorshipTwoPctRows = survivorshipStress.stress_grid.filter(
  (row) => row.contamination_rate === 0.02,
);
const survivorshipBreakEvenRows = survivorshipStress.break_even_by_exit_return;
const survivorshipControlRows = survivorshipStress.controls;
const survivorshipAttackRows = survivorshipStress.attacks;
const survivorshipSevere80 = survivorshipTwoPctRows.find((row) => row.exit_return === -0.8)!;
const survivorshipSevere100 = survivorshipTwoPctRows.find((row) => row.exit_return === -1)!;
const temporalBootstrap = temporalTailRobustness.moving_block_bootstrap;
const temporalCluster = temporalTailRobustness.calendar_cluster;
const temporalRemoveOne = temporalTailRobustness.best_year_removals.find(
  (row) => row.removed_count === 1,
)!;
const temporalRemoveThree = temporalTailRobustness.best_year_removals.find(
  (row) => row.removed_count === 3,
)!;
const temporalTailTen = temporalTailRobustness.tail_event_removals.find(
  (row) => row.removed_count === 10,
)!;
const temporalTailFortySix = temporalTailRobustness.tail_event_removals.find(
  (row) => row.removed_count === 46,
)!;
const temporalControlRows = temporalTailRobustness.controls;
const temporalAttackRows = temporalTailRobustness.attacks;
const multiplicityEligible = baselineMultiplicity.primary_baselines.eligible_equal_return;
const multiplicityComplete = baselineMultiplicity.primary_baselines.complete_cohort_equal_return;
const multiplicityQqq = baselineMultiplicity.primary_baselines.qqq_return;
const multiplicityBootstrap = baselineMultiplicity.common_bootstrap;
const multiplicityControlRows = baselineMultiplicity.controls;
const multiplicityAttackRows = baselineMultiplicity.attacks;
const crowdingEffective = correlationCrowding.original_crowding.effective_bets;
const crowdingHighPairs = correlationCrowding.original_crowding.high_correlation_pairs;
const crowdingMaxPair = correlationCrowding.original_crowding.maximum_pairwise_correlation;
const crowdingMeanPair = correlationCrowding.original_crowding.mean_pairwise_correlation;
const crowdingFamilyRows = correlationCrowding.family.comparisons;
const crowdingOriginal = crowdingFamilyRows.find((row) => row.id === "original_top7")!;
const crowdingRemoveOne = crowdingFamilyRows.find((row) => row.id === "remove_top1_contributor")!;
const crowdingRemoveThree = crowdingFamilyRows.find((row) => row.id === "remove_top3_contributors")!;
const crowdingCap = correlationCrowding.correlation_cap2_stress;
const crowdingContributors = correlationCrowding.current_symbol_contributors;
const crowdingLeaveOne = correlationCrowding.leave_one_symbol_out.rows_sorted_weakest_first;
const crowdingControlRows = correlationCrowding.controls;
const crowdingAttackRows = correlationCrowding.attacks;
const commonRiskFamilyRows = commonRiskResidual.family.comparisons;
const commonRiskRawEligible = commonRiskFamilyRows.find((row) => row.id === "RAW__eligible")!;
const commonRiskQqqEligible = commonRiskFamilyRows.find((row) => row.id === "QQQ_252__eligible")!;
const commonRiskQqqComplete = commonRiskFamilyRows.find((row) => row.id === "QQQ_252__complete_cohort")!;
const commonRiskCohortComplete = commonRiskFamilyRows.find((row) => row.id === "COHORT_252__complete_cohort")!;
const commonRiskQqqGap = commonRiskResidual.beta_gap_summaries.find((row) => row.id === "QQQ_252__eligible")!;
const commonRiskQqqUp = commonRiskResidual.primary_stresses.qqq_forward_regimes_ex_post_not_a_signal.qqq_nonnegative;
const commonRiskQqqDown = commonRiskResidual.primary_stresses.qqq_forward_regimes_ex_post_not_a_signal.qqq_negative;
const commonRiskTail = commonRiskResidual.primary_stresses.remove_largest_absolute_beta_contribution;
const commonRiskSector = commonRiskResidual.current_sector_label_diagnostic.summary;
const commonRiskSectorRows = Object.entries(commonRiskResidual.current_sector_label_diagnostic.selection_slots_by_current_sector)
  .map(([sector, count]) => ({ sector, count }))
  .sort((left, right) => right.count - left.count || left.sector.localeCompare(right.sector));
const commonRiskControlRows = commonRiskResidual.controls;
const commonRiskAttackRows = commonRiskResidual.attacks;
const rankFamilyRows = rankMonotonicityPlacebo.family.comparisons;
const rankEligibleTopMiddle = rankFamilyRows.find((row) => row.id === "eligible_top_middle")!;
const rankEligibleMiddleBottom = rankFamilyRows.find((row) => row.id === "eligible_middle_bottom")!;
const rankEligibleTopBottom = rankFamilyRows.find((row) => row.id === "eligible_top_bottom")!;
const rankCompleteTopMiddle = rankFamilyRows.find((row) => row.id === "complete_top_middle")!;
const rankCompleteMiddleBottom = rankFamilyRows.find((row) => row.id === "complete_middle_bottom")!;
const rankCompleteTopBottom = rankFamilyRows.find((row) => row.id === "complete_top_bottom")!;
const rankEligiblePlacebo = rankMonotonicityPlacebo.placebo.eligible;
const rankCompletePlacebo = rankMonotonicityPlacebo.placebo.complete;
const rankRegimes = rankMonotonicityPlacebo.primary_stresses.qqq_forward_regimes_ex_post_not_a_signal;
const rankTails = rankMonotonicityPlacebo.primary_stresses.remove_largest_absolute_spreads;
const rankControlRows = rankMonotonicityPlacebo.controls;
const rankAttackRows = rankMonotonicityPlacebo.attacks;
const reversalFamilyRows = reversalVolatilityAttribution.family.comparisons;
const reversalEligibleRawTop = reversalFamilyRows.find((row) => row.id === "eligible_raw_top_middle")!;
const reversalCompleteRawTop = reversalFamilyRows.find((row) => row.id === "complete_raw_top_middle")!;
const reversalEligibleRawBottom = reversalFamilyRows.find((row) => row.id === "eligible_raw_bottom_middle")!;
const reversalCompleteRawBottom = reversalFamilyRows.find((row) => row.id === "complete_raw_bottom_middle")!;
const reversalEligibleResidualTop = reversalFamilyRows.find((row) => row.id === "eligible_residual_top_middle")!;
const reversalCompleteResidualTop = reversalFamilyRows.find((row) => row.id === "complete_residual_top_middle")!;
const reversalEligibleResidualBottom = reversalFamilyRows.find((row) => row.id === "eligible_residual_bottom_middle")!;
const reversalCompleteResidualBottom = reversalFamilyRows.find((row) => row.id === "complete_residual_bottom_middle")!;
const reversalEligibleAttribution = reversalVolatilityAttribution.attribution_summary.eligible;
const reversalCompleteAttribution = reversalVolatilityAttribution.attribution_summary.complete;
const reversalRegimes = reversalVolatilityAttribution.primary_stresses.qqq_trailing_20d_known_at_signal;
const reversalTails = reversalVolatilityAttribution.primary_stresses.remove_largest_raw_bottom_middle;
const reversalControlRows = reversalVolatilityAttribution.controls;
const reversalAttackRows = reversalVolatilityAttribution.attacks;
const calendarCandidate = calendarCapitalAccounting.paths.top7_five_slot;
const calendarEligiblePath = calendarCapitalAccounting.paths.eligible_equal_five_slot;
const calendarCompletePath = calendarCapitalAccounting.paths.complete_equal_five_slot;
const calendarQqqEvent = calendarCapitalAccounting.paths.qqq_event_five_slot;
const calendarQqq = calendarCapitalAccounting.paths.qqq_buy_hold;
const calendarPathRows = Object.values(calendarCapitalAccounting.paths);
const calendarFamilyRows = calendarCapitalAccounting.family.comparisons;
const calendarEligible = calendarFamilyRows.find((row) => row.baseline_id === "eligible_equal_five_slot")!;
const calendarComplete = calendarFamilyRows.find((row) => row.baseline_id === "complete_equal_five_slot")!;
const calendarRemovedYears = calendarCapitalAccounting.stresses.best_three_years_removed;
const calendarCrisisRows = Object.entries(calendarCapitalAccounting.stresses.crisis_years);
const calendarCostRows = Object.entries(calendarCapitalAccounting.stresses.costs);
const calendarControlRows = calendarCapitalAccounting.controls;
const calendarAttackRows = calendarCapitalAccounting.attacks;
const overlayCandidate = qqqReplacementOverlay.paths.top7_qqq_overlay;
const overlayEligiblePath = qqqReplacementOverlay.paths.eligible_qqq_overlay;
const overlayCompletePath = qqqReplacementOverlay.paths.complete_qqq_overlay;
const overlayPlaceboPath = qqqReplacementOverlay.paths.qqq_switch_placebo;
const overlayCashPath = qqqReplacementOverlay.paths.top7_cash_five_slot;
const overlayQqq = qqqReplacementOverlay.paths.qqq_buy_hold;
const overlayPathRows = Object.values(qqqReplacementOverlay.paths);
const overlayFamilyRows = qqqReplacementOverlay.family.comparisons;
const overlayQqqComparison = overlayFamilyRows.find((row) => row.baseline_id === "qqq_buy_hold")!;
const overlayRemovedYears = qqqReplacementOverlay.stresses.best_three_years_removed;
const overlayEventTail = qqqReplacementOverlay.stresses.favorable_46_events_removed;
const overlayCrisisRows = Object.entries(qqqReplacementOverlay.stresses.crisis_years);
const overlayCostRows = Object.entries(qqqReplacementOverlay.stresses.costs);
const overlayControlRows = qqqReplacementOverlay.controls;
const overlayAttackRows = qqqReplacementOverlay.attacks;
const resonanceCandidate = multiWindowResonance.paths.resonance3_qqq_overlay;
const resonanceMatched20 = multiWindowResonance.paths.matched_20d_qqq_overlay;
const resonanceOriginal = multiWindowResonance.paths.original_top7_qqq_overlay;
const resonanceQqq = multiWindowResonance.paths.qqq_buy_hold;
const resonancePathRows = Object.values(multiWindowResonance.paths);
const resonanceFamilyRows = multiWindowResonance.family.comparisons;
const resonanceQqqComparison = resonanceFamilyRows.find((row) => row.baseline_id === "qqq_buy_hold")!;
const resonanceMatched20Comparison = resonanceFamilyRows.find((row) => row.baseline_id === "matched_20d_qqq_overlay")!;
const resonanceOriginalComparison = resonanceFamilyRows.find((row) => row.baseline_id === "original_top7_qqq_overlay")!;
const resonanceRemovedYears = multiWindowResonance.stresses.best_three_years_removed;
const resonanceEventTail = multiWindowResonance.stresses.favorable_46_events_removed;
const resonanceCostRows = Object.entries(multiWindowResonance.stresses.costs);
const resonanceCrisisRows = Object.entries(multiWindowResonance.stresses.crisis_years);
const resonanceRegimeRows = Object.entries(multiWindowResonance.stresses.known_at_qqq_regimes);
const resonanceSelectionRows = multiWindowResonance.selection_distribution.candidate_count_histogram;
const resonanceControlRows = multiWindowResonance.controls;
const resonanceAttackRows = multiWindowResonance.attacks;
const disclosureCoverage = disclosureReadiness.coverage;
const disclosureSourceRows = disclosureReadiness.source_catalog;
const disclosureKnownAt = disclosureReadiness.known_at;
const disclosureLag = disclosureReadiness.lag;
const disclosureLegal = disclosureReadiness.legal;
const resonanceGateLabels: Record<string, string> = {
  exact_inputs: "固定輸入與父收據精確",
  parent_event_reconstruction: "905 宗父事件逐列重播",
  slot_clock: "五槽與成交時鐘精確",
  resonance_ranking: "四窗共振與排名精確",
  partial_allocations: "部分替換比例精確",
  daily_identities: "每日資產與持倉 identity",
  parent_and_placebo_identities: "父路徑與 QQQ placebo identity",
  candidate_cagr_vs_qqq: "CAGR 高於 QQQ",
  candidate_terminal_vs_qqq: "期末值高於 QQQ",
  candidate_sharpe_vs_qqq: "SHY 超額 Sharpe 高於 QQQ",
  candidate_drawdown_vs_qqq: "跌幅不比 QQQ 深超過 5pp",
  candidate_cagr_vs_original: "CAGR 高於第 30 輪 Top-7",
  candidate_cagr_vs_matched20: "CAGR 高於相同比例 20 日排名",
  candidate_cagr_vs_equal_baselines: "CAGR 高於兩條等權 baseline",
  statistical_vs_qqq: "相對 QQQ 統計門檻",
  statistical_vs_matched: "相對 matched 路徑統計門檻",
  fixed_halves: "固定前後半期同向",
  best_three_years_removed: "移除最佳三年仍通過",
  crisis_and_regimes: "危機年與已知市場狀態",
  global_cost_and_tail: "6,229 trials、成本與 46-event 尾部",
};
const rankPlaceboRows = [
  ...rankEligiblePlacebo.rows.map((row) => ({ universe: "合資格池", ...row })),
  ...rankCompletePlacebo.rows.map((row) => ({ universe: "完整現時股池", ...row })),
];
const rankSleeveRows = [
  { universe: "合資格池", bucket: "高段", ...rankMonotonicityPlacebo.sleeve_summary.eligible.top },
  { universe: "合資格池", bucket: "中段", ...rankMonotonicityPlacebo.sleeve_summary.eligible.middle },
  { universe: "合資格池", bucket: "低段", ...rankMonotonicityPlacebo.sleeve_summary.eligible.bottom },
  { universe: "完整現時股池", bucket: "高段", ...rankMonotonicityPlacebo.sleeve_summary.complete.top },
  { universe: "完整現時股池", bucket: "中段", ...rankMonotonicityPlacebo.sleeve_summary.complete.middle },
  { universe: "完整現時股池", bucket: "低段", ...rankMonotonicityPlacebo.sleeve_summary.complete.bottom },
];
const providerGapRouteRows = providerGapClosure.route_summary;
const providerGapControlRows = providerGapClosure.controls;
const providerGapAttackRows = providerGapClosure.attacks;
const providerGapBest = providerGapClosure.best_documented_route;
const providerGapStatusLabels: Record<string, string> = {
  explicit_primary_documentation: "明確",
  partial_primary_documentation: "部分",
  contradicted_by_primary_documentation: "不符",
  unresolved_primary_documentation: "未解",
  validated_authorized_sample: "樣本通過",
  qualified_provider_package: "完整合格",
};
const providerGapCapabilityLabels: Record<string, string> = {
  authorized_research_license: "研究授權",
  point_in_time_sp500_membership: "逐期 S&P 500 成分",
  membership_announced_at: "成分公布時間",
  membership_effective_at: "成分生效時間",
  permanent_security_company_ids: "永久證券／公司 ID",
  security_metadata_known_at: "Metadata KnownAt",
  raw_daily_ohlcv_status: "Raw 日線及狀態",
  distribution_event_clock_terms: "分派事件時鐘及條款",
  delist_exit_economics: "退市／退出經濟",
  post_removal_price_path: "移除後價格路徑",
  xnys_session_open_close: "XNYS 日曆",
  synchronized_qqq_spy_execution: "同步 QQQ／SPY",
  exact_one_month_daily_simple_rf: "精確一個月日度 RF",
  row_level_provenance_replay: "逐列來源重播",
};
const providerGapCapabilityRows = Object.entries(providerGapClosure.routes[0].capabilities).map(([key]) => ({
  key,
  label: providerGapCapabilityLabels[key] ?? key,
  statuses: providerGapClosure.routes.map((route) => (
    route.capabilities as Record<string, { status: string }>
  )[key].status),
}));
const providerConvergenceControlRows = providerConvergence.controls;
const providerConvergenceAttackRows = providerConvergence.attacks;
const providerDirectRows = Object.entries(providerConvergence.capability_matrix.direct);
const providerOverlayRows = Object.entries(providerConvergence.capability_matrix.overlay_required);
const riskFreeControlRows = riskFreeStaging.controls;
const riskFreeAttackRows = riskFreeStaging.attacks;
const riskFreeCoveragePct = riskFreeStaging.study.coverage_fraction * 100;
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
              <span>今日決定</span>
              <b>{realMoneyReady ? "參考配置開放" : "今天不下單"}</b>
            </div>
            <div className="capital-number"><small>實金 readiness</small><strong>{data.readiness.passed_gate_count}/{data.readiness.required_gate_count}</strong></div>
            <dl className="decision-list">
              <div><dt>今日動作</dt><dd className="locked">今天不下單</dd></div>
              <div>
                <dt>配置與本金試算</dt>
                <dd className={realMoneyReady ? undefined : "locked"}>
                  {realMoneyReady ? "通過 11/11；只供參考" : "未達 11/11，暫不顯示"}
                </dd>
              </div>
              <div><dt>下一步</dt><dd>{paper.pending_order ? "等待下一交易日開市模擬成交" : "等待下次月末檢查"}</dd></div>
              <div><dt>實金動作</dt><dd className="locked">US$0 · 不落盤</dd></div>
            </dl>
            <p>Paper 狀態及歷史最後權重只供驗證；未通過全部前瞻門檻前，不呈列為交易配置。</p>
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
              <article><span>今日可執行狀態</span><strong className="danger-text">今天不下單</strong><p>待成交指令不等於成交；實金配置仍鎖定。</p></article>
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
          <PaperAllocationLab paperOnly={!realMoneyReady} />
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
            <details><summary>目前市場判讀是買入還是避險？</summary><p>歷史凍結回測規則曾在每個完整月末把比例拉回 80/20；這不是現時交易指示，今天不下單。最新五年窗仍領先 SPY，但組合距歷史高位約 {pct(Math.abs(diagnostics.portfolio_underwater.current_drawdown), 1)}，不能解讀為保證反彈。</p></details>
            <details><summary>為甚麼報告仍會出現 US$1,000？</summary><p>這只是把歷史資金路徑換算成一致的比較尺度，不是建議本金。未達 11/11 前，頁面不顯示任何當前配置百分比或金額試算。</p></details>
          </div>
        </section>
        </div>

        <div id="short-term" data-strategy-panel="aggressive">
          <section className="hero aggressive-hero wrap">
            <div className="hero-copy">
              <div className="eyebrow-row">
                <span className="eyebrow">SHORT-TERM RETURN RESEARCH · DISCLOSURE KNOWN-AT · PHASE 1</span>
                <span className="status-chip research"><i /> 尚未啟動 PAPER</span>
              </div>
              <h1>短線高回報<br />公開披露先過合法與 known-at；現在不跟單</h1>
              <p className="hero-lead">
                Phase 1 只在擷取數據或設計策略前固定六類官方披露的經濟語意、公開可得時間與合規邊界。實際就緒只過 <strong>{disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total}</strong>；觀察來源 <strong>{disclosureCoverage.source_types_observed}/{disclosureCoverage.source_types_required}</strong>、文件 {disclosureCoverage.documents_observed}、事件 {disclosureCoverage.events_observed}，不聲稱 20 年完整覆蓋。
                Congress 披露的精確用途尚未獲書面法律／授權判定；公開可看不等於可作任何投資或網站用途。申報日、SEC accepted 時間或法定期限也不能單獨冒充 `known_at`。因此不擷取、不選股、不回測；動態選擇停用，策略運行 0。<strong>今天不下單</strong>；短線 Paper 全現金、持倉 0、實金 US$0。
              </p>
              <div className="hero-actions">
                <a className="primary-button aggressive-button" href="#disclosure-readiness">查看公開披露就緒 2/20</a>
                <a className="primary-button aggressive-button" href="#multi-window-resonance">查看第 38 輪 11/20 共振反證</a>
                <a className="primary-button aggressive-button" href="#qqq-replacement-overlay">查看第 30 輪 13/20 QQQ 疊加</a>
                <a className="primary-button aggressive-button" href="#calendar-capital-accounting">查看第 29 輪 13/18 資金回測</a>
                <a className="primary-button aggressive-button" href="#reversal-volatility-attribution">查看第 28 輪 6/14 歸因</a>
                <a className="primary-button aggressive-button" href="#rank-monotonicity-placebo">查看第 27 輪 5/14 反證</a>
                <a className="primary-button aggressive-button" href="#common-risk-residual">查看第 26 輪 6/14 反證</a>
                <a className="primary-button aggressive-button" href="#correlation-crowding">查看第 25 輪 7/12 反證</a>
                <a className="primary-button aggressive-button" href="#baseline-multiplicity">查看第 24 輪 6/9 反證</a>
                <a className="primary-button aggressive-button" href="#temporal-tail-robustness">查看第 23 輪 7/8 反證</a>
                <a className="primary-button aggressive-button" href="#survivorship-contamination">查看 20 格退出壓力</a>
                <a className="primary-button aggressive-button" href="#provider-gap-closure">查看五路徑 14 項矩陣</a>
                <a className="primary-button aggressive-button" href="#provider-convergence">查看 CRSP 直接 5/10</a>
                <a className="primary-button aggressive-button" href="#risk-free-staging">查看官方 RF 5,009/5,031</a>
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
                <b>披露就緒 {disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total} · dynamic selection disabled</b>
              </div>
              <div className="capital-number"><small>讀者動作</small><strong>今天不下單</strong></div>
              <div className="research-lock" aria-label="短線策略尚未開放配置">
                <span>目前短線配置</span><strong>US$0</strong><small>正式結果 0 · 就緒 1/18 · Paper 保持全現金</small>
              </div>
              <dl className="decision-list">
                <div><dt>公開披露 Phase 1</dt><dd>{disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total} · 未通過</dd></div>
                <div><dt>觀察來源／文件／事件</dt><dd>{disclosureCoverage.source_types_observed}/{disclosureCoverage.source_types_required} · {disclosureCoverage.documents_observed} · {disclosureCoverage.events_observed}</dd></div>
                <div><dt>Congress 精確用途法律准許</dt><dd>{disclosureLegal.congress_exact_use_written_clearance ? "通過" : "未通過"}</dd></div>
                <div><dt>動態選擇／策略運行</dt><dd>停用 · {disclosureReadiness.decision.strategy_runs}</dd></div>
                <div><dt>第 38 輪四窗共振</dt><dd>{multiWindowResonance.gate_summary.passed}/{multiWindowResonance.gate_summary.total} · 未通過</dd></div>
                <div><dt>共振候選終值／CAGR</dt><dd>{money(resonanceCandidate.terminal_usd)} · {pct(resonanceCandidate.cagr)}</dd></div>
                <div><dt>原 Top-7／20 日配對</dt><dd>{money(resonanceOriginal.terminal_usd)} · {money(resonanceMatched20.terminal_usd)}</dd></div>
                <div><dt>相對 QQQ NW t／max-t p</dt><dd>{resonanceQqqComparison.newey_west.t_stat.toFixed(2)} · {resonanceQqqComparison.bootstrap_max_t_p.toFixed(3)}</dd></div>
                <div><dt>平均候選數／事件股票目標</dt><dd>{multiWindowResonance.selection_distribution.mean_candidates.toFixed(2)} · {pct(multiWindowResonance.selection_distribution.mean_stock_target_fraction)}</dd></div>
                <div><dt>移除最佳三年／46 事件</dt><dd>t {resonanceRemovedYears.newey_west.t_stat.toFixed(2)} · {pp(resonanceEventTail.candidate_cagr_differences.qqq_buy_hold)}</dd></div>
                <div><dt>共振控制與攻擊</dt><dd>{multiWindowResonance.control_summary.passed}/{multiWindowResonance.control_summary.total} · {multiWindowResonance.attack_summary.rejected}/{multiWindowResonance.attack_summary.total}</dd></div>
                <div><dt>第 30 輪 QQQ 疊加</dt><dd>{qqqReplacementOverlay.gate_summary.passed}/{qqqReplacementOverlay.gate_summary.total} · 未通過</dd></div>
                <div><dt>候選終值／CAGR</dt><dd>{money(overlayCandidate.terminal_usd)} · {pct(overlayCandidate.cagr)}</dd></div>
                <div><dt>QQQ 終值／CAGR</dt><dd>{money(overlayQqq.terminal_usd)} · {pct(overlayQqq.cagr)}</dd></div>
                <div><dt>SHY 超額 Sharpe／最大跌幅</dt><dd>{overlayCandidate.shy_excess_sharpe.toFixed(2)} · {pct(overlayCandidate.max_drawdown)}</dd></div>
                <div><dt>QQQ NW t／max-t p</dt><dd>{overlayQqqComparison.newey_west.t_stat.toFixed(2)} · {overlayQqqComparison.bootstrap_max_t_p.toFixed(3)}</dd></div>
                <div><dt>移除最佳三年／46 事件</dt><dd>t {overlayRemovedYears.newey_west.t_stat.toFixed(2)} · {pp(overlayEventTail.candidate_cagr_differences.qqq_buy_hold)}</dd></div>
                <div><dt>疊加控制與攻擊</dt><dd>{qqqReplacementOverlay.control_summary.passed}/{qqqReplacementOverlay.control_summary.total} · {qqqReplacementOverlay.attack_summary.rejected}/{qqqReplacementOverlay.attack_summary.total}</dd></div>
                <div><dt>第 29 輪五槽資金回測</dt><dd>{calendarCapitalAccounting.gate_summary.passed}/{calendarCapitalAccounting.gate_summary.total} · 未通過</dd></div>
                <div><dt>第 28 輪反轉／波幅歸因</dt><dd>{reversalVolatilityAttribution.gate_summary.passed}/{reversalVolatilityAttribution.gate_summary.total} · 未通過</dd></div>
                <div><dt>原始→控制後 NW t</dt><dd>{reversalEligibleRawTop.newey_west.t_stat.toFixed(2)}→{reversalEligibleResidualTop.newey_west.t_stat.toFixed(2)}／{reversalCompleteRawTop.newey_west.t_stat.toFixed(2)}→{reversalCompleteResidualTop.newey_west.t_stat.toFixed(2)}</dd></div>
                <div><dt>高段優勢保留</dt><dd>{pct(reversalEligibleAttribution.aggregate_top_middle_retention_fraction, 1)}／{pct(reversalCompleteAttribution.aggregate_top_middle_retention_fraction, 1)}</dd></div>
                <div><dt>QQQ 過去 20 日下跌組</dt><dd>NW t {reversalRegimes.eligible.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}／{reversalRegimes.complete.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}</dd></div>
                <div><dt>歸因控制與攻擊</dt><dd>{reversalVolatilityAttribution.control_summary.passed}/{reversalVolatilityAttribution.control_summary.total} · {reversalVolatilityAttribution.attack_summary.rejected}/{reversalVolatilityAttribution.attack_summary.total}</dd></div>
                <div><dt>第 27 輪排序／placebo</dt><dd>{rankMonotonicityPlacebo.gate_summary.passed}/{rankMonotonicityPlacebo.gate_summary.total} · 未通過</dd></div>
                <div><dt>高段對中段 NW t</dt><dd>{rankEligibleTopMiddle.newey_west.t_stat.toFixed(2)}／{rankCompleteTopMiddle.newey_west.t_stat.toFixed(2)}</dd></div>
                <div><dt>中段對低段平均</dt><dd>{pp(rankEligibleMiddleBottom.mean, 3)}／{pp(rankCompleteMiddleBottom.mean, 3)}</dd></div>
                <div><dt>完整股池／最強 placebo t</dt><dd>{rankCompleteTopBottom.newey_west.t_stat.toFixed(2)}／{rankCompletePlacebo.maximum_placebo_t.toFixed(2)}</dd></div>
                <div><dt>排序控制與攻擊</dt><dd>{rankMonotonicityPlacebo.control_summary.passed}/{rankMonotonicityPlacebo.control_summary.total} · {rankMonotonicityPlacebo.attack_summary.rejected}/{rankMonotonicityPlacebo.attack_summary.total}</dd></div>
                <div><dt>第 26 輪共同風險殘差</dt><dd>{commonRiskResidual.gate_summary.passed}/{commonRiskResidual.gate_summary.total} · 未通過</dd></div>
                <div><dt>QQQ beta 貢獻</dt><dd>{pct(commonRiskQqqGap.beta_contribution_share_of_raw_mean, 1)} raw eligible 差額</dd></div>
                <div><dt>QQQ 殘差完整股池</dt><dd>NW t {commonRiskQqqComplete.newey_west.t_stat.toFixed(2)}</dd></div>
                <div><dt>殘差控制與攻擊</dt><dd>{commonRiskResidual.control_summary.passed}/{commonRiskResidual.control_summary.total} · {commonRiskResidual.attack_summary.rejected}/{commonRiskResidual.attack_summary.total}</dd></div>
                <div><dt>第 25 輪相關性擠擁</dt><dd>{correlationCrowding.gate_summary.passed}/{correlationCrowding.gate_summary.total} · 未通過</dd></div>
                <div><dt>中位有效獨立注數</dt><dd>{crowdingEffective.median.toFixed(2)}／7 · 未通過</dd></div>
                <div><dt>剔除 MU／AMD／MA</dt><dd>NW t {crowdingRemoveThree.newey_west.t_stat.toFixed(2)} · 低於 1.96</dd></div>
                <div><dt>擠擁控制與攻擊</dt><dd>{correlationCrowding.control_summary.passed}/{correlationCrowding.control_summary.total} · {correlationCrowding.attack_summary.rejected}/{correlationCrowding.attack_summary.total}</dd></div>
                <div><dt>第 24 輪公平基準／多重檢驗</dt><dd>{baselineMultiplicity.gate_summary.passed}/{baselineMultiplicity.gate_summary.total} · 未通過</dd></div>
                <div><dt>完整股池 NW t</dt><dd>{multiplicityComplete.newey_west.t_stat.toFixed(2)} · 低於 1.96</dd></div>
                <div><dt>6,208 次搜尋校正</dt><dd>p {multiplicityEligible.global_bonferroni_p.toFixed(2)} · 未通過</dd></div>
                <div><dt>基準／多重控制與攻擊</dt><dd>{baselineMultiplicity.control_summary.passed}/{baselineMultiplicity.control_summary.total} · {baselineMultiplicity.attack_summary.rejected}/{baselineMultiplicity.attack_summary.total}</dd></div>
                <div><dt>第 23 輪集中度反證</dt><dd>{temporalTailRobustness.gate_summary.passed}/{temporalTailRobustness.gate_summary.total} · 未通過</dd></div>
                <div><dt>刪除最佳三年</dt><dd>NW t {temporalRemoveThree.newey_west_lag4.t_stat.toFixed(2)} · 低於 1.96</dd></div>
                <div><dt>時間／尾部控制與攻擊</dt><dd>{temporalTailRobustness.control_summary.passed}/{temporalTailRobustness.control_summary.total} · {temporalTailRobustness.attack_summary.rejected}/{temporalTailRobustness.attack_summary.total}</dd></div>
                <div><dt>正式就緒控制</dt><dd>{formalReadinessControl.gate_summary.passed}/{formalReadinessControl.gate_summary.total} · 只限合成</dd></div>
                <div><dt>就緒攻擊</dt><dd>{formalBacktestReadiness.attack_summary.rejected}/{formalBacktestReadiness.attack_summary.total} · 全部拒收</dd></div>
                <div><dt>第 22 輪主要壓力</dt><dd>{survivorshipStress.primary_gate_summary.passed}/{survivorshipStress.primary_gate_summary.total} · 只限合成</dd></div>
                <div><dt>退出壓力控制／攻擊</dt><dd>{survivorshipStress.control_summary.passed}/{survivorshipStress.control_summary.total} · {survivorshipStress.attack_summary.rejected}/{survivorshipStress.attack_summary.total}</dd></div>
                <div><dt>-50% 統計 break-even</dt><dd>{pct(survivorshipBreakEvenRows.find((row) => row.exit_return === -0.5)!.newey_west_below_1_96_contamination_rate, 2)} 污染率</dd></div>
                <div><dt>第 21 輪路徑</dt><dd>{providerGapClosure.qualified_route_count}/5 合格 · {providerGapBest.explicit_count}/14 最多明確</dd></div>
                <div><dt>補缺控制／攻擊</dt><dd>{providerGapClosure.control_summary.passed}/{providerGapClosure.control_summary.total} · {providerGapClosure.attack_summary.rejected}/{providerGapClosure.attack_summary.total}</dd></div>
                <div><dt>供應商直接能力</dt><dd>{providerConvergence.capability_matrix.direct_documented_count}/10 · 尚欠 {providerConvergence.capability_matrix.overlay_required_count} 份證據層</dd></div>
                <div><dt>收斂控制／攻擊</dt><dd>{providerConvergence.control_summary.passed}/{providerConvergence.control_summary.total} · {providerConvergence.attack_summary.rejected}/{providerConvergence.attack_summary.total}</dd></div>
                <div><dt>官方 RF 覆蓋</dt><dd>{riskFreeStaging.study.available_sessions.toLocaleString("zh-HK")}/{riskFreeStaging.study.required_sessions.toLocaleString("zh-HK")} · 尚欠 {riskFreeStaging.study.missing_session_count} 日</dd></div>
                <div><dt>RF staging 攻擊</dt><dd>{riskFreeStaging.attack_summary.rejected}/{riskFreeStaging.attack_summary.total} · 全部拒收</dd></div>
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
              <article><span>披露數據就緒</span><strong>{disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total}</strong><small>只固定協議與來源語意</small></article>
              <article><span>實際觀察來源</span><strong>{disclosureCoverage.source_types_observed}/{disclosureCoverage.source_types_required}</strong><small>原始包未配置 · 不擷取</small></article>
              <article><span>動態選擇</span><strong>停用</strong><small>策略未定義 · 運行 0</small></article>
              <article><span>法律／授權硬門檻</span><strong>未通過</strong><small>Congress 精確用途未獲書面准許</small></article>
              <article><span>第 38 輪共振門檻</span><strong>{multiWindowResonance.gate_summary.passed}/{multiWindowResonance.gate_summary.total}</strong><small>九項未通過 · 不升格</small></article>
              <article><span>四窗共振終值</span><strong>{money(resonanceCandidate.terminal_usd)}</strong><small>20 bp／資產 · CAGR {pct(resonanceCandidate.cagr)}</small></article>
              <article><span>原 Top-7 終值</span><strong>{money(resonanceOriginal.terminal_usd)}</strong><small>CAGR {pct(resonanceOriginal.cagr)} · 較簡單規則勝出</small></article>
              <article><span>相同比例 20 日排名</span><strong>{money(resonanceMatched20.terminal_usd)}</strong><small>CAGR {pct(resonanceMatched20.cagr)}</small></article>
              <article><span>QQQ 買入並持有</span><strong>{money(resonanceQqq.terminal_usd)}</strong><small>CAGR {pct(resonanceQqq.cagr)}</small></article>
              <article><span>相對 QQQ NW t</span><strong>{resonanceQqqComparison.newey_west.t_stat.toFixed(2)}</strong><small>Holm／max-t {resonanceQqqComparison.holm_adjusted_p.toFixed(3)}／{resonanceQqqComparison.bootstrap_max_t_p.toFixed(3)}</small></article>
              <article><span>相對 20 日排名 t</span><strong>{resonanceMatched20Comparison.newey_west.t_stat.toFixed(2)}</strong><small>兩個固定半期皆落後</small></article>
              <article><span>移除最佳三年 NW t</span><strong>{resonanceRemovedYears.newey_west.t_stat.toFixed(2)}</strong><small>{resonanceRemovedYears.removed_years.join("／")}</small></article>
              <article><span>100 bp 候選減 QQQ</span><strong>{pp(multiWindowResonance.stresses.costs["100"].candidate_cagr_differences.qqq_buy_hold)}</strong><small>高換手成本大幅拖累</small></article>
              <article><span>共振控制／攻擊</span><strong>{multiWindowResonance.control_summary.passed}/{multiWindowResonance.control_summary.total} · {multiWindowResonance.attack_summary.rejected}/{multiWindowResonance.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 30 輪疊加門檻</span><strong>{qqqReplacementOverlay.gate_summary.passed}/{qqqReplacementOverlay.gate_summary.total}</strong><small>歷史輪次保留 · 13/20</small></article>
              <article><span>正式回測就緒</span><strong>{formalBacktestReadiness.actual_formal_readiness.passed}/{formalBacktestReadiness.actual_formal_readiness.total}</strong><small>只通過事前凍結</small></article>
              <article><span>第 28 輪反證門檻</span><strong>{reversalVolatilityAttribution.gate_summary.passed}/{reversalVolatilityAttribution.gate_summary.total}</strong><small>八項未通過</small></article>
              <article><span>原始→控制後 t</span><strong>{reversalEligibleRawTop.newey_west.t_stat.toFixed(2)}→{reversalEligibleResidualTop.newey_west.t_stat.toFixed(2)}</strong><small>完整股池 {reversalCompleteRawTop.newey_west.t_stat.toFixed(2)}→{reversalCompleteResidualTop.newey_west.t_stat.toFixed(2)}</small></article>
              <article><span>高段優勢保留</span><strong>{pct(reversalEligibleAttribution.aggregate_top_middle_retention_fraction, 1)}／{pct(reversalCompleteAttribution.aggregate_top_middle_retention_fraction, 1)}</strong><small>eligible／complete</small></article>
              <article><span>complete 後半殘差</span><strong>{pp(reversalCompleteResidualTop.fixed_halves.second.mean, 3)}</strong><small>方向轉負</small></article>
              <article><span>QQQ 過去 20 日下跌組</span><strong>{reversalRegimes.eligible.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}／{reversalRegimes.complete.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}</strong><small>訊號日已知 · eligible／complete t</small></article>
              <article><span>46-event 尾部</span><strong>{reversalTails.eligible.newey_west.t_stat.toFixed(2)}／{reversalTails.complete.newey_west.t_stat.toFixed(2)}</strong><small>兩者均不高於 1.96</small></article>
              <article><span>歸因控制／攻擊</span><strong>{reversalVolatilityAttribution.control_summary.passed}/{reversalVolatilityAttribution.control_summary.total} · {reversalVolatilityAttribution.attack_summary.rejected}/{reversalVolatilityAttribution.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 27 輪反證門檻</span><strong>{rankMonotonicityPlacebo.gate_summary.passed}/{rankMonotonicityPlacebo.gate_summary.total}</strong><small>九項未通過</small></article>
              <article><span>原始／共同事件</span><strong>{rankMonotonicityPlacebo.input.events}／{rankMonotonicityPlacebo.input.events}</strong><small>沒有縮樣本或 coverage repair</small></article>
              <article><span>eligible 高段勝中段</span><strong>NW t {rankEligibleTopMiddle.newey_west.t_stat.toFixed(2)}</strong><small>Holm／max-t {rankEligibleTopMiddle.holm_adjusted_p.toFixed(3)}／{rankEligibleTopMiddle.bootstrap_max_t_p.toFixed(3)}</small></article>
              <article><span>complete top-bottom</span><strong>NW t {rankCompleteTopBottom.newey_west.t_stat.toFixed(2)}</strong><small>低於 placebo {rankCompletePlacebo.maximum_placebo_t_id} · {rankCompletePlacebo.maximum_placebo_t.toFixed(2)}</small></article>
              <article><span>QQQ 下跌組</span><strong>{rankRegimes.eligible.qqq_negative.newey_west.t_stat.toFixed(2)}／{rankRegimes.complete.qqq_negative.newey_west.t_stat.toFixed(2)}</strong><small>eligible／complete NW t</small></article>
              <article><span>46-event 尾部</span><strong>{rankTails.eligible.newey_west.t_stat.toFixed(2)}／{rankTails.complete.newey_west.t_stat.toFixed(2)}</strong><small>兩者均低於 1.96</small></article>
              <article><span>排序控制／攻擊</span><strong>{rankMonotonicityPlacebo.control_summary.passed}/{rankMonotonicityPlacebo.control_summary.total} · {rankMonotonicityPlacebo.attack_summary.rejected}/{rankMonotonicityPlacebo.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 26 輪反證門檻</span><strong>{commonRiskResidual.gate_summary.passed}/{commonRiskResidual.gate_summary.total}</strong><small>八項未通過</small></article>
              <article><span>原始／共同樣本</span><strong>{commonRiskResidual.input.events}／{commonRiskResidual.input.family_common_events}</strong><small>MA 最早 39 事件不足 252 日</small></article>
              <article><span>QQQ beta 平均解釋</span><strong>{pct(commonRiskQqqGap.beta_contribution_share_of_raw_mean, 1)}</strong><small>raw eligible 平均差</small></article>
              <article><span>QQQ 殘差 eligible</span><strong>NW t {commonRiskQqqEligible.newey_west.t_stat.toFixed(2)}</strong><small>Holm／max-t {commonRiskQqqEligible.holm_adjusted_p.toFixed(3)}／{commonRiskQqqEligible.bootstrap_max_t_p.toFixed(3)}</small></article>
              <article><span>QQQ 殘差完整股池</span><strong>NW t {commonRiskQqqComplete.newey_west.t_stat.toFixed(2)}</strong><small>後半平均 {pp(commonRiskQqqComplete.fixed_halves.second.mean_difference, 3)}</small></article>
              <article><span>QQQ 下跌組</span><strong>NW t {commonRiskQqqDown.newey_west.t_stat.toFixed(2)}</strong><small>{commonRiskQqqDown.events} 個事後分組事件</small></article>
              <article><span>現時 sector 過半</span><strong>{pct(commonRiskSector.events_with_current_sector_majority_fraction, 1)}</strong><small>只作單向風險警示</small></article>
              <article><span>殘差控制／攻擊</span><strong>{commonRiskResidual.control_summary.passed}/{commonRiskResidual.control_summary.total} · {commonRiskResidual.attack_summary.rejected}/{commonRiskResidual.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 25 輪反證門檻</span><strong>{correlationCrowding.gate_summary.passed}/{correlationCrowding.gate_summary.total}</strong><small>五項未通過</small></article>
              <article><span>中位有效獨立注數</span><strong>{crowdingEffective.median.toFixed(2)}／7</strong><small>{pct(crowdingEffective.fraction_below_3, 1)} 少於三注</small></article>
              <article><span>至少一對高相關</span><strong>{pct(crowdingHighPairs.events_with_any_fraction, 1)}</strong><small>中位最高相關 {crowdingMaxPair.median.toFixed(3)}</small></article>
              <article><span>剔除前三貢獻股</span><strong>NW t {crowdingRemoveThree.newey_west.t_stat.toFixed(2)}</strong><small>max-t p {crowdingRemoveThree.bootstrap_max_t_p.toFixed(3)}</small></article>
              <article><span>相關 cap 2 減幅</span><strong>{crowdingCap.crowding_change.mean_pairwise_correlation_reduction.toFixed(3)}</strong><small>{crowdingMeanPair.mean.toFixed(3)} → {crowdingCap.crowding_change.mean_pairwise_correlation_after.toFixed(3)}</small></article>
              <article><span>擠擁控制／攻擊</span><strong>{correlationCrowding.control_summary.passed}/{correlationCrowding.control_summary.total} · {correlationCrowding.attack_summary.rejected}/{correlationCrowding.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 24 輪反證門檻</span><strong>{baselineMultiplicity.gate_summary.passed}/{baselineMultiplicity.gate_summary.total}</strong><small>三項未通過</small></article>
              <article><span>完整股池 NW t</span><strong>{multiplicityComplete.newey_west.t_stat.toFixed(2)}</strong><small>低於固定 1.96</small></article>
              <article><span>主要 Holm／max-t p</span><strong>{multiplicityEligible.holm_adjusted_p.toFixed(3)}／{multiplicityEligible.bootstrap_max_t_p.toFixed(3)}</strong><small>family 內通過</small></article>
              <article><span>6,208 次 Bonferroni</span><strong>{multiplicityEligible.global_bonferroni_p.toFixed(2)}</strong><small>全專案搜尋壓力失敗</small></article>
              <article><span>第 23 輪反證門檻</span><strong>{temporalTailRobustness.gate_summary.passed}/{temporalTailRobustness.gate_summary.total}</strong><small>刪除最佳三年未通過</small></article>
              <article><span>刪除最佳三年 NW t</span><strong>{temporalRemoveThree.newey_west_lag4.t_stat.toFixed(2)}</strong><small>低於固定 1.96</small></article>
              <article><span>移除最大 5% 事件</span><strong>{pp(temporalTailFortySix.mean_difference, 3)}</strong><small>NW t {temporalTailFortySix.newey_west_lag4.t_stat.toFixed(2)}</small></article>
              <article><span>時間／尾部攻擊</span><strong>{temporalTailRobustness.attack_summary.rejected}/{temporalTailRobustness.attack_summary.total}</strong><small>全部 fail closed</small></article>
              <article><span>第 22 輪主要合成格</span><strong>{survivorshipStress.primary_gate_summary.passed}/{survivorshipStress.primary_gate_summary.total}</strong><small>不能修復存活者偏差</small></article>
              <article><span>-100%／2% NW t</span><strong>{survivorshipSevere100.expected.newey_west.t_stat.toFixed(2)}</strong><small>低於 1.96；統計證據失效</small></article>
              <article><span>退出壓力攻擊</span><strong>{survivorshipStress.attack_summary.rejected}/{survivorshipStress.attack_summary.total}</strong><small>只證明協議 fail closed</small></article>
              <article><span>第 21 輪合格路徑</span><strong>{providerGapClosure.qualified_route_count}/5</strong><small>公開文件最高只屬採購候選</small></article>
              <article><span>多供應商補缺攻擊</span><strong>{providerGapClosure.attack_summary.rejected}/{providerGapClosure.attack_summary.total}</strong><small>不是供應商數據通過</small></article>
              <article><span>Stock CIZ 直接能力</span><strong>{providerConvergence.capability_matrix.direct_documented_count}/10</strong><small>另 {providerConvergence.capability_matrix.overlay_required_count} 份須 evidence overlay</small></article>
              <article><span>指南收斂攻擊</span><strong>{providerConvergence.attack_summary.rejected}/{providerConvergence.attack_summary.total}</strong><small>不是供應商數據通過</small></article>
              <article><span>官方 RF 覆蓋</span><strong>{riskFreeStaging.study.available_sessions.toLocaleString("zh-HK")}/{riskFreeStaging.study.required_sessions.toLocaleString("zh-HK")}</strong><small>尚欠 2026 年 7 月 {riskFreeStaging.study.missing_session_count} 日</small></article>
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

          <section
            className="section wrap"
            id="disclosure-readiness"
            data-sanitized-disclosure="true"
            data-dynamic-selection="disabled"
          >
            <div className="section-heading">
              <div><span>DISCLOSURE SOURCE READINESS · PHASE 1</span><h2>來源就緒 2/20；公開披露不是即時名人跟單訊號</h2></div>
              <p>六種披露來源只固定語意，不產生選股名單；公開輸出不呈列人物、股票代號、原始列或逐文件賬本。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>真實輸入尚未到位</span>
                <h3>觀察來源 {disclosureCoverage.source_types_observed}/{disclosureCoverage.source_types_required}；文件 {disclosureCoverage.documents_observed}，事件 {disclosureCoverage.events_observed}</h3>
                <p>現存收據只證明二十道門檻已事前定義，不是數據覆蓋、回測或策略質素證明。不聲稱任何 20 年完整披露歷史。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>known-at 與延遲</span><strong>{disclosureKnownAt.events_validated} 宗通過</strong><p>延遲固定為 known_at 減 event_at；缺精確時間就標記未解，不補 0。</p></article>
                <article><span>Congress 法律／授權</span><strong>{disclosureLegal.congress_exact_use_written_clearance ? "通過" : "未通過"}</strong><p>未就本專案精確用途取得有效書面准許前，兩個 Congress 來源均不收集任何一列。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>今天不下單；Paper 全現金、持倉 0、實金 US$0</b>
              <p>動態選擇停用，策略未定義且運行 0。20/20 也只可開始另一份事前凍結研究，不會自動開啟 Paper 或實金。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>數據就緒</span><strong>{disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total}</strong><p>只通過協議／schema／收據一致與官方來源語意固定。</p></article>
              <article><span>20 年覆蓋</span><strong>未驗證</strong><p>逐來源、逐年份分母、延遲、修訂與缺失尚未對數。</p></article>
              <article><span>decision_at</span><strong>已定義</strong><p>嚴格晚於 known_at 的第一個官方 XNYS 收市。</p></article>
              <article><span>trade_at</span><strong>已定義</strong><p>再下一個官方 XNYS 開市；目前通過事件 {disclosureLag.events_with_valid_trade_clock}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SIX FIXED SOURCE TYPES</span><h3>來源類別不等於六種買入訊號</h3></div>
              <p>PTR 是延遲金額區間，Form 4 必須分辨交易 code，13D／13G 是實益擁有權快照，13F 是滯後季末持倉快照。</p>
            </div>
            <div className="note-grid">
              {disclosureSourceRows.map((source) => (
                <article key={source.source_type}>
                  <span>{source.source_type}</span>
                  <h3>{source.label}</h3>
                  <p>{source.economic_semantics}。不可推論：{source.cannot_infer}。</p>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>KNOWN-AT, LAG &amp; XNYS CLOCK</span><h3>已知時間、延遲與落盤時鐘不可互換</h3></div>
              <p>官方 public timestamp 優先，其次是獨立不可回填 first-seen；兩者皆無時，保守使用本地 first observed。法定期限、filed 或 accepted 不得回推。</p>
            </div>

            <div className="decision-banner negative-banner">
              <div><span>PHASE 1 DECISION</span><b>法律、known-at、覆蓋與真實小樣本未封口；動態選擇停用</b></div>
              <strong>{disclosureReadiness.readiness.passed}/{disclosureReadiness.readiness.total}</strong>
            </div>
            <div className="source-line">
              <span>公開輸出</span><code>SANITIZED · NO SELECTION</code>
              <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_DISCLOSURE_READINESS_REPORT.md" target="_blank" rel="noreferrer">完整就緒報告</a>
              <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_DISCLOSURE_KNOWN_AT_PROTOCOL.md" target="_blank" rel="noreferrer">known-at 協議</a>
            </div>
          </section>

          <section className="section wrap" id="multi-window-resonance">
            <div className="section-heading">
              <div><span>MULTI-WINDOW RESONANCE · ROUND 38</span><h2>四窗共振只過 11/20；沒有勝過原 Top-7 或同持倉比率 20 日排名</h2></div>
              <p>5／10／15／20 日各取 Top-7，至少三窗入選才佔一個七分之一股票子槽；不足七隻的部分繼續持有 QQQ。這是固定複雜度增量測試，不是最新選股名單。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>US$1,000 歷史尺度 · 每資產 20 bp 來回成本</span>
                <h3>共振候選終值 {money(resonanceCandidate.terminal_usd)}；原 Top-7 為 {money(resonanceOriginal.terminal_usd)}</h3>
                <p>候選 CAGR {pct(resonanceCandidate.cagr)}，只比 QQQ 的 {pct(resonanceQqq.cagr)} 高 {pp(resonanceCandidate.cagr - resonanceQqq.cagr)}，卻比原 Top-7 低 {pp(resonanceCandidate.cagr - resonanceOriginal.cagr)}，也比相同比例 20 日排名低 {pp(resonanceCandidate.cagr - resonanceMatched20.cagr)}。複雜度沒有帶來增值。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>相對 QQQ 證據</span><strong>NW t {resonanceQqqComparison.newey_west.t_stat.toFixed(2)}</strong><p>Holm／共同 max-t p {resonanceQqqComparison.holm_adjusted_p.toFixed(4)}／{resonanceQqqComparison.bootstrap_max_t_p.toFixed(4)}；6,229 次 Bonferroni p {resonanceQqqComparison.global_bonferroni_p.toFixed(2)}。</p></article>
                <article><span>最直接的簡單規則反證</span><strong>對 20 日排名 t {resonanceMatched20Comparison.newey_west.t_stat.toFixed(2)}</strong><p>前後兩半平均日差均為負；對原 Top-7 的 NW t 亦只有 {resonanceOriginalComparison.newey_west.t_stat.toFixed(2)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>今天不下單；11/20 不是候選 Paper 的啟動條件</b>
              <p>這批 {multiWindowResonance.input.events} 宗事件仍由 2026 現時代號倒推，缺逐期成分、永久 ID、完整公司行動及退市經濟；point-in-time 就緒只有 {multiWindowResonance.decision.point_in_time_readiness}。網站不呈列最新逐股名單、建議比例或金額試算；Paper 全現金、持倉 0、實金 US$0。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>共同事件／五槽</span><strong>{multiWindowResonance.input.events}／{multiWindowResonance.method.slot_count}</strong><p>每槽 {multiWindowResonance.method.events_per_slot} 宗；D+1 開市、持有 {multiWindowResonance.method.holding_sessions} 個交易日。</p></article>
              <article><span>平均候選數</span><strong>{multiWindowResonance.selection_distribution.mean_candidates.toFixed(2)}／7</strong><p>事件開始的平均股票目標 {pct(multiWindowResonance.selection_distribution.mean_stock_target_fraction)}；餘額留在 QQQ。</p></article>
              <article><span>實際平均股票 driver</span><strong>{pct(resonanceCandidate.average_stock_driver_fraction)}</strong><p>QQQ driver {pct(resonanceCandidate.average_qqq_driver_fraction)}；全程無槓桿。</p></article>
              <article><span>候選成本扣賬操作</span><strong>{multiWindowResonance.calendar_integrity.candidate_cost_charge_operations.toLocaleString("zh-HK")}</strong><p>按每個被替換子槽的四個單向名義成本扣賬；不是券商成交單數。</p></article>
              <article><span>日線 identity</span><strong>{multiWindowResonance.calendar_integrity.maximum_daily_identity_residual.toExponential(1)}</strong><p>父 Top-7 最大殘差 {multiWindowResonance.calendar_integrity.maximum_original_top7_parent_residual.toExponential(1)}。</p></article>
              <article><span>正式策略運行</span><strong>{multiWindowResonance.decision.formal_strategy_runs}</strong><p>provider package {multiWindowResonance.decision.qualified_provider_packages} · 實金 US${multiWindowResonance.decision.real_money_action_usd}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SELECTION DISTRIBUTION</span><h3>共振大多保留五至七隻；沒有形成稀疏、高確信股票集</h3></div>
              <p>905 宗事件最少仍有 {multiWindowResonance.selection_distribution.minimum_candidates} 隻、最多 {multiWindowResonance.selection_distribution.maximum_candidates} 隻；這是歷史選擇數分布，不公開逐股結果作交易提示。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>每宗事件候選數</th><th>事件數</th><th>佔 905 宗</th><th>事件股票目標</th><th>QQQ 餘額</th></tr></thead>
                <tbody>{resonanceSelectionRows.map((row) => (
                  <tr className={row.candidate_count >= 5 ? "featured-row" : ""} key={row.candidate_count}>
                    <th><b>{row.candidate_count} 隻</b></th><td>{row.events}</td><td>{pct(row.events / multiWindowResonance.input.events)}</td><td>{pct(row.candidate_count / 7)}</td><td>{pct(1 - row.candidate_count / 7)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>NINE FIXED PATHS</span><h3>九條同日曆資金路徑；複雜候選與公平持倉比率 baseline 一次呈列</h3></div>
              <p>matched 路徑逐事件使用相同股票總比例；原 Top-7 保留第 30 輪全替換；QQQ placebo 量度同時鐘換手成本。不能只選較弱的 SPY／SHY 作比較。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>路徑</th><th>CAGR</th><th>終值</th><th>SHY 超額 Sharpe</th><th>最大跌幅</th><th>成本拖累 CAGR</th><th>年率化換手</th></tr></thead>
                <tbody>{resonancePathRows.map((row) => (
                  <tr className={row.path_id === "resonance3_qqq_overlay" ? "featured-row" : ""} key={row.path_id}>
                    <th><b>{row.label}</b><span>{row.asset_round_trip_cost_bps} bp／資產</span></th><td>{pct(row.cagr)}</td><td>{money(row.terminal_usd)}</td><td>{row.shy_excess_sharpe.toFixed(2)}</td><td>{pct(row.max_drawdown)}</td><td>{pct(row.cost_drag_cagr)}</td><td>{row.annual_turnover.toFixed(1)}x</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EIGHT-HYPOTHESIS FAMILY</span><h3>八個比較共同校正；相對 QQQ 及簡單排名均沒有統計確認</h3></div>
              <p>Newey–West lag 20；63-session circular blocks、20,000 條共同 bootstrap、seed 38,202,608。全專案搜尋次數由 6,221 增至 6,229，不可重設。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>候選相對基準</th><th>年率化算術差</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半日均</th><th>後半日均</th></tr></thead>
                <tbody>{resonanceFamilyRows.map((row) => (
                  <tr className={row.baseline_id === "qqq_buy_hold" ? "featured-row" : ""} key={row.baseline_id}>
                    <th><b>{row.baseline_label}</b><span>{row.sessions.toLocaleString("zh-HK")} 日</span></th><td>{pct(row.newey_west.annualized_arithmetic_difference, 2)}</td><td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td><td>{row.holm_adjusted_p.toFixed(4)}</td><td>{row.bootstrap_max_t_p.toFixed(4)}</td><td>{(row.fixed_halves.first.mean_daily_difference * 10000).toFixed(2)} bp</td><td>{(row.fixed_halves.second.mean_daily_difference * 10000).toFixed(2)} bp</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, TIME &amp; EVENT TAIL</span><h3>較高成本、最佳年份移除及 46-event 尾部均推翻正面 headline</h3></div>
              <p>50／100 bp 同步重建所有路徑；46-event 壓力把同一批最有利事件在候選與 matched 路徑改回 QQQ，不刪日期或重排資金槽。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>每資產來回成本</th><th>子槽四腿名義成本</th><th>共振 CAGR</th><th>QQQ CAGR</th><th>原 Top-7</th><th>20 日配對</th><th>候選減 QQQ</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>20 bp</b></th><td>40 bp</td><td>{pct(resonanceCandidate.cagr)}</td><td>{pct(resonanceQqq.cagr)}</td><td>{pct(resonanceOriginal.cagr)}</td><td>{pct(resonanceMatched20.cagr)}</td><td>{pp(resonanceCandidate.cagr - resonanceQqq.cagr)}</td></tr>
                  {resonanceCostRows.map(([cost, row]) => (
                    <tr key={cost}><th><b>{cost} bp</b></th><td>{Number(cost) * 2} bp</td><td>{pct(row.paths.resonance3_qqq_overlay.cagr)}</td><td>{pct(row.paths.qqq_buy_hold.cagr)}</td><td>{pct(row.paths.original_top7_qqq_overlay.cagr)}</td><td>{pct(row.paths.matched_20d_qqq_overlay.cagr)}</td><td className="negative-number">{pp(row.candidate_cagr_differences.qqq_buy_hold)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="evidence-stat-grid">
              <article><span>移除最佳三年</span><strong>NW t {resonanceRemovedYears.newey_west.t_stat.toFixed(2)}</strong><p>{resonanceRemovedYears.removed_years.join("／")}；平均日差 {(resonanceRemovedYears.mean_daily_difference * 10000).toFixed(2)} bp。</p></article>
              <article><span>移除 46 有利事件</span><strong>{pp(resonanceEventTail.candidate_cagr_differences.qqq_buy_hold)}</strong><p>候選減 QQQ CAGR；減 20 日配對為 {pp(resonanceEventTail.candidate_cagr_differences.matched_20d_qqq_overlay)}。</p></article>
              {resonanceRegimeRows.map(([regime, row]) => (
                <article key={regime}><span>訊號日 QQQ 20 日{regime === "negative" ? "下跌" : "非負"}</span><strong>{pp(row.average_event_difference, 3)}</strong><p>{row.events} 宗；平均候選 {row.average_candidates.toFixed(2)} 隻。</p></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS PERIODS</span><h3>2008、2020、2022 沒有同時勝過 QQQ</h3></div>
              <p>危機年份及已知 QQQ 狀態均在協議中固定；2008／2020 候選落後 QQQ，QQQ 過去 20 日下跌組的平均事件差亦為負。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>年份</th><th>候選回報</th><th>候選最大跌幅</th><th>QQQ 回報</th><th>QQQ 最大跌幅</th><th>回報差</th></tr></thead>
                <tbody>{resonanceCrisisRows.map(([year, paths]) => (
                  <tr key={year}><th><b>{year}</b></th><td>{pct(paths.resonance3_qqq_overlay.return)}</td><td>{pct(paths.resonance3_qqq_overlay.max_drawdown)}</td><td>{pct(paths.qqq_buy_hold.return)}</td><td>{pct(paths.qqq_buy_hold.max_drawdown)}</td><td>{pp(paths.resonance3_qqq_overlay.return - paths.qqq_buy_hold.return)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>TWENTY FALSIFICATION GATES</span><h3>二十項門檻逐項呈列；11/20 不升格</h3></div>
              <p>工程 identity 通過不代表經濟結果通過；失敗集中在 Sharpe、簡單規則、統計、半期、最佳年份、危機、成本及尾部。</p>
            </div>
            <div className="gate-grid compact-gates">
              {multiWindowResonance.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "failed"} key={gate.id}><span>{gate.passed ? "通過" : "未通過"}</span><b>{resonanceGateLabels[gate.id] ?? gate.id}</b><strong>{gate.passed ? "✓" : "×"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FAIL-CLOSED RECEIPTS</span><h3>四十五道控制通過；三十九項單欄偷換全部拒收</h3></div>
              <p>這只證明 protocol、父收據、排名、比例、成本、family、壓力與決策邊界可重播，不代表共振選股有效。</p>
            </div>
            <details className="receipt-details">
              <summary>展開 {resonanceControlRows.length} 道控制</summary>
              <div className="gate-grid compact-gates">
                {resonanceControlRows.map((control) => (
                  <article className={control.passed ? "passed" : "failed"} key={control.id}><span>{control.id}</span><b>{control.label.replaceAll("_", " ")}</b><strong>{control.passed ? "✓" : "×"}</strong></article>
                ))}
              </div>
            </details>
            <details className="receipt-details">
              <summary>展開 {resonanceAttackRows.length} 項突變攻擊</summary>
              <div className="attack-grid">
                {resonanceAttackRows.map((attack) => (
                  <article className={attack.rejected ? "rejected" : "escaped"} key={attack.id}><span>{attack.id}</span><b>{attack.label.replaceAll("_", " ")}</b><code>{attack.observed_error_code}</code></article>
                ))}
              </div>
            </details>

            <div className="decision-banner negative-banner">
              <div><span>ROUND 38 DECISION</span><b>共振候選只略高於 QQQ，卻落後兩條更簡單的動量路徑；不建立新策略</b></div>
              <strong>{multiWindowResonance.gate_summary.passed}/{multiWindowResonance.gate_summary.total}</strong>
            </div>
            <div className="source-line">
              <span>數據最後退出日</span><code>{multiWindowResonance.input.last_exit_date}</code>
              <span>Protocol</span><code>{multiWindowResonance.protocol.commit.slice(0, 12)}</code>
              <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_MULTI_WINDOW_RESONANCE_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">完整研究報告</a>
              <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_multi_window_resonance_validation.json" target="_blank" rel="noreferrer">機器收據</a>
            </div>
          </section>

          <section className="section wrap" id="qqq-replacement-overlay">
            <div className="section-heading">
              <div><span>QQQ REPLACEMENT OVERLAY · ROUND 30</span><h2>Headline 首次高於 QQQ，但二十項門檻只過 13/20</h2></div>
              <p>五個槽位在沒有事件時持有 QQQ；事件開始才把該槽換成凍結 Top-7，完整計入四個交易腿。這直接測試選股能否為全投資 QQQ 增值，而不是用閒置現金拖低比較基準。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>US$1,000 歷史尺度 · 每資產 20 bp 來回成本</span>
                <h3>候選終值 {money(overlayCandidate.terminal_usd)}；QQQ 終值 {money(overlayQqq.terminal_usd)}</h3>
                <p>候選 CAGR {pct(overlayCandidate.cagr)}，比 QQQ 的 {pct(overlayQqq.cagr)} 高 {pp(overlayCandidate.cagr - overlayQqq.cagr)}；SHY 超額 Sharpe {overlayCandidate.shy_excess_sharpe.toFixed(2)}，最大跌幅 {pct(overlayCandidate.max_drawdown)}。這是正面 headline，不是升格結論。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>相對 QQQ 證據</span><strong>NW t {overlayQqqComparison.newey_west.t_stat.toFixed(2)}</strong><p>Holm／共同 max-t p {overlayQqqComparison.holm_adjusted_p.toFixed(4)}／{overlayQqqComparison.bootstrap_max_t_p.toFixed(4)}；6,221 次 Bonferroni p {overlayQqqComparison.global_bonferroni_p.toFixed(2)}。</p></article>
                <article><span>時間與事件尾部</span><strong>移除三年 t {overlayRemovedYears.newey_west.t_stat.toFixed(2)}</strong><p>移除 {overlayRemovedYears.removed_years.join("、")} 後平均差轉負；移除最有利 46 宗事件後，候選減 QQQ CAGR 為 {pp(overlayEventTail.candidate_cagr_differences.qqq_buy_hold)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>Headline 高於 QQQ，不等於已證明可交易 alpha</b>
              <p>本輪仍使用同一批已見 2026 現時 survivor cohort，缺逐期成分、永久 ID、公司行動及退市／退出經濟；而且對 QQQ 的統計、固定半期、危機、成本與事件尾部均未全部通過。數據最後退出日為 {shortDate(qqqReplacementOverlay.input.last_exit_date)}，不是即市買入訊號。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>日曆交易日</span><strong>{qqqReplacementOverlay.calendar_integrity.sessions.toLocaleString("zh-HK")}</strong><p>{shortDate(qqqReplacementOverlay.calendar_integrity.first_date)} 至 {shortDate(qqqReplacementOverlay.calendar_integrity.last_date)}。</p></article>
              <article><span>資金槽／事件</span><strong>{qqqReplacementOverlay.method.slot_count} × {pct(qqqReplacementOverlay.method.slot_initial_weight, 0)}</strong><p>每槽 {qqqReplacementOverlay.method.events_per_slot} 宗；全程無槓桿。</p></article>
              <article><span>候選交易腿</span><strong>{qqqReplacementOverlay.calendar_integrity.candidate_total_transaction_legs.toLocaleString("zh-HK")}</strong><p>正常事件四腿；不是只收一次 Top-7 成本。</p></article>
              <article><span>首次成交後持倉</span><strong>100%</strong><p>最大現金誤差 {qqqReplacementOverlay.calendar_integrity.post_entry_maximum_cash_value.toExponential(1)}。</p></article>
              <article><span>QQQ placebo 誤差</span><strong>{qqqReplacementOverlay.calendar_integrity.maximum_qqq_placebo_residual.toExponential(1)}</strong><p>相同 QQQ 價格路徑乘累積成本。</p></article>
              <article><span>正式策略運行</span><strong>{qqqReplacementOverlay.decision.formal_strategy_runs}</strong><p>Paper 全現金 · 持倉 0 · 實金 US${qqqReplacementOverlay.decision.real_money_action_usd}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EIGHT FIXED PATHS</span><h3>八條完整資金路徑，同時保留強弱基準</h3></div>
              <p>eligible／complete overlay 使用相同槽位、QQQ 底倉、事件時鐘及四腿成本；QQQ placebo 專門量度高換手成本；第 29 輪現金路徑亦原樣保留。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>路徑</th><th>CAGR</th><th>終值</th><th>SHY 超額 Sharpe</th><th>最大跌幅</th><th>年率化換手</th><th>平均持倉</th></tr></thead>
                <tbody>{overlayPathRows.map((row) => (
                  <tr className={row.path_id === "top7_qqq_overlay" ? "featured-row" : ""} key={row.path_id}>
                    <th><b>{row.label}</b><span>{row.asset_round_trip_cost_bps} bp／資產</span></th>
                    <td>{pct(row.cagr)}</td><td>{money(row.terminal_usd)}</td><td>{row.shy_excess_sharpe.toFixed(2)}</td><td>{pct(row.max_drawdown)}</td><td>{row.annual_turnover.toFixed(1)}x</td><td>{pct(row.average_exposure)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SEVEN-BASELINE FAMILY</span><h3>Headline、完整股池、QQQ及多重檢驗一次呈列</h3></div>
              <p>Newey–West lag 20；63-session circular blocks、20,000 條共同 bootstrap 路徑。QQQ 配對是主要機會成本，不能用較弱 placebo 取代。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>候選相對基準</th><th>年率化算術差</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半日均</th><th>後半日均</th></tr></thead>
                <tbody>{overlayFamilyRows.map((row) => (
                  <tr className={row.baseline_id === "qqq_buy_hold" ? "featured-row" : ""} key={row.baseline_id}>
                    <th><b>{row.baseline_label}</b><span>{row.sessions.toLocaleString("zh-HK")} 日</span></th>
                    <td>{pct(row.newey_west.annualized_arithmetic_difference, 2)}</td><td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td><td>{row.holm_adjusted_p.toFixed(4)}</td><td>{row.bootstrap_max_t_p.toFixed(4)}</td><td>{(row.fixed_halves.first.mean_daily_difference * 10000).toFixed(2)} bp</td><td>{(row.fixed_halves.second.mean_daily_difference * 10000).toFixed(2)} bp</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST, TIME &amp; EVENT TAIL</span><h3>高換手令 20 bp 優勢在較高成本及尾部壓力下反轉</h3></div>
              <p>每資產 50／100 bp 表示正常事件名義總成本 100／200 bp；46-event 壓力按事前固定 Top-7 減 QQQ gross difference 排序，三條選股 overlay 同時移除。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>每資產成本</th><th>事件名義總成本</th><th>候選 CAGR</th><th>QQQ CAGR</th><th>Eligible overlay</th><th>Complete overlay</th><th>候選減 QQQ</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>20 bp</b></th><td>40 bp</td><td>{pct(overlayCandidate.cagr)}</td><td>{pct(overlayQqq.cagr)}</td><td>{pct(overlayEligiblePath.cagr)}</td><td>{pct(overlayCompletePath.cagr)}</td><td>{pp(overlayCandidate.cagr - overlayQqq.cagr)}</td></tr>
                  {overlayCostRows.map(([cost, row]) => (
                    <tr key={cost}><th><b>{cost} bp</b></th><td>{row.normal_overlay_event_total_nominal_bps} bp</td><td>{pct(row.paths.top7_qqq_overlay.cagr)}</td><td>{pct(row.paths.qqq_buy_hold.cagr)}</td><td>{pct(row.paths.eligible_qqq_overlay.cagr)}</td><td>{pct(row.paths.complete_qqq_overlay.cagr)}</td><td className="negative-number">{pp(row.candidate_cagr_differences.qqq_buy_hold)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="evidence-stat-grid">
              <article><span>移除最佳三年</span><strong>NW t {overlayRemovedYears.newey_west.t_stat.toFixed(2)}</strong><p>{overlayRemovedYears.removed_years.join("／")}；平均日差 {(overlayRemovedYears.mean_daily_difference * 10000).toFixed(2)} bp。</p></article>
              <article><span>移除 46 有利事件</span><strong>{pp(overlayEventTail.candidate_cagr_differences.qqq_buy_hold)}</strong><p>候選減 QQQ CAGR；減 complete 為 {pp(overlayEventTail.candidate_cagr_differences.complete_qqq_overlay)}。</p></article>
              <article><span>現金路徑對照</span><strong>{money(overlayCashPath.terminal_usd)}</strong><p>第 29 輪只持倉 {pct(overlayCashPath.average_exposure)}；不能與全投資 QQQ 混為一談。</p></article>
              <article><span>QQQ 換手 placebo</span><strong>{money(overlayPlaceboPath.terminal_usd)}</strong><p>把相同資產反覆沽買也會被成本大幅侵蝕。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CRISIS PERIODS</span><h3>2008、2020、2022 沒有全部勝過 QQQ及守住最大跌幅</h3></div>
              <p>危機年份在協議中事前固定；策略是高股票持倉替換，不是現金或短債替代品。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>年份</th><th>候選回報</th><th>候選最大跌幅</th><th>QQQ 回報</th><th>QQQ 最大跌幅</th><th>回報差</th></tr></thead>
                <tbody>{overlayCrisisRows.map(([year, paths]) => (
                  <tr key={year}><th><b>{year}</b></th><td>{pct(paths.top7_qqq_overlay.return)}</td><td>{pct(paths.top7_qqq_overlay.max_drawdown)}</td><td>{pct(paths.qqq_buy_hold.return)}</td><td>{pct(paths.qqq_buy_hold.max_drawdown)}</td><td>{pp(paths.top7_qqq_overlay.return - paths.qqq_buy_hold.return)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>TWENTY PRE-FROZEN GATES</span><h3>二十項門檻逐項呈列；13/20 不升格</h3></div>
              <p>CAGR及終值高於 QQQ 的兩項通過，不能抵銷配對統計、完整股池、半期、最佳年份、危機及成本／尾部失敗。</p>
            </div>
            <div className="point-in-time-gate-list">
              {qqqReplacementOverlay.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 30 輪事前固定門檻</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>二十九道輸入、QQQ 底倉、四腿成本、統計及決策控制</h3></div>
              <p>29/29 只證明程式遵守已推送協議，不是盈利或 Paper 通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {overlayControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 30 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>二十九項 hash、底倉、成本、family、尾部及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中指定錯誤碼，包括 qqq_overlay_leg_contract_mismatch 及 qqq_overlay_decision_boundary_breached。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {overlayAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}><div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div><p>{attack.expected_error_code}</p></article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 30 DECISION</span><b>全投資 headline 高於 QQQ，但統計、時間、危機、成本及事件尾部沒有同時通過；不建立新策略</b></div>
              <p>正式就緒 {qqqReplacementOverlay.decision.formal_readiness}、逐股 point-in-time {qqqReplacementOverlay.decision.point_in_time_readiness}、合資格數據包 0、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。下一個可升級證據仍是獲授權逐期成分、永久 ID、公司行動及退市／退出經濟，再按既有正式預先登記運行一次。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 30 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_QQQ_REPLACEMENT_OVERLAY_PROTOCOL.md" target="_blank" rel="noreferrer">事前 QQQ 疊加協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_qqq_replacement_overlay_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="calendar-capital-accounting">
            <div className="section-heading">
              <div><span>CALENDAR CAPITAL ACCOUNTING · ROUND 29</span><h2>五槽資金回測只過 13/18；Top-7 有正回報，但長期明顯落後 QQQ</h2></div>
              <p>把 905 宗重疊事件放回同一條 2006–2026 日曆時間線；五個資金槽各佔 20%，同槽不重疊、不借貸，並同時列出事件式公平基準及 QQQ／SPY／SHY 買入並持有。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>US$1,000 讀者換算 · 20 bp 來回成本</span>
                <h3>Top-7 終值 {money(calendarCandidate.terminal_usd)}；QQQ 終值 {money(calendarQqq.terminal_usd)}</h3>
                <p>候選 CAGR {pct(calendarCandidate.cagr)}、SHY 超額 Sharpe {calendarCandidate.shy_excess_sharpe.toFixed(2)}、最大跌幅 {pct(calendarCandidate.max_drawdown)}；QQQ CAGR {pct(calendarQqq.cagr)}，所以「有盈利」不等於「值得取代簡單基準」。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>統計完整性</span><strong>完整股池 t {calendarComplete.newey_west.t_stat.toFixed(2)}</strong><p>合資格池局部 Holm／max-t p 為 {calendarEligible.holm_adjusted_p.toFixed(4)}／{calendarEligible.bootstrap_max_t_p.toFixed(4)}，但全專案 Bonferroni p {calendarEligible.global_bonferroni_p.toFixed(2)}。</p></article>
                <article><span>時間集中</span><strong>移除最佳三年 t {calendarRemovedYears.newey_west.t_stat.toFixed(2)}</strong><p>剔除 {calendarRemovedYears.removed_years.join("、")} 後不再達 1.96；前後半一致性亦未通過。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>真實與合成分開；同一已見 survivor cohort 不是正式 point-in-time 回測</b>
              <p>股票仍使用 2026 現時代號，缺逐期成分、永久 ID、歷史行業、公司行動及退市／退出經濟。完整資金會計能修正重疊持倉與本金重用，不能修正存活者偏差；數據截至 {shortDate(calendarCapitalAccounting.input.last_exit_date)}，不是即市訊號。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>日曆交易日</span><strong>{calendarCapitalAccounting.calendar_integrity.sessions.toLocaleString("zh-HK")}</strong><p>{shortDate(calendarCapitalAccounting.calendar_integrity.first_date)} 至 {shortDate(calendarCapitalAccounting.calendar_integrity.last_date)}。</p></article>
              <article><span>資金槽</span><strong>{calendarCapitalAccounting.method.slot_count} × {pct(calendarCapitalAccounting.method.slot_initial_weight, 0)}</strong><p>每槽 {calendarCapitalAccounting.method.events_per_slot} 宗；最高同時持有 {calendarCapitalAccounting.reconstruction.maximum_concurrent_intervals} 槽。</p></article>
              <article><span>Top-7 平均持倉</span><strong>{pct(calendarCandidate.average_exposure)}</strong><p>最高 {pct(calendarCandidate.maximum_exposure)}；年率化換手 {calendarCandidate.annual_turnover.toFixed(1)} 倍。</p></article>
              <article><span>成本拖累</span><strong>{pp(calendarCandidate.cost_drag_cagr)}</strong><p>相對零成本終值少 {money(calendarCandidate.cost_drag_terminal_usd)}。</p></article>
              <article><span>2008／2022 回報</span><strong>{pct(calendarCapitalAccounting.stresses.crisis_years["2008"].top7_five_slot.return)}／{pct(calendarCapitalAccounting.stresses.crisis_years["2022"].top7_five_slot.return)}</strong><p>不是低風險現金替代品。</p></article>
              <article><span>正式策略運行</span><strong>{calendarCapitalAccounting.decision.formal_strategy_runs}</strong><p>Paper 全現金 · 實金 US${calendarCapitalAccounting.decision.real_money_action_usd}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SEVEN FIXED PATHS</span><h3>七條同起訖日路徑，不只展示候選</h3></div>
              <p>所有 Sharpe 均以 SHY 日回報作超額回報代理；US$ 終值只把相對淨值換算成讀者示例本金。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>路徑</th><th>CAGR</th><th>終值</th><th>SHY 超額 Sharpe</th><th>最大跌幅</th><th>年率化換手</th><th>平均持倉</th></tr></thead>
                <tbody>{calendarPathRows.map((row) => (
                  <tr className={row.path_id === "top7_five_slot" ? "featured-row" : ""} key={row.path_id}>
                    <th><b>{row.label}</b><span>{row.round_trip_cost_bps} bp</span></th>
                    <td>{pct(row.cagr)}</td><td>{money(row.terminal_usd)}</td><td>{row.shy_excess_sharpe.toFixed(2)}</td><td>{pct(row.max_drawdown)}</td><td>{row.annual_turnover.toFixed(1)}x</td><td>{pct(row.average_exposure)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SIX-BASELINE FAMILY</span><h3>公平事件基準、買入並持有及多重檢驗一次呈列</h3></div>
              <p>Newey–West lag 20；63-session circular blocks、20,000 條共同 bootstrap 路徑。前後半為固定日曆切割，不因結果移動。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Top-7 相對基準</th><th>年率化算術差</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半日均</th><th>後半日均</th></tr></thead>
                <tbody>{calendarFamilyRows.map((row) => (
                  <tr className={row.baseline_id === "eligible_equal_five_slot" ? "featured-row" : ""} key={row.baseline_id}>
                    <th><b>{row.baseline_label}</b><span>{row.sessions.toLocaleString("zh-HK")} 日</span></th>
                    <td>{pct(row.newey_west.annualized_arithmetic_difference, 2)}</td><td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td><td>{row.holm_adjusted_p.toFixed(4)}</td><td>{row.bootstrap_max_t_p.toFixed(4)}</td><td>{(row.fixed_halves.first.mean_daily_difference * 10000).toFixed(2)} bp</td><td>{(row.fixed_halves.second.mean_daily_difference * 10000).toFixed(2)} bp</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COST &amp; CRISIS STRESS</span><h3>換手令成本不能忽略；危機年份並非只看平均 CAGR</h3></div>
              <p>50／100 bp 來回成本沿用同一五槽路徑；2008、2020、2022 使用該曆年內的實際日線回報。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>成本</th><th>Top-7 CAGR</th><th>終值</th><th>合資格池</th><th>完整現時股池</th><th>QQQ event</th></tr></thead>
                <tbody>
                  <tr className="featured-row"><th><b>20 bp</b></th><td>{pct(calendarCandidate.cagr)}</td><td>{money(calendarCandidate.terminal_usd)}</td><td>{pct(calendarEligiblePath.cagr)}</td><td>{pct(calendarCompletePath.cagr)}</td><td>{pct(calendarQqqEvent.cagr)}</td></tr>
                  {calendarCostRows.map(([cost, row]) => (
                    <tr key={cost}><th><b>{cost} bp</b></th><td>{pct(row.paths.top7_five_slot.cagr)}</td><td>{money(row.paths.top7_five_slot.terminal_usd)}</td><td>{pct(row.paths.eligible_equal_five_slot.cagr)}</td><td>{pct(row.paths.complete_equal_five_slot.cagr)}</td><td>{pct(row.paths.qqq_event_five_slot.cagr)}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>危機年份</th><th>Top-7 回報</th><th>Top-7 最大跌幅</th><th>QQQ</th><th>SPY</th><th>SHY</th></tr></thead>
                <tbody>{calendarCrisisRows.map(([year, paths]) => (
                  <tr key={year}><th><b>{year}</b></th><td>{pct(paths.top7_five_slot.return)}</td><td>{pct(paths.top7_five_slot.max_drawdown)}</td><td>{pct(paths.qqq_buy_hold.return)}</td><td>{pct(paths.spy_buy_hold.return)}</td><td>{pct(paths.shy_buy_hold.return)}</td></tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EIGHTEEN PRE-FROZEN GATES</span><h3>十八項門檻逐項呈列；13/18 不升格</h3></div>
              <p>五槽會計、正回報或局部顯著不能抵銷 QQQ、完整股池、前後半、最佳年份集中及全專案多重搜尋失敗。</p>
            </div>
            <div className="point-in-time-gate-list">
              {calendarCapitalAccounting.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 29 輪事前固定門檻</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>二十五道輸入、資金、成本、統計及決策控制</h3></div>
              <p>25/25 只證明程式遵守凍結協議，不是未來盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {calendarControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 29 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>二十五項 hash、槽位、成本、family、壓力及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中指定錯誤碼，包括 calendar_capital_bootstrap_contract_mismatch 及 calendar_capital_decision_boundary_breached。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {calendarAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}><div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div><p>{attack.expected_error_code}</p></article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 29 DECISION</span><b>事件層優勢經資金佔用後仍不足以勝過 QQQ、完整股池及全專案多重搜尋；不建立新策略</b></div>
              <p>正式就緒 {calendarCapitalAccounting.decision.formal_readiness}、逐股 point-in-time {calendarCapitalAccounting.decision.point_in_time_readiness}、合資格數據包 0、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。下一個可升級證據是獲授權逐期成分、永久 ID、公司行動及退市／退出經濟，再以首段真正未見數據驗證已凍結規則。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 29 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CALENDAR_CAPITAL_ACCOUNTING_PROTOCOL.md" target="_blank" rel="noreferrer">事前資金會計協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_calendar_capital_accounting_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="reversal-volatility-attribution">
            <div className="section-heading">
              <div><span>REVERSAL &amp; VOLATILITY ATTRIBUTION · ROUND 28</span><h2>十四項反證只過 6/14；控制後 top-middle 只保留 42%／35%</h2></div>
              <p>固定第二十七輪同一 905 個事件與 bucket；只加入訊號日已知的 5 日回報及 20 日波幅，以橫截面 OLS 分拆原始、模型解釋及殘差，沒有改 Top-K、持有期、成本或入場時鐘。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>八假說共同 family · {reversalVolatilityAttribution.gate_summary.passed}/{reversalVolatilityAttribution.gate_summary.total}</span>
                <h3>eligible 原始 NW t {reversalEligibleRawTop.newey_west.t_stat.toFixed(2)}，控制後只有 {reversalEligibleResidualTop.newey_west.t_stat.toFixed(2)}</h3>
                <p>完整現時股池亦由 t {reversalCompleteRawTop.newey_west.t_stat.toFixed(2)} 降至 {reversalCompleteResidualTop.newey_west.t_stat.toFixed(2)}；控制後平均只保留 {pct(reversalEligibleAttribution.aggregate_top_middle_retention_fraction, 1)}／{pct(reversalCompleteAttribution.aggregate_top_middle_retention_fraction, 1)}，完整股池後半更為 {pp(reversalCompleteResidualTop.fixed_halves.second.mean, 3)}。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>底段反彈未完全解釋</span><strong>殘差 {pp(reversalEligibleResidualBottom.mean, 3)}／{pp(reversalCompleteResidualBottom.mean, 3)}</strong><p>eligible／complete bottom-middle 仍為正，但 t 只有 {reversalEligibleResidualBottom.newey_west.t_stat.toFixed(2)}／{reversalCompleteResidualBottom.newey_west.t_stat.toFixed(2)}。</p></article>
                <article><span>市場及尾部</span><strong>弱市 t {reversalRegimes.eligible.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}／{reversalRegimes.complete.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}</strong><p>移除 46 個最大原始底段反彈後，殘差 top-middle t 亦只有 {reversalTails.eligible.newey_west.t_stat.toFixed(2)}／{reversalTails.complete.newey_west.t_stat.toFixed(2)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>原始／共同 905／905；同一已見 survivor cohort</b>
              <p>本輪重播第二十七輪 bucket hash，沒有縮樣本或 coverage repair。股票仍是 2026 現時代號，缺 point-in-time 成分、永久 ID、歷史行業及退市／收購經濟；這是機制歸因，不是獨立未見確認。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>研究事件</span><strong>{reversalVolatilityAttribution.input.events}</strong><p>{shortDate(reversalVolatilityAttribution.input.first_signal_date)} 至 {shortDate(reversalVolatilityAttribution.input.last_signal_date)}。</p></article>
              <article><span>eligible 原始→殘差 t</span><strong>{reversalEligibleRawTop.newey_west.t_stat.toFixed(2)}→{reversalEligibleResidualTop.newey_west.t_stat.toFixed(2)}</strong><p>保留 {pct(reversalEligibleAttribution.aggregate_top_middle_retention_fraction, 1)}。</p></article>
              <article><span>complete 原始→殘差 t</span><strong>{reversalCompleteRawTop.newey_west.t_stat.toFixed(2)}→{reversalCompleteResidualTop.newey_west.t_stat.toFixed(2)}</strong><p>保留 {pct(reversalCompleteAttribution.aggregate_top_middle_retention_fraction, 1)}。</p></article>
              <article><span>OLS 完整性</span><strong>rank 3 · condition ≤ {reversalVolatilityAttribution.attribution_integrity.maximum_condition_number.toFixed(0)}</strong><p>raw = predicted + residual；數值 12 位、feature hash {reversalVolatilityAttribution.attribution_integrity.feature_receipt_decimal_places} 位跨平台量化。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>RAW → PREDICTED → RESIDUAL</span><h3>高段優勢被共同控制大幅吸收；底段反彈沒有被完整解釋</h3></div>
              <p>所有數字均為每個事件的 20 日淨回報差；predicted 只由訊號日前數據推算，不使用未來市場方向。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>原始 top-middle</th><th>殘差 top-middle</th><th>保留</th><th>原始 bottom-middle</th><th>模型解釋 bottom-middle</th><th>殘差 bottom-middle</th></tr></thead>
                <tbody>
                  <tr><th><b>合資格池</b></th><td>{pp(reversalEligibleRawTop.mean, 3)}</td><td>{pp(reversalEligibleResidualTop.mean, 3)}</td><td>{pct(reversalEligibleAttribution.aggregate_top_middle_retention_fraction, 1)}</td><td>{pp(reversalEligibleRawBottom.mean, 3)}</td><td>{pp(reversalEligibleAttribution.predicted_bottom_middle.mean, 3)}</td><td>{pp(reversalEligibleResidualBottom.mean, 3)}</td></tr>
                  <tr className="featured-row"><th><b>完整現時股池</b></th><td>{pp(reversalCompleteRawTop.mean, 3)}</td><td>{pp(reversalCompleteResidualTop.mean, 3)}</td><td>{pct(reversalCompleteAttribution.aggregate_top_middle_retention_fraction, 1)}</td><td>{pp(reversalCompleteRawBottom.mean, 3)}</td><td>{pp(reversalCompleteAttribution.predicted_bottom_middle.mean, 3)}</td><td>{pp(reversalCompleteResidualBottom.mean, 3)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SIGNAL-DATE ATTRIBUTION</span><h3>低段近期跌得更多；完整股池低段亦明顯較高波幅</h3></div>
              <p>rank gap 為 bottom-middle；beta 及貢獻均逐事件估計再做 Newey–West lag 4，不把平均係數誤當固定交易規則。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>5 日 rank gap</th><th>波幅 rank gap</th><th>5 日 beta</th><th>波幅 beta</th><th>5 日貢獻</th><th>波幅貢獻</th></tr></thead>
                <tbody>
                  <tr><th><b>合資格池</b></th><td>{reversalEligibleAttribution.prior5_rank_gap_bottom_middle.mean.toFixed(3)}</td><td>{reversalEligibleAttribution.volatility_rank_gap_bottom_middle.mean.toFixed(3)}</td><td>{pp(reversalEligibleAttribution.beta_prior5.mean, 3)}</td><td>{pp(reversalEligibleAttribution.beta_volatility.mean, 3)}</td><td>{pp(reversalEligibleAttribution.prior5_contribution_bottom_middle.mean, 3)}</td><td>{pp(reversalEligibleAttribution.volatility_contribution_bottom_middle.mean, 3)}</td></tr>
                  <tr className="featured-row"><th><b>完整現時股池</b></th><td>{reversalCompleteAttribution.prior5_rank_gap_bottom_middle.mean.toFixed(3)}</td><td>{reversalCompleteAttribution.volatility_rank_gap_bottom_middle.mean.toFixed(3)}</td><td>{pp(reversalCompleteAttribution.beta_prior5.mean, 3)}</td><td>{pp(reversalCompleteAttribution.beta_volatility.mean, 3)}</td><td>{pp(reversalCompleteAttribution.prior5_contribution_bottom_middle.mean, 3)}</td><td>{pp(reversalCompleteAttribution.volatility_contribution_bottom_middle.mean, 3)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EIGHT-HYPOTHESIS FAMILY</span><h3>原始與殘差、兩個 universe、兩個差額，一次共同校正</h3></div>
              <p>52-event circular blocks、20,000 條共同路徑及固定 seed；原始顯著不等於殘差 family 通過。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>固定比較</th><th>平均</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半</th><th>後半</th></tr></thead>
                <tbody>{reversalFamilyRows.map((row) => (
                  <tr className={row.id.includes("residual") ? "featured-row" : ""} key={row.id}>
                    <th><b>{row.id.replace("eligible", "合資格池").replace("complete", "完整現時股池").replace("raw", "原始").replace("residual", "殘差").replace("top_middle", "高段－中段").replace("bottom_middle", "低段－中段")}</b><span>{row.events} 個事件</span></th>
                    <td>{pp(row.mean, 3)}</td><td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td><td>{row.holm_adjusted_p.toFixed(4)}</td><td>{row.bootstrap_max_t_p.toFixed(4)}</td><td>{pp(row.fixed_halves.first.mean, 3)}</td><td className={row.fixed_halves.second.mean < 0 ? "negative-number" : ""}>{pp(row.fixed_halves.second.mean, 3)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>KNOWN-AT REGIME &amp; TAIL</span><h3>QQQ 過去 20 日轉弱時殘差為負；尾部移除後亦未通過</h3></div>
              <p>市場環境在訊號日已知；尾部壓力固定移除每個 universe 最大 46 個原始 bottom-middle 絕對差，再測殘差 top-middle。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>固定壓力</th><th>事件</th><th>殘差平均</th><th>NW t</th></tr></thead>
                <tbody>
                  <tr><th><b>合資格池</b></th><td>QQQ 過去 20 日非負</td><td>{reversalRegimes.eligible.qqq_trailing_nonnegative.events}</td><td>{pp(reversalRegimes.eligible.qqq_trailing_nonnegative.mean, 3)}</td><td>{reversalRegimes.eligible.qqq_trailing_nonnegative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr className="featured-row"><th><b>合資格池</b></th><td>QQQ 過去 20 日負</td><td>{reversalRegimes.eligible.qqq_trailing_negative.events}</td><td>{pp(reversalRegimes.eligible.qqq_trailing_negative.mean, 3)}</td><td>{reversalRegimes.eligible.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>合資格池</b></th><td>移除最大 46 個底段差</td><td>{reversalTails.eligible.events}</td><td>{pp(reversalTails.eligible.mean, 3)}</td><td>{reversalTails.eligible.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>完整現時股池</b></th><td>QQQ 過去 20 日非負</td><td>{reversalRegimes.complete.qqq_trailing_nonnegative.events}</td><td>{pp(reversalRegimes.complete.qqq_trailing_nonnegative.mean, 3)}</td><td>{reversalRegimes.complete.qqq_trailing_nonnegative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr className="featured-row"><th><b>完整現時股池</b></th><td>QQQ 過去 20 日負</td><td>{reversalRegimes.complete.qqq_trailing_negative.events}</td><td>{pp(reversalRegimes.complete.qqq_trailing_negative.mean, 3)}</td><td>{reversalRegimes.complete.qqq_trailing_negative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>完整現時股池</b></th><td>移除最大 46 個底段差</td><td>{reversalTails.complete.events}</td><td>{pp(reversalTails.complete.mean, 3)}</td><td>{reversalTails.complete.newey_west.t_stat.toFixed(2)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOURTEEN FALSIFICATION GATES</span><h3>十四項門檻逐項呈列；6/14 不升格</h3></div>
              <p>輸入、coverage、bucket 重播、OLS 身份及原始 top-middle 通過，不能抵銷殘差、bottom-middle、共同校正、弱市及尾部失敗。</p>
            </div>
            <div className="point-in-time-gate-list">
              {reversalVolatilityAttribution.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 28 輪事前固定門檻</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>二十三道輸入、特徵、OLS、歸因、family 及決策控制</h3></div>
              <p>23/23 只證明程式遵守凍結協議，不是策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {reversalControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 28 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>二十三項 hash、窗口、rank、OLS、bucket、bootstrap 及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中指定錯誤碼，包括 reversal_volatility_regression_contract_mismatch 及 reversal_volatility_decision_boundary_breached。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {reversalAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}><div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div><p>{attack.expected_error_code}</p></article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 28 DECISION</span><b>原始高段優勢大部分由共同控制吸收；殘差、弱市、尾部及共同校正均未通過，不建立新策略</b></div>
              <p>正式就緒 1/18、逐股 point-in-time 1/20、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。下一個可升級證據仍是獲授權逐期成分、永久 ID、歷史行業、公司行動及退市／退出經濟，再用未見期作一次固定規則確認。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 28 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_REVERSAL_VOLATILITY_ATTRIBUTION_PROTOCOL.md" target="_blank" rel="noreferrer">事前反轉／波幅協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_reversal_volatility_attribution_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="rank-monotonicity-placebo">
            <div className="section-heading">
              <div><span>RANK MONOTONICITY &amp; PLACEBO · ROUND 27</span><h2>十四項反證只過 5/14；高段勝中段，但底段反彈破壞排序單調性</h2></div>
              <p>固定同一 905 個事件、訊號日 20 日動量、三分組、八假說共同 family 及 20 組隨機排序；沒有改 Top-K、持有期、成本、入場時鐘或事後只展示最有利分段。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>八假說共同 family · {rankMonotonicityPlacebo.gate_summary.passed}/{rankMonotonicityPlacebo.gate_summary.total}</span>
                <h3>eligible 高段對中段 NW t {rankEligibleTopMiddle.newey_west.t_stat.toFixed(2)}，但中段對低段為 {rankEligibleMiddleBottom.newey_west.t_stat.toFixed(2)}</h3>
                <p>高段對中段平均 {pp(rankEligibleTopMiddle.mean, 3)}，可是低段平均回報高於中段，令 top-bottom 只餘 {pp(rankEligibleTopBottom.mean, 3)}、NW t {rankEligibleTopBottom.newey_west.t_stat.toFixed(2)}。這是局部排名線索，不是完整單調 alpha。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>完整現時股池</span><strong>top-bottom NW t {rankCompleteTopBottom.newey_west.t_stat.toFixed(2)}</strong><p>低於最強隨機 placebo {rankCompletePlacebo.maximum_placebo_t_id} · NW t {rankCompletePlacebo.maximum_placebo_t.toFixed(2)}。</p></article>
                <article><span>市場及尾部</span><strong>下跌市 {rankRegimes.eligible.qqq_negative.newey_west.t_stat.toFixed(2)}／{rankRegimes.complete.qqq_negative.newey_west.t_stat.toFixed(2)}</strong><p>移除最大 46 個差額後只有 t {rankTails.eligible.newey_west.t_stat.toFixed(2)}／{rankTails.complete.newey_west.t_stat.toFixed(2)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>原始／共同 905／905；沒有 coverage repair</b>
              <p>這仍是第 24–26 輪已見的同一批事件，不是獨立未見確認。eligible 每事件 7–25 股，complete 每事件固定 25 股；每段互斥、聯集完整且大小最多相差一。股票仍是 2026 現時代號，沒有 point-in-time 成分、永久 ID 或退市／收購經濟，因此本輪只可反證，不可升格。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>原始／共同事件</span><strong>{rankMonotonicityPlacebo.input.events}／{rankMonotonicityPlacebo.input.events}</strong><p>{shortDate(rankMonotonicityPlacebo.input.first_signal_date)} 至 {shortDate(rankMonotonicityPlacebo.input.last_signal_date)}。</p></article>
              <article><span>合資格股數</span><strong>{rankMonotonicityPlacebo.input.eligible_count.minimum}／{rankMonotonicityPlacebo.input.eligible_count.median.toFixed(0)}／{rankMonotonicityPlacebo.input.eligible_count.maximum}</strong><p>每事件最少／中位／最多，全部三分組。</p></article>
              <article><span>eligible top-middle</span><strong>NW t {rankEligibleTopMiddle.newey_west.t_stat.toFixed(2)}</strong><p>Holm p {rankEligibleTopMiddle.holm_adjusted_p.toFixed(4)}；共同 max-t p {rankEligibleTopMiddle.bootstrap_max_t_p.toFixed(4)}。</p></article>
              <article><span>complete top-bottom</span><strong>NW t {rankCompleteTopBottom.newey_west.t_stat.toFixed(2)}</strong><p>後半平均只有 {pp(rankCompleteTopBottom.fixed_halves.second.mean, 3)}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>THREE SLEEVES</span><h3>高、中、低三段的實際 20 日等權回報</h3></div>
              <p>各段均扣除 20 bps round trip；top-bottom 只是診斷差額，沒有冒充可執行沽空組合。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>三分組</th><th>平均 net return</th><th>中位 net return</th></tr></thead>
                <tbody>{rankSleeveRows.map((row) => (
                  <tr key={`${row.universe}-${row.bucket}`}><th><b>{row.universe}</b></th><td>{row.bucket}</td><td>{pct(row.mean_net_return, 2)}</td><td>{pct(row.median_net_return, 2)}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <div className="subsection-heading stock-heading">
              <div><span>EIGHT-HYPOTHESIS FAMILY</span><h3>六個三段差額與兩個 rank IC，一次共同校正</h3></div>
              <p>52-event circular blocks、20,000 條共同路徑及固定 seed；不刪除負面的 middle-bottom 或完整股池列。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>固定比較</th><th>平均</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半</th><th>後半</th></tr></thead>
                <tbody>{rankFamilyRows.map((row) => {
                  const rankIc = row.id.endsWith("rank_ic");
                  const render = (value: number) => rankIc ? value.toFixed(4) : pp(value, 3);
                  return (
                    <tr className={row.id.includes("middle_bottom") ? "featured-row" : ""} key={row.id}>
                      <th><b>{row.id.replace("eligible", "合資格池").replace("complete", "完整現時股池").replace("top_middle", "高段－中段").replace("middle_bottom", "中段－低段").replace("top_bottom", "高段－低段").replace("rank_ic", "rank IC")}</b><span>{row.events} 個事件</span></th>
                      <td className={row.mean < 0 ? "negative-number" : ""}>{render(row.mean)}</td>
                      <td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td>
                      <td>{row.holm_adjusted_p.toFixed(4)}</td><td>{row.bootstrap_max_t_p.toFixed(4)}</td>
                      <td>{render(row.fixed_halves.first.mean)}</td><td className={row.fixed_halves.second.mean < 0 ? "negative-number" : ""}>{render(row.fixed_halves.second.mean)}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>
            <div className="subsection-heading stock-heading">
              <div><span>RANDOM-RANK PLACEBOS</span><h3>每個 universe 20 組固定亂數排序，完整呈列最強比較</h3></div>
              <p>eligible 真實平均及 t 同時高於 placebo 最大值；complete 真實 t {rankCompleteTopBottom.newey_west.t_stat.toFixed(2)} 低於 P14 的 {rankCompletePlacebo.maximum_placebo_t.toFixed(2)}，故跨 universe 門檻失敗。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>真實平均</th><th>真實 NW t</th><th>placebo 最大平均</th><th>最強 t</th><th>同時勝出</th></tr></thead>
                <tbody>
                  <tr><th><b>合資格池</b></th><td>{pp(rankEligiblePlacebo.true_mean, 3)}</td><td>{rankEligiblePlacebo.true_t.toFixed(2)}</td><td>{rankEligiblePlacebo.maximum_placebo_mean_id} · {pp(rankEligiblePlacebo.maximum_placebo_mean, 3)}</td><td>{rankEligiblePlacebo.maximum_placebo_t_id} · {rankEligiblePlacebo.maximum_placebo_t.toFixed(2)}</td><td>是</td></tr>
                  <tr className="featured-row"><th><b>完整現時股池</b></th><td>{pp(rankCompletePlacebo.true_mean, 3)}</td><td>{rankCompletePlacebo.true_t.toFixed(2)}</td><td>{rankCompletePlacebo.maximum_placebo_mean_id} · {pp(rankCompletePlacebo.maximum_placebo_mean, 3)}</td><td>{rankCompletePlacebo.maximum_placebo_t_id} · {rankCompletePlacebo.maximum_placebo_t.toFixed(2)}</td><td className="negative-number">否</td></tr>
                </tbody>
              </table>
            </div>
            <details className="method-details">
              <summary>展開全部 40 組隨機排序 placebo</summary>
              <div className="metric-table-wrap">
                <table className="metric-table compact-table">
                  <thead><tr><th>Universe</th><th>Placebo</th><th>平均 top-bottom</th><th>NW t</th><th>前半</th><th>後半</th></tr></thead>
                  <tbody>{rankPlaceboRows.map((row) => (
                    <tr key={`${row.universe}-${row.id}`}><th><b>{row.universe}</b></th><td>{row.id}</td><td className={row.mean < 0 ? "negative-number" : ""}>{pp(row.mean, 3)}</td><td>{row.newey_west.t_stat.toFixed(2)}</td><td>{pp(row.fixed_halves.first.mean, 3)}</td><td className={row.fixed_halves.second.mean < 0 ? "negative-number" : ""}>{pp(row.fixed_halves.second.mean, 3)}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </details>

            <div className="subsection-heading stock-heading">
              <div><span>REGIME &amp; TAIL FALSIFICATION</span><h3>QQQ 下跌組兩個平均皆負；最大 46 個差額移除後亦未過</h3></div>
              <p>未來 QQQ 方向是事後壓力，不是可知的 regime 訊號；尾部壓力分別移除各 universe 最大的絕對 top-bottom 差額。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Universe</th><th>固定壓力</th><th>事件</th><th>平均 top-bottom</th><th>NW t</th></tr></thead>
                <tbody>
                  <tr><th><b>合資格池</b></th><td>未來 QQQ 非負</td><td>{rankRegimes.eligible.qqq_nonnegative.events}</td><td>{pp(rankRegimes.eligible.qqq_nonnegative.mean, 3)}</td><td>{rankRegimes.eligible.qqq_nonnegative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr className="featured-row"><th><b>合資格池</b></th><td>未來 QQQ 負</td><td>{rankRegimes.eligible.qqq_negative.events}</td><td className="negative-number">{pp(rankRegimes.eligible.qqq_negative.mean, 3)}</td><td className="negative-number">{rankRegimes.eligible.qqq_negative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>合資格池</b></th><td>移除最大 46 個差額</td><td>{rankTails.eligible.events}</td><td>{pp(rankTails.eligible.mean, 3)}</td><td>{rankTails.eligible.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>完整現時股池</b></th><td>未來 QQQ 非負</td><td>{rankRegimes.complete.qqq_nonnegative.events}</td><td>{pp(rankRegimes.complete.qqq_nonnegative.mean, 3)}</td><td>{rankRegimes.complete.qqq_nonnegative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr className="featured-row"><th><b>完整現時股池</b></th><td>未來 QQQ 負</td><td>{rankRegimes.complete.qqq_negative.events}</td><td className="negative-number">{pp(rankRegimes.complete.qqq_negative.mean, 3)}</td><td className="negative-number">{rankRegimes.complete.qqq_negative.newey_west.t_stat.toFixed(2)}</td></tr>
                  <tr><th><b>完整現時股池</b></th><td>移除最大 46 個差額</td><td>{rankTails.complete.events}</td><td>{pp(rankTails.complete.mean, 3)}</td><td>{rankTails.complete.newey_west.t_stat.toFixed(2)}</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOURTEEN FALSIFICATION GATES</span><h3>十四項門檻逐項呈列；5/14 不升格</h3></div>
              <p>重建、覆蓋及高段對中段通過，不可抵銷底段、完整 top-bottom、IC、多重校正、placebo、市況及尾部失敗。</p>
            </div>
            <div className="point-in-time-gate-list">
              {rankMonotonicityPlacebo.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 27 輪事前固定門檻</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>二十三道輸入、排序、bucket、family、placebo 及決策控制</h3></div>
              <p>23/23 只證明程式遵守凍結協議，不是策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {rankControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}><span>{gate.id}</span><div><b>{gate.label}</b><p>第 27 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>二十三項 hash、時鐘、universe、bucket、IC、seed 及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中指定錯誤碼，包括 rank_monotonicity_placebo_contract_mismatch 及 rank_monotonicity_decision_boundary_breached。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {rankAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}><div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div><p>{attack.expected_error_code}</p></article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 27 DECISION</span><b>高段對中段有局部線索，但完整單調性、placebo、下跌市及尾部均未通過；不建立新策略</b></div>
              <p>正式就緒 1/18、逐股 point-in-time 1/20、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。下一個可升級證據仍是獲授權逐期成分、永久 ID、歷史行業、公司行動及退市／退出經濟，而不是改 bucket 或只買事後最有利的 top sleeve。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_RANK_MONOTONICITY_PLACEBO_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 27 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_RANK_MONOTONICITY_PLACEBO_PROTOCOL.md" target="_blank" rel="noreferrer">事前排序／placebo 協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_rank_monotonicity_placebo_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="common-risk-residual">
            <div className="section-heading">
              <div><span>COMMON RISK RESIDUAL · ROUND 26</span><h2>十四項反證只過 6/14；扣除市場 beta 後仍未通過完整股池及共同校正</h2></div>
              <p>固定第二十四輪的 Top-7、合資格池、完整現時 25 股股池、成本與 D+1 執行時鐘；只測試共同風險解釋，沒有調校入場、退出、Top-K 或持有期。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>十假說共同 family · {commonRiskResidual.gate_summary.passed}/{commonRiskResidual.gate_summary.total}</span>
                <h3>QQQ 殘差 eligible NW t {commonRiskQqqEligible.newey_west.t_stat.toFixed(2)}，但 Holm p {commonRiskQqqEligible.holm_adjusted_p.toFixed(4)}、共同 max-t p {commonRiskQqqEligible.bootstrap_max_t_p.toFixed(4)}</h3>
                <p>原始 eligible 差額為 {pp(commonRiskRawEligible.mean_difference, 3)}、NW t {commonRiskRawEligible.newey_west.t_stat.toFixed(2)}；扣除訊號日前 252 日 QQQ beta 後仍有 {pp(commonRiskQqqEligible.mean_difference, 3)}，卻沒有通過同一十假說 family 的兩項校正。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>完整現時股池</span><strong>NW t {commonRiskQqqComplete.newey_west.t_stat.toFixed(2)}</strong><p>QQQ 殘差平均 {pp(commonRiskQqqComplete.mean_difference, 3)}；固定 25 股共同因子殘差只有 t {commonRiskCohortComplete.newey_west.t_stat.toFixed(2)}。</p></article>
                <article><span>市場方向壓力</span><strong>上升 {commonRiskQqqUp.newey_west.t_stat.toFixed(2)}／下跌 {commonRiskQqqDown.newey_west.t_stat.toFixed(2)}</strong><p>按未來 QQQ 回報事後分組，只作反證；下跌組沒有達到固定 1.96。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>父協議先停止；866-event coverage repair 不是獨立首次證據</b>
              <p>父協議先完整重建原始 905 個事件，但 MA 在最早 39 個事件的訊號日前沒有足夠 252 日歷史，首次執行以 common_risk_beta_window_mismatch 停止且沒有產生結果。修復協議只准十列統一使用 2007-06-01 起的 866 個共同事件；它屬同一研究 family 的透明修復，不是新的獨立確認。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>原始 905／共同 866</span><strong>{commonRiskResidual.input.events}／{commonRiskResidual.input.family_common_events}</strong><p>39 個早期事件只因 MA 不足 252 日；原始四條回報仍逐列完全重建。</p></article>
              <article><span>QQQ beta 平均解釋</span><strong>{pct(commonRiskQqqGap.beta_contribution_share_of_raw_mean, 1)}</strong><p>平均 beta 貢獻 {pp(commonRiskQqqGap.mean_beta_contribution, 3)}，不是可交易訊號。</p></article>
              <article><span>QQQ 絕對 beta gap</span><strong>{commonRiskQqqGap.median_absolute_beta_gap.toFixed(3)}／{commonRiskQqqGap.p95_absolute_beta_gap.toFixed(3)}</strong><p>中位／95th，兩者均高於固定 0.10／0.25 門檻。</p></article>
              <article><span>QQQ 下跌組 NW t</span><strong>{commonRiskQqqDown.newey_west.t_stat.toFixed(2)}</strong><p>{commonRiskQqqDown.events} 個事件，平均 {pp(commonRiskQqqDown.mean_difference, 3)}；不能證明逆市穩健。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>TEN-HYPOTHESIS FAMILY</span><h3>五種風險模型 × 兩個公平 baseline，同時呈列共同校正</h3></div>
              <p>全部使用相同 866 個事件、52-event circular blocks、20,000 條共同路徑及固定 seed；不事後挑出 QQQ 252 這一列作唯一結論。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>模型 × baseline</th><th>平均殘差</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半</th><th>後半</th></tr></thead>
                <tbody>{commonRiskFamilyRows.map((row) => (
                  <tr className={row.id === "QQQ_252__eligible" ? "featured-row" : ""} key={row.id}>
                    <th><b>{row.label.replace("complete_cohort", "完整現時股池").replace("eligible", "合資格池")}</b><span>{row.events} 個共同事件</span></th>
                    <td>{pp(row.mean_difference, 3)}</td>
                    <td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td>
                    <td>{row.holm_adjusted_p.toFixed(4)}</td>
                    <td>{row.bootstrap_max_t_p.toFixed(4)}</td>
                    <td>{pp(row.fixed_halves.first.mean_difference, 3)}</td>
                    <td className={row.fixed_halves.second.mean_difference < 0 ? "negative-number" : ""}>{pp(row.fixed_halves.second.mean_difference, 3)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>BETA GAP ATTRIBUTION</span><h3>市場敏感度差距解釋多少原始排名差</h3></div>
              <p>beta 只用訊號收市或以前的 60／252 日數據；factor 未來回報使用與股票相同的 D+1 經調整開市至退出收市時鐘。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>模型 × baseline</th><th>平均 beta gap</th><th>絕對 gap 中位</th><th>絕對 gap 95th</th><th>beta 貢獻</th><th>佔 raw 差額</th></tr></thead>
                <tbody>{commonRiskResidual.beta_gap_summaries.map((row) => (
                  <tr className={row.id === "QQQ_252__eligible" ? "featured-row" : ""} key={row.id}>
                    <th><b>{row.id.replace("complete_cohort", "完整現時股池").replace("eligible", "合資格池")}</b><span>{pct(row.positive_beta_gap_fraction, 1)} beta gap 為正</span></th>
                    <td>{row.mean_beta_gap.toFixed(3)}</td>
                    <td>{row.median_absolute_beta_gap.toFixed(3)}</td>
                    <td>{row.p95_absolute_beta_gap.toFixed(3)}</td>
                    <td>{pp(row.mean_beta_contribution, 3)}</td>
                    <td>{pct(row.beta_contribution_share_of_raw_mean, 1)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>REGIME, TAIL &amp; CURRENT SECTOR CAUTIONS</span><h3>下跌市證據不足；46 個最大 beta 貢獻事件及現時 sector 集中度完整披露</h3></div>
              <p>市場方向使用未來回報，因此不是訊號；sector 是 2026 現時分類，不是逐期分類，只可作單向警示。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>固定壓力</th><th>事件</th><th>平均殘差</th><th>NW t</th><th>判讀</th></tr></thead>
                <tbody>
                  <tr><th><b>未來 QQQ 非負</b><span>事後市場分組</span></th><td>{commonRiskQqqUp.events}</td><td>{pp(commonRiskQqqUp.mean_difference, 3)}</td><td>{commonRiskQqqUp.newey_west.t_stat.toFixed(2)}</td><td>通過單列 t 門檻</td></tr>
                  <tr className="featured-row"><th><b>未來 QQQ 負</b><span>事後市場分組</span></th><td>{commonRiskQqqDown.events}</td><td>{pp(commonRiskQqqDown.mean_difference, 3)}</td><td className="negative-number">{commonRiskQqqDown.newey_west.t_stat.toFixed(2)}</td><td>不通過</td></tr>
                  <tr><th><b>移除最大絕對 beta 貢獻</b><span>移除 {commonRiskTail.removed_events} 個固定事件</span></th><td>{commonRiskTail.events}</td><td>{pp(commonRiskTail.mean_difference, 3)}</td><td>{commonRiskTail.newey_west.t_stat.toFixed(2)}</td><td>移除 {pct(commonRiskTail.removed_absolute_beta_contribution_share, 1)} 絕對貢獻後仍通過</td></tr>
                </tbody>
              </table>
            </div>
            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>2026 現時 sector 標籤 · 非 point-in-time</span>
                <h3>中位有效 sector {commonRiskSector.median_effective_current_sectors.toFixed(2)}；{pct(commonRiskSector.events_with_current_sector_majority_fraction, 1)} 事件有至少四股同 sector</h3>
                <p>單一 sector 最多佔 {commonRiskSector.maximum_current_sector_stocks}/7；這只能警示選股可能重複承擔相同風險，不能用來證明歷史 sector 歸因或建立買入名單。</p>
              </article>
              <div className="aggressive-risk-stack">
                {commonRiskSectorRows.map(({ sector, count }) => (
                  <article key={sector}><span>{sectorLabels[sector] ?? sector}</span><strong>{count.toLocaleString("zh-HK")} slots</strong><p>佔 {pct(count / (commonRiskResidual.input.family_common_events * 7), 1)} 的共同事件持倉格。</p></article>
                ))}
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOURTEEN FALSIFICATION GATES</span><h3>十四項門檻逐項呈列；6/14 不升格</h3></div>
              <p>輸入完整、數學可重建不代表投資命題成立；完整 baseline、共同校正及下跌市壓力均是硬門檻。</p>
            </div>
            <div className="point-in-time-gate-list">
              {commonRiskResidual.gates.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 26 輪事前固定門檻</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>二十一道輸入、覆蓋、beta、baseline、bootstrap 及決策控制</h3></div>
              <p>21/21 只證明程式遵守父協議與 coverage repair，並非策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {commonRiskControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 26 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>二十一項 hash、共同樣本、factor、beta、baseline 及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中事前指定錯誤碼，包括 common_risk_decision_boundary_breached 與 common_risk_coverage_repair_mismatch。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {commonRiskAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 26 DECISION</span><b>部分 raw 排名差不能完全由市場 beta 解釋，但完整股池、共同校正及下跌市證據未通過；不建立新策略</b></div>
              <p>本輪只把「可能全是高 beta」收窄為「不是全部，但仍不夠穩健」；正式就緒 1/18、逐股 point-in-time 1/20、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。下一個正式步驟仍是已授權逐期成分、退市／收購與逐列 known-at 數據，而不是再挑一個更有利的 beta 規格。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_COMMON_RISK_RESIDUAL_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 26 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_COMMON_RISK_RESIDUAL_PROTOCOL.md" target="_blank" rel="noreferrer">事前共同風險協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_COMMON_RISK_RESIDUAL_COVERAGE_REPAIR_PROTOCOL.md" target="_blank" rel="noreferrer">866-event 覆蓋修復協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_common_risk_residual_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="correlation-crowding">
            <div className="section-heading">
              <div><span>CORRELATION CROWDING · ROUND 25</span><h2>十二項反證只過 7/12；名義 Top-7 的中位有效獨立注數只有 {crowdingEffective.median.toFixed(2)}</h2></div>
              <p>固定第二十四輪的 905 個 20 日 Top-7 事件，只檢查 60 日相關性、有效獨立注數、現時代號歸因、剔除壓力及 cap 2；沒有調 Top-K、持有期、成本或入場規則。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>事前反證結果 · {correlationCrowding.gate_summary.passed}/{correlationCrowding.gate_summary.total}</span>
                <h3>{pct(crowdingEffective.fraction_below_3, 1)} 的事件少於三注獨立風險；{pct(crowdingHighPairs.events_with_any_fraction, 1)} 至少有一對高相關</h3>
                <p>七股共有 21 對；中位最高 pairwise correlation 為 {crowdingMaxPair.median.toFixed(3)}，中位有效獨立注數只有 {crowdingEffective.median.toFixed(2)}。名義持有七個代號不等於有七個獨立風險來源。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>剔除事後前三貢獻股</span><strong>NW t {crowdingRemoveThree.newey_west.t_stat.toFixed(2)}</strong><p>MU、AMD、MA 剔除後平均 {pp(crowdingRemoveThree.mean_difference, 3)}；Holm／max-t p {crowdingRemoveThree.holm_adjusted_p.toFixed(3)}／{crowdingRemoveThree.bootstrap_max_t_p.toFixed(3)}。</p></article>
                <article><span>相關 cap 2</span><strong>{crowdingMeanPair.mean.toFixed(3)} → {crowdingCap.crowding_change.mean_pairwise_correlation_after.toFixed(3)}</strong><p>只減少 {crowdingCap.crowding_change.mean_pairwise_correlation_reduction.toFixed(3)}，遠低於固定 0.05 門檻；中位有效獨立注數仍約 {crowdingCap.crowding_change.median_effective_bets_after.toFixed(2)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>父協議先停止；matched-cash repair 不是獨立首次證據</b>
              <p>父協議因刪除壓力後不足七隻合資格股份而以 crowding_baseline_fairness_breached 停止、沒有輸出。事前 repair 只容許不足七股的測試把空缺留作零回報現金，候選和 baseline 維持同一 K／7 持倉比率與成本；這是同一研究 family 的透明修復，不是新一輪獨立確認。</p>
            </div>

            <div className="evidence-stat-grid">
              <article><span>名義／有效注數</span><strong>7／{crowdingEffective.median.toFixed(2)}</strong><p>平均 {crowdingEffective.mean.toFixed(2)}；第 5–95 百分位 {crowdingEffective.p05.toFixed(2)}–{crowdingEffective.p75.toFixed(2)}+。</p></article>
              <article><span>任何高相關 pair</span><strong>{pct(crowdingHighPairs.events_with_any_fraction, 1)}</strong><p>門檻為 60 日相關度嚴格高於 0.70。</p></article>
              <article><span>最高單一代號 slot share</span><strong>{pct(correlationCrowding.symbol_selection_concentration.maximum_single_symbol_slot_share, 2)}</strong><p>前三合計 {pct(correlationCrowding.symbol_selection_concentration.top3_symbol_slot_share, 2)}；選中次數並不集中。</p></article>
              <article><span>cap 2 平均持倉</span><strong>{crowdingCap.accepted_count.mean.toFixed(2)}／7</strong><p>平均股票持倉比率 {pct(crowdingCap.accepted_count.mean_equity_exposure, 1)}；完整七股事件 {pct(crowdingCap.accepted_count.full_top7_fraction, 1)}。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FOUR-HYPOTHESIS FAMILY</span><h3>原始、剔除一股、剔除三股及相關 cap 2 同時校正</h3></div>
              <p>四列共用 20,000 條 52-event circular block 路徑及同一 seed；前後半均固定，不可事後選最有利壓力。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>固定比較</th><th>平均差</th><th>NW t</th><th>Holm p</th><th>Max-t p</th><th>前半</th><th>後半</th></tr></thead>
                <tbody>{crowdingFamilyRows.map((row) => (
                  <tr className={row.id === "remove_top3_contributors" ? "featured-row" : ""} key={row.id}>
                    <th><b>{row.label}</b><span>{row.events} 個共同事件</span></th>
                    <td>{pp(row.mean_difference, 3)}</td>
                    <td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td>
                    <td className={row.holm_adjusted_p > 0.05 ? "negative-number" : ""}>{row.holm_adjusted_p.toFixed(4)}</td>
                    <td className={row.bootstrap_max_t_p > 0.05 ? "negative-number" : ""}>{row.bootstrap_max_t_p.toFixed(4)}</td>
                    <td>{pp(row.fixed_halves.first.mean_difference, 3)}</td>
                    <td>{pp(row.fixed_halves.second.mean_difference, 3)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CORRELATION CAP 2</span><h3>回報比較仍正，但幾乎沒有降低擠擁</h3></div>
              <p>只從原 Top-7 依排名逐隻接受，不回補；每隻仍佔 1/7，拒收部分留現金，matched eligible 與 QQQ 採同一實際股票持倉比率。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>cap 2 檢查</th><th>平均差／數值</th><th>NW t</th><th>持倉／前半</th><th>完整七股／後半</th></tr></thead>
                <tbody>
                  <tr><th><b>對 matched eligible</b><span>相同 K／7 持倉比率及成本</span></th><td>{pp(crowdingCap.vs_matched_eligible.mean_difference, 3)}</td><td>{crowdingCap.vs_matched_eligible.newey_west.t_stat.toFixed(2)}</td><td>{pp(crowdingCap.vs_matched_eligible.fixed_halves.first.mean_difference, 3)}</td><td>{pp(crowdingCap.vs_matched_eligible.fixed_halves.second.mean_difference, 3)}</td></tr>
                  <tr><th><b>對 matched QQQ</b><span>相同 K／7 QQQ 機會成本</span></th><td>{pp(crowdingCap.vs_matched_qqq.mean_difference, 3)}</td><td>{crowdingCap.vs_matched_qqq.newey_west.t_stat.toFixed(2)}</td><td>{pp(crowdingCap.vs_matched_qqq.fixed_halves.first.mean_difference, 3)}</td><td>{pp(crowdingCap.vs_matched_qqq.fixed_halves.second.mean_difference, 3)}</td></tr>
                  <tr className="featured-row"><th><b>擠擁改變</b><span>不是收益最佳化</span></th><td>{crowdingMeanPair.mean.toFixed(3)} → {crowdingCap.crowding_change.mean_pairwise_correlation_after.toFixed(3)}</td><td className="negative-number">只減 {crowdingCap.crowding_change.mean_pairwise_correlation_reduction.toFixed(3)}</td><td>平均 {crowdingCap.accepted_count.mean.toFixed(2)} 股／{pct(crowdingCap.accepted_count.mean_equity_exposure, 1)}</td><td>{pct(crowdingCap.accepted_count.full_top7_fraction, 1)}／最少 {crowdingCap.accepted_count.minimum} 股</td></tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EX-POST SYMBOL ATTRIBUTION</span><h3>25 個現時代號全部呈列；MU、AMD、MA 不是買入名單</h3></div>
              <p>代號只按 2026 現時 ticker 回填，沒有永久證券 ID，亦未修復退市／歷史成分偏差。貢獻排名和 leave-one 結果都是事後診斷，不可外推成下一期推薦。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>現時代號</th><th>選中次數</th><th>slot share</th><th>平均淨貢獻</th><th>淨貢獻佔比</th><th>剔除後平均差</th><th>剔除後 NW t</th></tr></thead>
                <tbody>{crowdingContributors.map((row) => {
                  const leaveOne = crowdingLeaveOne.find((item) => item.symbol === row.symbol)!;
                  return (
                    <tr className={row.net_contribution_rank <= 3 ? "featured-row" : ""} key={row.symbol}>
                      <th><b>{row.symbol}</b><span>事後淨貢獻第 {row.net_contribution_rank}</span></th>
                      <td>{row.selection_count}</td>
                      <td>{pct(row.selection_slot_share, 2)}</td>
                      <td>{pp(row.active_contribution_to_mean, 3)}</td>
                      <td>{pct(row.share_of_net_active_sum, 1)}</td>
                      <td>{pp(leaveOne.mean_difference, 3)}</td>
                      <td>{leaveOne.newey_west.t_stat.toFixed(2)}</td>
                    </tr>
                  );
                })}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRE-FROZEN FALSIFICATION GATES</span><h3>十二項門檻逐項呈列；7/12 不升格</h3></div>
              <p>有效注數兩項、剔除前三貢獻股、相關度減幅及 family correction 五項失敗；不能以原始回報仍正掩蓋。</p>
            </div>
            <div className="point-in-time-gate-list">
              {correlationCrowding.gates.map((gate, index) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{String(index + 1).padStart(2, "0")}</span><div><b>{gate.label}</b><p>第 25 輪固定反證</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>十九道輸入、相關、代號、matched-cash、bootstrap 及決策控制</h3></div>
              <p>19/19 只證明程式遵守事前協議及修復協議，並非策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {crowdingControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 25 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>十九項 hash、時鐘、相關、代號、baseline 及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中事前指定錯誤碼，包括 crowding_decision_boundary_breached。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {crowdingAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 25 DECISION</span><b>原始排名差仍正，但組合實際擠擁且前三事後貢獻股剔除壓力未通過；不建立新策略</b></div>
              <p>原 Top-7 平均差 {pp(crowdingOriginal.mean_difference, 3)}、NW t {crowdingOriginal.newey_west.t_stat.toFixed(2)}；只剔除 MU 仍有 {pp(crowdingRemoveOne.mean_difference, 3)}、NW t {crowdingRemoveOne.newey_west.t_stat.toFixed(2)}，但同時剔除 MU、AMD、MA 後證據失效。正式就緒 1/18、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CORRELATION_CROWDING_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 25 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CORRELATION_CROWDING_PROTOCOL.md" target="_blank" rel="noreferrer">事前相關擠擁協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_CORRELATION_CROWDING_SCHEMA_REPAIR_PROTOCOL.md" target="_blank" rel="noreferrer">matched-cash 修復協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_correlation_crowding_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="baseline-multiplicity">
            <div className="section-heading">
              <div><span>FAIR BASELINES &amp; MULTIPLICITY · ROUND 24</span><h2>九項反證只過 6/9；正面排名未通過完整股池及全專案搜尋壓力</h2></div>
              <p>固定 5／10／20 日、三個同成本 baseline 及 905 個共同事件；Holm、共同 max-t、Romano–Wolf、Reality Check 與 6,208 次 Bonferroni 全部呈列。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>20 日主要期限 · 九假說 family</span>
                <h3>對合資格池 NW t {multiplicityEligible.newey_west.t_stat.toFixed(2)}；對完整股池只有 {multiplicityComplete.newey_west.t_stat.toFixed(2)}</h3>
                <p>主要 Holm p {multiplicityEligible.holm_adjusted_p.toFixed(4)}、共同 max-t p {multiplicityEligible.bootstrap_max_t_p.toFixed(4)}、Reality Check p {multiplicityBootstrap.reality_check_p_value.toFixed(4)}；family 內仍有訊號，但完整現時股池和 6,208 次搜尋校正未通過。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>完整現時股池 baseline</span><strong>NW t {multiplicityComplete.newey_west.t_stat.toFixed(2)}</strong><p>平均差 {pp(multiplicityComplete.mean_difference, 3)}，低於固定 1.96；完整股池本身仍有存活者偏差。</p></article>
                <article><span>全專案搜尋壓力</span><strong>p {multiplicityEligible.global_bonferroni_p.toFixed(2)}</strong><p>普通 p 必須低於 {baselineMultiplicity.global_unadjusted_p_threshold.toFixed(8)}；本輪不把 6,208 重設成 9 或 1。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>公平分母不是任選一個</b>
              <p>合資格池回答 Top-7 是否勝過已通過趨勢與流動性濾網的股票；完整現時股池回答排名加濾網後能否勝過更廣分母；QQQ 顯示機會成本。三者缺一不可，而且全部仍未修復退市及歷史成分偏差。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>20-DAY ATTRIBUTION</span><h3>排名效果為正，但合資格濾網本身拖低完整股池比較</h3></div>
              <p>逐事件恆等式嚴格成立；不把合資格池視為唯一可接受 baseline。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>20 日歸因</th><th>定義</th><th>平均差</th><th>NW t</th><th>前半</th><th>後半</th></tr></thead>
                <tbody>{[
                  { label: "Top-7 排名效果", row: baselineMultiplicity.primary_attribution.ranking_effect },
                  { label: "合資格濾網效果", row: baselineMultiplicity.primary_attribution.eligibility_effect },
                  { label: "對完整股池合計", row: baselineMultiplicity.primary_attribution.combined_effect },
                ].map(({ label, row }) => (
                  <tr className={row.mean_difference < 0 ? "featured-row" : ""} key={label}>
                    <th><b>{label}</b><span>固定 905 事件</span></th>
                    <td>{row.definition}</td>
                    <td className={row.mean_difference < 0 ? "negative-number" : ""}>{pp(row.mean_difference, 3)}</td>
                    <td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td>
                    <td>{pp(row.fixed_halves.first.mean_difference, 3)}</td>
                    <td>{pp(row.fixed_halves.second.mean_difference, 3)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>NINE PAIRED HYPOTHESES</span><h3>三個期限 × 三個 baseline，不只展示最漂亮一格</h3></div>
              <p>普通 p 來自固定 NW t；Holm、共同 max-t、Romano–Wolf 及全專案搜尋壓力使用同一 0.05 門檻。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>期限／baseline</th><th>平均差</th><th>NW t</th><th>普通 p</th><th>Holm</th><th>Max-t</th><th>RW step-down</th><th>6,208×</th></tr></thead>
                <tbody>{baselineMultiplicity.comparisons.map((row) => (
                  <tr className={row.horizon === 20 && row.baseline_key === "eligible_equal_return" ? "featured-row" : ""} key={row.id}>
                    <th><b>{row.horizon} 日 · {row.baseline_label}</b><span>{row.events} 個共同事件</span></th>
                    <td>{pp(row.mean_difference, 3)}</td>
                    <td className={row.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west.t_stat.toFixed(2)}</td>
                    <td>{row.raw_normal_p.toFixed(4)}</td>
                    <td className={row.holm_adjusted_p > 0.05 ? "negative-number" : ""}>{row.holm_adjusted_p.toFixed(4)}</td>
                    <td className={row.bootstrap_max_t_p > 0.05 ? "negative-number" : ""}>{row.bootstrap_max_t_p.toFixed(4)}</td>
                    <td className={row.romano_wolf_stepdown_p > 0.05 ? "negative-number" : ""}>{row.romano_wolf_stepdown_p.toFixed(4)}</td>
                    <td className="negative-number">{row.global_bonferroni_p.toFixed(2)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>COMMON BLOCK BOOTSTRAP</span><h3>九列共用 20,000 條 52-event circular 路徑</h3></div>
              <p>各列在零假設下去中心化，同日跨期限及 baseline 關係保留，不逐格重抽較有利亂數。</p>
            </div>
            <div className="evidence-stat-grid">
              <article><span>Reality Check p</span><strong>{multiplicityBootstrap.reality_check_p_value.toFixed(4)}</strong><p>觀察最大正 t {multiplicityBootstrap.observed_max_positive_t.toFixed(2)}。</p></article>
              <article><span>主要 max-t p</span><strong>{multiplicityEligible.bootstrap_max_t_p.toFixed(4)}</strong><p>九假說 single-step family-wise。</p></article>
              <article><span>主要 RW p</span><strong>{multiplicityEligible.romano_wolf_stepdown_p.toFixed(4)}</strong><p>固定兩尾 step-down。</p></article>
              <article><span>全專案通過界線</span><strong>{baselineMultiplicity.global_unadjusted_p_threshold.toFixed(8)}</strong><p>0.05／6,208，不冒充正式 DSR。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRE-FROZEN FALSIFICATION GATES</span><h3>九項門檻逐項呈列；6/9 不升格</h3></div>
              <p>完整股池、全專案搜尋及三期限共同 max-t 三項失敗，不能用其餘六項掩蓋。</p>
            </div>
            <div className="point-in-time-gate-list">
              {baselineMultiplicity.gates.map((gate, index) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{String(index + 1).padStart(2, "0")}</span><div><b>{gate.label}</b><p>第 24 輪固定反證</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>十六道輸入、共同樣本、family、bootstrap 及決策控制</h3></div>
              <p>16/16 只證明程式遵守事前協議，並非策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {multiplicityControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 24 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>十六項期限、baseline、family、路徑及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中事前指定錯誤碼。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {multiplicityAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 24 DECISION</span><b>family 內的 20 日排名線索保留；公平分母及全專案搜尋偏誤仍拒絕升格</b></div>
              <p>20 日對 QQQ 的事件差 {pp(multiplicityQqq.mean_difference, 3)}、NW t {multiplicityQqq.newey_west.t_stat.toFixed(2)}，但 QQQ 的 Holm p {multiplicityQqq.holm_adjusted_p.toFixed(4)} 亦略高於 0.05。正式 1/18、正式策略 run 0、Paper 全現金、持倉 0、實金 US$0。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_BASELINE_MULTIPLICITY_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 24 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_BASELINE_MULTIPLICITY_PROTOCOL.md" target="_blank" rel="noreferrer">事前多重檢驗協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_baseline_multiplicity_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="temporal-tail-robustness">
            <div className="section-heading">
              <div><span>TEMPORAL &amp; TAIL ROBUSTNESS · ROUND 23</span><h2>八項反證只過 7/8；最佳三年移除後統計門檻失效</h2></div>
              <p>只分析凍結的 905 個 20 日配對事件，不調 Top-K、持有期、成本或 baseline。年度聚類、52-event 區塊重抽、最佳年份刪除及對稱 winsor 全部在計算前固定。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>事前反證結果 · {temporalTailRobustness.gate_summary.passed}/{temporalTailRobustness.gate_summary.total}</span>
                <h3>原始平均 {pp(temporalTailRobustness.observed.mean_active_difference, 3)}；曆年 cluster t {temporalCluster.t_stat.toFixed(2)}</h3>
                <p>52-event circular block bootstrap 的 95% 區間為 {pp(temporalBootstrap.mean_difference_quantiles.p025, 3)} 至 {pp(temporalBootstrap.mean_difference_quantiles.p975, 3)}，正平均路徑 {pct(temporalBootstrap.positive_mean_fraction, 1)}。這只描述現時 survivor cohort，不是退市修正後區間。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>刪除最佳三年</span><strong>NW t {temporalRemoveThree.newey_west_lag4.t_stat.toFixed(2)}</strong><p>{temporalRemoveThree.removed_years.join("、")} 移除後平均 {pp(temporalRemoveThree.mean_difference, 3)}，低於固定 1.96 門檻。</p></article>
                <article><span>刪除最大 5% 正事件</span><strong>{pp(temporalTailFortySix.mean_difference, 3)}</strong><p>46 列佔全部正配對差 {pct(temporalTailFortySix.share_of_positive_sum, 1)}；移除後 NW t {temporalTailFortySix.newey_west_lag4.t_stat.toFixed(2)}。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>判讀邊界</b>
              <p>7/8 是負結果，不可四捨五入成通過。現有事件沒有歷史永久 ID 或行業身份，故本輪沒有假裝做逐股集中度；正式 point-in-time／退市逐股回測仍是 0 次。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>DEPENDENCE FRONTIER</span><h3>四個 Newey–West lag 與 21 個曆年 cluster</h3></div>
              <p>lag 4 約涵蓋一個重疊持有期；13、26、52 全部呈列，不能事後挑選。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>統計</th><th>事件／cluster</th><th>平均差</th><th>標準誤</th><th>t 值</th><th>固定門檻</th></tr></thead>
                <tbody>
                  {temporalTailRobustness.hac_frontier.map((row) => (
                    <tr key={row.lag}>
                      <th><b>NW lag {row.lag}</b><span>每週重疊事件</span></th>
                      <td>{temporalTailRobustness.input.events}</td>
                      <td>{pp(row.mean_difference, 3)}</td>
                      <td>{pp(row.standard_error, 3)}</td>
                      <td>{row.t_stat.toFixed(2)}</td>
                      <td>完整呈列</td>
                    </tr>
                  ))}
                  <tr className="featured-row">
                    <th><b>曆年 cluster</b><span>有限樣本修正</span></th>
                    <td>{temporalCluster.clusters}</td>
                    <td>{pp(temporalCluster.mean_difference, 3)}</td>
                    <td>{pp(temporalCluster.standard_error, 3)}</td>
                    <td>{temporalCluster.t_stat.toFixed(2)}</td>
                    <td>t(20) ≥ {temporalCluster.two_sided_5pct_critical.toFixed(6)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED MARKET EPOCHS</span><h3>五個市場時段平均全正，但各段證據強度有限</h3></div>
              <p>時段在結果前固定；不合併較弱年份，也不以近期高回報取代全期。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>固定時段</th><th>事件</th><th>平均差</th><th>中位差</th><th>正配對</th><th>NW4 t</th></tr></thead>
                <tbody>{temporalTailRobustness.epochs.map((row) => (
                  <tr key={row.id}>
                    <th><b>{row.label}</b><span>{row.start} 至 {row.end}</span></th>
                    <td>{row.events}</td>
                    <td>{pp(row.mean_difference, 3)}</td>
                    <td>{pp(row.median_difference, 3)}</td>
                    <td>{pct(row.positive_fraction, 1)}</td>
                    <td>{row.newey_west_lag4.t_stat.toFixed(2)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>CALENDAR-YEAR CONCENTRATION</span><h3>{temporalTailRobustness.positive_calendar_years}/21 年平均為正；2025–2026 貢獻偏高</h3></div>
              <p>淨差貢獻可為負或超過普通比例；它量化每年對全期配對差總和的影響。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>年份</th><th>事件</th><th>平均差</th><th>中位差</th><th>正配對</th><th>淨差貢獻</th></tr></thead>
                <tbody>{temporalTailRobustness.calendar_years.map((row) => (
                  <tr className={row.year >= 2025 ? "featured-row" : ""} key={row.year}>
                    <th><b>{row.year}</b><span>曆年 cluster</span></th>
                    <td>{row.events}</td>
                    <td className={row.mean_difference < 0 ? "negative-number" : ""}>{pp(row.mean_difference, 3)}</td>
                    <td>{pp(row.median_difference, 3)}</td>
                    <td>{pct(row.positive_fraction, 1)}</td>
                    <td>{pct(row.share_of_net_sum, 1)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>INFLUENCE &amp; TAIL TESTS</span><h3>刪除最佳年份及最大正事件，集中度完整披露</h3></div>
              <p>這些是反證壓力，不是建議正式策略排除真實贏家。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>壓力</th><th>移除</th><th>剩餘平均差</th><th>NW4 t</th><th>年度 cluster t</th><th>判讀</th></tr></thead>
                <tbody>
                  {[temporalRemoveOne, temporalRemoveThree].map((row) => (
                    <tr className={row.removed_count === 3 ? "featured-row" : ""} key={`year-${row.removed_count}`}>
                      <th><b>最佳年份</b><span>按原始 sum(D) 排序一次</span></th>
                      <td>{row.removed_years.join("、")}</td>
                      <td>{pp(row.mean_difference, 3)}</td>
                      <td className={row.newey_west_lag4.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west_lag4.t_stat.toFixed(2)}</td>
                      <td>{row.calendar_cluster.t_stat.toFixed(2)}</td>
                      <td>{row.newey_west_lag4.t_stat >= 1.96 ? "未跌穿" : "門檻失效"}</td>
                    </tr>
                  ))}
                  {[temporalTailTen, temporalTailFortySix].map((row) => (
                    <tr key={`tail-${row.removed_count}`}>
                      <th><b>最大正事件</b><span>固定 deterministic 排序</span></th>
                      <td>{row.removed_count} 列</td>
                      <td>{pp(row.mean_difference, 3)}</td>
                      <td className={row.newey_west_lag4.t_stat < 1.96 ? "negative-number" : ""}>{row.newey_west_lag4.t_stat.toFixed(2)}</td>
                      <td>{row.calendar_cluster.t_stat.toFixed(2)}</td>
                      <td>佔正差 {pct(row.share_of_positive_sum, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>SYMMETRIC WINSOR</span><h3>1% 與 5% 對稱截尾均保留，沒有只剪負尾</h3></div>
              <p>線性分位數及四個 HAC lag 均在協議中固定。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>Winsor</th><th>上下界</th><th>平均差</th><th>NW4</th><th>NW13</th><th>NW26</th><th>NW52</th></tr></thead>
                <tbody>{temporalTailRobustness.winsorized.map((row) => (
                  <tr key={row.lower_quantile}>
                    <th><b>{pct(row.lower_quantile, 0)}／{pct(row.upper_quantile, 0)}</b><span>對稱截尾</span></th>
                    <td>{pp(row.lower_bound, 2)} 至 {pp(row.upper_bound, 2)}</td>
                    <td>{pp(row.mean_difference, 3)}</td>
                    {row.hac_frontier.map((hac) => <td key={hac.lag}>{hac.t_stat.toFixed(2)}</td>)}
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRE-FROZEN FALSIFICATION GATES</span><h3>八項門檻逐項呈列；7/8 不升格</h3></div>
              <p>唯一失敗是刪除最佳三年後 NW t 低於 1.96；差距再小也不改門檻。</p>
            </div>
            <div className="point-in-time-gate-list">
              {temporalTailRobustness.gates.map((gate, index) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{String(index + 1).padStart(2, "0")}</span><div><b>{gate.label}</b><p>第 23 輪固定反證</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>十五道輸入、時間、尾部、重抽及決策邊界控制</h3></div>
              <p>15/15 只證明輸出遵守事前協議，並非策略可投資。</p>
            </div>
            <div className="point-in-time-gate-list">
              {temporalControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 23 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>十五項路徑、時間、尾部、bootstrap 及越權偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中事前指定錯誤碼。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {temporalAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>ROUND 23 DECISION</span><b>保留值得以合法數據原樣重測的假說；不把 7/8 寫成成功</b></div>
              <p>sign test 為正 {temporalTailRobustness.sign_test.positive}、負 {temporalTailRobustness.sign_test.negative}、零 {temporalTailRobustness.sign_test.zero}，雙尾 p={temporalTailRobustness.sign_test.two_sided_exact_p_value.toFixed(4)}；但幅度及年度集中度仍令一項主要門檻失敗。正式 1/18、Paper 全現金、持倉 0、實金 US$0。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 23 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_TEMPORAL_TAIL_ROBUSTNESS_PROTOCOL.md" target="_blank" rel="noreferrer">事前反證協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_temporal_tail_robustness_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="survivorship-contamination">
            <div className="section-heading">
              <div><span>SURVIVORSHIP CONTAMINATION · ROUND 22</span><h2>主要合成格 5/5；嚴重退出令統計證據先於平均值消失</h2></div>
              <p>只壓測已凍結的 20 日 Top-7 訊號，不搜尋新參數。候選與同日合資格池 baseline 同時加入同一缺失股份；合成結果只可否決，不能升格。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>固定主要格 · -50% 退出／2% 污染</span>
                <h3>配對差仍為 {pp(survivorshipPrimary.expected.mean_difference, 3)}，NW t {survivorshipPrimary.expected.newey_west.t_stat.toFixed(2)}</h3>
                <p>觀察配對差是 {pp(survivorshipStress.observed_signal.mean_active_difference, 3)}；2,000 條固定亂數路徑的平均差 95% 區間為 {pp(survivorshipPrimary.monte_carlo.mean_difference_quantiles.p025, 3)} 至 {pp(survivorshipPrimary.monte_carlo.mean_difference_quantiles.p975, 3)}。5/5 只表示這個特定合成格未推翻訊號。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>-80%／2%</span><strong>NW t {survivorshipSevere80.expected.newey_west.t_stat.toFixed(2)}</strong><p>平均差 {pp(survivorshipSevere80.expected.mean_difference, 3)}，但統計門檻已失敗。</p></article>
                <article><span>-100%／2%</span><strong>NW t {survivorshipSevere100.expected.newey_west.t_stat.toFixed(2)}</strong><p>平均差 {pp(survivorshipSevere100.expected.mean_difference, 3)}；不能只看平均仍為正。</p></article>
              </div>
            </div>

            <div className="comparison-caveat">
              <b>模型邊界</b>
              <p>這不是對真實退市率的估計，亦沒有合成被漏股份的完整事前動量。每個受污染事件只加入一隻本來會入選的失敗股份；Top-7 以 1/7 承受，合資格池以 1/(N+1) 承受。正式 point-in-time／退市回測仍是 0 次。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FULL FIXED GRID</span><h3>四種退出回報 × 五種污染率，20 格全部呈列</h3></div>
              <p>重疊 20 日事件的配對差不是可複利 CAGR；MC 區間只反映污染位置，不是未來市場回報區間。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>退出回報</th><th>污染率</th><th>期望配對差</th><th>NW t</th><th>MC 95% 區間</th><th>正平均路徑</th><th>前後十年同正</th></tr></thead>
                <tbody>{survivorshipStress.stress_grid.map((row) => (
                  <tr className={row.exit_return === -0.5 && row.contamination_rate === 0.02 ? "featured-row" : ""} key={`${row.exit_return}-${row.contamination_rate}`}>
                    <th><b>{pct(row.exit_return, 0)}</b><span>缺失入選股份</span></th>
                    <td>{pct(row.contamination_rate, 1)}</td>
                    <td>{pp(row.expected.mean_difference, 3)}</td>
                    <td className={row.expected.newey_west.t_stat < 1.96 ? "negative-number" : ""}>{row.expected.newey_west.t_stat.toFixed(2)}</td>
                    <td>{pp(row.monte_carlo.mean_difference_quantiles.p025, 3)} 至 {pp(row.monte_carlo.mean_difference_quantiles.p975, 3)}</td>
                    <td>{pct(row.monte_carlo.positive_mean_fraction, 1)}</td>
                    <td>{pct(row.monte_carlo.both_halves_positive_fraction, 1)}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>BREAK-EVEN BOUNDARY</span><h3>統計證據比平均差更早失效</h3></div>
              <p>固定 0.01 個百分點污染率網格；不按結果做連續調校。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table compact-table">
                <thead><tr><th>退出回報</th><th>平均差降至零</th><th>NW t 跌穿 1.96</th><th>判讀</th></tr></thead>
                <tbody>{survivorshipBreakEvenRows.map((row) => (
                  <tr key={row.exit_return}>
                    <th><b>{pct(row.exit_return, 0)}</b><span>每個受污染事件一隻</span></th>
                    <td>{pct(row.mean_zero_contamination_rate, 2)}</td>
                    <td>{pct(row.newey_west_below_1_96_contamination_rate, 2)}</td>
                    <td>先失去統計確認，再失去正平均差</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PRE-FROZEN SURVIVAL GATES</span><h3>主要格五項門檻逐項呈列</h3></div>
              <p>通過不能提升正式就緒；失敗則必須保留為反證。</p>
            </div>
            <div className="point-in-time-gate-list">
              {survivorshipStress.primary_gates.map((gate, index) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{String(index + 1).padStart(2, "0")}</span><div><b>{gate.label}</b><p>固定 -50%／2% 主要合成格</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>PROTOCOL CONTROLS</span><h3>十二道輸入、格網、亂數、公平基準及統計控制</h3></div>
              <p>12/12 只證明程式遵守事前協議，並非策略盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {survivorshipControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>第 22 輪固定控制</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>MUTATION ATTACKS</span><h3>十二項期限、Top-K、壓力格、亂數及 baseline 偷換全拒收</h3></div>
              <p>每項只改一個契約欄位並命中指定錯誤碼。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {survivorshipAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>SCHEMA REPAIR &amp; DECISION</span><b>最後訊號日手寫錯誤在計算前 fail closed；repair 先提交，結果後才產生</b></div>
              <p>實際 905 個固定事件為 {survivorshipStress.observed_signal.first_signal_date} 至 {survivorshipStress.observed_signal.last_signal_date}。repair 只改為由已綁定 SHA 的事件列讀取日期；20 日、Top-7、20 格、統計及門檻全部不變。正式 1/18、Paper 全現金、持倉 0、實金 US$0。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_RESEARCH_REPORT.md" target="_blank" rel="noreferrer">第 22 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_PROTOCOL.md" target="_blank" rel="noreferrer">事前壓力協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_SURVIVORSHIP_CONTAMINATION_SCHEMA_REPAIR_PROTOCOL.md" target="_blank" rel="noreferrer">日期 repair 附錄</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_survivorship_contamination_validation.json" target="_blank" rel="noreferrer">機器收據</a>
              </div>
            </div>
          </section>

          <section className="section wrap" id="provider-gap-closure">
            <div className="section-heading">
              <div><span>PROVIDER GAP CLOSURE · ROUND 21</span><h2>五條路徑逐項對齊 14 項正式能力；0/5 合格</h2></div>
              <p>只採用供應商或數據擁有者的一手頁面、指南及 API 文件。公開產品說明最高只可成為採購候選，不等於已訂閱、已授權、已交付或可開始回測。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict provider-verdict">
                <span>最新研究判斷</span>
                <h3>CRSP＋S&amp;P DJI 最接近完整；LSEG 是最完整的單一品牌候選</h3>
                <p>前者有成分生效、永久 ID、raw 日線、分派及退市字典，亦有 S&amp;P DJI 公布政策，但仍欠逐列 AnnouncedAt、Metadata KnownAt、缺失退出實收、移除後價格路徑及精確一個月日度 RF。LSEG 的 PIT、歷史成分、永久 ID 及已退市公司覆蓋較完整，但「有已退市公司」不等於每次退出的經濟回報齊備。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>最佳公開文件路徑</span><strong>{providerGapBest.explicit_count} 明確 · {providerGapBest.partial_count} 部分</strong><p>{providerGapBest.hard_gap_count}/14 仍不是明確能力；完整合格 0。</p></article>
                <article><span>真實決策</span><strong>1/18 · strategy run 0</strong><p>provider package 0、完整 RF 0、Paper 全現金、實金 US$0。</p></article>
              </div>
            </div>

            <div className="provider-grid provider-gap-grid" aria-label="第 21 輪五條供應商路徑">
              {providerGapRouteRows.map((row) => {
                const counts = row.status_counts;
                return (
                  <article className={row.id === providerGapBest.id ? "first-enquiry" : undefined} key={row.id}>
                    <div className="provider-card-head"><span>{row.id === providerGapBest.id ? "FIRST COMPOSITE ENQUIRY" : row.id === providerGapClosure.strongest_standalone_brand_candidate_id ? "FIRST STANDALONE ENQUIRY" : "DOCUMENT REVIEW"}</span><b>{row.name}</b></div>
                    <strong>{counts.explicit_primary_documentation}/14 明確 · {counts.partial_primary_documentation}/14 部分</strong>
                    <p>{row.role}</p>
                    <ul>
                      <li>{counts.contradicted_by_primary_documentation}/14 官方明示不符</li>
                      <li>{counts.unresolved_primary_documentation}/14 公開證據未解</li>
                      <li>授權樣本 0 · 完整合格 0</li>
                    </ul>
                    <small>判斷：只屬採購候選；未通過真實 package 驗收。</small>
                  </article>
                );
              })}
            </div>

            <div className="comparison-caveat">
              <b>最重要反證</b>
              <p>S&amp;P Global Market Intelligence 的公開 Index Data 規格明示 <code>Point In Time: No</code>；Bloomberg 的公司／定價 PIT 公開產品只有 17 年；CRSP Treasury 的日度系列是 4／13／26 週。歷史長、品牌大或數據種類多，都不能填入不相同的正式欄位。</p>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED CAPABILITY MATRIX</span><h3>同一 14 項合約，不用相近欄位補洞</h3></div>
              <p>「部分」仍是硬缺口；只有使用者帳戶內的授權細樣本及完整 package 驗收才可以進一步升格。</p>
            </div>
            <div className="metric-table-wrap">
              <table className="metric-table provider-table provider-gap-table">
                <thead><tr><th>正式能力</th>{providerGapClosure.routes.map((route) => <th key={route.id}>{route.name}</th>)}</tr></thead>
                <tbody>{providerGapCapabilityRows.map((capability) => (
                  <tr key={capability.key}>
                    <th><b>{capability.label}</b><span>{capability.key}</span></th>
                    {capability.statuses.map((status, index) => (
                      <td key={providerGapClosure.routes[index].id}><span className={`provider-status ${status}`}>{providerGapStatusLabels[status]}</span></td>
                    ))}
                  </tr>
                ))}</tbody>
              </table>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED PROCUREMENT QUESTIONS</span><h3>第一封詢價只問九個可驗收問題</h3></div>
              <p>回答若沒有產品代碼、欄位、timestamp、覆蓋率及細樣本，保持「未解」，不靠銷售口頭承諾升格。</p>
            </div>
            <div className="point-in-time-groups provider-question-grid">
              {providerGapClosure.procurement_questions.map((row, index) => (
                <article className="blocked" key={row.capability}><span>{String(index + 1).padStart(2, "0")}</span><b>{providerGapCapabilityLabels[row.capability]}</b><strong>待供應商回答</strong><p>{row.question}</p></article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>EVIDENCE CONTROLS</span><h3>十五道證據控制，全數通過</h3></div>
              <p>15/15 只表示公開文件解讀可重播且 fail closed，不表示取得任何市場列或策略有盈利能力。</p>
            </div>
            <div className="point-in-time-gate-list">
              {providerGapControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>REFUSAL-OF-SUBSTITUTION SUITE</span><h3>十五項產品、時間、價格、退出及 RF 攻擊全拒收</h3></div>
              <p>每項只放入一個語義錯誤並命中指定代碼；不以 generic hash error 掩蓋前視或口徑偷換。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {providerGapAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>向 CRSP＋S&amp;P DJI 及 LSEG 索取相同的授權 data dictionary 與細樣本</b></div>
              <p>{providerGapClosure.next_action} 收到真實樣本後仍按文件 12/12、隔離匯入 16/16、point-in-time 20/20、execution 16/16、RF 完整及正式 18/18 的固定次序驗收。</p>
              <div className="data-source-links">
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_REPORT.md" target="_blank" rel="noreferrer">第 21 輪完整報告</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_GAP_CLOSURE_PROTOCOL.md" target="_blank" rel="noreferrer">事前補缺協議</a>
                <a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_provider_gap_closure_validation.json" target="_blank" rel="noreferrer">機器收據</a>
                {Object.entries(providerGapSourceProbe.observations).map(([key, source]) => <a href={source.url} target="_blank" rel="noreferrer" key={key}>{source.owner}</a>)}
              </div>
            </div>
          </section>

          <section className="section wrap" id="provider-convergence">
            <div className="section-heading">
              <div><span>PROVIDER CONVERGENCE · ROUND 20</span><h2>Stock CIZ 直接支持 5/10；其餘 5/10 仍須逐列證據層</h2></div>
              <p>最新一手指南把供應商請求收窄，但沒有把公開 data dictionary 寫成已訂閱、已交付或可回測。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>同一 CRSP／WRDS 路徑最接近完整；時間證據及精確 RF 仍未封口</h3>
                <p>Stock CIZ 有永久 ID、成分生效區間、raw 日線、公司行動及退市數據字典；但 `MbrStartDt` 不是 `AnnouncedAt`、`SecInfoStartDt` 不是 `KnownAt`。Treasury 的 4 週日度 RF 亦不是凍結的 1 個月日度簡單回報。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>能力收斂</span><strong>{providerConvergence.capability_matrix.direct_documented_count} 份直接 · {providerConvergence.capability_matrix.overlay_required_count} 份 overlay</strong><p>只確認指南層能力；供應商 package、S&amp;P 500 INDNO 及逐列覆蓋仍未驗收。</p></article>
                <article><span>正式決策</span><strong>provider 0 · RF 0 · strategy run 0</strong><p>正式就緒 {providerConvergence.actual_formal_readiness.passed}/{providerConvergence.actual_formal_readiness.total}；Paper 全現金，實金 US$0。</p></article>
              </div>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FIXED INPUT MATRIX</span><h3>十份正式輸入，不用相近欄位補洞</h3></div>
              <p>直接能力仍要真實授權及列級驗收；overlay 缺口則要另外提供來源 reference 及可知時間。</p>
            </div>
            <div className="point-in-time-groups" aria-label="第二十輪供應商能力矩陣">
              {providerDirectRows.map(([name, status], index) => (
                <article className="passed" key={name}><span>{String(index + 1).padStart(2, "0")}</span><b>{name}</b><strong>指南直接支持</strong><p>{status.replaceAll("_", " ")}</p></article>
              ))}
              {providerOverlayRows.map(([name, status], index) => (
                <article className="blocked" key={name}><span>{String(index + 6).padStart(2, "0")}</span><b>{name}</b><strong>仍須證據層</strong><p>{status.replaceAll("_", " ")}</p></article>
              ))}
            </div>

            <div className="short-evidence-grid">
              <article><span>Stock CIZ 指南</span><strong>{providerConvergence.guides.stock_ciz.effective_date} · {providerConvergence.guides.stock_ciz.page_count} 頁</strong><p>PDF SHA-256 已凍結；公開指南不等於帳戶內可交付數據。</p></article>
              <article><span>Treasury 指南</span><strong>{providerConvergence.guides.treasury.effective_date} · {providerConvergence.guides.treasury.page_count} 頁</strong><p>個別票據有 TDRETNUA；日度 RF 只有 4／13／26 週。</p></article>
              <article><span>每日指南核對</span><strong>{providerGuideProbe.all_match_frozen_guides ? "兩份均與凍結版本一致" : "有新版待人工審閱"}</strong><p>新版永不自動獲資格或改寫能力矩陣。</p></article>
              <article><span>精確 1 個月系列</span><strong>月度 · 非正式日度 RF</strong><p>TREASNOX 2000001 不以年率除 252；4 週亦不冒充 1 個月。</p></article>
              <article><span>成分時間</span><strong>有效區間 ≠ 公布時間</strong><p>需要逐列 `AnnouncedAt` 及證據 reference，避免成分前視。</p></article>
              <article><span>退市缺值</span><strong>不填 0</strong><p>DelRet missing type 是原因標記，不是零損益證明。</p></article>
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>GUIDE EVIDENCE CONTROLS</span><h3>十二道指南、欄位、年期、單位及決策控制</h3></div>
              <p>12/12 只表示 frozen interpretation 可重播；不是市場數據、策略回報或盈利通過。</p>
            </div>
            <div className="point-in-time-gate-list">
              {providerConvergenceControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>REFUSAL-OF-SUBSTITUTION SUITE</span><h3>十二項協議、版本、時間、退市及 RF 替代攻擊全拒收</h3></div>
              <p>每項只保留一個語義錯誤，避免普通 hash 失敗掩蓋前視、缺值補洞或年期偷換。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {providerConvergenceAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>只核對已授權 CRSP／WRDS 真實交付、五份 evidence overlay 及相同經濟定義 RF</b></div>
              <p>{providerConvergence.next_action} 指南通過不產生選股名單；真實 18/18 前不運行正式 20 年回測、不啟動或回填短線 Paper。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_CONVERGENCE_REPORT.md" target="_blank" rel="noreferrer">第二十輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_PROVIDER_CONVERGENCE_PROTOCOL.md" target="_blank" rel="noreferrer">凍結收斂協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_provider_convergence_validation.json" target="_blank" rel="noreferrer">機器收據</a><a href={providerConvergence.guides.stock_ciz.landing_url} target="_blank" rel="noreferrer">CRSP Stock CIZ 指南</a><a href={providerConvergence.guides.treasury.landing_url} target="_blank" rel="noreferrer">CRSP Treasury 指南</a></div>
            </div>
          </section>

          <section className="section wrap" id="risk-free-staging">
            <div className="section-heading">
              <div><span>OFFICIAL RISK-FREE STAGING · ROUND 19</span><h2>官方 RF 已覆蓋 5,009/5,031；仍欠最後 22 個 XNYS session</h2></div>
              <p>首次把「RF 未收到」收窄成可核對的真實缺口：官方 202606 snapshot 只到 2026-06-30，不能以 99.56% 當作完整，更不能補 0、複製 6 月或用 SHY 偷代。</p>
            </div>

            <div className="aggressive-overview-grid">
              <article className="aggressive-verdict point-in-time-verdict">
                <span>最新研究判斷</span>
                <h3>經濟定義正確、轉換可重現；正式時間軸仍缺一整個月</h3>
                <p>來源 RF 是在該月交易日複利至一個月美國國庫券回報的 simple daily rate。原檔百分點只除以 100 一次；{riskFreeStaging.study.missing_session_count} 個缺日及明確授權證據未解決前，不生成正式 `risk_free_manifest.json`。</p>
              </article>
              <div className="aggressive-risk-stack">
                <article><span>真實覆蓋</span><strong>{riskFreeStaging.study.available_sessions.toLocaleString("zh-HK")}/{riskFreeStaging.study.required_sessions.toLocaleString("zh-HK")} · {riskFreeCoveragePct.toFixed(2)}%</strong><p>2006-08-01 至 2026-06-30 完整對上 XNYS；額外日期 {riskFreeStaging.study.extra_session_count}。</p></article>
                <article><span>正式決策</span><strong>RF 完整包 0 · strategy run 0</strong><p>正式就緒維持 {riskFreeStaging.actual_formal_readiness.passed}/{riskFreeStaging.actual_formal_readiness.total}；Paper 全現金，實金 US$0。</p></article>
              </div>
            </div>

            <div className="short-evidence-grid">
              <article><span>官方 data cut</span><strong>{riskFreeStaging.source.data_cut}</strong><p>官方日度檔最後 session：{riskFreeStaging.source.full_last_session}。</p></article>
              <article><span>每日來源掃描</span><strong>{riskFreeSourceProbe.matches_frozen_source ? "與凍結 snapshot 一致" : "發現新來源待核對"}</strong><p>掃描只比較 hash、data cut 及覆蓋；新來源不會自動獲正式資格。</p></article>
              <article><span>正式研究期</span><strong>{riskFreeStaging.study.required_sessions.toLocaleString("zh-HK")} 日</strong><p>{riskFreeStaging.study.start} 至 {riskFreeStaging.study.end}，固定 XNYS 日曆。</p></article>
              <article><span>已覆蓋</span><strong>{riskFreeStaging.study.available_sessions.toLocaleString("zh-HK")} 日</strong><p>由 {riskFreeStaging.study.first_available_session} 至 {riskFreeStaging.study.last_available_session}。</p></article>
              <article><span>仍缺失</span><strong>{riskFreeStaging.study.missing_session_count} 日</strong><p>{riskFreeStaging.study.missing_sessions[0]} 至 {riskFreeStaging.study.missing_sessions.at(-1)}，不作任何填補。</p></article>
              <article><span>來源／權限</span><strong>公開下載 · 授權待證</strong><p>官方 bytes 及 SHA-256 已凍結；未把公開下載推論為完整本地研究授權條款。</p></article>
              <article><span>正式檔案</span><strong>刻意不生成</strong><p>partial 檔名與正式驗證器要求不同，不可能誤接入一次性回測。</p></article>
            </div>

            <div className="comparison-caveat"><b>精確缺日：</b><p>{riskFreeStaging.study.missing_sessions.join("、")}</p></div>

            <div className="subsection-heading stock-heading">
              <div><span>REAL SOURCE CONTROLS</span><h3>八道官方來源、單位、session、權限及決策控制</h3></div>
              <p>8/8 代表 202606 snapshot 被安全處理並準確報缺；不是完整 5,031/5,031，也不是策略回報。</p>
            </div>
            <div className="point-in-time-gate-list">
              {riskFreeControlRows.map((gate) => (
                <article className={gate.passed ? "passed" : "blocked"} key={gate.id}>
                  <span>{gate.id}</span><div><b>{gate.label}</b><p>{gate.detail}</p></div><strong>{gate.passed ? "通過" : "未通過"}</strong>
                </article>
              ))}
            </div>

            <div className="subsection-heading stock-heading">
              <div><span>FROZEN ADVERSARIAL SUITE</span><h3>八項來源 ZIP、定義、日期、單位、路徑及越權攻擊全拒收</h3></div>
              <p>尤其測試「缺 22 日仍要求正式 manifest」：必須以 `rf_decision_boundary_violation` 停止。</p>
            </div>
            <div className="test-matrix point-in-time-tests acceptance-tests">
              {riskFreeAttackRows.map((attack) => (
                <article className="test-card" key={attack.id}>
                  <div><span>{attack.id} · {attack.label}</span><b className="negative-number">{attack.rejected ? "拒收" : "誤收"}</b></div>
                  <p>{attack.expected_error_code}</p>
                </article>
              ))}
            </div>

            <div className="data-source-decision provider-decision">
              <div><span>NEXT VALID ACTION</span><b>等同一經濟定義補齊 2026 年 7 月，仍須與逐股 provider package 一起通過 18/18</b></div>
              <p>{riskFreeStaging.next_action} RF 完整只關閉一個缺口；退市、成分公布時間、公司行動及 point-in-time 股池仍不能省略。</p>
              <div className="data-source-links"><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_RISK_FREE_STAGING_REPORT.md" target="_blank" rel="noreferrer">第十九輪完整報告</a><a href="https://github.com/voidful/us_fddk/blob/main/docs/SHORT_TERM_RISK_FREE_STAGING_PROTOCOL.md" target="_blank" rel="noreferrer">凍結暫存協議</a><a href="https://github.com/voidful/us_fddk/blob/main/artifacts/short_term_risk_free_staging_validation.json" target="_blank" rel="noreferrer">機器收據</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html" target="_blank" rel="noreferrer">Fama/French Data Library</a><a href="https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html" target="_blank" rel="noreferrer">RF 經濟定義</a></div>
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
