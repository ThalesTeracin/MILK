<#
    Instalação limpa do MILK.

    Seguro de rodar numa máquina já instalada: cada passo verifica antes
    se o destino existe, e não refaz o que já está pronto. Os passos 4 e
    5 são os únicos que dependem de rede e concentram os 250 MB que o
    repositório não carrega.

    A tarefa agendada NÃO é registrada por padrão. Registrar altera o
    Windows fora do repositório, então exige o parâmetro explícito
    -RegistrarTarefa.

    Uso:
        powershell -ExecutionPolicy Bypass -File installer\INSTALAR.ps1
        powershell -ExecutionPolicy Bypass -File installer\INSTALAR.ps1 -RegistrarTarefa
#>

param(
    [switch]$RegistrarTarefa
)

$ErrorActionPreference = "Stop"

$Raiz         = "C:\JARVIS"
$ModeloUrl    = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
$ModeloDest   = Join-Path $Raiz "models\ggml-base.bin"
$ModeloBytes  = 147951465
$WhisperDir   = Join-Path $Raiz "third_party\whisper-prebuilt"

Set-Location $Raiz

# --- 1. Python ---
$versao = (& python -c "import sys; print('%d.%d' % sys.version_info[:2])").Trim()
if ([version]$versao -lt [version]"3.12") {
    throw "Python $versao encontrado. O MILK exige 3.12 ou mais novo."
}
Write-Host "Python $versao" -ForegroundColor Green

# --- 2. Dependências ---
Write-Host "Instalando dependências..."
& python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }

# --- 3. config/local/ a partir dos exemplos ---
$local = Join-Path $Raiz "config\local"
New-Item -ItemType Directory -Force -Path $local | Out-Null

foreach ($nome in @("audio_device", "whisper_local")) {
    $destino = Join-Path $local "$nome.json"
    if (Test-Path $destino) {
        Write-Host "config/local/$nome.json já existe, mantido."
    } else {
        Copy-Item (Join-Path $Raiz "config\$nome.example.json") $destino
        Write-Host "config/local/$nome.json criado do exemplo." -ForegroundColor Yellow
    }
}

# --- 4. Modelo do Whisper (148 MB) ---
if ((Test-Path $ModeloDest) -and ((Get-Item $ModeloDest).Length -eq $ModeloBytes)) {
    Write-Host "Modelo do Whisper já presente."
} else {
    Write-Host "Baixando o modelo do Whisper (148 MB)..."
    New-Item -ItemType Directory -Force -Path (Split-Path $ModeloDest) | Out-Null
    try {
        Invoke-WebRequest -Uri $ModeloUrl -OutFile $ModeloDest
    } catch {
        throw "Download do modelo falhou: $_`nRode INSTALAR.ps1 de novo; os passos anteriores serão pulados."
    }
}

# --- 5. Binário do Whisper ---
if (Test-Path (Join-Path $WhisperDir "Release\whisper-cli.exe")) {
    Write-Host "whisper-cli já presente."
} else {
    Write-Host "whisper-cli ausente em $WhisperDir." -ForegroundColor Yellow
    Write-Host "Rode INSTALAR_WHISPER_PRECOMPILADO.ps1 (na raiz do repositório) e depois este script de novo."
    exit 1
}

# --- 6. Microfone ---
$audio = Get-Content (Join-Path $local "audio_device.json") -Raw | ConvertFrom-Json
# O que conta como configurado e o nome, nao o indice: o indice e a
# posicao na lista do PortAudio e muda quando um fone conecta ou sai.
# O ramo do input_device atende quem ainda tem o arquivo no formato antigo.
if ([string]::IsNullOrWhiteSpace($audio.input_name) -and $audio.input_device -eq 0) {
    Write-Host "Escolha o microfone:" -ForegroundColor Cyan
    & python "Selecionar_Microfone.py"
} elseif ([string]::IsNullOrWhiteSpace($audio.input_name)) {
    Write-Host "Microfone configurado por indice ($($audio.input_device)), formato antigo." -ForegroundColor Yellow
    Write-Host "Rode Selecionar_Microfone.py para gravar o nome; por indice o MILK pode abrir o microfone errado."
} else {
    Write-Host "Microfone ja configurado ($($audio.input_name))."
}

# --- 7. Tarefa agendada (só com -RegistrarTarefa) ---
if ($RegistrarTarefa) {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $Raiz "installer\REGISTRAR_TAREFA_AGENDADA.ps1")
    if ($LASTEXITCODE -ne 0) { throw "o registro da tarefa agendada falhou" }
} else {
    Write-Host "Tarefa agendada não registrada (rode com -RegistrarTarefa para o MILK subir no logon)." -ForegroundColor Yellow
}

# --- 8. Provar que funciona ---
Write-Host "Validando a instalação..."
& python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "os testes falharam; a instalação não está sã" }

Write-Host ""
Write-Host "MILK instalado. Versão: $(& python 'src\main.py' '--version')" -ForegroundColor Green
