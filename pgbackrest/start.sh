#!/bin/bash
set -e

# Start the cron service
service cron start

# Ensure log directory exists for pgbackrest cron
mkdir -p /var/log/pgbackrest
chown -R postgres:postgres /var/log/pgbackrest

# Execute the original postgres entrypoint
exec docker-entrypoint.sh "$@"
