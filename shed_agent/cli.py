from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from shed_agent.config import DEFAULT_CONFIG_PATH, load_config
from shed_agent.deduplicate import deduplicate_observations
from shed_agent.decision import decision_check
from shed_agent.extract_listing import extract_listing, refresh_extraction
from shed_agent.facebook_marketplace import (
    collect_facebook_marketplace,
    diagnose_facebook_collector,
    format_collection_summary,
    import_facebook_capture_file,
)
from shed_agent.generate_dashboard import generate_dashboard_html
from shed_agent.generate_daily_digest import generate_daily_digest
from shed_agent.generate_market_report import generate_market_report
from shed_agent.ingest import ingest_craigslist_rss, ingest_watchlist
from shed_agent.llm_analysis import analyze_observations_with_llm
from shed_agent.retail_comparable import add_retail_comparable_from_text, ingest_retail_comparable_urls
from shed_agent.routine import run_routine
from shed_agent.sample_data import build_sample_observations
from shed_agent.score_observation import score_observation
from shed_agent.status import update_listing_status
from shed_agent.storage import DEFAULT_DATA_PATH, add_observation, load_observations, save_observations
from shed_agent.supplier.config import DEFAULT_SUPPLIER_CONFIG_PATH, load_supplier_config
from shed_agent.supplier.conversation import analyze_supplier_thread
from shed_agent.supplier.followup import generate_follow_up_plan
from shed_agent.supplier.message_queue import (
    approve_message_draft,
    build_initial_rfq_draft,
    build_follow_up_draft,
    mark_message_sent_manually,
)
from shed_agent.supplier.models import ProductCandidate, Supplier, SupplierMessage, SupplierThread, now_iso
from shed_agent.supplier.report import generate_supplier_rfq_pack
from shed_agent.supplier.rfq import generate_rfq_template
from shed_agent.supplier.scoring import score_supplier_candidate
from shed_agent.supplier.storage import (
    DEFAULT_MESSAGE_QUEUE_PATH,
    DEFAULT_PRODUCTS_PATH,
    DEFAULT_SUPPLIERS_PATH,
    DEFAULT_THREADS_PATH,
    add_message_draft,
    add_product_candidate,
    add_supplier,
    load_message_queue,
    load_product_candidates,
    load_supplier_threads,
    load_suppliers,
    save_message_queue,
    save_product_candidates,
    save_suppliers,
    save_supplier_threads,
)


