---
name: douyin-upload
description: Use esta skill quando o agente precisar entrar na conta do Douyin, validar o cookie, enviar um vídeo ou publicar um post de imagens usando a CLI `sau` já instalada. Ela serve em ambientes onde o `social-auto-upload` está instalado e o comando `sau` está disponível. Prefira esta skill para um fluxo estável por comando no Douyin, em vez de começar lendo o código do uploader.
---

# Skill de envio para o Douyin

Trate o `sau` como a interface principal.

Não suponha que o ambiente consegue ler o código do repositório.
Não comece lendo o `uploader/`.
Só recorra ao guia de problemas quando o comando não existir ou a CLI falhar.

## Visão geral

| Função | Comando | Descrição |
| --- | --- | --- |
| Entrar na conta do Douyin | `sau douyin login --account <name>` | gera ou renova o cookie da conta |
| Validar o cookie | `sau douyin check --account <name>` | confere se o cookie da conta ainda vale |
| Enviar vídeo | `sau douyin upload-video ...` | envia e publica um vídeo no Douyin |
| Enviar post de imagens | `sau douyin upload-note ...` | envia e publica um post de imagens no Douyin |

Convenção de metadados:

- vídeo usa `title + desc + tags`
- post de imagens usa `title + note + tags`

## Fluxo padrão

1. Confira os pré-requisitos em `references/runtime-requirements.md`.
2. Confira o contrato de comandos em `references/cli-contract.md`.
3. Rode o comando `sau douyin ...` correspondente.
4. Se o comando falhar, veja `references/troubleshooting.md`.

## Ações possíveis

- `sau douyin login --account <name>` para entrar na conta do Douyin
- `sau douyin check --account <name>` para validar o cookie
- `sau douyin upload-video ...` para enviar um vídeo ao Douyin
- `sau douyin upload-note ...` para enviar um post de imagens ao Douyin

## Qual comando usar

- Quando o usuário precisa de um cookie novo, ou o atual expirou, use `login`
- Quando ele só quer saber o estado do cookie, use `check`
- Quando ele vai publicar um vídeo, use `upload-video`
- Quando ele vai publicar um post de imagens, use `upload-note`

## Antes de executar

- Confirme se o `sau` pode ser chamado no shell atual
- Se o `sau` não estiver disponível, siga a alternativa de `references/runtime-requirements.md`
- Quando o usuário pedir com ou sem janela, passe `--headless` ou `--headed` explicitamente
- Só use `--schedule` quando o usuário pedir publicação agendada
- Se o login gerar uma imagem de QR code, não mande só o caminho do arquivo
- Essa imagem existe para ser escaneada: mostre ou envie o arquivo direto ao usuário

## Modelos prontos

Quando quiser um modelo de comando estável, use os arquivos de `scripts/examples/`:

- `douyin_commands.ps1`
- `douyin_commands.sh`
- `douyin_cli_template.py`

## Documentos de referência

- Pré-requisitos: `references/runtime-requirements.md`
- Contrato da CLI: `references/cli-contract.md`
- Solução de problemas: `references/troubleshooting.md`
