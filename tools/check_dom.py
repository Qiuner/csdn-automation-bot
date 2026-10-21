"""Read-only DOM checks. Never clicks, fills, submits, or claims rewards."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

SELECTORS = {
    "blog_article": ".navList-box .mainContent .blog-list-box .blog-list-box-top",
    "like": "#is-like > a, #sidebar-like",
    "liked_icon": "#is-like img.isactive, #sidebar-like.active",
    "collection": ".toolbox-list .is-collection, #sidebar-collect",
    "collection_confirm": ".collect-btn",
    "comment_entry": ".toolbox-list .tool-item-comment, .go-side-comment, .detail-shell-toolbar__item.is-comment",
    "comment_editor": ".comment-edit-box .comment-content",
    "comment_submit": ".comment-edit-box .btn-comment",
    "chat_item": ".msg-item_inner",
    "chat_unread": ".unread-num",
    "chat_editor": "#messageText",
    "loading_mask": ".el-loading-mask",
    "redpack_list": ".red-packet-icon-mini",
    "redpack_card": ".redpack-card",
    "comment_reward": ".comment-reward-item",
    "redpack_open": ".red-openbtn",
}


def inspect_page(page, url):
    result = {"requested": url, "status": None, "navigation_timeout": False}
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        result["status"] = response.status if response else None
    except PlaywrightTimeout:
        result["navigation_timeout"] = True
    except Exception as exc:
        result["navigation_error"] = type(exc).__name__
        return result
    page.wait_for_timeout(5000)
    # Exclude queries, text, form values and cookies from diagnostic output.
    result["page_path"] = page.url.split("?")[0].split("#")[0]
    result["login_required"] = urlsplit(page.url).hostname == "passport.csdn.net"
    result["frames"] = []
    for frame in page.frames:
        details = {"path": frame.url.split("?")[0].split("#")[0], "selectors": {}}
        try:
            for name, selector in SELECTORS.items():
                details["selectors"][name] = frame.locator(selector).evaluate_all(
                    """els => ({
                        count: els.length,
                        visible: els.filter(e => {
                            const s = getComputedStyle(e);
                            return s.display !== 'none' && s.visibility !== 'hidden'
                                && e.getClientRects().length > 0;
                        }).length
                    })"""
                )
        except Exception as exc:
            details["inspection_error"] = type(exc).__name__
        result["frames"].append(details)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="CSDN pages to inspect")
    parser.add_argument("--login", action="store_true", help="Wait for manual login first")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--profile", type=Path,
        default=Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        / "csdn-automation-bot" / "inspection-profile",
    )
    args = parser.parse_args()
    if args.login and args.headless:
        parser.error("--login requires a visible browser")
    for url in args.urls:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if parsed.scheme != "https" or not (host == "csdn.net" or host.endswith(".csdn.net")):
            parser.error("Only HTTPS CSDN URLs are supported")
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(args.profile), headless=args.headless
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            if args.login:
                try:
                    page.goto("https://passport.csdn.net/login?code=applets",
                              wait_until="domcontentloaded", timeout=25000)
                except PlaywrightTimeout:
                    print("Login navigation timed out; check the browser window.")
                input("Complete login in the browser, then press Enter here: ")
            results = [inspect_page(page, url) for url in args.urls]
            report = json.dumps(results, ensure_ascii=True, indent=2)
            if args.output:
                args.output.write_text(report + "\n", encoding="utf-8")
            print(report)
        finally:
            context.close()


if __name__ == "__main__":
    main()
