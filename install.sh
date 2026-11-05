#!/usr/bin/env sh
set -eu

SCOPE="project"
PROJECT_ROOT="$(pwd)"
FORCE=""
LINK=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --scope)
      SCOPE="$2"
      shift 2
      ;;
    --project-root)
      PROJECT_ROOT="$2"
      shift 2
      ;;
    --force)
      FORCE="--force"
      shift
      ;;
    --link)
      LINK="--link"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3.10 or newer is required." >&2
  exit 2
fi
if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Python 3.10 or newer is required." >&2
  exit 2
fi
exec "$PYTHON" "$SCRIPT_DIR/scripts/install_skill.py" \
  --scope "$SCOPE" \
  --project-root "$PROJECT_ROOT" \
  ${FORCE:+$FORCE} \
  ${LINK:+$LINK}
