#!/usr/bin/env bash
# Run in the checkout root after the importer, including on fetch failure.
# Only JSON data is committed; a non-fast-forward push must fail, never overwrite.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
if [[ "$(git branch --show-current)" != main ]]; then
  echo 'Archivänderungen dürfen nur von main gespeichert werden.' >&2
  exit 1
fi

git add -- data/appointments.json data/status.json
if ! git diff --cached --quiet -- data/appointments.json data/status.json; then
  git -c user.name='github-actions[bot]' \
    -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
    commit --only -m 'data: update donation archive and fetch status' \
    -- data/appointments.json data/status.json >&2
fi
git push origin HEAD:main >&2
git rev-parse HEAD
