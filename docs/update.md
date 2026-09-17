# Como atualizar

Este documento tem duas partes:

- `For Humans`: para quem usa o repositório
- `For AI Agents`: para agentes que executam comandos e investigam sozinhos

## For Humans

### 1. Puxar o código mais novo

```bash
git pull
```

Se você costuma trabalhar em branches, confira antes em qual está.

### 2. Atualizar a instalação editável

Se a CLI, os scripts de entrada ou as dependências mudaram, rode de novo:

```bash
uv pip install -e .
```

### 3. Atualizar o navegador, se precisar

O projeto usa o `patchright`.

Windows PowerShell:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS:

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

### 4. Conferir depois de atualizar

Vale checar pelo menos:

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
sau douyin check --account your_account
sau kuaishou check --account your_account
sau xiaohongshu check --account your_account
sau bilibili check --account your_account
```

Se você usa as skills, dê uma olhada também em:

- `skills/douyin-upload/SKILL.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/xiaohongshu-upload/SKILL.md`
- `skills/bilibili-upload/SKILL.md`
- `docs/CLI.md`

## For AI Agents

Se você é um agente, depois de atualizar o repositório faça esta verificação mínima:

1. Puxe o código mais novo:

```bash
git pull
```

2. Sincronize a instalação local:

```bash
uv pip install -e .
```

3. Se precisar do navegador, atualize o Chromium do `patchright`

4. Confira a CLI de novo:

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

5. Se a tarefa envolve as plataformas que usam navegador, confira também:

```bash
sau douyin check --account test
sau kuaishou check --account test
sau xiaohongshu check --account test
sau bilibili check --account test
```

6. Se o usuário depende das skills, veja se estes caminhos ainda existem e se o contrato não mudou:

- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/douyin-upload/references/runtime-requirements.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`
- `skills/kuaishou-upload/references/runtime-requirements.md`
- `skills/xiaohongshu-upload/SKILL.md`
- `skills/xiaohongshu-upload/references/cli-contract.md`
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
- `skills/bilibili-upload/SKILL.md`
- `skills/bilibili-upload/references/cli-contract.md`
- `skills/bilibili-upload/references/runtime-requirements.md`

### Observações extras para agentes

- Confie no `pyproject.toml`; o `requirements.txt` não é a verdade atual
- O README é só visão geral: instalação e atualização são o `docs/install.md` e o `docs/update.md`
- A parte Web é caminho antigo, descrito em `docs/legacy-web.md`
- Se o login gerar uma imagem de QR code, mostre ou envie a imagem ao usuário; não devolva só o caminho
- Os comandos do Bilibili conferem e atualizam o `biliup` sozinhos
- O login do Bilibili ainda deve ser feito pelo próprio usuário num terminal de verdade; se o QR code sair cortado, peça que abra o `qrcode.png`
