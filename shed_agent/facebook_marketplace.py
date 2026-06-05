from __future__ import annotations

import random
import re
import os
import shutil
import subprocess
import time
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from urllib.error import URLError
from urllib.parse import quote_plus, urljoin, urlparse
from urllib.request import urlopen

from shed_agent.config import AgentConfig
from shed_agent.deduplicate import merge_observations, observation_key
from shed_agent.decision import decision_check
from shed_agent.extract_listing import extract_listing, fast_moving_signal, missing_parts_or_damage_risk
from shed_agent.models import MarketObservation
from shed_agent.score_observation import score_observation
from shed_agent.storage import load_observations, save_observations


FACEBOOK_SOURCE_TYPE = "facebook_marketplace_playwright"
MARKETPLACE_BASE_URL = "https://www.facebook.com/marketplace"
CHALLENGE_TERMS = (
    "captcha",
    "security check",
    "log in forgot account",
    "forgot account",
    "email or phone",
    "confirm it's you",
    "confirm your identity",
    "checkpoint",
    "account temporarily locked",
    "unusual activity",
    "access denied",
)
CHALLENGE_URL_TERMS = (
    "login",
    "checkpoint",
    "two_step_verification",
    "authentication",
    "recover",
)


@dataclass
class FacebookCard:
    title: str
    price: float | None
    location: str
    url: str
    thumbnail_url: str = ""
    raw_text: str = ""
    search_keyword: str = ""


@dataclass
class FacebookCollectionSummary:
    keywords_searched: list[str] = field(default_factory=list)
    listings_found: int = 0
    new_observations: int = 0
    duplicates_skipped: int = 0
    detail_pages_opened: int = 0
    high_signal_listings: list[MarketObservation] = field(default_factory=list)
    average_price_by_category: dict[str, float] = field(default_factory=dict)
    delivery_gap_count: int = 0
    assembly_gap_count: int = 0
    decision: str = "continue watching"
    decision_reasons: list[str] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class FacebookDiagnostic:
    status: str
    checks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def build_marketplace_search_url(keyword: str, location_slug: str = "") -> str:
    location_part = f"/{location_slug.strip('/')}" if location_slug else ""
    return f"{MARKETPLACE_BASE_URL}{location_part}/search/?query={quote_plus(keyword)}"


def expand_user_data_dir(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path)))


