[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string[]]$SourceRepositories,
    [Parameter(Mandatory = $true)][string[]]$ConsumerInboxes,
    [ValidateSet('decision_confirmed', 'feature_verified', 'release_tagged', 'manual')]
    [string]$Trigger = 'manual',
    [string]$Summary = ''
)

$ErrorActionPreference = 'Stop'

function Get-RepositorySnapshot([string]$Path) {
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not (Test-Path -LiteralPath (Join-Path $resolved '.git'))) {
        throw "Not a Git repository: $resolved"
    }

    $gitPrefix = @('-c', "safe.directory=$resolved", '-C', $resolved)
    $headOutput = @(& git @gitPrefix rev-parse HEAD)
    if ($LASTEXITCODE -ne 0) { throw "Cannot read HEAD: $resolved" }
    $head = ($headOutput -join '').Trim()
    $branch = (@(& git @gitPrefix branch --show-current) -join '').Trim()
    $status = @(& git @gitPrefix status --short)
    $tagOutput = @(& git @gitPrefix describe --tags --abbrev=0 2>$null)
    $latestTag = if ($LASTEXITCODE -eq 0) { ($tagOutput -join '').Trim() } else { '' }

    [ordered]@{
        path = $resolved
        name = Split-Path -Leaf $resolved
        head = $head
        branch = $branch
        latest_tag = $latestTag
        dirty = $status.Count -gt 0
        changed_files = @($status | ForEach-Object { $_.Substring([Math]::Min(3, $_.Length)).Trim() })
    }
}

$snapshot = [ordered]@{
    schema_version = '1.0'
    generated_at = [DateTimeOffset]::Now.ToString('o')
    trigger = $Trigger
    summary = $Summary
    repositories = @($SourceRepositories | ForEach-Object { Get-RepositorySnapshot $_ })
}

$json = $snapshot | ConvertTo-Json -Depth 8
foreach ($inbox in $ConsumerInboxes) {
    $resolvedInbox = [IO.Path]::GetFullPath($inbox)
    New-Item -ItemType Directory -Force -Path $resolvedInbox | Out-Null
    $target = Join-Path $resolvedInbox 'project-context.json'
    [IO.File]::WriteAllText($target, $json + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
    Write-Output $target
}
