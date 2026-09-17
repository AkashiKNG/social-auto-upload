---
name: bilibili-upload
description: Use esta skill quando o agente precisar entrar na conta do Bilibili, validar a conta ou enviar um vídeo usando a CLI `sau` já instalada. Prefira `sau bilibili ...`: o programa prepara o `biliup` sozinho, sem exigir instalação manual.
---

# Skill de envio para o Bilibili

Trate o `sau` como a interface principal.

Não peça ao usuário para procurar o `biliup` nem baixar a release na mão.
O programa confere, baixa e atualiza o `biliup` sozinho, em tempo de execução.

## Visão geral

| Função | Comando | Descrição |
| --- | --- | --- |
| Entrar na conta | `sau bilibili login --account <name>` | o usuário precisa rodar num terminal de verdade; gera ou renova os dados de login |
| Validar | `sau bilibili check --account <name>` | confere se a conta ainda está válida |
| Enviar vídeo | `sau bilibili upload-video ...` | envia um vídeo ao Bilibili |

## Fluxo padrão

1. Confira `references/runtime-requirements.md`
2. Confira `references/cli-contract.md`
3. Rode o comando `sau bilibili ...` correspondente
4. Se o comando falhar, veja `references/troubleshooting.md`

## Qual comando usar

- Sem dados de login, peça ao usuário que rode o `login` no terminal dele
- Se ele só quer conferir o estado da conta, use `check`
- Se ele vai publicar um vídeo, use `upload-video`

## Antes de executar

- Confirme que o ambiente consegue rodar o `sau`
- Se o `sau` não estiver no PATH, use o `sau_cli.py` do repositório
- Não peça ao usuário para baixar o `biliup` na mão
- Na primeira execução de um comando do Bilibili, o programa pode baixar o `biliup` pela rede
- Como agente, não force o `sau bilibili login` em ambiente não interativo
- O certo é pedir ao usuário que rode `sau bilibili login --account <name>` no terminal dele
- Se o QR code sair cortado no terminal, peça que ele abra o `qrcode.png` da pasta atual

## Modelos prontos

- `scripts/examples/bilibili_commands.ps1`
- `scripts/examples/bilibili_commands.sh`
- `scripts/examples/bilibili_cli_template.py`

## Documentos de referência

- Pré-requisitos: `references/runtime-requirements.md`
- Contrato da CLI: `references/cli-contract.md`
- Solução de problemas: `references/troubleshooting.md`