def collect_facebook_marketplace(
    config: AgentConfig,
    data_path: Path,
    interactive: bool = True,
) -> FacebookCollectionSummary:
    if not config.enable_facebook_marketplace_collector:
        return FacebookCollectionSummary(diagnostics=["Facebook Marketplace collector is disabled in config."])
    if not config.facebook_search_keywords:
        return FacebookCollectionSummary(diagnostics=["No facebookSearchKeywords configured."])

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run: py -m pip install -e . && py -m playwright install chromium"
        ) from exc

    summary = FacebookCollectionSummary(keywords_searched=list(config.facebook_search_keywords))
    user_data_dir = expand_user_data_dir(config.facebook_user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)
    incoming: list[MarketObservation] = []
    seen_urls: set[str] = set()

    with sync_playwright() as playwright:
        browser = None
        launched_process = None
        search_page = None
        try:
            context, browser, launched_process = _open_facebook_browser(playwright, config, user_data_dir, summary)
        except Exception as exc:
            summary.diagnostics.append(
                "Facebook browser launch failed. Details: "
                f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
            )
            return summary
        try:
            search_page = context.new_page()
            page = search_page
            _ensure_facebook_ready(page, config, interactive)
            detail_budget = config.max_detail_pages_per_run
            for keyword in config.facebook_search_keywords:
                url = build_marketplace_search_url(keyword, config.facebook_marketplace_location_slug)
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                _delay(config)
                _stop_for_challenge_if_present(page, config, interactive)
                _wait_for_results_best_effort(page, PlaywrightTimeoutError)

                for _ in range(config.max_scrolls_per_keyword):
                    page.mouse.wheel(0, 2200)
                    _delay(config)

                cards = _collect_listing_cards(page, keyword, config.max_listings_per_keyword)
                if not cards:
                    summary.diagnostics.append(_zero_cards_diagnostic(page, keyword))
                for card in cards:
                    normalized_url = normalize_facebook_listing_url(card.url)
                    if normalized_url in seen_urls:
                        continue
                    seen_urls.add(normalized_url)
                    summary.listings_found += 1

                    detail_text = ""
                    detail_metadata: dict[str, object] = {}
                    if config.open_detail_pages and detail_budget > 0:
                        detail_budget -= 1
                        summary.detail_pages_opened += 1
                        detail_text, detail_metadata = _collect_detail_page(context, normalized_url, config, interactive)

                    observation = card_to_observation(card, detail_text, detail_metadata)
                    observation.url = normalized_url
                    incoming.append(score_observation(observation, config))
        finally:
            if search_page:
                try:
                    search_page.close()
                except Exception:
                    pass
            _close_facebook_browser(context, browser, launched_process, config)

    existing = load_observations(data_path)
    existing_keys = {observation_key(item) for item in existing}
    merged, new_items, changes = merge_observations(existing, incoming)
    rescored = [score_observation(item, config) for item in merged]
    save_observations(rescored, data_path)

    summary.new_observations = len(new_items)
    summary.duplicates_skipped = max(0, len(incoming) - len([item for item in incoming if observation_key(item) not in existing_keys]))
    summary.diagnostics.extend(changes)
    summary.high_signal_listings = sorted(
        [
            item
            for item in new_items
            if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"} and item.overall_signal_score >= 7
        ],
        key=lambda item: item.overall_signal_score,
        reverse=True,
    )[:10]
    summary.average_price_by_category = _average_price_by_category(rescored)
    summary.delivery_gap_count = sum(1 for item in incoming if item.pickup_required and not item.delivery_mentioned)
    summary.assembly_gap_count = sum(1 for item in incoming if item.assembly_mentioned)
    summary.decision, summary.decision_reasons = decision_check(rescored, config)
    if summary.listings_found == 0 and not summary.diagnostics:
        summary.diagnostics.append(
            "No Facebook Marketplace listings were captured. Verify login/session, Marketplace location, and whether the page layout changed."
        )
    return summary


def diagnose_facebook_collector(config: AgentConfig, attempt_launch: bool = False) -> FacebookDiagnostic:
    checks: list[str] = []
    recommendations: list[str] = []
    endpoint = _facebook_cdp_endpoint(config)
    user_data_dir = expand_user_data_dir(config.facebook_user_data_dir)
    chrome_path = _find_chrome_executable(config.facebook_chrome_executable_path)

    checks.append(f"Collector enabled: {config.enable_facebook_marketplace_collector}")
    checks.append(f"Launch mode: {config.facebook_launch_mode}")
    checks.append(f"Marketplace URL: {_marketplace_home_url(config)}")
    checks.append(f"User data dir: {user_data_dir}")
    checks.append(f"Chrome executable: {chrome_path or 'not found'}")
    checks.append(f"CDP endpoint: {endpoint}")
    checks.append(f"CDP endpoint reachable: {_cdp_endpoint_available(endpoint)}")
    remote_debugging_processes = _chrome_remote_debugging_processes()
    checks.append(f"Chrome remote-debugging processes: {len(remote_debugging_processes)}")
    for process in remote_debugging_processes[:5]:
        checks.append(f"- PID {process.get('pid')}: {process.get('command_line')}")

    try:
        import playwright  # noqa: F401

        checks.append("Playwright import: ok")
    except ImportError:
        checks.append("Playwright import: missing")
        recommendations.append("Install Playwright runtime: py -m pip install -e . && py -m playwright install chromium")

    if not config.enable_facebook_marketplace_collector:
        recommendations.append("Enable enableFacebookMarketplaceCollector to run Facebook collection.")
    if not chrome_path:
        recommendations.append("Install Google Chrome or set facebookChromeExecutablePath.")
    if config.facebook_launch_mode == "cdp" and not _cdp_endpoint_available(endpoint):
        recommendations.append(
            "CDP endpoint is not reachable. A local Chrome instance must be running with "
            f"--remote-debugging-port={config.facebook_cdp_port} before collection can attach."
        )

    if attempt_launch and chrome_path:
        launch_result = _diagnostic_launch_chrome(chrome_path, config, user_data_dir, endpoint)
        checks.extend(launch_result)
        if not _cdp_endpoint_available(endpoint):
            recommendations.append(
                "Diagnostic launch did not open the CDP endpoint. In this Windows session, Chrome may not allow "
                "remote-debugging launch from the automation shell; routine will keep logging this cleanly."
            )

    status = "ok" if _cdp_endpoint_available(endpoint) or config.facebook_launch_mode != "cdp" else "blocked"
    return FacebookDiagnostic(status=status, checks=checks, recommendations=recommendations)


