# Making the App More Lightweight

Ways to reduce app size without dropping features.

## 1. Use the Lite build (biggest saving)

The **full** build ships a bundled Python runtime (~100–200 MB+). The **lite** build does **not** include Python; the app uses the Mac’s Python 3 (Homebrew or system). Same functionality, much smaller DMG.

**Build lite from repo root:**

```bash
npm run build:mac:unsigned:lite
npm run dmg
```

**For users:** They need Python 3 installed (`brew install python@3.12`) and must run the app’s **install-deps.command** once (Right‑click app → Show Package Contents → Contents/Resources/web-react → double‑click install-deps.command). Your release notes should say this for the lite build.

**Optional:** Offer both “Full” and “Lite” on the download page (e.g. two sets of buttons or a note: “Lite build: smaller download, requires Python 3”).

---

## 2. Electron / DMG settings

In your **electron-builder** config (e.g. `electron/electron-builder.config.js` or `electron/package.json` → `"build"`):

- **DMG compression:** Use maximum compression so the DMG file is smaller (build may be slower):
  ```json
  "dmg": {
    "compression": "maximum"
  }
  ```
- **Locales:** If you only need English, restrict included locales to reduce size:
  ```json
  "mac": {
    "electronLanguages": ["en"]
  }
  ```
- **extraResources:** Only include what’s needed (e.g. `web-react` with a tight `filter`). Avoid shipping dev files, `.venv`, or large assets you don’t use at runtime.

---

## 3. Python bundle (full build only)

If you keep the full build with bundled Python:

- **Strip debug symbols** from the Python binary and `.so`/`.dylib` files in the bundle (e.g. in `afterPack.js` or in your `python-bundle` prep script):
  ```bash
  strip -x python3/bin/python3
  find python3/lib -name '*.so' -o -name '*.dylib' | xargs strip -x
  ```
  This can save a significant amount of space.
- **Trim the Python install:** After `pip install -r requirements.txt`, remove things you don’t need at runtime, e.g.:
  - `python3/bin/pip*`, `python3/bin/wheel`
  - `python3/lib/python3.x/test/`
  - `__pycache__` directories: `find python3 -type d -name __pycache__ -exec rm -rf {} +`
  Only do this if you’re sure nothing in your app or dependencies uses them.

---

## 4. React build

- You’re already using `GENERATE_SOURCEMAP=false` in the React build, which helps.
- Keep dependencies minimal; remove unused npm packages so the built `build/` (and thus the app) stays smaller.

---

## Summary

| Approach              | Size impact      | Effort   | Trade-off                          |
|-----------------------|------------------|----------|------------------------------------|
| **Lite build**        | Very large       | Low      | Users need Python 3 + install-deps |
| **DMG compression**   | Moderate         | Config   | Slightly longer build time         |
| **Strip Python**      | Moderate         | Script   | None if you only strip binaries    |
| **Trim Python bundle**| Moderate        | Careful  | Don’t remove anything you need    |
| **electronLanguages** | Small            | Config   | None if you only need English      |

Starting with the **lite** build and **maximum** DMG compression will get you the biggest size reduction with the least risk to functionality.
