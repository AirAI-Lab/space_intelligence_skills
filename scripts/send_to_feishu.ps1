# 发送通知到飞书 Webhook
param(
    [Parameter(Mandatory=$true)]
    [string]$Message
)

# 配置文件路径
$configFile = Join-Path $PSScriptRoot "feishu_config.json"

# 读取配置
$webhook = $null
if (Test-Path $configFile) {
    try {
        $config = Get-Content $configFile -Raw | ConvertFrom-Json
        $webhook = $config.webhook
    } catch {
        Write-Output "Failed to read config: $_"
    }
}

if (-not $webhook) {
    Write-Output "No webhook configured. Please create $configFile with content:"
    Write-Output '{ "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR-WEBHOOK-ID" }'
    exit 1
}

try {
    $body = @{
        msg_type = "text"
        content = @{
            text = $Message
        }
    } | ConvertTo-Json -Depth 3

    $response = Invoke-RestMethod -Uri $webhook -Method Post -Body $body -ContentType "application/json; charset=utf-8"

    if ($response.StatusCode -eq 0) {
        Write-Output "Feishu notification sent successfully"
    } else {
        Write-Output "Failed to send notification: $($response.msg)"
    }
} catch {
    Write-Output "Error sending notification: $_"
    exit 1
}