def import_facebook_capture_file(capture_path: Path, data_path: Path, config: AgentConfig) -> FacebookCollectionSummary:
    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    cards_payload = payload.get("cards", []) if isinstance(payload, dict) else []
    keywords = sorted({str(item.get("search_keyword", "")) for item in cards_payload if item.get("search_keyword")})
    summary = FacebookCollectionSummary(keywords_searched=keywords)
    incoming: list[MarketObservation] = []
    seen_urls: set[str] = set()
    for item in cards_payload:
        if not isinstance(item, dict):
            continue
        url = normalize_facebook_listing_url(str(item.get("url", "")))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        card = FacebookCard(
            title=str(item.get("title", "")),
            price=_coerce_price(item.get("price")),
            location=str(item.get("location", "")),
            url=url,
            thumbnail_url=str(item.get("thumbnail_url", "")),
            raw_text=str(item.get("raw_text", "")),
            search_keyword=str(item.get("search_keyword", "")),
        )
        observation = card_to_observation(card, str(item.get("detail_text", "")), item.get("detail_metadata") or {})
        observation.source_metadata.update(
            {
                "capture_method": "chrome_extension_visible_tab",
                "capture_url": payload.get("url", ""),
                "captured_at": payload.get("captured_at", ""),
            }
        )
        incoming.append(score_observation(observation, config))
        summary.listings_found += 1

    existing = load_observations(data_path)
    existing_keys = {observation_key(item) for item in existing}
    merged, new_items, changes = merge_observations(existing, incoming)
    rescored = [score_observation(item, config) for item in merged]
    save_observations(rescored, data_path)
    summary.new_observations = len(new_items)
    summary.duplicates_skipped = sum(1 for item in incoming if observation_key(item) in existing_keys)
    summary.diagnostics.extend(changes)
    summary.high_signal_listings = sorted(
        [
            item
            for item in new_items
            if item.target_sku_fit in {"4x6_horizontal", "6x5_vertical"} and item.overall_signal_score >= 7
        ],
        key=lambda item: item.overall_signal_score,
        reverse=True,
    )[:10]
    summary.average_price_by_category = _average_price_by_category(rescored)
    summary.delivery_gap_count = sum(1 for item in incoming if item.pickup_required and not item.delivery_mentioned)
    summary.assembly_gap_count = sum(1 for item in incoming if item.assembly_mentioned)
    summary.decision, summary.decision_reasons = decision_check(rescored, config)
    if not incoming:
        summary.diagnostics.append(f"No importable Facebook cards found in {capture_path}.")
    return summary


