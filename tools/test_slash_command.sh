#!/usr/bin/env bash
# Test whether Claude Code expands slash-commands in --print mode.
# Run inside the API container: podman exec -i ai-data-factory_api_1 bash < tools/test_slash_command.sh

set -e

TEST_DIR=/tmp/claude-slash-test
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

# Claude Code looks for .claude/commands/ relative to the cwd.
cp -r /app/.claude "$TEST_DIR/"

# Minimal input for /generate-schema.
cat > "$TEST_DIR/dataset_description.md" <<'DESC'
Simple user signup dataset: users with id, name, email, signup_date, country.
Locale en_US. About 100 users across 5 countries.
DESC

cd "$TEST_DIR"

echo "=== Running /generate-schema via claude --print ==="
# IS_SANDBOX=1 tells Claude Code it's in a sandboxed env, allowing
# --dangerously-skip-permissions to run as root (same as the backend).
export IS_SANDBOX=1
unset ANTHROPIC_API_KEY
time claude --print --dangerously-skip-permissions \
  --model claude-haiku-4-5 \
  --disallowedTools "Bash,Write,Edit,Glob,Grep,WebFetch,WebSearch,Task,TodoWrite,NotebookEdit" \
  -- "/generate-schema" 2>&1 | tee /tmp/slash-test-output.log | head -120

echo ""
echo "=== Files in test dir after run ==="
ls -la "$TEST_DIR"

echo ""
echo "=== data_schema_spec.md (if created) ==="
if [ -f "$TEST_DIR/data_schema_spec.md" ]; then
  head -40 "$TEST_DIR/data_schema_spec.md"
else
  echo "NOT CREATED"
fi
