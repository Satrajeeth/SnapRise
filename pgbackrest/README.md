# SnapRise Database Backup & Restore Guide

This folder contains the configuration and setup for **pgBackRest**, an industry-standard, high-performance backup solution for PostgreSQL.

## 🧠 How It Works

Our architecture uses a custom PostgreSQL Docker image that has `pgBackRest` and `cron` natively embedded. 

1. **Storage Location**: All backups and Write-Ahead Logs (WAL) are saved directly to your host machine's HDD at `F:\database_backups`.
2. **Continuous Archiving**: Every time a change happens in the database, Postgres immediately ships a WAL file to the `F:\` drive. This ensures zero data loss.
3. **Automated Cron Jobs**: A background task automatically runs backups on the following schedule:
   - **Hourly**: Incremental Backup (Only saves what changed).
   - **Daily (2:00 AM)**: Full Backup (Complete fresh snapshot).
4. **Retention Policy**: The system is configured to keep exactly **7 days** of full backups. Older backups are automatically deleted to prevent your disk from filling up.

---

## 📸 Taking a Manual Backup

If you are about to run a dangerous migration or script and want to take a backup *right now*:

```bash
# Take an Incremental Backup (Very fast)
docker exec -u postgres postgres pgbackrest --stanza=main --log-level-console=info backup --type=incr

# Take a Full Backup
docker exec -u postgres postgres pgbackrest --stanza=main --log-level-console=info backup --type=full
```

---

## ⏪ How to Restore

Because Postgres cannot be actively running while you overwrite its files, you cannot just `docker exec` into the running container to restore. You must stop the database and run a temporary restore container.

### Step 1: Stop the Database
Bring down the currently running Postgres container so it stops locking the files:
```bash
docker compose stop postgres
```

### Step 2: Run the Restore Command
Run a temporary container that mounts your data and backups, executes the restore, and then deletes itself. 
*(We use `--delta` which smartly only overwrites corrupted or missing files, making the restore much faster!)*

```bash
docker run --rm --user postgres `
  -v snaprise_postgres_data:/var/lib/postgresql/data `
  -v "F:\database_backups:/var/lib/pgbackrest" `
  --entrypoint pgbackrest `
  snaprise-postgres --stanza=main --log-level-console=info restore --delta
```

### Step 3: Restart the Database
Once the restore says `completed successfully`, simply start your database back up!
```bash
docker compose start postgres
```

---

## 🕒 Point-in-Time Recovery (PITR)

Did someone accidentally drop a table at exactly 2:45 PM? You can restore the database to how it looked at **exactly 2:44 PM** using the WAL logs!

Just add `--type=time` and `--target` to your restore command in Step 2:

```bash
docker run --rm --user postgres `
  -v snaprise_postgres_data:/var/lib/postgresql/data `
  -v "F:\database_backups:/var/lib/pgbackrest" `
  --entrypoint pgbackrest `
  snaprise-postgres --stanza=main --log-level-console=info restore --delta `
  --type=time --target="2026-06-23 14:44:00+05:30"
```
*(Make sure to match the target timezone properly!)*
