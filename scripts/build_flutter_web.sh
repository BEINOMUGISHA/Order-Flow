#!/usr/bin/env bash
set -euo pipefail

base_href="${1:-/}"
if [[ -z "${ORDERFLOW_WS_URL:-}" ]]; then
  echo "ORDERFLOW_WS_URL must be set to the deployed backend WebSocket URL." >&2
  exit 1
fi

if ! command -v flutter >/dev/null 2>&1; then
  flutter_home="${FLUTTER_HOME:-${TMPDIR:-/tmp}/flutter-sdk}"
  if [[ ! -x "$flutter_home/bin/flutter" ]]; then
    git clone --depth 1 --branch stable https://github.com/flutter/flutter.git "$flutter_home"
  fi
  export PATH="$flutter_home/bin:$PATH"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/frontend"
flutter pub get
flutter build web \
  --release \
  --base-href "$base_href" \
  --dart-define="ORDERFLOW_WS_URL=$ORDERFLOW_WS_URL"