<#
    Registra o MILK como Tarefa Agendada do Windows (Fase 3 da unificação
    de entry points, 2026-08-27).

    Substitui o mecanismo antigo (atalho .vbs em Startup rodando apenas
    MILK_Presence.py). Agora um único processo -- src/main.py, que reúne
    cérebro (MilkCore) + overlay/avatar + scheduler -- é iniciado:

      - Gatilho: ao logon do usuário atual (AtLogOn).
      - Reinício automático em caso de falha: até 3 tentativas, a cada 1
        minuto (RestartCount / RestartInterval).
      - LogonType Interactive: necessário porque o processo usa
        microfone, TTS e uma janela Tkinter (overlay) -- não pode rodar
        como serviço não interativo (SYSTEM) sem acesso à sessão do
        desktop.
      - Sem privilégio elevado (RunLevel Limited): consistente com o
        gate de permissão da Fase 2 -- o processo em si não roda como
        administrador.

    Uso (PowerShell, como o usuário que vai usar o MILK, não precisa ser
    administrador para esta tarefa em particular):

        powershell -ExecutionPolicy Bypass -File installer\REGISTRAR_TAREFA_AGENDADA.ps1

    Para remover: installer\REMOVER_TAREFA_AGENDADA.ps1
#>

$ErrorActionPreference = "Stop"

$TaskName    = "MILK_Assistant"
$JarvisRoot  = "C:\JARVIS"
$MainScript  = Join-Path $JarvisRoot "src\main.py"
$PythonwExe = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonwExe) {
    # Fallback: deriva pythonw.exe a partir do python.exe encontrado no PATH
    # (ficam sempre na mesma pasta em instalações padrão do Python no Windows).
    $PyExe = (Get-Command python.exe -ErrorAction Stop).Source
    $PythonwExe = Join-Path (Split-Path $PyExe -Parent) "pythonw.exe"
}
if (-not (Test-Path $PythonwExe)) {
    throw "Não encontrei pythonw.exe. Verifique se o Python está instalado e no PATH, e ajuste `$PythonwExe manualmente neste script."
}
if (-not (Test-Path $MainScript)) {
    throw "Não encontrei $MainScript. Rode este script a partir de uma cópia válida de $JarvisRoot."
}

Write-Host "Python (janela oculta): $PythonwExe"
Write-Host "Script principal:       $MainScript"

$action = New-ScheduledTaskAction `
    -Execute $PythonwExe `
    -Argument "`"$MainScript`"" `
    -WorkingDirectory $JarvisRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

# Remove uma tarefa antiga com o mesmo nome, se existir, para permitir
# re-registrar com configurações atualizadas.
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "MILK - assistente pessoal (cérebro + overlay + scheduler em processo único). Inicia ao logon, reinicia sozinho em caso de falha." `
    | Out-Null

Write-Host ""
Write-Host "Tarefa '$TaskName' registrada com sucesso." -ForegroundColor Green
Write-Host "Ela vai iniciar automaticamente no próximo logon."
Write-Host "Para iniciar agora sem reiniciar a sessão: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Para remover: installer\REMOVER_TAREFA_AGENDADA.ps1"
