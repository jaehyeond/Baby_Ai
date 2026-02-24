#!/bin/bash
# Ablation Study Orchestrator for ICDL 2026 Paper
# Runs 4 conditions × 5 repetitions × 60 conversations (in batches of 10)
# Total: 20 runs × 6 batches = 120 API calls
#
# Usage:
#   bash scripts/run_ablation.sh                    # Run all 20
#   bash scripts/run_ablation.sh C_full 1           # Run single condition+rep
#   bash scripts/run_ablation.sh C_full 1 --dry-run # Dry run

SUPABASE_URL="https://extbfhoktzozgqddjcps.supabase.co"
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV4dGJmaG9rdHpvemdxZGRqY3BzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgxMTE5NzMsImV4cCI6MjA1MzY4Nzk3M30.8lE3ZFzzCnLkO8Ht76vOj8IB6A06kl4woagGQXGbJmk"
EF_URL="${SUPABASE_URL}/functions/v1/ablation-runner"
BATCH_SIZE=10
LOG_DIR="scripts/ablation_logs"

mkdir -p "$LOG_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

run_single() {
  local condition=$1
  local rep=$2
  local dry_run=${3:-false}
  local log_file="${LOG_DIR}/${condition}_r${rep}.log"

  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${CYAN}  ${condition} rep=${rep} $([ "$dry_run" = "true" ] && echo "[DRY RUN]")${NC}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  local run_id=""
  local running_state=""
  local start_turn=1
  local total_concepts=0
  local total_relations=0
  local run_start=$(date +%s)

  while [ $start_turn -le 60 ]; do
    local batch_start=$(date +%s)
    local end_turn=$((start_turn + BATCH_SIZE - 1))
    [ $end_turn -gt 60 ] && end_turn=60

    echo -ne "  ${YELLOW}Batch turns ${start_turn}-${end_turn}...${NC} "

    # Build request body
    local body="{\"condition\":\"${condition}\",\"repetition\":${rep},\"start_turn\":${start_turn},\"batch_size\":${BATCH_SIZE}"
    if [ "$dry_run" = "true" ]; then
      body="${body},\"dry_run\":true"
    fi
    if [ -n "$run_id" ]; then
      body="${body},\"run_id\":\"${run_id}\""
    fi
    if [ -n "$running_state" ]; then
      body="${body},\"running_state\":${running_state}"
    fi
    body="${body}}"

    # Call ablation-runner
    local result
    result=$(curl -s -X POST "$EF_URL" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${ANON_KEY}" \
      -d "$body" \
      --max-time 150)

    # Parse result
    local success=$(echo "$result" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('success','false'))" 2>/dev/null || echo "false")

    if [ "$success" = "True" ] || [ "$success" = "true" ]; then
      run_id=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null)
      running_state=$(echo "$result" | python -c "import sys,json; import json as j; print(j.dumps(json.load(sys.stdin)['running_state']))" 2>/dev/null)
      total_concepts=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('new_concepts',0))" 2>/dev/null)
      total_relations=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('new_relations',0))" 2>/dev/null)
      local batch_time=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('batch_time_ms',0))" 2>/dev/null)
      local is_complete=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('is_complete',False))" 2>/dev/null)

      local batch_elapsed=$(( $(date +%s) - batch_start ))
      echo -e "${GREEN}OK${NC} (${batch_elapsed}s) concepts=${total_concepts} rels=${total_relations}"

      # Log
      echo "[$(date -Iseconds)] ${condition} r${rep} turns ${start_turn}-${end_turn}: concepts=${total_concepts} rels=${total_relations} time=${batch_time}ms" >> "$log_file"

      if [ "$is_complete" = "True" ] || [ "$is_complete" = "true" ] || [ "$dry_run" = "true" ]; then
        break
      fi

      start_turn=$((end_turn + 1))

      # Brief pause between batches
      sleep 2
    else
      local error=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('error','Unknown'))" 2>/dev/null || echo "$result")
      echo -e "${RED}FAIL: ${error}${NC}"
      echo "[$(date -Iseconds)] FAIL ${condition} r${rep} turns ${start_turn}-${end_turn}: ${error}" >> "$log_file"

      # Retry once after 5 seconds
      echo -ne "  ${YELLOW}Retrying in 5s...${NC} "
      sleep 5

      result=$(curl -s -X POST "$EF_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${ANON_KEY}" \
        -d "$body" \
        --max-time 150)

      success=$(echo "$result" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('success','false'))" 2>/dev/null || echo "false")

      if [ "$success" = "True" ] || [ "$success" = "true" ]; then
        run_id=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin)['run_id'])" 2>/dev/null)
        running_state=$(echo "$result" | python -c "import sys,json; import json as j; print(j.dumps(json.load(sys.stdin)['running_state']))" 2>/dev/null)
        total_concepts=$(echo "$result" | python -c "import sys,json; print(json.load(sys.stdin).get('new_concepts',0))" 2>/dev/null)
        echo -e "${GREEN}OK (retry)${NC}"
        start_turn=$((end_turn + 1))
        sleep 2
      else
        echo -e "${RED}FAIL (retry failed, skipping to next run)${NC}"
        echo "[$(date -Iseconds)] FATAL ${condition} r${rep}: retry failed" >> "$log_file"
        break
      fi
    fi
  done

  local run_elapsed=$(( $(date +%s) - run_start ))
  echo -e "  ${GREEN}Completed: ${total_concepts} concepts, ${total_relations} relations in ${run_elapsed}s${NC}"
  echo ""
}

# Parse arguments
if [ -n "$1" ] && [ -n "$2" ]; then
  # Single run mode
  dry_run="false"
  [ "$3" = "--dry-run" ] && dry_run="true"
  run_single "$1" "$2" "$dry_run"
else
  # Full run: 4 conditions × 5 repetitions
  CONDITIONS=("C_full" "C_nostage" "C_noemo" "C_nosleep")
  TOTAL_RUNS=20
  COMPLETED=0
  OVERALL_START=$(date +%s)

  echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║  ICDL 2026 Ablation Study: ${TOTAL_RUNS} runs              ║${NC}"
  echo -e "${CYAN}║  4 conditions × 5 reps × 60 conversations       ║${NC}"
  echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
  echo ""

  for condition in "${CONDITIONS[@]}"; do
    for rep in 1 2 3 4 5; do
      COMPLETED=$((COMPLETED + 1))
      echo -e "${YELLOW}[${COMPLETED}/${TOTAL_RUNS}]${NC} Starting ${condition} rep=${rep}"
      run_single "$condition" "$rep"

      # Pause between runs to let DB settle
      if [ $COMPLETED -lt $TOTAL_RUNS ]; then
        echo -e "  ${YELLOW}Pausing 5s before next run...${NC}"
        sleep 5
      fi
    done
  done

  OVERALL_ELAPSED=$(( $(date +%s) - OVERALL_START ))
  echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  All ${TOTAL_RUNS} runs completed in $((OVERALL_ELAPSED / 60))m $((OVERALL_ELAPSED % 60))s       ${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
fi
