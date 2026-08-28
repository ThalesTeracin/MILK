<#
    Atualiza o MILK com reversão automática.

    A ordem dos passos não é arbitrária:

    - Verificar se há uma origem configurada é o primeiro passo porque,
      sem remote (por exemplo, em uma cópia local sem git clone de um
      servidor), não existe atualização possível: `git pull` falharia
      sem sentido. Ausência de origem não é uma falha da atualização,
      é a ausência da própria atualização -- por isso o script sai com
      código 0, sem tocar em git nem na tarefa agendada.

    - Exigir árvore limpa é o que torna a reversão segura. git reset
      --hard descarta alterações não commitadas; recusar entrar com a
      árvore suja garante que não há trabalho a destruir na saída.

    - Parar a tarefa antes de migrar, porque o processo mantém o SQLite
      aberto em modo WAL. Isso só se aplica quando a tarefa agendada
      'MILK_Assistant' está de fato registrada nesta máquina -- este
      script nunca cria, registra ou modifica tarefas agendadas, só
      consulta e liga/desliga uma que já exista. Se ela não existir, o
      MILK não é parado e a atualização segue mesmo assim; quem estiver
      rodando o MILK por outro caminho (fora de uma tarefa agendada)
      pode ter o banco preso em WAL até reiniciar manualmente.
      Stop-ScheduledTask retorna antes do processo morrer, então
      esperamos a tarefa deixar de estar em execução pelo estado
      relatado pela própria tarefa agendada (Get-ScheduledTask), não
      por Get-Process pythonw: um pythonw de outro programa qualquer na
      máquina casaria com esse nome de processo e faria o script esperar
      à toa, ou pior, cancelar por engano.

    - Instalar as dependências vem antes de migrar e de testar porque
      uma versão nova pode trazer dependência nova. Sem esse passo ela
      faltaria, os testes falhariam e a atualização boa seria revertida:
      nenhuma versão que acrescentasse dependência poderia ser aceita.
      O pip NÃO é desfeito na reversão -- pacote instalado a mais é
      inofensivo, pelo mesmo motivo que a migração aditiva é.

    - A reversão só é segura porque as migrações são somente aditivas
      (ADD COLUMN). Se a migração rodou e os testes falharam, o código
      volta e o banco fica adiante sem quebrar.

    Uso:
        powershell -ExecutionPolicy Bypass -File installer\Atualizar_MILK.ps1
#>

$ErrorActionPreference = "Continue"

$Raiz     = "C:\JARVIS"
$Tarefa   = "MILK_Assistant"
$LogFile  = Join-Path $Raiz "logs\update.log"

Set-Location $Raiz

function Versao {
    (& python "src\main.py" "--version" 2>$null | Select-Object -First 1)
}

function Registrar($antes, $depois, $resultado, $detalhe) {
    $py = @"
import sys, datetime
sys.path.insert(0, 'src')
from core.update_log import linha_de_log, registrar
from pathlib import Path
registrar(Path(r'$LogFile'), linha_de_log(
    datetime.datetime.now(), r'''$antes''', r'''$depois''',
    r'''$resultado''', r'''$detalhe''' or None))
"@
    $py | & python -
}

# --- 0. Existe origem configurada? ---
# Sem remote, ou com a branch atual sem upstream, não há de onde
# atualizar. Sair aqui, antes de qualquer outra checagem: não é um
# erro, é a ausência do próprio cenário de atualização.
$remotos = & git remote 2>$null
$upstream = & git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
if (-not $remotos -or -not $upstream) {
    Write-Host "Nenhuma origem configurada para este repositório (sem remote ou sem upstream)." -ForegroundColor Yellow
    Write-Host "Não há de onde atualizar. Nada a fazer." -ForegroundColor Yellow
    exit 0
}

# --- 1. Árvore limpa ---
$sujo = & git status --porcelain
if ($sujo) {
    Write-Host "Há alterações não commitadas. A atualização foi cancelada." -ForegroundColor Yellow
    Write-Host "Commite ou descarte antes de atualizar:" -ForegroundColor Yellow
    Write-Host $sujo
    exit 1
}

# --- 2. Guardar o ponto de retorno ---
$antesCommit = (& git rev-parse HEAD).Trim()
$antesVersao = Versao
Write-Host "Versão atual: $antesVersao"

# --- 3. Parar a tarefa (se registrada) e esperar o processo morrer ---
$tarefaExiste = $null -ne (Get-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue)

if ($tarefaExiste) {
    Write-Host "Parando $Tarefa..."
    Stop-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue

    $limite = (Get-Date).AddSeconds(30)
    while ((Get-ScheduledTask -TaskName $Tarefa).State -eq 'Running') {
        if ((Get-Date) -gt $limite) {
            Write-Host "O processo do MILK não encerrou em 30s. Atualização cancelada." -ForegroundColor Red
            Start-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue
            exit 1
        }
        Start-Sleep -Milliseconds 500
    }
} else {
    Write-Host "Tarefa agendada '$Tarefa' não está registrada nesta máquina; o MILK não será parado." -ForegroundColor Yellow
}

# --- 4 a 6. Atualizar, migrar, testar ---
$falha = $null

try {
    Write-Host "Atualizando..."
    & git pull
    if ($LASTEXITCODE -ne 0) { throw "git pull falhou" }

    # Antes de migrar: uma versao nova pode trazer dependencia nova, e
    # sem este passo ela faltaria, os testes falhariam e a atualizacao
    # boa seria revertida -- ou seja, nenhuma versao que acrescente
    # dependencia poderia ser aceita.
    Write-Host "Instalando dependências..."
    & python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }

    Write-Host "Migrando o banco..."
    & python -c "import sys; sys.path.insert(0,'src'); from memory.long_memory import LongMemory; LongMemory().close()"
    if ($LASTEXITCODE -ne 0) { throw "migração falhou" }

    Write-Host "Rodando os testes..."
    & python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "testes falharam" }
}
catch {
    $falha = $_.Exception.Message
}

# --- 7. Concluir ou reverter ---
if ($falha) {
    Write-Host "Falhou: $falha. Revertendo para $antesCommit." -ForegroundColor Red
    & git reset --hard $antesCommit | Out-Null
    if ($tarefaExiste) { Start-ScheduledTask -TaskName $Tarefa }
    Registrar $antesVersao (Versao) "FALHOU" "$falha  revertido"
    exit 1
}

$depoisVersao = Versao
if ($tarefaExiste) { Start-ScheduledTask -TaskName $Tarefa }
Registrar $antesVersao $depoisVersao "OK" ""

Write-Host ""
Write-Host "Atualizado: $antesVersao -> $depoisVersao" -ForegroundColor Green
Write-Host "Registro em logs\update.log"
