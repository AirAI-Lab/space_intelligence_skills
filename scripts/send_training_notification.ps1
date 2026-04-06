# 发送 ACTA+ViT-Large 训练通知到飞书
# 使用 OpenClaw 的 message 工具

param(
    [Parameter(Mandatory=$true)]
    [string]$Title,
    
    [Parameter(Mandatory=$true)]
    [string]$Message,
    
    [string]$CardType = "interactive"
)

# 构建飞书卡片消息
$card = @{
    msg_type = $CardType
    card = @{
        header = @{
            title = @{
                tag = "plain_text"
                content = $Title
            }
            template = "blue"
        }
        elements = @(
            @{
                tag = "div"
                text = @{
                    tag = "lark_md"
                    content = $Message
                }
            },
            @{
                tag = "note"
                elements = @(
                    @{
                        tag = "plain_text"
                        content = "时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                    }
                )
            }
        )
    }
}

# 保存到临时文件
$tempFile = Join-Path $env:TEMP "feishu_card_$(Get-Date -Format 'yyyyMMddHHmmss').json"
$card | ConvertTo-Json -Depth 10 | Set-Content $tempFile -Encoding UTF8

Write-Output "卡片消息已生成: $tempFile"
Write-Output "请使用 OpenClaw message 工具发送，或将此卡片配置到监控脚本中"

# 显示卡片内容
Write-Output "`n卡片内容:"
Get-Content $tempFile

return $tempFile
