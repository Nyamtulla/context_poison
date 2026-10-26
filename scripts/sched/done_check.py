"""Exit 0 when a cell's registry already covers every dose, 1 otherwise."""
import json, pathlib, sys
want = {0, 1, 2, 3, 5, 10}
p = pathlib.Path(sys.argv[1])
try:
    d = json.loads(p.read_text())
except Exception:
    sys.exit(1)
done = d.get("doses_done")
if done is None:
    r = d.get("results")
    done = [x.get("n_poison") for x in r] if isinstance(r, list) else list(r or [])
try:
    sys.exit(0 if want <= {int(x) for x in done} else 1)
except (TypeError, ValueError):
    sys.exit(1)
