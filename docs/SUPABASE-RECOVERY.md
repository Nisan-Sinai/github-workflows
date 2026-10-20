# Supabase Cloud safety and recovery

The central Supabase Cloud gate is deliberately read-only. It accepts only an
exact project URL plus a publishable (or legacy `anon`) key. Never pass a
management token, database password, secret key, or `service_role` key to the
gate.

## Before a database change

1. Keep every schema change in a reviewed migration in the consumer repository.
2. Reconcile local and remote migration history; never run `db push` while the
   histories disagree.
3. Run migrations and RLS/integration tests against a fresh local Supabase
   database.
4. Record the consumer commit, central workflow SHA, project ref, and current
   remote migration list.
5. On the Free plan, create an off-site logical backup with `supabase db dump`
   before a production database change. Supabase recommends regular exports for
   Free projects because scheduled restorable backups are a paid-plan feature.
6. Apply one reviewed migration at a time during a planned maintenance window.

## Recovery order

1. Stop the deployment or feature that is still writing bad data.
2. Roll back application code by reverting its Git commit or rolling back the
   Vercel deployment. This does not roll back the database.
3. Prefer a reviewed forward-fix migration for compatible schema mistakes.
4. For data loss or corruption, restore the last verified logical dump into an
   isolated project first, validate it, and only then plan production recovery.
5. Paid projects may restore a scheduled backup from **Database > Backups**;
   plan downtime. Point-in-Time Recovery is a separate paid add-on.
6. After recovery, rerun the local migration/RLS suite, the read-only cloud
   smoke gate, application E2E tests, and Supabase security/performance advisors.

Database backups do not restore deleted Storage objects; back up object data
separately when the application uses Supabase Storage. Never commit dumps or
credentials to this public repository.

Official reference: [Supabase Database Backups](https://supabase.com/docs/guides/platform/backups).