def card_to_observation(card: FacebookCard, detail_text: str = "", detail_metadata: dict[str, object] | None = None) -> MarketObservation:
    detail_metadata = detail_metadata or {}
    raw_parts = [card.title, card.raw_text, detail_text]
    raw_text = "\n".join(part for part in raw_parts if part).strip()
    raw_lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    parsed_title = _best_title_from_lines(raw_lines, card.search_keyword)
    parsed_location = _best_location_from_lines(raw_lines)
    observation = extract_listing(
        raw_text,
        source="facebook_marketplace",
        source_type=FACEBOOK_SOURCE_TYPE,
        url=normalize_facebook_listing_url(card.url),
        location=str(detail_metadata.get("location") or parsed_location or card.location),
    )
    if card.price is not None:
        observation.price = card.price
    if detail_metadata.get("title"):
        observation.title = str(detail_metadata["title"])
    elif parsed_title:
        observation.title = parsed_title
    elif card.title:
        observation.title = card.title
    if detail_metadata.get("condition"):
        observation.condition = str(detail_metadata["condition"])
    if detail_metadata.get("posted_time"):
        observation.posted_time = str(detail_metadata["posted_time"])
    if detail_metadata.get("listing_status"):
        observation.listing_status = str(detail_metadata["listing_status"])
    else:
        observation.listing_status = "active"
    observation.search_keyword = card.search_keyword
    observation.thumbnail_url = card.thumbnail_url
    observation.image_urls = [str(url) for url in detail_metadata.get("image_urls", []) if url]
    observation.source_metadata = {
        "search_keyword": card.search_keyword,
        "thumbnail_url": card.thumbnail_url,
        "detail_metadata": detail_metadata,
        "fast_moving_signal": fast_moving_signal(raw_text),
        "missing_parts_or_damage_risk": missing_parts_or_damage_risk(raw_text),
    }
    return observation


def _coerce_price(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d{1,5}(?:,\d{3})?(?:\.\d{2})?", str(value))
    return float(match.group(0).replace(",", "")) if match else None


def normalize_facebook_listing_url(url: str) -> str:
    absolute = urljoin("https://www.facebook.com", url)
    parsed = urlparse(absolute)
    match = re.search(r"/marketplace/item/[^/?#]+", parsed.path)
    if match:
        return f"https://www.facebook.com{match.group(0)}"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def format_collection_summary(summary: FacebookCollectionSummary) -> str:
    lines = [
        "Facebook Marketplace Collection Summary",
        "",
        f"Keywords searched: {len(summary.keywords_searched)}",
        f"Listings captured: {summary.listings_found}",
        f"New observations: {summary.new_observations}",
        f"Duplicates skipped: {summary.duplicates_skipped}",
        f"Detail pages opened: {summary.detail_pages_opened}",
        f"High-signal listings: {len(summary.high_signal_listings)}",
        "",
        "Top signals:",
    ]
    if summary.high_signal_listings:
        for index, item in enumerate(summary.high_signal_listings[:5], start=1):
            price = f"${item.price:.0f}" if item.price is not None else "unknown price"
            lines.append(
                f"{index}. {item.title} - {price} - {item.location or 'unknown'} - "
                f"target_sku_fit: {item.target_sku_fit} - overall {item.overall_signal_score}/10"
            )
    else:
        lines.append("No high-signal listings captured in this run.")

    lines.extend(["", "Average price by inferred category:"])
    if summary.average_price_by_category:
        for category, average_price in sorted(summary.average_price_by_category.items()):
            lines.append(f"- {category}: ${average_price:.0f}")
    else:
        lines.append("- No priced observations yet.")

    lines.extend(
        [
            "",
            "Delivery / assembly gap signals:",
            f"- Pickup without delivery: {summary.delivery_gap_count}",
            f"- Assembly/disassembly mentions: {summary.assembly_gap_count}",
            "",
            "Decision:",
            summary.decision,
        ]
    )
    lines.extend(f"- {reason}" for reason in summary.decision_reasons)
    if summary.diagnostics:
        lines.extend(["", "Diagnostics:"])
        lines.extend(f"- {item}" for item in summary.diagnostics[:20])
    return "\n".join(lines)


def _open_facebook_browser(playwright, config: AgentConfig, user_data_dir: Path, summary: FacebookCollectionSummary):
    mode = str(config.facebook_launch_mode or "persistent_playwright").lower()
    if mode == "cdp":
        return _open_facebook_browser_cdp(playwright, config, user_data_dir, summary)
    if mode not in {"persistent_playwright", "persistent"}:
        summary.diagnostics.append(
            f"Unknown facebookLaunchMode '{config.facebook_launch_mode}', falling back to persistent_playwright."
        )
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=config.headless,
        viewport={"width": 1365, "height": 900},
    )
    return context, None, None


