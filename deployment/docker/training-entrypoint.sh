#!/bin/bash
# Training container entrypoint

APP_LOG="/app/work/entrypoint.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [entrypoint] $1" | tee -a "$APP_LOG" || true; }

# GPU check
if [ "${USE_GPU:-true}" = "true" ]; then
    log "Checking GPU..."
    python3 -c "
import torch, sys
if not torch.cuda.is_available():
    print('FATAL: CUDA not available'); sys.exit(1)
mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f'GPU: {torch.cuda.get_device_name(0)}, {mem:.1f} GB')
" 2>&1 | tee -a "$APP_LOG" || log "WARNING: GPU check failed"
fi

log "Starting training service..."
exec python3 app.py
