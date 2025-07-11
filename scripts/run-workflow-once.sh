#!/bin/bash
# Run a workflow once for testing using Temporal CLI
# This script executes a workflow once with optional input parameters

# Default values
WORKFLOW_ID=""
WORKFLOW_TYPE=""
TASK_QUEUE="the-assistant"
TEMPORAL_ADDRESS=${TEMPORAL_HOST:-"localhost:7233"}
TEMPORAL_NAMESPACE=${TEMPORAL_NAMESPACE:-"default"}
INPUT_PARAMS=""
USER_ID="1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --workflow-id)
      WORKFLOW_ID="$2"
      shift 2
      ;;
    --workflow-type)
      WORKFLOW_TYPE="$2"
      shift 2
      ;;
    --task-queue)
      TASK_QUEUE="$2"
      shift 2
      ;;
    --input)
      INPUT_PARAMS="$2"
      shift 2
      ;;
    --user-id)
      USER_ID="$2"
      shift 2
      ;;
    --address)
      TEMPORAL_ADDRESS="$2"
      shift 2
      ;;
    --namespace)
      TEMPORAL_NAMESPACE="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --workflow-id ID       Workflow ID (required)"
      echo "  --workflow-type TYPE   Workflow type (required)"
      echo "  --task-queue QUEUE     Task queue (default: the-assistant)"
      echo "  --user-id ID           User ID (default: 1)"
      echo "  --input JSON           Input parameters as JSON string"
      echo "  --address ADDR         Temporal server address (default: localhost:7233)"
      echo "  --namespace NS         Temporal namespace (default: default)"
      echo "  --help                 Show this help message"
      echo ""
      echo "Example:"
      echo "  $0 --workflow-id test-daily-briefing --workflow-type DailyBriefing"
      echo "  $0 --workflow-id test-daily-briefing --workflow-type DailyBriefing --user-id 2"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate required parameters
if [ -z "$WORKFLOW_ID" ]; then
  echo "Error: --workflow-id is required"
  exit 1
fi

if [ -z "$WORKFLOW_TYPE" ]; then
  echo "Error: --workflow-type is required"
  exit 1
fi

# Build the command
CMD="temporal workflow start --workflow-id $WORKFLOW_ID --workflow-type $WORKFLOW_TYPE --task-queue $TASK_QUEUE --address $TEMPORAL_ADDRESS --namespace $TEMPORAL_NAMESPACE"

# Add user_id as input parameter (always required for workflows)
if [ ! -z "$INPUT_PARAMS" ]; then
  # If custom input is provided, assume it includes user_id
  CMD="$CMD --input '$INPUT_PARAMS'"
else
  # Default case: pass user_id as the only parameter
  CMD="$CMD --input '$USER_ID'"
fi

# Execute the workflow
echo "Starting workflow '$WORKFLOW_TYPE' with ID '$WORKFLOW_ID'"
echo "Task queue: $TASK_QUEUE"
echo "User ID: $USER_ID"
echo "Temporal server: $TEMPORAL_ADDRESS, Namespace: $TEMPORAL_NAMESPACE"
if [ ! -z "$INPUT_PARAMS" ]; then
  echo "Input parameters: $INPUT_PARAMS"
else
  echo "Using default user_id: $USER_ID"
fi

eval $CMD

# Check if the workflow was started successfully
if [ $? -eq 0 ]; then
  echo "Workflow started successfully!"
  echo "To view the workflow status, run: temporal workflow show --workflow-id $WORKFLOW_ID"
else
  echo "Failed to start workflow."
  exit 1
fi