def main(argv: list[str] | None = None) -> int:
    _configure_console_encoding()
    parser = argparse.ArgumentParser(prog="shed-agent", description="Private local shed market monitoring agent.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to observations JSON.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config JSON.")
    parser.add_argument("--supplier-config", type=Path, default=DEFAULT_SUPPLIER_CONFIG_PATH, help="Path to supplier config JSON.")
    parser.add_argument("--suppliers-data", type=Path, default=DEFAULT_SUPPLIERS_PATH, help="Path to suppliers JSON.")
    parser.add_argument("--products-data", type=Path, default=DEFAULT_PRODUCTS_PATH, help="Path to product candidates JSON.")
    parser.add_argument("--threads-data", type=Path, default=DEFAULT_THREADS_PATH, help="Path to supplier threads JSON.")
    parser.add_argument("--message-queue-data", type=Path, default=DEFAULT_MESSAGE_QUEUE_PATH, help="Path to supplier message queue JSON.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add-observation", help="Manually add and score a listing or raw text.")
    add_parser.add_argument("--source", default="manual")
    add_parser.add_argument("--source-type", default="manual")
    add_parser.add_argument("--text", help="Raw listing text. If omitted, you will be prompted.")
    add_parser.add_argument("--url", default="")
    add_parser.add_argument("--location", default="")
    add_parser.add_argument("--status", default="unknown", choices=["active", "disappeared", "sold", "unknown"])
    add_parser.add_argument("--notes", default="")

    snippet_parser = subparsers.add_parser("add-local-snippet", help="Add a local demand snippet from Nextdoor, local FB groups, or pasted local posts.")
    snippet_parser.add_argument(
        "--source-type",
        default="manual_local_post",
        choices=["manual_local_post", "nextdoor_snippet", "local_facebook_group_snippet", "manual"],
    )
    snippet_parser.add_argument("--source", default="local_snippet")
    snippet_parser.add_argument("--text", help="Raw local post/snippet text. If omitted, you will be prompted.")
    snippet_parser.add_argument("--url", default="")
    snippet_parser.add_argument("--location", default="")
    snippet_parser.add_argument("--notes", default="")

    retail_parser = subparsers.add_parser("add-retail-comparable", help="Manually add a retail benchmark from pasted product text.")
    retail_parser.add_argument("--retailer", default="")
    retail_parser.add_argument("--source-type", default="")
    retail_parser.add_argument("--url", default="")
    retail_parser.add_argument("--text", help="Raw retail product page text. If omitted, you will be prompted.")
    retail_parser.add_argument("--notes", default="")

    retail_fetch_parser = subparsers.add_parser("ingest-retail-comparables", help="Low-frequency fetch of configured retail comparable URLs.")
    retail_fetch_parser.add_argument("--url", action="append", help="Retail URL. Can be provided multiple times.")

    rss_parser = subparsers.add_parser("ingest-craigslist-rss", help="Fetch configured Craigslist RSS feeds.")
    rss_parser.add_argument("--url", action="append", help="RSS URL. Can be provided multiple times.")

    watch_parser = subparsers.add_parser("ingest-watchlist", help="Fetch or register configured watchlist URLs.")
    watch_parser.add_argument("--url", action="append", help="Watchlist URL. Can be provided multiple times.")

    subparsers.add_parser("fb-collect", help="Run the local Playwright Facebook Marketplace collector.")
    fb_diag_parser = subparsers.add_parser("fb-diagnose", help="Diagnose local Facebook Marketplace collector readiness.")
    fb_diag_parser.add_argument("--attempt-launch", action="store_true", help="Try a short local Chrome CDP launch and report the result.")

    fb_import_parser = subparsers.add_parser("import-facebook-capture", help="Import a conservative Chrome-extension Facebook capture JSON file.")
    fb_import_parser.add_argument("capture", type=Path, help="Path to capture JSON.")
    subparsers.add_parser("routine", help="Run the full local scheduled-agent routine.")
    subparsers.add_parser("analyze-llm", help="Run LLM-assisted analysis for new or changed observations.")

    subparsers.add_parser("analyze-observations", help="Refresh extraction/scoring and deduplicate saved observations.")
    subparsers.add_parser("list-observations", help="List saved observations.")

    analyze_one = subparsers.add_parser("analyze-observation", help="Analyze raw listing text without saving.")
    analyze_one.add_argument("--source", default="manual")
    analyze_one.add_argument("--source-type", default="manual")
    analyze_one.add_argument("--text", help="Raw listing text. If omitted, you will be prompted.")

    status_parser = subparsers.add_parser("update-status", help="Manually update status or check URL-based sources.")
    status_parser.add_argument("--id", help="Observation ID for a manual status update.")
    status_parser.add_argument("--status", choices=["active", "disappeared", "sold", "unknown"])
    status_parser.add_argument("--check-urls", action="store_true")

    daily_parser = subparsers.add_parser("generate-daily-digest", help="Generate a daily Markdown digest.")
    daily_parser.add_argument("--out", type=Path)

    weekly_parser = subparsers.add_parser("generate-weekly-report", help="Generate the weekly Local Shed Market Report.")
    weekly_parser.add_argument("--out", type=Path)

    dashboard_parser = subparsers.add_parser("generate-dashboard", help="Generate a local HTML dashboard for the active observation window.")
    dashboard_parser.add_argument("--out", type=Path)

    subparsers.add_parser("decision-check", help="Evaluate threshold-based market recommendation.")

    export_parser = subparsers.add_parser("export-report", help="Alias for generate-weekly-report with default output.")
    export_parser.add_argument("--out", type=Path)

    legacy_report = subparsers.add_parser("generate-report", help="Alias for generate-weekly-report.")
    legacy_report.add_argument("--out", type=Path)

    subparsers.add_parser("seed-sample-data", help="Write sample observations for testing.")

    supplier_parser = subparsers.add_parser("add-supplier", help="Add a supplier to the private sourcing workflow.")
    supplier_parser.add_argument("--name", required=True)
    supplier_parser.add_argument("--platform", default="other")
    supplier_parser.add_argument("--url", default="")
    supplier_parser.add_argument("--contact-name", default="")
    supplier_parser.add_argument("--contact-channel", default="")
    supplier_parser.add_argument("--contact-email", default="")
    supplier_parser.add_argument("--location", default="")
    supplier_parser.add_argument("--us-export-experience", choices=["yes", "no", "unknown"], default="unknown")
    supplier_parser.add_argument("--export-notes", default="")
    supplier_parser.add_argument("--notes", default="")
    supplier_parser.add_argument("--status", choices=["new", "contacted", "replied", "waiting", "strong_candidate", "rejected", "archived"], default="new")

    product_parser = subparsers.add_parser("add-product-candidate", help="Add a supplier product candidate.")
    product_parser.add_argument("--supplier-id", required=True)
    product_parser.add_argument("--name", required=True)
    product_parser.add_argument("--url", default="")
    product_parser.add_argument("--product-type", choices=["4x6_horizontal", "6x5_vertical", "deck_box", "accessory", "other"], default="other")
    product_parser.add_argument("--external-dimensions", default="")
    product_parser.add_argument("--internal-dimensions", default="")
    product_parser.add_argument("--material", default="unknown")
    product_parser.add_argument("--has-floor", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--uv-weather-resistant", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--color", default="")
    product_parser.add_argument("--unit-price", type=float)
    product_parser.add_argument("--currency", default="USD")
    product_parser.add_argument("--moq", type=int)
    product_parser.add_argument("--price-tier", action="append", help="Price tier in QUANTITY=PRICE format. Can be repeated.")
    product_parser.add_argument("--sample-cost", type=float)
    product_parser.add_argument("--sample-lead-time", default="")
    product_parser.add_argument("--production-lead-time", default="")
    product_parser.add_argument("--carton-size", default="")
    product_parser.add_argument("--gross-weight", type=float)
    product_parser.add_argument("--net-weight", type=float)
    product_parser.add_argument("--cartons-per-unit", type=int)
    product_parser.add_argument("--shipping-estimate", type=float)
    product_parser.add_argument("--shipping-terms", default="")
    product_parser.add_argument("--packaging-notes", default="")
    product_parser.add_argument("--english-manual", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--installation-video", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--spare-parts", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--neutral-branding", choices=["yes", "no", "unknown"], default="unknown")
    product_parser.add_argument("--warranty-notes", default="")
    product_parser.add_argument("--assembly-notes", default="")
    product_parser.add_argument("--quote-date", default="")
    product_parser.add_argument("--follow-up-status", default="not_started")
    product_parser.add_argument("--risk-note", action="append")
    product_parser.add_argument("--quote-text", default="")
    product_parser.add_argument("--quote-file", type=Path)

    subparsers.add_parser("list-suppliers", help="List saved suppliers.")
    subparsers.add_parser("list-product-candidates", help="List saved supplier product candidates.")

    rfq_parser = subparsers.add_parser("generate-rfq-template", help="Generate Chinese and English supplier RFQ text.")
    rfq_parser.add_argument("--product-type", choices=["4x6_horizontal", "6x5_vertical"], required=True)
    rfq_parser.add_argument("--language", choices=["english", "chinese", "both"], default="both")
    rfq_parser.add_argument("--out", type=Path)
    rfq_parser.add_argument("--queue-for-supplier", help="Supplier ID to queue this RFQ for human approval.")
    rfq_parser.add_argument("--thread-id", help="Existing supplier thread ID when queueing an RFQ.")
    rfq_parser.add_argument("--product-id", action="append", help="Product candidate ID to attach to the queued RFQ.")

    message_parser = subparsers.add_parser("add-supplier-message", help="Add pasted supplier conversation text.")
    message_parser.add_argument("--supplier-id", required=True)
    message_parser.add_argument("--thread-id")
    message_parser.add_argument("--product-id", action="append")
    message_parser.add_argument("--direction", choices=["inbound", "outbound_draft", "outbound_sent"], default="inbound")
    message_parser.add_argument("--language", default="unknown")
    message_parser.add_argument("--text")
    message_parser.add_argument("--text-file", type=Path)
    message_parser.add_argument("--source", default="manual")

    analyze_thread_parser = subparsers.add_parser("analyze-supplier-thread", help="Extract quote details and update supplier conversation state.")
    analyze_thread_parser.add_argument("--thread-id", required=True)

    follow_up_parser = subparsers.add_parser("generate-follow-up-draft", help="Create a pending supplier follow-up draft.")
    follow_up_parser.add_argument("--thread-id", required=True)

    subparsers.add_parser("list-message-queue", help="List supplier message drafts and approval status.")

    approve_parser = subparsers.add_parser("approve-message-draft", help="Approve a supplier draft for manual sending.")
    approve_parser.add_argument("--draft-id", required=True)

    sent_parser = subparsers.add_parser("mark-message-sent-manually", help="Record that an approved draft was sent manually.")
    sent_parser.add_argument("--draft-id", required=True)
    sent_parser.add_argument("--language", choices=["chinese", "english"], default="chinese")

    supplier_report_parser = subparsers.add_parser("generate-supplier-report", help="Generate the private Supplier RFQ Pack report.")
    supplier_report_parser.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    config = load_config(args.config)
    supplier_config = load_supplier_config(args.supplier_config)

    if args.command == "add-observation":
        raw_text = args.text or _read_multiline("Paste listing text, then press Ctrl+Z and Enter on Windows:")
        observation = extract_listing(raw_text, args.source, args.source_type, args.url, args.location)
        observation.listing_status = args.status
        observation.notes = args.notes
        observation = score_observation(observation, config)
        add_observation(observation, args.data)
        print(f"Saved observation {observation.id}")
        print(_format_observation(observation))
        return 0

    if args.command == "add-local-snippet":
        raw_text = args.text or _read_multiline("Paste local post/snippet text, then press Ctrl+Z and Enter on Windows:")
        observation = extract_listing(raw_text, args.source, args.source_type, args.url, args.location)
        observation.notes = args.notes
        observation.listing_status = "active" if args.url else "unknown"
        observation = score_observation(observation, config)
        add_observation(observation, args.data)
        print(f"Saved local demand snippet {observation.id}")
        print(_format_observation(observation))
        return 0

    if args.command == "ingest-craigslist-rss":
        count, changes = ingest_craigslist_rss(config, args.data, args.url)
        print(f"New observations added: {count}")
        for change in changes:
            print(f"- {change}")
        return 0

    if args.command == "ingest-watchlist":
        count, changes = ingest_watchlist(config, args.data, args.url)
        print(f"New observations added: {count}")
        for change in changes:
            print(f"- {change}")
        return 0

    if args.command == "add-retail-comparable":
        raw_text = args.text or _read_multiline("Paste retail product text, then press Ctrl+Z and Enter on Windows:")
        observation = add_retail_comparable_from_text(
            raw_text,
            url=args.url,
            retailer=args.retailer,
            source_type=args.source_type,
            notes=args.notes,
            config=config,
        )
        add_observation(observation, args.data)
        print(f"Saved retail comparable {observation.id}")
        print(_format_observation(observation))
        return 0

    if args.command == "ingest-retail-comparables":
        result = ingest_retail_comparable_urls(config, args.data, args.url)
        print(f"Retail comparables added: {result.added}")
        print(f"Retail pages blocked: {result.blocked}")
        print(f"Retail fetch failures: {result.failed}")
        for message in result.messages:
            print(f"- {message}")
        return 0

    if args.command == "fb-collect":
        summary = collect_facebook_marketplace(config, args.data)
        if config.enable_llm_analysis:
            llm_summary = analyze_observations_with_llm(args.data, config)
            print(
                f"LLM analysis: {llm_summary.analyzed} analyzed, {llm_summary.cache_hits} cache hits, "
                f"{llm_summary.fallback} fallback, {llm_summary.skipped_unchanged} skipped unchanged."
            )
        print(format_collection_summary(summary))
        return 0

    if args.command == "fb-diagnose":
        diagnostic = diagnose_facebook_collector(config, attempt_launch=args.attempt_launch)
        print(f"Facebook collector diagnostic status: {diagnostic.status}")
        print("Checks:")
        for check in diagnostic.checks:
            print(f"- {check}")
        print("Recommendations:")
        for recommendation in diagnostic.recommendations or ["No immediate recommendations."]:
            print(f"- {recommendation}")
        return 0

    if args.command == "import-facebook-capture":
        summary = import_facebook_capture_file(args.capture, args.data, config)
        if config.enable_llm_analysis:
            llm_summary = analyze_observations_with_llm(args.data, config)
            print(
                f"LLM analysis: {llm_summary.analyzed} analyzed, {llm_summary.cache_hits} cache hits, "
                f"{llm_summary.fallback} fallback, {llm_summary.skipped_unchanged} skipped unchanged."
            )
        print(format_collection_summary(summary))
        return 0

    if args.command == "routine":
        result = run_routine(args.data, config)
        print(f"Routine {result.status}. Exit code: {result.exit_code}")
        for message in result.messages:
            print(f"- {message}")
        for path in result.files_written:
            print(f"Wrote {path}")
        return result.exit_code

    if args.command == "analyze-observations":
        observations = [score_observation(refresh_extraction(item), config) for item in load_observations(args.data)]
        observations = deduplicate_observations(observations)
        save_observations([score_observation(item, config) for item in observations], args.data)
        print(f"Analyzed and deduplicated {len(observations)} observations.")
        return 0

    if args.command == "analyze-llm":
        llm_summary = analyze_observations_with_llm(args.data, config)
        print(
            f"LLM analysis complete: {llm_summary.analyzed} analyzed, {llm_summary.cache_hits} cache hits, "
            f"{llm_summary.fallback} fallback, {llm_summary.skipped_unchanged} skipped unchanged."
        )
        for error in llm_summary.errors[:5]:
            print(f"- {error}")
        return 0

    if args.command == "list-observations":
        observations = load_observations(args.data)
        if not observations:
            print("No observations saved yet.")
            return 0
        for observation in observations:
            print(_format_observation(observation))
        return 0

    if args.command == "analyze-observation":
        raw_text = args.text or _read_multiline("Paste listing text, then press Ctrl+Z and Enter on Windows:")
        observation = score_observation(extract_listing(raw_text, args.source, args.source_type), config)
        print(_format_observation(observation))
        for note in observation.score_notes:
            print(f"- {note}")
        return 0

    if args.command == "update-status":
        if not args.status and not args.check_urls:
            print("Provide --status or --check-urls.")
            return 2
        changes = update_listing_status(args.data, config, args.id, args.status, args.check_urls)
        print("Status updates:")
        for change in changes or ["No changes recorded."]:
            print(f"- {change}")
        return 0

    if args.command == "generate-daily-digest":
        report = generate_daily_digest(load_observations(args.data), config)
        return _write_or_print(report, args.out)

    if args.command in {"generate-weekly-report", "generate-report"}:
        report = generate_market_report(load_observations(args.data), config)
        return _write_or_print(report, args.out)

    if args.command == "generate-dashboard":
        out = args.out or Path(config.dashboard_output_file)
        report = generate_dashboard_html(load_observations(args.data), config)
        return _write_or_print(report, out)

    if args.command == "export-report":
        out = args.out or Path(config.report_output_directory) / "local-shed-market-report.md"
        report = generate_market_report(load_observations(args.data), config)
        return _write_or_print(report, out)

    if args.command == "decision-check":
        decision, reasons = decision_check(load_observations(args.data), config)
        print(f"Decision: {decision}")
        for reason in reasons:
            print(f"- {reason}")
        return 0

    if args.command == "seed-sample-data":
        save_observations(build_sample_observations(config), args.data)
        print(f"Wrote sample observations to {args.data}")
        return 0

    if args.command == "add-supplier":
        supplier = Supplier(
            supplier_name=args.name,
            platform=args.platform,
            supplier_url=args.url,
            contact_name=args.contact_name,
            contact_channel=args.contact_channel,
            contact_email=args.contact_email,
            location_province=args.location,
            us_export_experience=args.us_export_experience,
            export_experience_notes=args.export_notes,
            notes=args.notes,
            status=args.status,
        )
        add_supplier(supplier, args.suppliers_data)
        print(f"Saved supplier {supplier.supplier_id} | {supplier.supplier_name} | {supplier.platform}")
        return 0

    if args.command == "add-product-candidate":
        if not _find_by_id(load_suppliers(args.suppliers_data), "supplier_id", args.supplier_id):
            print(f"Supplier not found: {args.supplier_id}")
            return 2
        quote_text = args.quote_text or (args.quote_file.read_text(encoding="utf-8") if args.quote_file else "")
        product = ProductCandidate(
            supplier_id=args.supplier_id,
            product_name=args.name,
            product_url=args.url,
            product_type=args.product_type,
            external_dimensions=args.external_dimensions,
            internal_dimensions=args.internal_dimensions,
            material=args.material,
            has_floor=args.has_floor,
            uv_weather_resistant=args.uv_weather_resistant,
            color=args.color,
            unit_price=args.unit_price,
            currency=args.currency,
            moq=args.moq,
            price_tiers=_parse_price_tiers(args.price_tier),
            sample_cost=args.sample_cost,
            sample_lead_time=args.sample_lead_time,
            production_lead_time=args.production_lead_time,
            carton_size=args.carton_size,
            gross_weight=args.gross_weight,
            net_weight=args.net_weight,
            cartons_per_unit=args.cartons_per_unit,
            estimated_shipping_cost=args.shipping_estimate,
            shipping_terms=args.shipping_terms,
            packaging_notes=args.packaging_notes,
            english_manual_available=args.english_manual,
            installation_video_available=args.installation_video,
            spare_parts_available=args.spare_parts,
            neutral_branding_available=args.neutral_branding,
            warranty_or_after_sales_notes=args.warranty_notes,
            assembly_notes=args.assembly_notes,
            quote_date=args.quote_date,
            follow_up_status=args.follow_up_status,
            risk_notes=args.risk_note or [],
            raw_quote_text=quote_text,
        )
        add_product_candidate(product, args.products_data)
        print(f"Saved product candidate {product.product_id} | {product.product_name} | {product.product_type}")
        return 0

    if args.command == "list-suppliers":
        suppliers = load_suppliers(args.suppliers_data)
        for supplier in suppliers:
            print(f"{supplier.supplier_id} | {supplier.supplier_name} | {supplier.platform} | {supplier.status}")
        if not suppliers:
            print("No suppliers saved yet.")
        return 0

    if args.command == "list-product-candidates":
        products = load_product_candidates(args.products_data)
        for product in products:
            price = f"{product.currency} {product.unit_price:.2f}" if product.unit_price is not None else "no price"
            print(f"{product.product_id} | {product.product_name} | {product.product_type} | {price} | MOQ {product.moq or 'unknown'}")
        if not products:
            print("No product candidates saved yet.")
        return 0

    if args.command == "generate-rfq-template":
        templates = generate_rfq_template(args.product_type, supplier_config)
        content = _select_rfq_language(templates, args.language)
        if args.queue_for_supplier:
            if not _find_by_id(load_suppliers(args.suppliers_data), "supplier_id", args.queue_for_supplier):
                print(f"Supplier not found: {args.queue_for_supplier}")
                return 2
            supplier_products = [
                item
                for item in load_product_candidates(args.products_data)
                if item.supplier_id == args.queue_for_supplier and item.product_type == args.product_type
            ]
            product_ids = args.product_id or [item.product_id for item in supplier_products]
            threads = load_supplier_threads(args.threads_data)
            thread = _find_by_id(threads, "thread_id", args.thread_id) if args.thread_id else None
            if thread is None:
                thread = _find_reusable_supplier_thread(threads, args.queue_for_supplier, product_ids)
            if thread is None:
                thread = SupplierThread(supplier_id=args.queue_for_supplier, product_ids=product_ids)
                threads.append(thread)
            else:
                thread.product_ids = list(dict.fromkeys(thread.product_ids + product_ids))
            draft = build_initial_rfq_draft(thread.thread_id, args.queue_for_supplier, args.product_type, supplier_config)
            add_message_draft(draft, args.message_queue_data)
            thread.thread_status = "draft_ready"
            thread.recommended_next_action = "review pending initial RFQ draft"
            thread.updated_at = now_iso()
            save_supplier_threads(threads, args.threads_data)
            print(f"Queued initial RFQ draft {draft.draft_id} in thread {thread.thread_id} for human approval. No message was sent.")
        return _write_or_print(content, args.out)

    if args.command == "add-supplier-message":
        suppliers = load_suppliers(args.suppliers_data)
        supplier = _find_by_id(suppliers, "supplier_id", args.supplier_id)
        if supplier is None:
            print(f"Supplier not found: {args.supplier_id}")
            return 2
        text = args.text or (args.text_file.read_text(encoding="utf-8") if args.text_file else "")
        if not text:
            text = _read_multiline("Paste supplier message text, then press Ctrl+Z and Enter on Windows:")
        supplier_products = [item for item in load_product_candidates(args.products_data) if item.supplier_id == args.supplier_id]
        product_ids = args.product_id or [item.product_id for item in supplier_products]
        threads = load_supplier_threads(args.threads_data)
        thread = _find_by_id(threads, "thread_id", args.thread_id) if args.thread_id else None
        if thread is None:
            thread = _find_reusable_supplier_thread(threads, args.supplier_id, product_ids)
        if thread is None:
            thread = SupplierThread(
                supplier_id=args.supplier_id,
                product_ids=product_ids,
                platform_channel=args.source,
            )
            threads.append(thread)
        elif product_ids:
            thread.product_ids = list(dict.fromkeys(thread.product_ids + product_ids))
        message = SupplierMessage(
            thread_id=thread.thread_id,
            direction=args.direction,
            message_text=text,
            language=args.language,
            source=args.source,
        )
        thread.messages.append(message)
        if args.direction == "inbound":
            thread.last_inbound_at = message.timestamp
            thread.thread_status = "reply_received"
            supplier.status = "replied"
        elif args.direction == "outbound_sent":
            thread.last_outbound_at = message.timestamp
            thread.thread_status = "waiting_for_reply"
            supplier.status = "waiting"
        elif args.direction == "outbound_draft":
            thread.thread_status = "draft_ready"
        supplier.updated_at = now_iso()
        thread.updated_at = now_iso()
        save_suppliers(suppliers, args.suppliers_data)
        save_supplier_threads(threads, args.threads_data)
        print(f"Saved message {message.message_id} in thread {thread.thread_id}")
        return 0

    if args.command == "analyze-supplier-thread":
        threads = load_supplier_threads(args.threads_data)
        thread = _find_by_id(threads, "thread_id", args.thread_id)
        if thread is None:
            print(f"Supplier thread not found: {args.thread_id}")
            return 2
        products = load_product_candidates(args.products_data)
        suppliers = load_suppliers(args.suppliers_data)
        supplier = _find_by_id(suppliers, "supplier_id", thread.supplier_id)
        thread, products, supplier, notes = analyze_supplier_thread(thread, products, supplier, supplier_config)
        if supplier:
            relevant_products = [item for item in products if item.product_id in thread.product_ids]
            scores = [score_supplier_candidate(supplier, item, thread, supplier_config) for item in relevant_products]
            if any(score.recommendation == "strong candidate" for score in scores):
                supplier.status = "strong_candidate"
            elif scores and all(score.recommendation == "reject" for score in scores):
                supplier.status = "rejected"
                thread.thread_status = "closed"
                thread.recommended_next_action = "pass unless terms change materially"
            else:
                supplier.status = "replied"
            supplier.updated_at = now_iso()
            save_suppliers(suppliers, args.suppliers_data)
        save_supplier_threads(threads, args.threads_data)
        save_product_candidates(products, args.products_data)
        print(f"Analyzed supplier thread {thread.thread_id}. Status: {thread.thread_status}")
        for note in notes:
            print(f"- {note}")
        for item in thread.missing_information:
            print(f"- Missing: {item}")
        return 0

    if args.command == "generate-follow-up-draft":
        threads = load_supplier_threads(args.threads_data)
        thread = _find_by_id(threads, "thread_id", args.thread_id)
        if thread is None:
            print(f"Supplier thread not found: {args.thread_id}")
            return 2
        products = [item for item in load_product_candidates(args.products_data) if item.product_id in thread.product_ids]
        supplier = _find_by_id(load_suppliers(args.suppliers_data), "supplier_id", thread.supplier_id)
        if supplier and supplier.status == "rejected":
            print(f"No follow-up draft queued for rejected supplier {supplier.supplier_name}.")
            return 0
        plan = generate_follow_up_plan(thread, products, supplier, supplier_config)
        if not plan.missing_information:
            print(f"No follow-up draft needed for thread {thread.thread_id}; no required information is missing.")
            return 0
        existing_draft = _pending_draft_for_thread(load_message_queue(args.message_queue_data), thread.thread_id)
        if existing_draft:
            print(f"Pending draft {existing_draft.draft_id} already exists for thread {thread.thread_id}.")
            return 0
        draft = build_follow_up_draft(plan, supplier.supplier_name if supplier else "", supplier_config)
        draft.supplier_id = thread.supplier_id
        add_message_draft(draft, args.message_queue_data)
        thread.thread_status = "draft_ready"
        thread.recommended_next_action = "review pending follow-up draft"
        thread.updated_at = now_iso()
        save_supplier_threads(threads, args.threads_data)
        print(f"Queued draft {draft.draft_id} for human approval. No message was sent.")
        return 0

    if args.command == "list-message-queue":
        drafts = load_message_queue(args.message_queue_data)
        supplier_by_id = {item.supplier_id: item for item in load_suppliers(args.suppliers_data)}
        for draft in drafts:
            supplier_name = supplier_by_id.get(draft.supplier_id).supplier_name if supplier_by_id.get(draft.supplier_id) else draft.supplier_id
            print(f"{draft.draft_id} | {supplier_name} | {draft.purpose} | {draft.approval_status} | thread {draft.thread_id}")
        if not drafts:
            print("No supplier message drafts queued.")
        return 0

    if args.command == "approve-message-draft":
        drafts = load_message_queue(args.message_queue_data)
        draft = _find_by_id(drafts, "draft_id", args.draft_id)
        if draft is None:
            print(f"Message draft not found: {args.draft_id}")
            return 2
        approve_message_draft(draft)
        save_message_queue(drafts, args.message_queue_data)
        print(f"Approved draft {draft.draft_id} for manual sending. No message was sent.")
        return 0

    if args.command == "mark-message-sent-manually":
        drafts = load_message_queue(args.message_queue_data)
        draft = _find_by_id(drafts, "draft_id", args.draft_id)
        if draft is None:
            print(f"Message draft not found: {args.draft_id}")
            return 2
        mark_message_sent_manually(draft)
        save_message_queue(drafts, args.message_queue_data)
        threads = load_supplier_threads(args.threads_data)
        thread = _find_by_id(threads, "thread_id", draft.thread_id)
        if thread:
            message_text = draft.draft_text_chinese if args.language == "chinese" else draft.draft_text_english
            message = SupplierMessage(
                thread_id=thread.thread_id,
                direction="outbound_sent",
                message_text=message_text,
                language=args.language,
                source="manual",
                notes=f"Recorded from approved draft {draft.draft_id}.",
            )
            thread.messages.append(message)
            thread.last_outbound_at = message.timestamp
            thread.thread_status = "waiting_for_reply"
            thread.recommended_next_action = "wait for supplier reply"
            thread.updated_at = now_iso()
            save_supplier_threads(threads, args.threads_data)
        suppliers = load_suppliers(args.suppliers_data)
        supplier = _find_by_id(suppliers, "supplier_id", draft.supplier_id)
        if supplier:
            supplier.status = "waiting"
            supplier.updated_at = now_iso()
            save_suppliers(suppliers, args.suppliers_data)
        print(f"Marked draft {draft.draft_id} as sent manually.")
        return 0

    if args.command == "generate-supplier-report":
        report = generate_supplier_rfq_pack(
            load_suppliers(args.suppliers_data),
            load_product_candidates(args.products_data),
            load_supplier_threads(args.threads_data),
            load_message_queue(args.message_queue_data),
            supplier_config,
        )
        out = args.out or Path(supplier_config.report_output_directory) / f"supplier-rfq-pack-{date.today().isoformat()}.md"
        return _write_or_print(report, out)

    return 1


def _read_multiline(prompt: str) -> str:
    print(prompt)
    try:
        return input()
    except EOFError:
        return ""


def _write_or_print(content: str, path: Path | None) -> int:
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")
    else:
        print(content)
    return 0


def _format_observation(observation) -> str:
    price = f"${observation.price:.0f}" if observation.price is not None else "no price"
    return (
        f"{observation.id} | {observation.title or '(untitled)'} | "
        f"{observation.target_sku_fit} | {price} | "
        f"overall {observation.overall_signal_score}/10 | status {observation.listing_status}"
    )


def _find_by_id(items, field_name: str, value: str | None):
    if not value:
        return None
    return next((item for item in items if getattr(item, field_name, None) == value), None)


def _select_rfq_language(templates: dict[str, str], language: str) -> str:
    if language == "english":
        return templates["english"] + "\n"
    if language == "chinese":
        return templates["chinese"] + "\n"
    return f"# English RFQ\n\n{templates['english']}\n\n# Chinese RFQ\n\n{templates['chinese']}\n"


def _parse_price_tiers(values: list[str] | None) -> dict[str, float]:
    tiers: dict[str, float] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Invalid price tier '{value}'. Use QUANTITY=PRICE.")
        quantity, price = value.split("=", 1)
        tiers[quantity.strip()] = float(price.strip())
    return tiers


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (AttributeError, OSError):
                pass


def _find_reusable_supplier_thread(
    threads: list[SupplierThread],
    supplier_id: str,
    product_ids: list[str],
) -> SupplierThread | None:
    active = [
        thread
        for thread in threads
        if thread.supplier_id == supplier_id and thread.thread_status not in {"closed", "archived"}
    ]
    for thread in reversed(active):
        if not product_ids or not thread.product_ids or set(thread.product_ids).intersection(product_ids):
            return thread
    return None


def _pending_draft_for_thread(drafts, thread_id: str):
    return next(
        (
            draft
            for draft in drafts
            if draft.thread_id == thread_id and draft.approval_status in {"pending", "approved"}
        ),
        None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
