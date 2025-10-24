#!/bin/bash
# Database migration helper script

set -e

COMMAND=${1:-help}

case $COMMAND in
  init)
    echo "Initializing Aerich"
    poetry run aerich init -t api.config.TORTOISE_ORM --location ./migrations
    ;;
  
  init-db)
    echo "Creating initial migration and applying to database"
    poetry run aerich init-db
    echo "Initial migration complete"
    ;;
  
  migrate)
    NAME=${2:-"update"}
    echo "Creating new migration: $NAME"
    poetry run aerich migrate --name $NAME
    echo "Migration created"
    ;;
  
  upgrade)
    echo "Applying pending migrations"
    poetry run aerich upgrade
    echo "Migrations applied"
    ;;
  
  downgrade)
    echo "Rolling back last migration"
    poetry run aerich downgrade
    echo "Rollback complete"
    ;;
  
  history)
    echo "Migration history"
    poetry run aerich history
    ;;
  
  heads)
    echo "Current migration heads"
    poetry run aerich heads
    ;;
  
  status)
    echo "Current migration status"
    docker exec postgres psql -U postgres -d domain_generator -c "SELECT * FROM aerich ORDER BY id DESC LIMIT 5;"
    ;;
  
  tables)
    echo "Current database tables"
    docker exec postgres psql -U postgres -d domain_generator -c "\dt"
    ;;
  
  help|*)
    echo "Database Migration Helper"
    echo ""
    echo "Usage: ./migrate.sh <command>"
    echo ""
    echo "Commands:"
    echo "  init          - Initialize Aerich"
    echo "  init-db       - Create initial migration and apply to DB"
    echo "  migrate [name] - Generate new migration from model changes"
    echo "  upgrade       - Apply pending migrations"
    echo "  downgrade     - Rollback last migration"
    echo "  history       - Show migration history"
    echo "  heads         - Show current migration heads"
    echo "  status        - Show current migration status"
    echo "  tables        - List all tables in database"
    echo ""
    echo "Examples:"
    echo "  ./migrate.sh migrate add_user_table"
    echo "  ./migrate.sh upgrade"
    echo "  ./migrate.sh status"
    ;;
esac