def _open_facebook_browser_cdp(playwright, config: AgentConfig, user_data_dir: Path, summary: FacebookCollectionSummary):
    endpoint = _facebook_cdp_endpoint(config)
    launched_process = None
    if not _cdp_endpoint_available(endpoint):
        if not config.facebook_start_chrome_for_cdp:
            raise RuntimeError(f"Chrome CDP endpoint is not available at {endpoint}.")
        chrome_path = _find_chrome_executable(config.facebook_chrome_executable_path)
        if not chrome_path:
            raise RuntimeError("Google Chrome executable was not found for facebookLaunchMode=cdp.")
        launched_process = _start_chrome_for_cdp(chrome_path, config, user_data_dir)
        if not _wait_for_cdp_endpoint(endpoint, timeout_seconds=20):
            raise RuntimeError(
                f"Started Chrome for CDP, but the endpoint did not become available at {endpoint}."
            )
        summary.diagnostics.append("Started local Chrome with remote debugging for Facebook collection.")
    else:
        summary.diagnostics.append("Connected to existing local Chrome remote debugging endpoint.")

    browser = playwright.chromium.connect_over_cdp(endpoint)
    if browser.contexts:
        context = browser.contexts[0]
    else:
        context = browser.new_context(viewport={"width": 1365, "height": 900})
    return context, browser, launched_process


def _close_facebook_browser(context, browser, launched_process, config: AgentConfig) -> None:
    mode = str(config.facebook_launch_mode or "persistent_playwright").lower()
    if mode == "cdp":
        # Leave local Chrome/session intact; closing a CDP browser can close the user's visible Chrome window.
        return
    try:
        context.close()
    except Exception:
        pass


def _facebook_cdp_endpoint(config: AgentConfig) -> str:
    if config.facebook_cdp_url:
        return config.facebook_cdp_url.rstrip("/")
    return f"http://127.0.0.1:{int(config.facebook_cdp_port)}"


