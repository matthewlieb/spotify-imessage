# Syncing GitHub branches with main

Use this when you want all remote branches to match your local `main` (e.g. after setting main as the default branch).

## 1. Commit and push main

From the repo root, with all changes committed on `main`:

```bash
git checkout main
git add -A
git status   # review
git commit -m "Your message"   # if there are changes to commit
git push origin main
```

## 2. Make develop and matt match main (then push)

This resets local `develop` and `matt` to the same commit as `main`, then force-pushes so GitHub has the same code on all three branches:

```bash
git checkout develop
git reset --hard main
git push origin develop --force

git checkout matt
git reset --hard main
git push origin matt --force

git checkout main
```

After this, `main`, `develop`, and `matt` on GitHub all point to the same commit.

## Alternative: delete develop and matt from GitHub

If you no longer need those branches:

```bash
git push origin --delete develop
git push origin --delete matt
```

Then delete the local branches if you want:

```bash
git branch -d develop
git branch -d matt
```
