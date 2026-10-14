# Architecture

```mermaid
flowchart TD
    A[Nisan-Sinai/github-workflows] --> B[Reusable CI: Node / Python / .NET]
    A --> C[Reusable security / Vercel gate]
    A --> D[Read-only public drift inventory]
    A --> E[Ruleset JSON templates]
    B --> F[Per-repo caller by immutable SHA]
    C --> F
    F --> G[Existing consumer CI / Vercel / Supabase tests]
    E -.-> H[Manual or separately authorized GitHub admin activation]
    H --> I[Branch protection: main / dev / master]
```

There is **no** implicit cross-repository write path. In consumer repos, adopt by PR and pin the hub commit. The hub CI must not publish any private-repository metadata.

Branch protection remains a repository control-plane setting, not a Git file. The chosen central hub is public to support both public and private consumers, and stores only public-safe data.
