"""
Verifica que a configuração de máquina foi separada da versionada.

O risco que estes testes cobrem: um git pull sobrescrever o índice do
microfone escolhido pelo usuário.
"""
import json
import subprocess

from core.config import CONFIG_DIR, LOCAL_DIR, config_path


def test_config_local_existe_com_os_arquivos_de_maquina():
    assert (LOCAL_DIR / "audio_device.json").exists()
    assert (LOCAL_DIR / "whisper_local.json").exists()


def test_arquivos_de_maquina_nao_estao_versionados():
    """git ls-files vazio == o arquivo não vem na atualização."""
    for nome in ["audio_device.json", "whisper_local.json"]:
        saida = subprocess.run(
            ["git", "ls-files", "config/%s" % nome],
            capture_output=True, text=True, cwd=CONFIG_DIR.parent,
        ).stdout.strip()
        assert saida == "", "config/%s ainda está no git" % nome


def test_os_exemplos_estao_versionados_e_sao_json_valido():
    for nome in ["audio_device.example.json", "whisper_local.example.json"]:
        caminho = CONFIG_DIR / nome
        assert caminho.exists()
        json.loads(caminho.read_text(encoding="utf-8-sig"))


def test_config_path_prefere_o_local_para_arquivos_de_maquina():
    assert config_path("whisper_local.json").parent == LOCAL_DIR
    assert config_path("audio_device.json").parent == LOCAL_DIR


def test_selecionar_microfone_grava_em_config_local():
    """
    O seletor é interativo e não dá para executar aqui, mas o destino da
    escrita é uma constante de módulo. Se ela apontar para config/, a
    escolha do usuário volta a ser sobrescrita pela atualização.
    """
    import ast

    fonte = (CONFIG_DIR.parent / "Selecionar_Microfone.py").read_text(encoding="utf-8")
    arvore = ast.parse(fonte)
    destinos = [
        no for no in ast.walk(arvore)
        if isinstance(no, ast.Assign)
        and any(getattr(a, "id", None) == "CONFIG" for a in no.targets)
    ]
    assert len(destinos) == 1, "esperava uma única atribuição de CONFIG"
    assert "LOCAL_DIR" in ast.dump(destinos[0]), "CONFIG não aponta para LOCAL_DIR"


def test_scripts_da_raiz_importam_de_src():
    """
    Scripts na raiz não têm src/ no sys.path por padrão. Quem importa de
    src/ precisa inserir o caminho antes, ou quebra com ModuleNotFoundError
    ao ser executado direto.

    Selecionar_Microfone.py chama input() no nível do módulo: usamos
    stdin=DEVNULL (gera EOFError, não ModuleNotFoundError) e um timeout
    para não travar o teste.
    """
    import sys as _sys

    for script in ["MILK_Command_Center", "Selecionar_Microfone"]:
        resultado = subprocess.run(
            [_sys.executable, "-c", "import %s" % script],
            capture_output=True, text=True, cwd=CONFIG_DIR.parent,
            stdin=subprocess.DEVNULL, timeout=15,
        )
        assert "ModuleNotFoundError" not in resultado.stderr, (
            "%s não é importável da raiz: %s" % (script, resultado.stderr[-300:])
        )


def test_erro_de_whisper_ausente_nomeia_o_caminho_resolvido(monkeypatch, tmp_path):
    """
    A mensagem de erro precisa nomear o caminho realmente resolvido por
    config_path() (pode ser config/local/whisper_local.json), não uma
    string fixa apontando sempre para config/whisper_local.json.
    """
    import voice.listener as listener

    caminho_inexistente = tmp_path / "whisper_local.json"
    monkeypatch.setattr(listener, "CONFIG", caminho_inexistente)

    try:
        listener.NaturalVoiceListener()
        assert False, "esperava RuntimeError por CONFIG ausente"
    except RuntimeError as erro:
        assert str(caminho_inexistente) in str(erro)
