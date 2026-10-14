# Installation: personal account, no Organization required

1. In GitHub, create a **public** repository `Nisan-Sinai/github-workflows` without initializing a README. Public is required to allow both public and private repositories to reuse the same workflows. The contents in this starter have been designed to be public-safe.
2. Extract the supplied ZIP and open a terminal in the extracted `github-workflows` folder.
3. Run:

   ```bash
   python -m pip install 'PyYAML==6.0.3'
   python scripts/validate.py
   python -m unittest discover -s tests -v
   git init -b main
   git add .
   git commit -m "feat: bootstrap centralized GitHub workflow hub"
   git remote add origin https://github.com/Nisan-Sinai/github-workflows.git
   git push -u origin main
   ```

4. Wait until the repository's `Hub / validate` check succeeds. If available, set this specific check as required on the **hub** `main` branch. Protect the hub itself, otherwise changes to it will indirectly affect future callers (even though consumers pin commits).
5. Open **Actions → Public policy drift report → Run workflow** for a read-only audit of the public repositories.
6. For each consumer, generate a caller pinned to a real full SHA:

   ```bash
   SHA=$(git rev-parse HEAD)
   python scripts/generate_consumer.py --repo Nisan-Sinai/artzi-energy --sha "$SHA" --preset node-npm
   ```

   Review the generated YAML; tailor commands to match the consumer's `package.json`. Add it by PR to the consumer as `.github/workflows/ci-shared.yml`. This repository DOES NOT auto-install itself in any consumer.
7. To protect branches: generate a ruleset from **real check context names** and import it as a separate approved admin action. Follow [Branch protection](BRANCH-PROTECTION.md).

## Work mode option

ChatGPT Work can create the repository and push this prepared folder through the graphical GitHub interface (or through a connected computer), complete user-required authorization steps, check CI, and open consumer PRs. Work does not remove GitHub permission boundaries: branch protection needs a repository administrator's authorization, and installing a GitHub App/token has its own security implications.

**Never paste a PAT into chat, a public repo, a PR, a screenshot, or an Actions log.**

### Configure admin rules after approval

See [Branch Protection](BRANCH-PROTECTION.md) for manual import and the optional **offline dry-run by default** `scripts/admin_ruleset.py`. It is a separate opt-in administrative step, not a consequence of merging this repository.
