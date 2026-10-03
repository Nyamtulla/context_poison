# SABER patch: `saber.config` is missing `HF_CACHE_DIR`

**Symptom.** Every GPU stage of the pipeline dies on import:

```
ImportError: cannot import name 'HF_CACHE_DIR' from 'saber.config'
```

`src/saber/extract/label_pk_ck.py:34` and `extract_hidden.py:48` both import
it, and both use it as the `cache_dir=` argument to `from_pretrained`
(lines 309/314 and 299/304). `src/saber/config.py` never defines it.

**Why the smoke test misses it.** `scripts/00_smoke.sh` checks `--help` on four
entry points — `build_split`, `saber_probe`, `joint_metrics`,
`cell_distribution` — none of which is in the extract package. The repo
reports "ALL SMOKE CHECKS PASSED" and then cannot run step 01.

**Fix.** Add the constant, deriving it from `HF_HOME` exactly as the config's
own docstring says it should ("HF_HOME -- Hugging Face cache root (standard
transformers var)"). Appended to `src/saber/config.py`:

```python
HF_CACHE_DIR = Path(os.environ.get("HF_HOME",
                                   Path.home() / ".cache" / "huggingface")) / "hub"
```

This points at the standard cache, so weights already on the machine are
reused rather than re-downloaded. Nothing else about the pipeline changes, and
no evaluation code is touched.
