#!/bin/bash
# Auto-update script for Wingman on TrueNAS SCALE
# This script can be scheduled as a cron job for automatic updates

set -e

NAMESPACE="${NAMESPACE:-wingman}"
IMAGE="${IMAGE:-ghcr.io/your-username/wingman:latest}"

echo "=== Wingman Auto-Update Script ==="
echo "Namespace: $NAMESPACE"
echo "Image: $IMAGE"
echo ""

# Check if deployment exists
if ! kubectl get deployment wingman -n "$NAMESPACE" >/dev/null 2>&1; then
    echo "Error: Wingman deployment not found in namespace $NAMESPACE"
    exit 1
fi

echo "Current image:"
kubectl get deployment wingman -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""

# Pull latest image
echo "Pulling latest image..."
docker pull "$IMAGE" || echo "Warning: Could not pull image directly"

# Restart deployment to trigger update
echo "Triggering rolling update..."
kubectl rollout restart deployment/wingman -n "$NAMESPACE"

# Wait for rollout to complete
echo "Waiting for rollout to complete..."
kubectl rollout status deployment/wingman -n "$NAMESPACE" --timeout=5m

echo ""
echo "New image:"
kubectl get deployment wingman -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[0].image}'
echo ""

echo "✓ Update complete!"
echo ""
echo "View logs with: kubectl logs -f deployment/wingman -n $NAMESPACE"
