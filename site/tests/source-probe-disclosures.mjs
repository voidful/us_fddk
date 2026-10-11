import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

export async function assertCurrentSourceProbeDisclosures(html) {
  const [rf, guides] = await Promise.all(
    ["short-term-risk-free-source-probe", "short-term-provider-guide-probe"].map(
      async (name) => JSON.parse(
        await readFile(new URL(`../data/${name}.json`, import.meta.url), "utf8"),
      ),
    ),
  );
  assert.equal(typeof rf.matches_frozen_source, "boolean");
  assert.equal(typeof guides.all_match_frozen_guides, "boolean");
  assert.equal(rf.new_source_qualified, false);
  assert.equal(rf.formal_rf_input_ready, false);
  assert.equal(guides.new_guide_qualified, false);
  assert.equal(guides.provider_package_qualified, false);
  for (const probe of [rf, guides]) {
    assert.equal(probe.formal_backtest_authorized, false);
    assert.equal(probe.paper_authorized, false);
    assert.equal(probe.paper_state, "all_cash");
    assert.equal(probe.strategy_run_count, 0);
    assert.equal(probe.real_money_action_usd, 0);
  }
  const rfStatus = rf.matches_frozen_source
    ? "與凍結 snapshot 一致"
    : "發現新來源待核對";
  const guideStatus = guides.all_match_frozen_guides
    ? "兩份均與凍結版本一致"
    : "有新版待人工審閱";
  assert.match(html, new RegExp(`<span>每日來源掃描</span><strong>${rfStatus}</strong>`));
  assert.match(html, new RegExp(`<span>每日指南核對</span><strong>${guideStatus}</strong>`));
  assert.match(html, /新來源不會自動獲正式資格/);
  assert.match(html, /新版永不自動獲資格或改寫能力矩陣/);
}
