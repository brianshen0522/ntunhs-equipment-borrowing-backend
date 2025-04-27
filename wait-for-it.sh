#!/usr/bin/env bash
host="$1"
shift
cmd="$@"

echo "Waiting for $host:5432 to be available..."

while ! nc -z "$host" 5432; do
  sleep 1
  echo "Waiting for Postgres..."
done

echo "Postgres is up - executing command"
exec $cmd
