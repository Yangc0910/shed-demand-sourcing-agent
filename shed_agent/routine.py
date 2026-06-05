from __future__ import annotations

import json
import traceback
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from time import monotonic

from shed_agent.config import AgentConfig
from shed_agent.decision import decision_check
from shed_agent.deduplicate import deduplicate_observations
from shed_agent.facebook_marketplace import collect_facebook_marketplace, format_collection_summary
from shed_agent.generate_dashboard import generate_dashboard_html
from shed_agent.generate_daily_digest import generate_daily_digest
from shed_agent.generate_market_report import generate_market_report
from shed_agent.ingest import ingest_craigslist_rss
from shed_agent.llm_analysis import analyze_observations_with_llm
from shed_agent.retail_comparable import ingest_retail_comparable_urls
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


@dataclass
class RoutineRunResult:
    status: str = "success"
    started_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    ended_at: str = ""
    messages: list[str] = field(default_factory=list)
    files_written: list[str] = field(default_factory=list)
    exit_code: int = 0


def run_routine(data_path: Path, config: AgentConfig) -> RoutineRunResult:
    result = RoutineRunResult()
    log_dir = Path(str(config.logging.get("logDir", "logs")))
    report_dir = Path(str(config.logging.get("reportDir", "reports")))
    log_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    log_path = log_dir / f"routine-{today}.log"

    with log_path.open("a", encoding="utf-8") as log_file, redirect_stdout(log_file), redirect_stderr(log_file):
        try:
            print(f"Routine started at {result.started_at}")
            _run_routine_steps(data_path, config, report_dir, result)
            result.status = "success"
            result.exit_code = 0
        except Exception as exc:
            result.status = "failed"
            result.exit_code = 1
            result.messages.append(str(exc))
            print("Routine failed:")
            print(traceback.format_exc())
        finally:
            result.ended_at = datetime.now().isoformat(timespec="seconds")
            print(f"Routine ended at {result.ended_at} with status {result.status}")

    latest = log_dir / "routine-latest.log"
    latest.write_text(log_path.read_text(encoding="utf-8"), encoding="utf-8")
    result.files_written.append(str(log_path))
    result.files_written.append(str(latest))
    _write_run_summaries(result, config, report_dir, today)
    return result


def _run_routine_steps(data_path: Path, config: AgentConfig, report_dir: Path, result: RoutineRunResult) -> None:
    routine_config = config.routine
    max_runtime_seconds = int(routine_config.get("maxRuntimeMinutes", 30)) * 60
    started = monotonic()

    if routine_config.get("runFacebookCollector", True) and config.enable_facebook_marketplace_collector:
        print("Running Facebook Marketplace collector in scheduled mode.")
        summary = collect_facebook_marketplace(config, data_path, interactive=False)
        formatted = format_collection_summary(summary)
        print(formatted)
        result.messages.append(
            f"Facebook collector: {summary.new_observations} new, {summary.duplicates_skipped} duplicates, {summary.listings_found} captured."
        )

    _check_runtime(started, max_runtime_seconds)

    if routine_config.get("runCraigslistCollector", False):
        print("Running Craigslist RSS collector.")
        count, changes = ingest_craigslist_rss(config, data_path)
        print(f"Craigslist RSS new observations: {count}")
        for change in changes:
            print(f"- {change}")
        result.messages.append(f"Craigslist RSS collector: {count} new observations.")

    _check_runtime(started, max_runtime_seconds)

    if routine_config.get("runRetailComparableCollector", False):
        print("Running retail comparable URL collector.")
        retail_result = ingest_retail_comparable_urls(config, data_path)
        print(
            f"Retail comparable collector: {retail_result.added} added, "
            f"{retail_result.blocked} blocked, {retail_result.failed} failed."
        )
        for message in retail_result.messages:
            print(f"- {message}")
        result.messages.append(
            f"Retail comparables: {retail_result.added} added, {retail_result.blocked} blocked, {retail_result.failed} failed."
        )

    _check_runtime(started, max_runtime_seconds)

    observations = deduplicate_observations(load_observations(data_path))
    save_observations([score_observation(item, config) for item in observations], data_path)
    result.messages.append(f"Deduplicated observations: {len(observations)}.")

    if routine_config.get("runLLMAnalysis", True) and config.enable_llm_analysis:
        print("Running LLM-assisted listing analysis.")
        llm_summary = analyze_observations_with_llm(data_path, config)
        print(json.dumps(asdict(llm_summary), indent=2))
        result.messages.append(
            f"LLM analysis: {llm_summary.analyzed} analyzed, {llm_summary.cache_hits} cache hits, {llm_summary.fallback} fallback."
        )

    _check_runtime(started, max_runtime_seconds)

    observations = load_observations(data_path)
    if routine_config.get("generateDailyDigest", True):
        daily_path = report_dir / f"daily-digest-{date.today().isoformat()}.md"
        daily_path.write_text(generate_daily_digest(observations, config), encoding="utf-8")
        result.files_written.append(str(daily_path))

    if _should_generate_weekly_report(config):
        weekly_path = report_dir / f"weekly-report-{date.today().isoformat()}.md"
        weekly_path.write_text(generate_market_report(observations, config), encoding="utf-8")
        result.files_written.append(str(weekly_path))

    if routine_config.get("runDecisionCheck", True):
        decision, reasons = decision_check(observations, config)
        decision_path = report_dir / f"decision-check-{date.today().isoformat()}.md"
        decision_text = "# Decision Check\n\n" + f"Decision: {decision}\n\n" + "\n".join(f"- {reason}" for reason in reasons) + "\n"
        decision_path.write_text(decision_text, encoding="utf-8")
        result.files_written.append(str(decision_path))
        result.messages.append(f"Decision: {decision}")

    dashboard_path = Path(config.dashboard_output_file)
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(generate_dashboard_html(observations, config), encoding="utf-8")
    result.files_written.append(str(dashboard_path))


def _write_run_summaries(result: RoutineRunResult, config: AgentConfig, report_dir: Path, today: str) -> None:
    if config.logging.get("saveRunSummaryJson", True):
        path = report_dir / f"routine-summary-{today}.json"
        path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
        result.files_written.append(str(path))
    if config.logging.get("saveRunSummaryMarkdown", True):
        path = report_dir / f"routine-summary-{today}.md"
        lines = [
            "# Routine Run Summary",
            "",
            f"- Status: {result.status}",
            f"- Started: {result.started_at}",
            f"- Ended: {result.ended_at}",
            f"- Exit code: {result.exit_code}",
            "",
            "## Messages",
        ]
        lines.extend(f"- {message}" for message in result.messages)
        lines.extend(["", "## Files Written"])
        lines.extend(f"- {path}" for path in result.files_written)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result.files_written.append(str(path))


def _should_generate_weekly_report(config: AgentConfig) -> bool:
    target_day = str(config.routine.get("generateWeeklyReportOn", "Sunday")).lower()
    return datetime.now().strftime("%A").lower() == target_day


def _check_runtime(started: float, max_runtime_seconds: int) -> None:
    if monotonic() - started > max_runtime_seconds:
        raise TimeoutError("Routine exceeded configured maxRuntimeMinutes.")
