# Edge Cloud WSL2 Keepalive Script
# Prevents systemd-logind from shutting down WSL2 when no sessions are active
while ($true) {
    wsl -d Ubuntu -- bash -c 'sleep 60' 2>$null
    Start-Sleep -Seconds 5
}
