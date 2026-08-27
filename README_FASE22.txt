MILK FASE 22 — MCP / PLUGINS

OBJETIVO
Permitir que a MILK se conecte a ferramentas externas por MCP sem dar
acesso irrestrito ao computador.

NOVO
- Registro de servidores MCP em config\mcp_servers.json
- Cliente MCP via stdio JSON-RPC
- Inicialização do protocolo MCP
- Descoberta de tools
- Execução de tools
- Confirmação obrigatória para ações consideradas arriscadas
- Log em logs\mcp.log
- Servidor MCP de teste incluído
- Não permite LLM gerar shell arbitrário diretamente

ARQUITETURA
MILK
  ↓
MCPManager
  ↓
Servidor MCP
  ↓
Tools autorizadas

SEGURANÇA
Tools com nomes como:
delete, remove, send, publish, push, deploy, write, update,
execute, shell e command
exigem confirmação.

Servidores não marcados como trusted também exigem confirmação.

INSTALAÇÃO
1. Copie tudo para C:\JARVIS e substitua.
2. Rode:
   cd C:\JARVIS
   python .\Testar_MCP.py

RESULTADO ESPERADO
- servidor milk_mock iniciado
- tools milk_echo e milk_time listadas
- chamadas funcionando
- mensagem:
  ✅ FASE 22 MCP VALIDADA.

NÃO precisa instalar pacote MCP externo para validar esta fase.

ADICIONAR UM MCP REAL
Edite:
C:\JARVIS\config\mcp_servers.json

Exemplo conceitual:
{
  "name": "meu_servidor",
  "enabled": true,
  "trusted": false,
  "command": "node",
  "args": ["C:\caminho\server.js"],
  "cwd": "C:\caminho",
  "always_confirm": ["send_email"]
}

IMPORTANTE
Só adicione comandos/servidores que você conhece e confia.
