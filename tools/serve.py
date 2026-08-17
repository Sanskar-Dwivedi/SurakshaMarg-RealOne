"""
Serve the demo pages locally, without caching.

    python tools/serve.py            # http://127.0.0.1:8765
    python tools/serve.py --port 9000

WHY THIS EXISTS AND WHY IT SETS NO-STORE
----------------------------------------
Two reasons the pages have to be served rather than opened off the disk:

  1. Web Serial needs a secure origin. `file://` is not one, so the bench and
     the console cannot reach the board unless they come from 127.0.0.1.

  2. `python -m http.server` sends Last-Modified and nothing else. With no
     Cache-Control and no Expires, a browser is free to apply heuristic
     freshness - typically a tenth of the file's age - and serve the page from
     cache without asking the server at all. On a 6.6 MB page that has just
     been rebuilt, that means you rebuild, reload, and study the previous
     build while believing you are looking at the new one. Every page here is
     regenerated constantly, so that failure mode is not an edge case; it is
     the normal working loop.

So: no-store on everything. A reload always fetches. Locally the cost is
nothing, and being certain which build is on screen is worth more than the
milliseconds.
"""

from __future__ import annotations

import argparse
from functools import partial
import http.server
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = [
    ("dashboard/simulator.html", "operations console - footage, vetoes, outcomes"),
    ("hardware/bench.html", "the bench governor - drives the board over USB"),
    ("hardware/handoff.html", "what works and how"),
    ("hardware/design.html", "build spec for the fabricator"),
]


class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_header(self, keyword: str, value: str) -> None:
        # Last-Modified is what the browser echoes back as If-Modified-Since to
        # earn a 304. Dropping it means a reload cannot be answered from cache
        # even by a browser that ignores no-store.
        if keyword.lower() == "last-modified":
            return
        super().send_header(keyword, value)

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - base name
        code = str(args[1]) if len(args) > 1 else ""
        if code.startswith("2") or code.startswith("3"):
            return                      # only shout about failures
        super().log_message(format, *args)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    # partial, not a class attribute: SimpleHTTPRequestHandler.__init__ always
    # assigns self.directory from its keyword argument (defaulting to the
    # process cwd), so a class attribute of the same name is silently ignored
    # and the server quietly serves whatever directory it was launched from.
    handler = partial(NoCache, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        base = f"http://127.0.0.1:{args.port}"
        print("Serving with caching switched off - a reload always refetches.")
        print()
        for rel, what in PAGES:
            mark = " " if (ROOT / rel).exists() else "  (not built yet)"
            print(f"  {base}/{rel}{mark}")
            print(f"      {what}")
        print()
        print("Ctrl-C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
