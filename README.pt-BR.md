# toolgate

[English](README.md) · **Português**

Um painel de controle para as ferramentas que um assistente de IA pode usar.
Você decide quem usa cada ferramenta, as senhas ficam criptografadas e toda chamada
fica registrada, para conferir depois quem fez o quê.

![toolgate](docs/screenshots/chat-history.png)

## O que dá para fazer

- **Conversar com as ferramentas.** Pergunte "quais convênios estão atrasados em MS?" e o chat escolhe a ferramenta certa, pede o que faltar e explica o resultado. As conversas ficam salvas.
- **Controlar quem usa o quê.** Cada perfil (admin, analista, auditor) só enxerga as ferramentas que tem permissão para chamar.
- **Adicionar ferramentas novas sem mexer no código.** Você cadastra um endpoint HTTP pelo painel e ele só entra no ar depois que *outra* pessoa aprova.
- **Guardar senhas e tokens com segurança.** Ficam criptografados e nunca aparecem de volta na tela.
- **Auditar tudo.** Cada chamada vira um registro com dados pessoais (CPF, e-mail, cartão) já mascarados. Os registros são encadeados por hash, então dá para ver se alguém editou um evento antigo.

Funciona com o Claude Desktop ou qualquer cliente MCP, além do painel web.

## Rodando

```bash
git clone https://github.com/murilo-bassan/mcp-tool-gateway.git
cd mcp-tool-gateway
pip install -r requirements-dev.txt

python -m pytest                              # testes
python scripts/demo_traffic.py                # opcional: gera atividade de exemplo
python -m uvicorn web.app:app --port 8600     # http://localhost:8600
```

Logins de teste: `admin/admin`, `analyst/analyst` e `auditor/auditor`. Também roda com `docker compose up --build`.

Para usar no Claude Desktop, copie [`docs/claude_desktop_config.example.json`](docs/claude_desktop_config.example.json).
Para testar pelo terminal:

```bash
python scripts/mcp_call.py list
python scripts/mcp_call.py call invoices.validate_tax_id '{"tax_id": "11.222.333/0001-81"}'
```

O chat funciona sem modelo nenhum. Para usar um LLM, defina `GATEWAY_LLM_API_KEY`, `GATEWAY_LLM_BASE_URL`
e `GATEWAY_LLM_MODEL` (qualquer API compatível com a da OpenAI).

## Como funciona

Toda chamada, venha do Claude Desktop, do painel ou de outro sistema, passa pelo mesmo caminho:
checa a permissão, aplica o limite de uso, valida os argumentos, executa e registra.
Nenhuma porta de entrada pula essas etapas.

```
gateway/
  executor.py   o caminho único de toda chamada
  access.py     usuários, perfis e permissões
  registry.py   ferramentas cadastradas pelo painel
  audit.py      registro encadeado por hash
  masking.py    mascaramento de dados pessoais
  chat.py       o chat
  domains/      as ferramentas de exemplo (notas fiscais e convênios)
server.py       servidor MCP
web/            painel web
```

As decisões de projeto estão em [`docs/adr`](docs/adr) e o modelo de segurança em [`docs/security.md`](docs/security.md).

## Telas

| Console | Auditoria |
|---|---|
| ![](docs/screenshots/console.png) | ![](docs/screenshots/audit.png) |
| **Ferramentas cadastradas** | **Permissões** |
| ![](docs/screenshots/registry.png) | ![](docs/screenshots/access.png) |

**Stack:** Python, FastAPI, MCP, SQLite, Docker

Os dados são fictícios. Licença MIT.
