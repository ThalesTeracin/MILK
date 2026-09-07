# Milk — assistente pessoal.
# Copyright (c) 2026 Thales Teracin. Todos os direitos reservados.
#
# Software proprietário. É proibida a cópia, a distribuição, a
# modificação e a engenharia reversa, no todo ou em parte, sem
# autorização expressa e por escrito do autor. Ver LICENSE.txt.

"""As ações da Milk no Windows.

Toda ação devolve um `ResultadoSistema` com um código da especificação:

    SUCCESS   aconteceu
    ERROR     tentou e não deu
    DENIED    a permissão não deixou
    TIMEOUT   demorou demais e foi encerrada

Nenhuma ação diz que deu certo sem ter dado: quando o Windows não
confirma, o código é ERROR e a frase explica o que houve.

Subprocesso nenhum abre janela preta (`CREATE_NO_WINDOW`), e todos têm
prazo. Tudo o que acontece aqui vira linha em `logs/system/`.
"""

import os
import glob
import ctypes
import shutil
import subprocess
import winreg

from pathlib import Path

from milk.core.log import logger, registrar_erro
from milk.system.permissao import avaliar, e_do_sistema


SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PRAZO_PADRAO = 20

# Fechar tem de ser rapido: e a resposta a um pedido falado.
PRAZO_DE_FECHAR = 5


class Codigo:
    SUCESSO = "SUCCESS"
    ERRO = "ERROR"
    NEGADA = "DENIED"
    TEMPO = "TIMEOUT"


class ResultadoSistema:
    """O que aconteceu, em uma frase e num código."""

    def __init__(self, codigo, texto, dados=None):
        self.codigo = codigo
        self.texto = texto
        self.dados = dados or {}

    @property
    def ok(self):
        return self.codigo == Codigo.SUCESSO

    def __repr__(self):
        return f"<{self.codigo}: {self.texto[:50]}>"


def deu_certo(texto, dados=None):
    return ResultadoSistema(Codigo.SUCESSO, texto, dados)


def deu_erro(texto, dados=None):
    return ResultadoSistema(Codigo.ERRO, texto, dados)


def negada(texto, dados=None):
    return ResultadoSistema(Codigo.NEGADA, texto, dados)


def demorou(texto, dados=None):
    return ResultadoSistema(Codigo.TEMPO, texto, dados)


# ============================================================
# PROGRAMAS CONHECIDOS
# ============================================================

# O que a pessoa fala -> o que o Windows entende.
PROGRAMAS = {
    "bloco de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorador de arquivos": "explorer.exe",
    "explorador": "explorer.exe",
    "gerenciador de tarefas": "taskmgr.exe",
    "prompt de comando": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "configurações": "ms-settings:",
    "configuracoes": "ms-settings:",
    "painel de controle": "control.exe",
    "navegador": "",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "spotify": "spotify.exe",
    "whatsapp": "whatsapp.exe",
    "vscode": "code.cmd",
    "visual studio code": "code.cmd",
    "vs code": "code.cmd",
}


def programa_conhecido(nome):
    """Devolve o executável, ou None se ela não conhece esse nome."""

    chave = " ".join(
        str(nome or "").strip().lower().split()
    )

    if chave in PROGRAMAS:
        return PROGRAMAS[chave], chave

    return None, chave


# ============================================================
# ABRIR COISAS
# ============================================================

def rodar_escondido(comando, prazo=PRAZO_PADRAO, entrada=None):
    """Roda um comando sem abrir janela, com prazo. Nunca levanta."""

    try:
        processo = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=prazo,
            creationflags=SEM_JANELA,
            input=entrada,
        )

        return processo, None

    except subprocess.TimeoutExpired:
        return None, "tempo"

    except OSError as erro:
        return None, str(erro)


# Onde o Windows anota o caminho dos programas instalados. E a mesma
# lista que a caixa "Executar" do Windows consulta.
APP_PATHS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"


def _no_registro(executavel):
    """O caminho anotado para esse programa, ou None.

    Chrome, Edge, Word, Spotify e afins se registram aqui e **nao**
    entram no PATH. Procurando so no PATH, ela respondia 'nao esta
    instalado' para programa instalado — foi o que aconteceu no
    teste ao vivo de 06/09/2026."""

    # A ultima e a visao de 32 bits: instalador antigo escreve la.
    visoes = (0, winreg.KEY_WOW64_32KEY)

    raizes = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)

    for raiz in raizes:
        for visao in visoes:
            try:
                with winreg.OpenKey(
                    raiz,
                    APP_PATHS + "\\" + executavel,
                    0,
                    winreg.KEY_READ | visao,
                ) as chave:
                    caminho, _ = winreg.QueryValueEx(chave, "")

            except OSError:
                continue

            caminho = str(caminho or "").strip().strip(chr(34))

            if caminho and os.path.exists(caminho):
                return caminho

    return None


