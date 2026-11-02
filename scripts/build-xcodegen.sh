#!/usr/bin/env bash
set -euo pipefail
: "${APP_CONFIG:?}" "${SOURCE_SHA:?}" "${RUNNER_TEMP:?}" "${ARTIFACT_AGE_RECIPIENT:?}"
app_dir=$(python3 -c 'import json,os; print(json.loads(os.environ["APP_CONFIG"])["directory"])')
scheme=$(python3 -c 'import json,os; print(json.loads(os.environ["APP_CONFIG"])["scheme"])')
project=$(python3 -c 'import json,os; print(json.loads(os.environ["APP_CONFIG"])["project"])')
python3 "$GITHUB_WORKSPACE/control/scripts/prepare-hex.py" "$GITHUB_WORKSPACE/source/$app_dir"
cd "$GITHUB_WORKSPACE/source/$app_dir"
# No signing secrets or Apple API credentials are available in this job.
command -v xcodegen >/dev/null || brew install xcodegen
xcodegen --version
xcodegen generate
mkdir -p "$RUNNER_TEMP/output"
xcodebuild archive \
  -project "$project" -scheme "$scheme" -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$RUNNER_TEMP/output/App.xcarchive" \
  -derivedDataPath "$RUNNER_TEMP/DerivedData" \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY='' \
  CURRENT_PROJECT_VERSION="${GITHUB_RUN_NUMBER}.${GITHUB_RUN_ATTEMPT}" \
  | tee "$RUNNER_TEMP/output/xcodebuild.log"
python3 "$GITHUB_WORKSPACE/control/scripts/package-archive.py"