def _cdp_endpoint_available(endpoint: str) -> bool:
    try:
        with urlopen(f"{endpoint}/json/version", timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def _wait_for_cdp_endpoint(endpoint: str, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _cdp_endpoint_available(endpoint):
            return True
        time.sleep(0.5)
    return False


def _start_chrome_for_cdp(chrome_path: Path, config: AgentConfig, user_data_dir: Path):
    args = [
        str(chrome_path),
        f"--remote-debugging-port={int(config.facebook_cdp_port)}",
        f"--user-data-dir={str(user_data_dir)}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        _marketplace_home_url(config),
    ]
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _diagnostic_launch_chrome(chrome_path: Path, config: AgentConfig, user_data_dir: Path, endpoint: str) -> list[str]:
    lines = ["Attempting diagnostic Chrome CDP launch."]
    try:
        process = _start_chrome_for_cdp(chrome_path, config, user_data_dir)
        time.sleep(8)
        exit_code = process.poll()
        lines.append(f"Diagnostic Chrome process PID: {process.pid}")
        lines.append(f"Diagnostic Chrome process exit code after 8s: {exit_code}")
        lines.append(f"CDP endpoint reachable after diagnostic launch: {_cdp_endpoint_available(endpoint)}")
    except Exception as exc:
        lines.append(f"Diagnostic Chrome launch failed: {type(exc).__name__}: {str(exc).splitlines()[0]}")
    return lines


def _find_chrome_executable(configured_path: str = "") -> Path | None:
    candidates: list[Path] = []
    if configured_path:
        candidates.append(Path(os.path.expandvars(os.path.expanduser(configured_path))))
    for value in (
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ):
        if value:
            candidates.append(Path(value))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _chrome_remote_debugging_processes() -> list[dict[str, object]]:
    if os.name != "nt":
        return []
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
            "Where-Object { $_.CommandLine -like '*remote-debugging-port*' } | "
            "ForEach-Object { [pscustomobject]@{ pid=$_.ProcessId; command_line=$_.CommandLine } } | "
            "ConvertTo-Json -Compress"
        ),
    ]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=10)
    except Exception:
        return []
    text = result.stdout.strip()
    if not text:
        return []
    try:
        import json

        parsed = json.loads(text)
    except Exception:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def extract_card_from_text(raw_text: str, url: str, keyword: str = "", thumbnail_url: str = "") -> FacebookCard:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    title = _best_title_from_lines(lines, keyword)
    return FacebookCard(
        title=title,
        price=_extract_price(raw_text),
        location=_best_location_from_lines(lines) or _extract_location_from_text(raw_text),
        url=normalize_facebook_listing_url(url),
        thumbnail_url=thumbnail_url,
        raw_text=raw_text,
        search_keyword=keyword,
    )


def extract_detail_metadata(raw_text: str, image_urls: list[str] | None = None) -> dict[str, object]:
    lower_text = raw_text.lower()
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return {
        "title": _best_title_from_lines(lines),
        "price": _extract_price(raw_text),
        "location": _best_location_from_lines(lines),
        "condition": _extract_condition(raw_text),
        "posted_time": _extract_posted_time(lines),
        "listing_status": _extract_status(lower_text),
        "fast_moving_signal": fast_moving_signal(raw_text),
        "missing_parts_or_damage_risk": missing_parts_or_damage_risk(raw_text),
        "image_urls": image_urls or [],
    }


def _collect_listing_cards(page, keyword: str, limit: int) -> list[FacebookCard]:
    cards: list[FacebookCard] = []
    anchors = page.locator('a[href*="/marketplace/item/"]')
    count = min(anchors.count(), limit * 3)
    seen_urls: set[str] = set()
    for index in range(count):
        if len(cards) >= limit:
            break
        anchor = anchors.nth(index)
        try:
            href = anchor.get_attribute("href")
            if not href:
                continue
            url = normalize_facebook_listing_url(href)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            raw_text = anchor.evaluate(
                """element => {
                    let best = element;
                    let node = element;
                    for (let i = 0; i < 7 && node; i++) {
                        const text = node.innerText || '';
                        const lines = text.split('\\n').filter(Boolean);
                        if (lines.length >= 3 && text.length > (best.innerText || '').length) {
                            best = node;
                        }
                        if (text.length > 500) {
                            break;
                        }
                        node = node.parentElement;
                    }
                    return best.innerText || element.innerText || '';
                }"""
            )
            if not raw_text or len(raw_text.strip()) < 3:
                raw_text = anchor.inner_text(timeout=2000)
            if not _looks_like_listing_text(raw_text):
                parent_text = anchor.evaluate(
                    """element => {
                        const parent = element.closest('[role="article"]') || element.parentElement;
                        return parent ? (parent.innerText || '') : '';
                    }"""
                )
                if _looks_like_listing_text(parent_text):
                    raw_text = parent_text
            thumbnail_url = ""
            images = anchor.locator("img")
            if images.count():
                thumbnail_url = images.first().get_attribute("src") or ""
            card = extract_card_from_text(raw_text, url, keyword, thumbnail_url)
            if card.title and (card.price is not None or keyword.lower() in card.raw_text.lower()):
                cards.append(card)
        except Exception:
            continue
    return cards


