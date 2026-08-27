# =============================================================================
# SUBSTITUÍDO (Fase 3 - unificação de entry points, 2026-08-27).
# O mecanismo atual de início automático é uma Tarefa Agendada -- use
# installer\REMOVER_TAREFA_AGENDADA.ps1 para desativar. Este script só
# removia o antigo atalho MILK_Presence.cmd/.vbs em Startup (já
# desativado/arquivado em installer\archive_startup\). Mantido apenas
# como referência.
# =============================================================================
$startup = [Environment]::GetFolderPath("Startup")
$cmd = Join-Path $startup "MILK_Presence.cmd"
if (Test-Path $cmd) {
    Remove-Item $cmd -Force
}
Write-Host "Inicialização automática da MILK removida." -ForegroundColor Yellow