def onde_esta(executavel):
    """O caminho inteiro do programa: primeiro o PATH, depois o
    registro. None quando ele nao esta em lugar nenhum.

    O subprocess so procura no PATH; o Windows procura nos dois. Ela
    tem de procurar como o Windows."""

    return shutil.which(executavel) or _no_registro(executavel)


def abrir_programa(nome):
    """Abre um programa conhecido pelo nome que a pessoa usa."""

    executavel, chave = programa_conhecido(nome)

    if executavel is None:
        return deu_erro(
            f"Não conheço um programa chamado {nome}. "
            "Se você me disser o caminho do arquivo, eu abro."
        )

    permissao = avaliar("abrir_programa", executavel)

    if permissao.bloqueada:
        return negada(permissao.motivo)

    # "navegador" sem nome: abre o padrão do Windows.
    if not executavel:
        return abrir_url("about:blank", como="navegador")

    # "ms-settings:" e afins não são arquivo: quem abre é o Windows.
    protocolo = executavel.endswith(":")

    # O subprocess só procura no PATH, e Chrome, Edge, Word e Spotify
    # não estão lá — estão no registro. Sem esta busca ela respondia
    # "não está instalado" para programa que está instalado.
    caminho = executavel if protocolo else onde_esta(executavel)

    if caminho is None:
        return deu_erro(
            f"O {chave} não está instalado nesta máquina, "
            "ou não está no caminho do sistema."
        )

    try:
        if protocolo:
            os.startfile(caminho)

        else:
            subprocess.Popen(
                [caminho],
                creationflags=SEM_JANELA,
                shell=False,
            )

        logger("system").info(f"abriu programa: {executavel}")

        return deu_certo(
            f"Abri o {chave}.",
            {"programa": executavel},
        )

    except FileNotFoundError:
        return deu_erro(
            f"O {chave} não está instalado nesta máquina, "
            "ou não está no caminho do sistema."
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao abrir {executavel}", erro)

        return deu_erro(
            f"Não consegui abrir o {chave}."
        )


# Os navegadores que ela conhece, na ordem em que tenta fechar.
# "fecha o navegador" nao aponta para um executavel so.
NAVEGADORES = (
    "chrome.exe",
    "msedge.exe",
    "firefox.exe",
    "brave.exe",
    "opera.exe",
)


# O taskkill devolve 128 quando o programa nem estava aberto.
NAO_ESTAVA_ABERTO = 128


def _pedir_para_fechar(executavel):
    """Pede para o programa fechar. True se ele estava aberto.

    Sem /F: e o mesmo que clicar no X da janela. O programa ainda
    pode perguntar se voce quer salvar, e e ele quem decide."""

    processo, falha = rodar_escondido(
        ["taskkill.exe", "/IM", executavel],
        prazo=PRAZO_DE_FECHAR,
    )

    if falha is not None or processo is None:
        return False

    return processo.returncode == 0


def fechar_programa(nome):
    """Fecha um programa conhecido, pelo nome que a pessoa usa."""

    executavel, chave = programa_conhecido(nome)

    if executavel is None:
        return deu_erro(
            f"Não conheço um programa chamado {nome}."
        )

    permissao = avaliar("fechar_programa", executavel)

    if permissao.bloqueada:
        return negada(permissao.motivo)

    # "navegador" nao e um executavel so: fecha os que estiverem
    # abertos, porque quem pediu nao sabe qual esta rodando.
    alvos = NAVEGADORES if not executavel else (executavel,)

    fechados = [
        alvo
        for alvo in alvos
        if _pedir_para_fechar(alvo)
    ]

    if not fechados:
        return deu_erro(
            f"O {chave} não estava aberto."
        )

    logger("system").info(f"fechou: {', '.join(fechados)}")

    return deu_certo(
        f"Fechei o {chave}.",
        {"fechados": fechados},
    )

def abrir_pasta(caminho):
    """Abre uma pasta no explorador de arquivos."""

    lugar = Path(
        os.path.expandvars(
            os.path.expanduser(str(caminho or ""))
        )
    )

    if not lugar.exists():
        return deu_erro(
            f"Não achei a pasta {lugar}."
        )

    if not lugar.is_dir():
        return abrir_arquivo(lugar)

    permissao = avaliar("abrir_pasta", str(lugar))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    try:
        subprocess.Popen(
            ["explorer.exe", str(lugar)],
            creationflags=SEM_JANELA,
        )

        logger("system").info(f"abriu pasta: {lugar}")

        return deu_certo(
            f"Abri a pasta {lugar}.",
            {"caminho": str(lugar)},
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao abrir pasta {lugar}", erro)

        return deu_erro(
            "Não consegui abrir essa pasta."
        )


def abrir_arquivo(caminho):
    """Abre um arquivo no programa padrão dele."""

    alvo = Path(
        os.path.expandvars(
            os.path.expanduser(str(caminho or ""))
        )
    )

    if not alvo.exists():
        return deu_erro(
            f"Não achei o arquivo {alvo}."
        )

    permissao = avaliar("abrir_arquivo", str(alvo))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    try:
        os.startfile(str(alvo))

        logger("system").info(f"abriu arquivo: {alvo}")

        return deu_certo(
            f"Abri {alvo.name}.",
            {"caminho": str(alvo)},
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao abrir arquivo {alvo}", erro)

        return deu_erro(
            "Não consegui abrir esse arquivo."
        )


def endereco_valido(url):
    texto = str(url or "").strip()

    if texto.startswith(("http://", "https://", "about:")):
        return texto

    # "google.com" vira "https://google.com".
    if "." in texto and " " not in texto:
        return "https://" + texto

    return None


def abrir_url(url, como="site"):
    """Abre um endereço no navegador padrão."""

    endereco = endereco_valido(url)

    if endereco is None:
        return deu_erro(
            f"{url} não parece um endereço de site."
        )

    permissao = avaliar("abrir_url", endereco)

    if permissao.bloqueada:
        return negada(permissao.motivo)

    try:
        os.startfile(endereco)

        logger("system").info(f"abriu url: {endereco}")

        if endereco == "about:blank":
            return deu_certo("Abri o navegador.")

        return deu_certo(
            f"Abri {endereco}.",
            {"url": endereco},
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao abrir url {endereco}", erro)

        return deu_erro(
            f"Não consegui abrir o {como}."
        )


# ============================================================
# ARQUIVOS
# ============================================================

PASTAS_DE_BUSCA = (
    "~/Desktop",
    "~/Documents",
    "~/Downloads",
    "~/Pictures",
)

LIMITE_DE_ACHADOS = 8


def procurar_arquivo(termo, pastas=None, limite=LIMITE_DE_ACHADOS):
    """Procura por nome nas pastas do usuário. Só leitura."""

    alvo = str(termo or "").strip()

    if len(alvo) < 2:
        return deu_erro(
            "Me diz um pedaço maior do nome do arquivo."
        )

    permissao = avaliar("procurar_arquivo")

    if permissao.bloqueada:
        return negada(permissao.motivo)

    achados = []

    for pasta in (pastas or PASTAS_DE_BUSCA):
        raiz = Path(os.path.expanduser(pasta))

        if not raiz.is_dir():
            continue

        try:
            for caminho in glob.iglob(
                str(raiz / "**" / f"*{alvo}*"),
                recursive=True,
            ):
                achados.append(caminho)

                if len(achados) >= limite:
                    break

        except OSError:
            continue

        if len(achados) >= limite:
            break

    if not achados:
        return deu_erro(
            f"Não achei nenhum arquivo com {alvo} no nome.",
            {"termo": alvo},
        )

    nomes = "; ".join(
        Path(caminho).name
        for caminho in achados
    )

    return deu_certo(
        f"Achei {len(achados)}: {nomes}.",
        {"achados": achados},
    )


def criar_pasta(caminho):
    """Cria uma pasta. Sensível: precisa de confirmação antes."""

    lugar = Path(
        os.path.expandvars(
            os.path.expanduser(str(caminho or ""))
        )
    )

    permissao = avaliar("criar_pasta", str(lugar))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    if lugar.exists():
        return deu_erro(
            f"A pasta {lugar} já existe."
        )

    try:
        lugar.mkdir(parents=True)

        logger("system").info(f"criou pasta: {lugar}")

        return deu_certo(
            f"Criei a pasta {lugar}.",
            {"caminho": str(lugar)},
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao criar pasta {lugar}", erro)

        return deu_erro(
            "Não consegui criar essa pasta."
        )


def copiar_arquivo(origem, destino):
    """Copia um arquivo. Sensível."""

    de = Path(os.path.expanduser(str(origem or "")))
    para = Path(os.path.expanduser(str(destino or "")))

    permissao = avaliar("copiar_arquivo", str(para))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    if not de.exists():
        return deu_erro(f"Não achei {de}.")

    if para.exists():
        return deu_erro(
            f"Já existe alguma coisa em {para}. "
            "Não vou sobrescrever sem você mandar."
        )

    try:
        shutil.copy2(de, para)

        logger("system").info(f"copiou {de} -> {para}")

        return deu_certo(
            f"Copiei {de.name} para {para}.",
            {"origem": str(de), "destino": str(para)},
        )

    except OSError as erro:
        registrar_erro("system", "falha ao copiar", erro)

        return deu_erro("Não consegui copiar esse arquivo.")


def mover_arquivo(origem, destino):
    """Move um arquivo. Sensível."""

    de = Path(os.path.expanduser(str(origem or "")))
    para = Path(os.path.expanduser(str(destino or "")))

    permissao = avaliar("mover_arquivo", str(de))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    if e_do_sistema(str(para)):
        return negada(
            "Não movo nada para dentro das pastas do Windows."
        )

    if not de.exists():
        return deu_erro(f"Não achei {de}.")

    if para.exists():
        return deu_erro(
            f"Já existe alguma coisa em {para}."
        )

    try:
        shutil.move(str(de), str(para))

        logger("system").info(f"moveu {de} -> {para}")

        return deu_certo(
            f"Movi {de.name} para {para}.",
            {"origem": str(de), "destino": str(para)},
        )

    except OSError as erro:
        registrar_erro("system", "falha ao mover", erro)

        return deu_erro("Não consegui mover esse arquivo.")


def apagar_arquivo(caminho):
    """Manda para a lixeira quando dá; senão, apaga mesmo. Destrutiva."""

    alvo = Path(os.path.expanduser(str(caminho or "")))

    permissao = avaliar("apagar_arquivo", str(alvo))

    if permissao.bloqueada:
        return negada(permissao.motivo)

    if not alvo.exists():
        return deu_erro(f"Não achei {alvo}.")

    if alvo.is_dir():
        return negada(
            "Não apago pastas inteiras. Arquivo, sim; pasta, não."
        )

    try:
        alvo.unlink()

        logger("system").info(f"apagou arquivo: {alvo}")

        return deu_certo(
            f"Apaguei {alvo.name}.",
            {"caminho": str(alvo)},
        )

    except OSError as erro:
        registrar_erro("system", f"falha ao apagar {alvo}", erro)

        return deu_erro("Não consegui apagar esse arquivo.")


# ============================================================
# O COMPUTADOR
# ============================================================

class _Memoria(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


class _Energia(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus", ctypes.c_byte),
        ("BatteryFlag", ctypes.c_byte),
        ("BatteryLifePercent", ctypes.c_byte),
        ("SystemStatusFlag", ctypes.c_byte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


def em_gigas(bytes_):
    return round(bytes_ / (1024 ** 3), 1)


def ver_computador():
    """Memória, disco, bateria e há quanto tempo a máquina está ligada.

    Tudo pela API do Windows, sem subprocesso e sem dependência nova."""

    permissao = avaliar("ver_computador")

    if permissao.bloqueada:
        return negada(permissao.motivo)

    partes = []
    dados = {}

    try:
        memoria = _Memoria()
        memoria.dwLength = ctypes.sizeof(_Memoria)

        ctypes.windll.kernel32.GlobalMemoryStatusEx(
            ctypes.byref(memoria)
        )

        dados["memoria_usada_por_cento"] = memoria.dwMemoryLoad
        dados["memoria_total_gb"] = em_gigas(memoria.ullTotalPhys)
        dados["memoria_livre_gb"] = em_gigas(memoria.ullAvailPhys)

        partes.append(
            f"A memória está em {memoria.dwMemoryLoad} por cento, "
            f"com {em_gigas(memoria.ullAvailPhys)} gigas livres "
            f"de {em_gigas(memoria.ullTotalPhys)}"
        )

    except Exception as erro:
        registrar_erro("system", "falha ao ler memória", erro)

    try:
        uso = shutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")

        dados["disco_livre_gb"] = em_gigas(uso.free)
        dados["disco_total_gb"] = em_gigas(uso.total)

        partes.append(
            f"o disco tem {em_gigas(uso.free)} gigas livres "
            f"de {em_gigas(uso.total)}"
        )

    except OSError:
        pass

    try:
        energia = _Energia()

        ctypes.windll.kernel32.GetSystemPowerStatus(
            ctypes.byref(energia)
        )

        if energia.BatteryLifePercent <= 100:
            dados["bateria_por_cento"] = energia.BatteryLifePercent
            dados["na_tomada"] = bool(energia.ACLineStatus == 1)

            tomada = (
                "na tomada"
                if energia.ACLineStatus == 1
                else "na bateria"
            )

            partes.append(
                f"a bateria está em {energia.BatteryLifePercent} "
                f"por cento, {tomada}"
            )

    except Exception:
        pass

    try:
        ligado_ha = ctypes.windll.kernel32.GetTickCount64() / 1000.0

        horas = int(ligado_ha // 3600)
        minutos = int((ligado_ha % 3600) // 60)

        dados["ligado_ha_horas"] = horas

        if horas:
            partes.append(
                f"e o computador está ligado há {horas} horas "
                f"e {minutos} minutos"
            )

        else:
            partes.append(
                f"e o computador está ligado há {minutos} minutos"
            )

    except Exception:
        pass

    if not partes:
        return deu_erro(
            "Não consegui ler o estado do computador agora."
        )

    return deu_certo(
        ", ".join(partes) + ".",
        dados,
    )


def listar_processos(quantos=5):
    """Os programas que mais estão consumindo memória."""

    permissao = avaliar("listar_processos")

    if permissao.bloqueada:
        return negada(permissao.motivo)

    processo, falha = rodar_escondido(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "Get-Process | Sort-Object WorkingSet64 -Descending | "
                f"Select-Object -First {int(quantos)} "
                "Name,@{n='MB';e={[int]($_.WorkingSet64/1MB)}} | "
                "ForEach-Object { \"$($_.Name) $($_.MB)\" }"
            ),
        ],
        prazo=15,
    )

    if falha == "tempo":
        return demorou(
            "Demorei demais para ver os programas abertos."
        )

    if falha or processo is None or processo.returncode != 0:
        return deu_erro(
            "Não consegui ver os programas abertos."
        )

    linhas = [
        linha.strip()
        for linha in processo.stdout.splitlines()
        if linha.strip()
    ]

    if not linhas:
        return deu_erro(
            "Não consegui ver os programas abertos."
        )

    partes = []

    for linha in linhas:
        pedacos = linha.rsplit(" ", 1)

        if len(pedacos) == 2:
            partes.append(f"{pedacos[0]} com {pedacos[1]} megas")

        else:
            partes.append(linha)

    return deu_certo(
        "Os que mais gastam memória agora: " + "; ".join(partes) + ".",
        {"processos": linhas},
    )


# ============================================================
# POWERSHELL
# ============================================================

LIMITE_DE_SAIDA = 1500


def executar_powershell(comando, prazo=PRAZO_PADRAO):
    """Roda um comando de PowerShell, escondido e com prazo.

    Sensível por natureza: quem chama já precisa ter passado pela
    confirmação. Comando crítico não roda nem confirmado."""

    texto = str(comando or "").strip()

    if not texto:
        return deu_erro("Você não me disse qual comando.")

    permissao = avaliar("powershell", texto)

    if permissao.bloqueada:
        return negada(permissao.motivo)

    processo, falha = rodar_escondido(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            texto,
        ],
        prazo=prazo,
    )

    if falha == "tempo":
        logger("system").warning(f"powershell demorou: {texto[:80]}")

        return demorou(
            f"O comando passou de {prazo} segundos e eu encerrei."
        )

    if falha or processo is None:
        return deu_erro(
            "Não consegui rodar esse comando."
        )

    saida = (processo.stdout or "").strip()
    erro = (processo.stderr or "").strip()

    logger("system").info(
        f"powershell (código {processo.returncode}): {texto[:80]}"
    )

    if processo.returncode != 0:
        return deu_erro(
            "O comando terminou com erro: "
            + (erro[:LIMITE_DE_SAIDA] or "sem detalhes."),
            {"codigo": processo.returncode},
        )

    if not saida:
        return deu_certo(
            "Rodei o comando. Ele não escreveu nada de volta.",
            {"codigo": 0},
        )

    return deu_certo(
        saida[:LIMITE_DE_SAIDA],
        {"codigo": 0, "saida": saida[:LIMITE_DE_SAIDA]},
    )


# ============================================================
# ÁREA DE TRANSFERÊNCIA
# ============================================================

def copiar_texto(texto):
    """Põe um texto na área de transferência."""

    conteudo = str(texto or "")

    if not conteudo.strip():
        return deu_erro("Não tem texto para copiar.")

    permissao = avaliar("copiar_texto")

    if permissao.bloqueada:
        return negada(permissao.motivo)

    processo, falha = rodar_escondido(
        ["clip.exe"],
        prazo=10,
        entrada=conteudo,
    )

    if falha or processo is None or processo.returncode != 0:
        return deu_erro("Não consegui copiar esse texto.")

    return deu_certo(
        "Copiei. É só colar onde você quiser.",
        {"tamanho": len(conteudo)},
    )