def _looks_like_listing_text(raw_text: str) -> bool:
    return bool(raw_text and ("$" in raw_text or re.search(r"\b(free|pending|sold)\b", raw_text, re.I)))


def _zero_cards_diagnostic(page, keyword: str) -> str:
    try:
        url = page.url
        title = page.title()
        body_text = page.locator("body").inner_text(timeout=3000)
        snippet = re.sub(r"\s+", " ", body_text).strip()[:220]
        anchor_count = page.locator('a[href*="/marketplace/item/"]').count()
        return (
            f"No listing cards found for keyword '{keyword}'. "
            f"URL: {url}. Title: {title}. Marketplace item link count: {anchor_count}. Page text sample: {snippet}"
        )
    except Exception as exc:
        return f"No listing cards found for keyword '{keyword}', and page diagnostics failed: {exc}"


def _collect_detail_page(context, url: str, config: AgentConfig, interactive: bool = True) -> tuple[str, dict[str, object]]:
    page = context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        _delay(config)
        _stop_for_challenge_if_present(page, config, interactive)
        raw_text = page.locator("body").inner_text(timeout=10000)
        image_urls = _collect_image_urls(page)
        metadata = extract_detail_metadata(raw_text, image_urls)
        return raw_text, metadata
    except Exception as exc:
        return "", {"error": str(exc)}
    finally:
        page.close()


def _ensure_facebook_ready(page, config: AgentConfig, interactive: bool = True) -> None:
    page.goto(_marketplace_home_url(config), wait_until="domcontentloaded", timeout=60000)
    _delay(config)
    if _login_or_challenge_visible(page):
        if not interactive:
            raise RuntimeError(
                "Facebook login/session challenge detected. Run `py -m shed_agent.cli fb-collect` interactively to refresh the session."
            )
        print("Facebook login or security challenge detected.")
        print("Please complete it in the visible browser window. The collector will resume automatically when the page clears.")
        if not _wait_for_manual_resolution(page, config):
            raise RuntimeError("Timed out waiting for manual Facebook login/challenge handling.")
    _stop_for_challenge_if_present(page, config, interactive)


def _stop_for_challenge_if_present(page, config: AgentConfig, interactive: bool = True) -> None:
    if _login_or_challenge_visible(page):
        if not interactive:
            raise RuntimeError(
                "Facebook login/session challenge detected. Run the interactive collector manually; no bypass attempted."
            )
        print("Facebook login/challenge/access warning is visible.")
        print("Handle it manually in the browser. The collector will resume automatically when the page clears.")
        if not _wait_for_manual_resolution(page, config):
            raise RuntimeError("Timed out waiting for manual Facebook login/challenge handling.")
        if _login_or_challenge_visible(page):
            raise RuntimeError("Facebook challenge/login is still present; stopping without bypassing.")


def _marketplace_home_url(config: AgentConfig) -> str:
    slug = config.facebook_marketplace_location_slug.strip("/")
    return f"{MARKETPLACE_BASE_URL}/{slug}/" if slug else f"{MARKETPLACE_BASE_URL}/"


def _login_or_challenge_visible(page) -> bool:
    try:
        current_url = page.url.lower()
        text = page.locator("body").inner_text(timeout=5000).lower()
    except Exception:
        return False
    return login_or_challenge_detected(current_url, text)


def login_or_challenge_detected(current_url: str, page_text: str) -> bool:
    current_url = current_url.lower()
    page_text = page_text.lower()
    return any(term in current_url for term in CHALLENGE_URL_TERMS) or any(term in page_text for term in CHALLENGE_TERMS)


def _wait_for_manual_resolution(page, config: AgentConfig) -> bool:
    deadline = time.monotonic() + config.facebook_manual_challenge_timeout_seconds
    while time.monotonic() < deadline:
        try:
            if not _login_or_challenge_visible(page):
                return True
            page.wait_for_timeout(2000)
        except Exception:
            time.sleep(2)
    return False


