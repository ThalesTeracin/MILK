$exe = "C:\JARVIS\dist\MILK\MILK.exe"
if (-not (Test-Path $exe)) {
    Write-Host "MILK.exe ainda não existe. Rode build_exe.ps1 primeiro." -ForegroundColor Yellow
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $desktop "MILK.lnk"

$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($link)
$s.TargetPath = $exe
$s.WorkingDirectory = "C:\JARVIS"
$s.Save()

Write-Host "Atalho criado no Desktop." -ForegroundColor Green
