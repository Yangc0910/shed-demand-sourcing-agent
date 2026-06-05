from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from statistics import mean

from shed_agent.config import AgentConfig
from shed_agent.decision import decision_check
from shed_agent.models import MarketObservation


def generate_dashboard_html(observations: list[MarketObservation], config: AgentConfig) -> str:
    today = date.today()
    window_start, window_end = observation_window(config, today)
    local = [item for item in observations if item.is_local_demand_source]
    window_items = [item for item in local if _within_window(item, window_start, window_end)]
    llm_count = sum(1 for item in observations if item.analysis_quality in {"llm", "llm_cached"})
    fallback_count = sum(1 for item in observations if item.analysis_quality == "fallback_only")
    decision, reasons = decision_check(observations, config)
    target_items = [item for item in window_items if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"}]
    comparables = [item for item in window_items if item.is_useful_comparable]
    adjacent = [item for item in window_items if item.is_adjacent_expansion]
    likely_noise = [item for item in window_items if item.verification_status == "likely_noise"]
    pickup_count = sum(1 for item in window_items if item.pickup_required)
    assembly_count = sum(1 for item in window_items if item.assembly_mentioned)
    delivery_count = sum(1 for item in window_items if item.delivery_mentioned)
    top_candidates = sorted(
        target_items,
        key=lambda item: (item.overall_signal_score, item.price_attractiveness_score),
        reverse=True,
    )[:8]
    adjacent_top = sorted(adjacent, key=lambda item: item.overall_signal_score, reverse=True)[:6]
    brands = Counter(
        item.inferred_brand for item in window_items if str(item.inferred_brand or "").strip() and item.inferred_brand != "unknown"
    )
    status_counts = Counter(item.listing_status for item in window_items)
    avg_target_score = mean([item.overall_signal_score for item in target_items]) if target_items else 0
    last_updated = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    pickup_without_delivery = sum(1 for item in window_items if item.pickup_required and not item.delivery_mentioned)
    summary_headline = _summary_headline(decision, len(target_items), len(comparables), pickup_without_delivery)
    risk_summary = _risk_summary(len(likely_noise), len(target_items), fallback_count)
    next_action_summary = _next_action_summary(decision, len(target_items), pickup_without_delivery)

    cards = [
        _metric_card("观察周期", f"{window_start.isoformat()} 至 {window_end.isoformat()}", "这是当前这轮 7 天 listening 周期，用来判断这一周本地需求是否在变强。"),
        _metric_card("当前建议", _decision_label(decision), "这是排除了零售 benchmark 干扰后，只基于本地需求信号得出的当前判断。"),
        _metric_card("本地需求信号", str(len(window_items)), "当前 7 天窗口里，来自 Facebook、Craigslist、本地帖子或手动片段的总观察数。"),
        _metric_card("目标候选", str(len(target_items)), "看起来接近 4x6 horizontal 或 6x5 vertical 的 listing 数量。"),
        _metric_card("可用可比项", str(len(comparables)), "有价格、且对我们目标 SKU 有参考价值的本地可比 listing。"),
        _metric_card("仅自提未送货", str(pickup_without_delivery), "这个数字越高，越说明本地 delivery / placement 可能是差异化点。"),
        _metric_card("组装相关提及", str(assembly_count), "出现组装、拆装、搬运麻烦等信号，意味着潜在服务机会。"),
        _metric_card("分析质量", f"{llm_count} 条 LLM / {fallback_count} 条 fallback", "告诉你当前市场判断里，有多少来自 LLM 分析，有多少还是保守 fallback。"),
    ]

    top_candidates_html = "".join(_candidate_row(item) for item in top_candidates) or _empty_row("No target-sized candidates inside the current 7-day window.")
    adjacent_html = "".join(_adjacent_row(item) for item in adjacent_top) or _empty_row(
        "No adjacent backyard opportunities are standing out right now.",
        colspan=4,
    )
    reasons_html = "".join(f"<li>{escape(reason)}</li>" for reason in reasons)
    brands_html = "".join(f"<li><strong>{escape(brand)}</strong>: {count}</li>" for brand, count in brands.most_common(8)) or "<li>No consistent brands yet.</li>"
    status_html = "".join(f"<li><strong>{escape(status)}</strong>: {count}</li>" for status, count in status_counts.items()) or "<li>No observations yet.</li>"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Shed Demand Listener 仪表盘</title>
  <style>
    :root {{
      --bg: #f5efe5;
      --panel: #fffdf8;
      --ink: #1d1b16;
      --muted: #665f52;
      --line: #d9cfbf;
      --accent: #1f6b4f;
      --accent-soft: #dfeee7;
      --warn: #8b5e1a;
      --warn-soft: #f7ebd0;
      --bad: #8f3d2e;
      --bad-soft: #f7dfd8;
      --shadow: 0 10px 30px rgba(56, 42, 16, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(31,107,79,0.12), transparent 26%),
        radial-gradient(circle at top right, rgba(139,94,26,0.10), transparent 24%),
        linear-gradient(180deg, #fbf7ef, var(--bg));
    }}
    .wrap {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 28px 20px 56px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 18px;
    }}
    .hero-card, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      border-radius: 8px;
    }}
    .hero-card {{
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      line-height: 1.05;
      letter-spacing: 0;
    }}
    .sub {{
      color: var(--muted);
      max-width: 62ch;
      line-height: 1.5;
      margin-bottom: 18px;
    }}
    .stamp {{
      color: var(--muted);
      font-size: 14px;
    }}
    .decision-box {{
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      background: linear-gradient(180deg, var(--accent-soft), #f7fcf9);
    }}
    .decision-tag {{
      display: inline-block;
      padding: 8px 12px;
      border-radius: 999px;
      background: #fff;
      border: 1px solid rgba(31,107,79,0.22);
      font-weight: 600;
      width: fit-content;
      margin-bottom: 10px;
    }}
    .decision-copy {{
      color: var(--muted);
      line-height: 1.5;
      font-size: 14px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }}
    .metric {{
      padding: 18px;
    }}
    .metric h3 {{
      margin: 0 0 8px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }}
    .metric .value {{
      font-size: 28px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .metric p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.4;
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .panel {{
      padding: 20px;
    }}
    .panel h2 {{
      margin: 0 0 6px;
      font-size: 20px;
    }}
    .panel .explain {{
      color: var(--muted);
      margin-bottom: 16px;
      line-height: 1.5;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      text-align: left;
      vertical-align: top;
      padding: 10px 8px;
      border-top: 1px solid var(--line);
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      border-top: 0;
      padding-top: 0;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      border: 1px solid transparent;
      white-space: nowrap;
    }}
    .fit {{ background: var(--accent-soft); color: var(--accent); border-color: rgba(31,107,79,0.15); }}
    .watch {{ background: var(--warn-soft); color: var(--warn); border-color: rgba(139,94,26,0.18); }}
    .noise {{ background: var(--bad-soft); color: var(--bad); border-color: rgba(143,61,46,0.16); }}
    ul {{
      margin: 0;
      padding-left: 18px;
    }}
    li {{
      margin: 8px 0;
      line-height: 1.45;
    }}
    .split {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    .footnote {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      margin-top: 14px;
    }}
    @media (max-width: 980px) {{
      .hero, .grid, .split, .metrics {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-card">
        <h1>Shed Demand Listener</h1>
        <div class="sub">这是一个面向 Lexington、Burlington、Waltham、Arlington、Bedford、Belmont、Winchester 周边本地市场的私有需求监听仪表盘。它的目的很简单：快速回答我们现在是否看到了足够真实的本地需求，值得继续观察、靠近小批量库存研究，还是暂时按住不动。</div>
        <div class="stamp">最近更新：{escape(last_updated)}</div>
      </div>
      <div class="hero-card decision-box">
        <div>
          <div class="decision-tag">{escape(_decision_label(decision))}</div>
          <h2 style="margin:0 0 8px;">当前结论</h2>
          <div class="decision-copy">我们仍处在 listening 阶段。这个页面会把真实本地需求、零售对比项和明显噪音拆开看，避免库存判断被虚假热度带偏。</div>
        </div>
        <div class="decision-copy">当前窗口内目标 shed 平均得分：<strong>{avg_target_score:.1f}/10</strong></div>
      </div>
    </section>

    <section class="metrics">
      {''.join(cards)}
    </section>

    <section class="grid">
      <div class="panel">
        <h2>一句话结论</h2>
        <div class="explain">如果你今天只看一眼，这一块应该最先看。</div>
        <div style="font-size:24px; font-weight:700; line-height:1.35; margin-bottom:12px;">{escape(summary_headline)}</div>
        <div class="footnote">这句话会结合当前 recommendation、目标候选数量、可用可比项数量，以及 delivery / pickup friction 来生成。</div>
      </div>
      <div class="panel">
        <h2>当前主要风险</h2>
        <div class="explain">这部分专门提醒你，为什么现在还不能轻易把“看到很多 listing”直接等同于“本地需求很强”。</div>
        <ul>
          <li>{escape(risk_summary)}</li>
          <li>Facebook Marketplace 搜索天然会混入非本地、partner、配件或噪音结果，所以 target fit 必须二次验证。</li>
          <li>Retail benchmark 已被单独隔离，不会直接抬高本地需求判断。</li>
        </ul>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>重点目标候选</h2>
        <div class="explain">这里放的是当前最接近核心业务问题的 listing。某条 listing 出现在这里，并不代表它已经被完全确认，所以右侧专门保留了“为什么值得关注”的说明。</div>
        <table>
          <thead>
            <tr>
              <th>Listing</th>
              <th>匹配类型</th>
              <th>价格</th>
              <th>评分</th>
              <th>为什么值得看</th>
            </tr>
          </thead>
          <tbody>{top_candidates_html}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>这些指标是什么意思</h2>
        <div class="explain">这是这个 dashboard 的速读说明，让你不用每次都去反向理解分析流程。</div>
        <ul>
          <li><strong>本地需求信号</strong>：来自 Facebook Marketplace、Craigslist、Nextdoor 片段、本地 Facebook 群片段，或者你手动粘贴的本地帖子。</li>
          <li><strong>目标候选</strong>：看起来像 `4x6_horizontal` 或 `6x5_vertical` 的机会，即使它们还需要二次验证。</li>
          <li><strong>可用可比项</strong>：带价格、而且对目标 SKU 的本地售价空间有参考价值的 listing。</li>
          <li><strong>仅自提未送货</strong>：这是最简单也最有力的一个信号，说明本地 delivery / placement 可能是用户真正愿意买单的便利。</li>
          <li><strong>分析质量</strong>：当前结论中有多少来自 LLM，有多少还是保守的规则 fallback。</li>
        </ul>
        <div class="footnote">现在这一版的判断质量比最早的 fallback-only 阶段更强，因为 OpenAI key 已经接通，listing analysis 正在使用结构化 LLM 输出。</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>决策信号</h2>
        <div class="explain">这里是通往库存判断的最短路径。下面这些点，就是当前 recommendation 背后的主要原因。</div>
        <ul>{reasons_html}</ul>
      </div>
      <div class="panel">
        <h2>数据质量与噪音</h2>
        <div class="explain">Marketplace 搜索本来就很吵。这个区块是用来判断当前信号够不够干净，值不值得相信。</div>
        <div class="split">
          <div>
            <h3 style="margin:0 0 8px;">状态分布</h3>
            <ul>{status_html}</ul>
          </div>
          <div>
            <h3 style="margin:0 0 8px;">品牌分布</h3>
            <ul>{brands_html}</ul>
          </div>
        </div>
        <div class="footnote">当前窗口内，疑似噪音：<strong>{len(likely_noise)}</strong>。提到 delivery：<strong>{delivery_count}</strong>。要求 pickup：<strong>{pickup_count}</strong>。提到组装/拆装：<strong>{assembly_count}</strong>。</div>
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>邻近机会观察清单</h2>
        <div class="explain">这些内容不会直接推动 compact shed 的库存决策。它们放在这里，是为了帮助我们看到未来 backyard / storage 的扩展方向，但不污染核心 demand 判断。</div>
        <table>
          <thead>
            <tr>
              <th>Listing</th>
              <th>类型</th>
              <th>价格</th>
              <th>建议动作</th>
            </tr>
          </thead>
          <tbody>{adjacent_html}</tbody>
        </table>
      </div>
      <div class="panel">
        <h2>接下来该做什么</h2>
        <div class="explain">这不是技术操作说明，而是今天看完 dashboard 以后，最实际的下一步动作。</div>
        <div style="font-size:18px; font-weight:600; line-height:1.45; margin-bottom:14px;">{escape(next_action_summary)}</div>
        <h3 style="margin:0 0 8px;">这个页面怎么用</h3>
        <ol style="margin:0; padding-left:18px; line-height:1.5;">
          <li>先看“当前建议”。它会先告诉你：市场现在是仍然混合、正在变强，还是偏弱。</li>
          <li>再看“重点目标候选”。如果相同 target fit 持续出现，而且价格和本地相关性都说得通，信心就会上升。</li>
          <li>重点盯 pickup 和 assembly friction。如果这个信号持续变强，说明服务差异化更有机会成立。</li>
          <li>邻近机会观察清单只用来帮助未来扩品，不应该直接逼着我们现在去做 compact shed 库存判断。</li>
        </ol>
        <div class="footnote">Dashboard 文件位置：{escape(str(Path(config.dashboard_output_file)))}。可以直接双击在浏览器里打开，不需要启动本地服务。</div>
      </div>
    </section>
  </div>
</body>
</html>
"""


def observation_window(config: AgentConfig, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    if config.observation_window_start_date:
        start = date.fromisoformat(config.observation_window_start_date)
        end = start + timedelta(days=max(config.observation_window_days, 1) - 1)
        return start, end
    days = max(config.observation_window_days, 1)
    start = today - timedelta(days=days - 1)
    return start, today


def _within_window(observation: MarketObservation, window_start: date, window_end: date) -> bool:
    for value in (observation.last_seen, observation.date_seen):
        try:
            seen = date.fromisoformat(value)
        except ValueError:
            continue
        if window_start <= seen <= window_end:
            return True
    return False


def _metric_card(title: str, value: str, explanation: str) -> str:
    return (
        '<div class="panel metric">'
        f"<h3>{escape(title)}</h3>"
        f'<div class="value">{escape(value)}</div>'
        f"<p>{escape(explanation)}</p>"
        "</div>"
    )


def _candidate_row(item: MarketObservation) -> str:
    rationale = item.llm_analysis.get("rationale") or "; ".join(item.learning_notes[:2]) or "还需要更多证据。"
    return (
        "<tr>"
        f"<td><strong>{escape(item.title or '(未命名)')}</strong><br><span style='color:#665f52'>{escape(item.location or '未知')}</span></td>"
        f"<td><span class='pill fit'>{escape(_fit_label(item.target_sku_fit))}</span></td>"
        f"<td>{escape(_money(item.price))}</td>"
        f"<td>{item.overall_signal_score:.1f}/10</td>"
        f"<td>{escape(rationale[:180])}</td>"
        "</tr>"
    )


def _adjacent_row(item: MarketObservation) -> str:
    action = item.llm_analysis.get("recommended_action", "watch")
    return (
        "<tr>"
        f"<td><strong>{escape(item.title or '(未命名)')}</strong><br><span style='color:#665f52'>{escape(item.location or '未知')}</span></td>"
        f"<td><span class='pill watch'>{escape(_product_type_label(item.product_type))}</span></td>"
        f"<td>{escape(_money(item.price))}</td>"
        f"<td>{escape(_action_label(action))}</td>"
        "</tr>"
    )


def _empty_row(message: str, colspan: int = 5) -> str:
    return f"<tr><td colspan='{colspan}' style='color:#665f52'>{escape(message)}</td></tr>"


def _money(value: float | None) -> str:
    return f"${value:.0f}" if value is not None else "未知"


def _summary_headline(decision: str, target_count: int, comparable_count: int, pickup_without_delivery: int) -> str:
    if decision == "inventory_candidate":
        return "这周本地 compact shed 信号已经比较成形，可以开始认真看小批量库存可行性，但仍需要价格和真实性复核。"
    if decision == "start_supplier_rfq":
        return "本地需求和服务空档正在变强，可以开始准备更深入的货源研究，但还不建议直接做采购动作。"
    if decision == "no_go":
        return "当前这周的本地信号偏弱，继续投入精力的回报可能不高，建议先收缩观察范围。"
    if target_count >= 3 and pickup_without_delivery >= 3:
        return "这周已经能看到一些目标 shed 候选，而且自提 friction 也在出现，方向值得继续盯，但证据还不够厚。"
    if comparable_count >= 3:
        return "本地已经开始形成一些可比项，价格带正在变得更清楚，但还没到足够果断下判断的时候。"
    return "现在更像是在积累证据阶段：市场不是没信号，但还不够稳定，不适合太快推进库存动作。"


def _risk_summary(noise_count: int, target_count: int, fallback_count: int) -> str:
    if target_count == 0:
        return "当前最大的风险是：看到不少 marketplace 内容，但真正贴近目标 SKU 的 listing 仍然太少。"
    if noise_count >= target_count:
        return "当前最大的风险是：噪音和非核心结果仍然不少，说明搜索结果里“看起来相关”和“真有本地需求”之间还有距离。"
    if fallback_count > 0:
        return "当前最大的风险是：仍有部分 observation 不是 LLM 深度分析结果，所以个别判断还偏保守。"
    return "当前最大的风险不是完全没信号，而是信号还不够密，容易被少数异常 listing 放大影响。"


def _next_action_summary(decision: str, target_count: int, pickup_without_delivery: int) -> str:
    if decision == "inventory_candidate":
        return "继续保持这周的采集频率，并重点复核高分 target candidate 的真实性、完整性和本地交付可行性。"
    if decision == "start_supplier_rfq":
        return "继续观察市场，同时把高频出现的尺寸、品牌、价格区间整理清楚，为后续更严肃的库存研究做准备。"
    if decision == "no_go":
        return "先不要扩大投入，优先确认是不是关键词、地域或采集质量导致了低信号，再决定是否缩小范围。"
    if target_count >= 2 and pickup_without_delivery >= 2:
        return "接下来最值得盯的是：目标候选是否持续出现，以及 pickup / assembly pain point 会不会继续累积。"
    return "接下来先把这一周跑完整，重点观察是否会持续出现 4x6 horizontal、6x5 vertical，以及明显的自提/组装痛点。"


def _decision_label(value: str) -> str:
    labels = {
        "continue_watching": "继续观察",
        "start_supplier_rfq": "准备进入供应商调研",
        "inventory_candidate": "可以作为库存候选",
        "no_go": "暂时不做",
    }
    return labels.get(value, value)


def _fit_label(value: str) -> str:
    labels = {
        "4x6_horizontal": "4x6 横向 shed",
        "6x5_vertical": "6x5 竖向 shed",
        "adjacent_expansion": "邻近扩展",
        "not_relevant": "不相关",
    }
    return labels.get(value, value or "未知")


def _product_type_label(value: str) -> str:
    labels = {
        "horizontal_shed": "横向 shed",
        "vertical_shed": "竖向 shed",
        "deck_box": "deck box",
        "large_shed": "大型 shed",
        "garden_dome": "花园穹顶",
        "greenhouse": "温室",
        "canopy_gazebo": "棚 / gazebo",
        "patio_storage": "庭院储物",
        "bike_storage": "自行车储物",
        "backyard_structure": "后院结构类",
        "shed_accessory": "shed 配件",
        "other": "其他",
    }
    return labels.get(value, value or "未知")


def _action_label(value: str) -> str:
    labels = {
        "ignore": "忽略",
        "watch": "继续观察",
        "useful_comparable": "作为可比项保留",
        "high_signal": "高信号",
        "supplier_research_later": "以后再研究供应",
        "first_inventory_candidate": "可做首批库存候选",
    }
    return labels.get(value, value or "继续观察")