def _wait_for_results_best_effort(page, timeout_error_type) -> None:
    try:
        page.locator('a[href*="/marketplace/item/"]').first.wait_for(timeout=15000)
    except timeout_error_type:
        return


def _collect_image_urls(page) -> list[str]:
    urls = []
    images = page.locator("img")
    for index in range(min(images.count(), 20)):
        try:
            src = images.nth(index).get_attribute("src")
            if src and src.startswith("http") and src not in urls:
                urls.append(src)
        except Exception:
            continue
    return urls


def _delay(config: AgentConfig) -> None:
    delay = config.delay_between_actions_ms
    if isinstance(delay, list) and len(delay) >= 2:
        milliseconds = random.randint(int(delay[0]), int(delay[1]))
    else:
        milliseconds = int(delay)
    time.sleep(milliseconds / 1000)


def _average_price_by_category(observations: list[MarketObservation]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for item in observations:
        if item.price is not None:
            buckets[item.inferred_size_category].append(item.price)
    return {category: mean(prices) for category, prices in buckets.items() if prices}


def _best_title_from_lines(lines: list[str], keyword: str = "") -> str:
    keyword_terms = [term for term in re.split(r"\s+", keyword.lower()) if len(term) > 2]
    fallback = ""
    for line in lines:
        if _is_noise_line(line) or _looks_like_location(line) or _is_price_line(line):
            continue
        if len(line) > 3 and any(term in line.lower() for term in keyword_terms):
            return line
        if len(line) > 3 and not fallback:
            fallback = line
    if fallback:
        return fallback
    for line in lines:
        if not _is_noise_line(line) and "$" not in line:
            return line
    return lines[0] if lines else ""


def _best_location_from_lines(lines: list[str]) -> str:
    for line in lines:
        if _looks_like_location(line):
            return _extract_location_from_text(line) or line
    return ""


def _extract_location_from_text(text: str) -> str:
    match = re.search(r"\b([A-Z][A-Za-z .'-]+,\s*(?:MA|Massachusetts|NH|RI|CT|ME|VT|NY|CA))\b", text)
    return match.group(1).strip() if match else ""


def _looks_like_location(line: str) -> bool:
    return bool(
        re.search(
            r"\b(MA|Massachusetts|Lexington|Burlington|Waltham|Arlington|Bedford|Belmont|Winchester|Newton|Cambridge|Somerville|Medford|Watertown|Concord|Acton|Needham|Woburn)\b",
            line,
            re.I,
        )
    )


def _is_noise_line(line: str) -> bool:
    return bool(
        re.search(
            r"^(just listed|listed|posted|sponsored|facebook marketplace|marketplace|ships|seller|message|save|share|see details|more options|today|yesterday|nearby|results)\b",
            line.strip(),
            re.I,
        )
    )


def _is_price_line(line: str) -> bool:
    return bool("$" in line or re.fullmatch(r"free", line.strip(), re.I))


def _extract_price(text: str) -> float | None:
    match = re.search(r"\$(\d{1,5}(?:,\d{3})?(?:\.\d{2})?)", text)
    return float(match.group(1).replace(",", "")) if match else None


def _extract_condition(text: str) -> str:
    lower_text = text.lower()
    for condition in ("new", "like new", "good", "fair", "used"):
        if re.search(rf"\bcondition\b.*\b{re.escape(condition)}\b|\b{re.escape(condition)} condition\b", lower_text):
            return condition
    return ""


def _extract_posted_time(lines: list[str]) -> str:
    for line in lines:
        if re.search(r"\b(listed|posted)\b", line, re.I):
            return line
    return ""


def _extract_status(lower_text: str) -> str:
    if any(term in lower_text for term in ("sold", "pending", "unavailable", "no longer available")):
        return "sold"
    return "active"
