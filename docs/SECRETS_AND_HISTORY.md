# Secrets and Git History

## What we did

`web-react/.env` was removed from **all git history** on `main` so that past commits no longer contain that file. The branches **develop** and **matt** were also processed; they did not contain `.env` in their history (they branch from before it was added), so no changes were needed there. Your local `.env` file is unchanged on disk; it was only removed from the repository history.

## What you need to do

### 1. Force-push the rewritten history

After the history rewrite, your local `main` (and `remotes/origin/main`) no longer contain `.env` in any commit. To update GitHub:

```bash
git push origin main --force
```

- **develop** and **matt**: They were run through the same cleanup; no `.env` was found in their history, so no change was required. You can still force-push them if you want the remotes to match your local refs:  
  `git push origin develop --force` and `git push origin matt --force` (optional).
- **Anyone else with a clone** should re-clone or run:
  ```bash
  git fetch origin && git reset --hard origin/main
  ```
  (They will lose local commits on `main` that aren’t on `origin`.)

### 2. Rotate credentials (important)

Because the old `.env` was once committed, assume those values were exposed:

1. **Spotify**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) → your app → **Settings**.
   - **Regenerate Client Secret** (and note any Client ID change).
   - Update your local `web-react/.env` and any deployed environment (e.g. Railway, local only) with the new Client ID and Client Secret.

2. **Flask**
   - If `FLASK_SECRET_KEY` was ever in the committed `.env`, generate a new one:
     ```bash
     openssl rand -hex 32
     ```
   - Put the new value in `web-react/.env` and in production config.

### 3. Optional: remove filter-branch backup refs

To drop the backup refs created by `git filter-branch` (so they aren’t pushed by mistake):

```bash
git for-each-ref --format='%(refname)' refs/original/ | xargs -n 1 git update-ref -d
```

---

After force-pushing and rotating credentials, the repo history and your secrets are in a safe state.
