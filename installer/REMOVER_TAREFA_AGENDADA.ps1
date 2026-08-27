<#
    Remove a Tarefa Agendada do MILK registrada por
    installer\REGISTRAR_TAREFA_AGENDADA.ps1.

    Não apaga nenhum arquivo do projeto -- apenas desativa o início
    automático ao logon.

    Uso:
        powershell -ExecutionPolicy Bypass -File installer\REMOVER_TAREFA_AGENDADA.ps1
#>

$ErrorActionPreference = "Stop"
$TaskName = "MILK_Assistant"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "Tarefa '$TaskName' não estava registrada. Nada a fazer."
    exit 0
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false

Write-Host "Tarefa '$TaskName' removida. O MILK não vai mais iniciar automaticamente ao logon." -ForegroundColor Yellow
