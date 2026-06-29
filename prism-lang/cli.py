#!/usr/bin/env python3
"""
Prism -- a single command-line entry point.

  prism run    <file.prism>     run a program (tree-walking interpreter)
  prism check  <file.prism>     statically check it (types / effects / failures / ...)
  prism reveal <file.prism>     show the inferred contract of each definition
  prism test   [core|gallery|all]  run the regression suite (default all; core = language only, fast)
  prism serve  [port] [--host H] serve the playground (loopback only; --host 0.0.0.0 for LAN)
  prism fetch-pyodide [version] download Pyodide into ./pyodide for OFFLINE playground
  prism help                    show this message

No build step. Needs only Python 3 -- no third-party dependencies.
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

USAGE = __doc__.strip()

def _need_file(rest, cmd):
    if not rest:
        print(f"usage: prism {cmd} <file.prism>", file=sys.stderr)
        sys.exit(2)
    return rest[0]

def main(argv):
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

    if not argv or argv[0] in ("help", "-h", "--help"):
        print(USAGE); return 0
    cmd, rest = argv[0], argv[1:]

    if cmd == "run":
        import prism
        path = _need_file(rest, "run")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        try:
            prism.run(src); return 0
        except (SyntaxError, RuntimeError, NameError, TypeError) as e:
            print(f"[prism error] {e}", file=sys.stderr); return 1

    if cmd in ("check", "reveal"):
        import check
        path = _need_file(rest, cmd)
        try:
            return check.reveal_file(path) if cmd == "reveal" else check.check_file(path)
        except (SyntaxError, RuntimeError) as e:
            print(f"[parse error] {e}", file=sys.stderr); return 2

    if cmd == "test":
        import test
        return test.main(rest[0] if rest else "all")

    if cmd == "fetch-pyodide":
        import urllib.request, tarfile, io as _io, shutil, re as _re
        ver = rest[0] if rest else "0.26.4"
        if not _re.fullmatch(r"\d+\.\d+\.\d+", ver):       # don't interpolate junk into the URL
            print(f"bad version {ver!r}: expected e.g. 0.26.4", file=sys.stderr)
            return 2
        url = (f"https://github.com/pyodide/pyodide/releases/download/"
               f"{ver}/pyodide-core-{ver}.tar.bz2")
        dest = os.path.join(HERE, "pyodide")
        print(f"downloading Pyodide {ver} (core) for offline use ...\n  {url}")
        try:
            data = urllib.request.urlopen(url).read()
        except Exception as e:
            print(f"download failed: {e}\n"
                  f"check the version, or browse https://github.com/pyodide/pyodide/releases",
                  file=sys.stderr)
            return 1
        print(f"  {len(data)//1024} KB downloaded; extracting -> {dest}")
        if os.path.isdir(dest): shutil.rmtree(dest)
        base = os.path.realpath(HERE)
        with tarfile.open(fileobj=_io.BytesIO(data), mode="r:bz2") as tar:
            for m in tar.getmembers():                     # explicit path-traversal guard (all Python versions)
                target = os.path.realpath(os.path.join(HERE, m.name))
                if target != base and not target.startswith(base + os.sep):
                    raise RuntimeError(f"refusing unsafe archive entry: {m.name!r}")
                if m.issym() or m.islnk():
                    raise RuntimeError(f"refusing link entry in archive: {m.name!r}")
            try: tar.extractall(HERE, filter="data")       # belt-and-suspenders on Python 3.12+
            except TypeError: tar.extractall(HERE)          # members already validated above
        ok = os.path.isfile(os.path.join(dest, "pyodide.js"))
        print("done. playground.html will now prefer the local copy (works offline)."
              if ok else "warning: pyodide.js not found after extract -- check the archive layout.")
        return 0 if ok else 1

    if cmd == "serve":
        import http.server
        # default: loopback only (the playground is for the local machine). Pass
        # `--host 0.0.0.0` (or any address) to expose it on the LAN, e.g. for a phone.
        host, args = "127.0.0.1", list(rest)
        if "--host" in args:
            i = args.index("--host")
            host = args[i + 1] if i + 1 < len(args) else "0.0.0.0"
            del args[i:i + 2]
        port = int(args[0]) if args else 8000
        os.chdir(HERE)
        shown = host if host not in ("", "0.0.0.0") else "localhost"
        url = f"http://{shown}:{port}/playground.html"
        print(f"Prism playground -> {url}   (Ctrl+C to stop)")
        if host in ("", "0.0.0.0"):
            print("  WARNING: serving on ALL network interfaces -- reachable by other "
                  "devices on your network. Use the default (loopback) unless you mean to.")
        # serve .wasm with the correct MIME, and add .mjs (Python maps it to text/plain).
        handler = http.server.SimpleHTTPRequestHandler
        handler.extensions_map = {**handler.extensions_map,
                                  ".wasm": "application/wasm", ".mjs": "text/javascript"}
        # THREADING: Pyodide pulls several large files (the ~6MB .wasm, stdlib zip, ...) in
        # parallel with the page's own fetches. A single-threaded server serializes them and
        # the load can stall/fail -- a threading server serves them concurrently.
        try:
            with http.server.ThreadingHTTPServer((host, port), handler) as httpd:
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped.")
        return 0

    print(f"prism: unknown command {cmd!r}\n", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
