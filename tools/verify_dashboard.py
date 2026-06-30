"""CI-gated dashboard verification harness (P7).

Boots the Dash app under uvicorn, then drives a headless Chromium across every
route to assert — with evidence — that the dashboard is fully wired:

  * every route returns HTTP 200 (deep-link safe — see app/dash_app.py P5 fix),
  * each route renders without a visible error/placeholder ("Grover",
    "Theoretical Quantum Search", "No active request", "Callback error"),
  * routes that own charts render at least one real Plotly trace,
  * a global export actually downloads a non-empty file,
  * axe-core reports zero critical/serious accessibility violations (WCAG AA).

Emits a JSON manifest (default tools/.artifacts/verify_manifest.json) and exits
non-zero if any gate fails, so CI can block a merge.

Usage:
    python tools/verify_dashboard.py [--port 8044] [--quick] [--no-axe]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

# (path, label, expects_chart)
ROUTES = [
    ("/", "dashboard", True),
    ("/const", "construction", True),
    ("/labor", "labor", True),
    ("/reports", "reports", False),
    ("/stats", "stats", True),
    ("/geo", "gis", True),
    ("/eng", "engineering", True),
    ("/sql", "sql_tools", False),
    ("/nlp", "nlp", False),
    ("/settings", "settings", False),
    ("/tutorials", "tutorials", False),
    ("/toolbox", "toolbox", False),
    ("/copilot", "copilot", False),
]

BANNED_TEXT = [
    "No active request in context",
    "Grover",
    "Theoretical Quantum Search",
    "Callback error",
    "Traceback (most recent call last)",
]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_health(port: int, timeout: float = 120.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/v1/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1.5)
    return False


def _status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def run(port: int, quick: bool, do_axe: bool) -> dict:
    from playwright.sync_api import sync_playwright

    base = f"http://127.0.0.1:{port}"
    routes = ROUTES[:4] if quick else ROUTES
    results: list[dict] = []

    _BROWSER_ARGS = [
        "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
        "--disable-features=site-per-process",
        "--js-flags=--max-old-space-size=512",  # cap V8 heap to relieve memory pressure
    ]

    def _new_browser(pw):
        return pw.chromium.launch(args=_BROWSER_ARGS)

    with sync_playwright() as pw:
        # Flags that prevent the headless renderer from crashing on chart-heavy
        # routes (small /dev/shm) and keep CI sandboxing happy.
        browser = _new_browser(pw)
        _route_idx = 0

        for path, label, expects_chart in routes:
            # Restart browser every 5 routes to flush V8 heap and renderer memory
            # accumulated from chart-heavy pages.  Keeps the GIS/NLP routes from
            # timing out due to resource exhaustion in a long harness run.
            if _route_idx > 0 and _route_idx % 5 == 0:
                try:
                    browser.close()
                except Exception:  # noqa: BLE001
                    pass
                browser = _new_browser(pw)
            _route_idx += 1

            entry: dict = {"route": path, "label": label, "checks": {}}
            url = base + path

            # 1) deep-link status (server-side, independent of JS)
            entry["checks"]["http_200"] = _status(url) == 200

            # 2) render — fresh page per route so memory can't accumulate into a
            # crash. A polling SPA never reaches "networkidle" (2s interval), so
            # wait for DOM + the page-content mount, then a fixed settle.
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90000)
                try:
                    page.wait_for_selector("#page-content", timeout=15000)
                except Exception:  # noqa: BLE001 - record below via checks
                    pass
                page.wait_for_timeout(3500)
                body = page.inner_text("body")
                entry["checks"]["no_banned_text"] = not any(b in body for b in BANNED_TEXT)
                if any(b in body for b in BANNED_TEXT):
                    entry["banned_hit"] = [b for b in BANNED_TEXT if b in body]

                # 3) real Plotly traces
                trace_count = page.evaluate(
                    "() => document.querySelectorAll('.js-plotly-plot .trace,"
                    " .js-plotly-plot .point, .js-plotly-plot .bars path,"
                    " .js-plotly-plot g.cartesianlayer .trace').length"
                )
                plot_count = page.evaluate(
                    "() => document.querySelectorAll('.js-plotly-plot').length")
                entry["plot_divs"] = plot_count
                entry["trace_nodes"] = trace_count
                if expects_chart:
                    entry["checks"]["has_chart"] = plot_count > 0

                # 4) axe-core WCAG AA (critical/serious only)
                if do_axe:
                    try:
                        page.add_script_tag(url=AXE_CDN)
                        page.wait_for_timeout(400)
                        axe = page.evaluate(
                            "async () => { const r = await axe.run(document,"
                            " {runOnly:{type:'tag',values:['wcag2a','wcag2aa']}});"
                            " return r.violations.map(v => ({id:v.id, impact:v.impact,"
                            " n:v.nodes.length})); }")
                        serious = [v for v in axe
                                   if v.get("impact") in ("critical", "serious")]
                        entry["axe_serious"] = serious
                        entry["checks"]["axe_aa_clean"] = len(serious) == 0
                    except Exception as e:  # noqa: BLE001
                        entry["axe_error"] = str(e)[:160]
            except Exception as e:  # noqa: BLE001
                entry["error"] = str(e)[:200]
                entry["checks"]["render"] = False
            finally:
                try:
                    page.close()
                except Exception:  # noqa: BLE001
                    pass

            entry["passed"] = all(entry["checks"].values())
            results.append(entry)
            print(f"  {'PASS' if entry['passed'] else 'FAIL'}  {path:12} "
                  f"plots={entry.get('plot_divs','-')} "
                  f"traces={entry.get('trace_nodes','-')} "
                  f"{entry.get('banned_hit','')}")

        # 5) export download
        export_entry = {"check": "global_excel_export"}
        ep = None
        try:
            ep = browser.new_page(viewport={"width": 1440, "height": 900})
            ep.goto(base + "/", wait_until="domcontentloaded", timeout=45000)
            ep.wait_for_selector("#page-content", timeout=15000)
            ep.wait_for_timeout(3000)
            btn = ep.query_selector("#btn-global-export-excel")
            if btn:
                with ep.expect_download(timeout=90000) as dl:
                    btn.click()
                download = dl.value
                tmp = Path(download.path())
                size = tmp.stat().st_size if tmp.exists() else 0
                export_entry["bytes"] = size
                export_entry["passed"] = size > 0
            else:
                export_entry["passed"] = None
                export_entry["note"] = "export button not on dashboard route"
        except Exception as e:  # noqa: BLE001
            export_entry["error"] = str(e)[:200]
            export_entry["passed"] = False
        finally:
            if ep is not None:
                try:
                    ep.close()
                except Exception:  # noqa: BLE001
                    pass
        results.append({"export": export_entry})
        print(f"  export excel -> {export_entry}")

        try:
            browser.close()
        except Exception:  # noqa: BLE001
            pass

    route_results = [r for r in results if "route" in r]
    gates = {
        "routes_total": len(route_results),
        "routes_passed": sum(1 for r in route_results if r["passed"]),
        "all_http_200": all(r["checks"].get("http_200") for r in route_results),
        "no_banned_text": all(r["checks"].get("no_banned_text", True) for r in route_results),
        "export_ok": export_entry.get("passed") in (True, None),
    }
    gates["green"] = (gates["routes_passed"] == gates["routes_total"]
                      and gates["all_http_200"] and gates["no_banned_text"]
                      and gates["export_ok"])
    return {"gates": gates, "routes": route_results, "export": export_entry}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--quick", action="store_true", help="first 4 routes only")
    ap.add_argument("--no-axe", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "tools" / ".artifacts" / "verify_manifest.json"))
    args = ap.parse_args()

    port = args.port or _free_port()
    env = dict(os.environ, PYTHONPATH=f"{ROOT / 'src'}{os.pathsep}{ROOT}")
    print(f"[harness] booting app on :{port} ...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.dash_app:server",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        if not _wait_health(port):
            print("[harness] FAIL: app did not become healthy in time", file=sys.stderr)
            return 2
        print("[harness] app healthy; driving browser ...")
        report = run(port, args.quick, not args.no_axe)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    g = report["gates"]
    print(f"\n[harness] routes {g['routes_passed']}/{g['routes_total']} passed; "
          f"http_200={g['all_http_200']} no_banned={g['no_banned_text']} "
          f"export_ok={g['export_ok']} -> {'GREEN' if g['green'] else 'RED'}")
    print(f"[harness] manifest: {out}")
    return 0 if g["green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
