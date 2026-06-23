#!/bin/bash
set -e

echo "Setting up pgBackRest repository..."
mkdir -p /var/lib/pgbackrest

echo "Creating pgBackRest stanza..."
pgbackrest --stanza=main --log-level-console=info stanza-create || echo "Stanza creation failed, you may need to run it manually once the DB fully starts."
