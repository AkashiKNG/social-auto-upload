# Instalação

Este documento tem duas partes:

- `For Humans`: para quem usa o repositório — desenvolvedores, criadores, gente na CLI
- `For AI Agents`: para agentes como OpenClaw, Codex e Claude Code

Se você está usando um cliente de agente e quer primeiro um texto de partida para mandar a ele, em vez de ler os detalhes abaixo, comece por:

- [Agent Bootstrap Prompt](./agent-bootstrap.md)

## For Humans

### 1. Clonar o projeto

```bash
git clone https://github.com/dreammis/social-auto-upload.git
cd social-auto-upload
```

### 2. Criar o ambiente virtual

Recomendo o `uv`:

Windows PowerShell:

```powershell
uv venv
.venv\Scripts\activate
```

Linux / macOS:

```bash
uv venv
source .venv/bin/activate
```

### 3. Instalar as dependências

As dependências atuais estão no `pyproject.toml`; o caminho direto é:

```bash
uv pip install -e .
```

Terminada a instalação, o comando `sau` fica registrado.

### 4. Instalar o Chromium do patchright

O projeto usa o `patchright` para dirigir o navegador.

Na China vale apontar um espelho antes de instalar o Chromium.

Windows PowerShell:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS:

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

### 5. Configurar o conf.py

Copie o arquivo de exemplo:

```bash
cp conf.example.py conf.py
```

No Windows dá para copiar e renomear na mão.

As opções que costumam ser usadas:

- `LOCAL_CHROME_PATH`
- `LOCAL_CHROME_HEADLESS`
- `DEBUG_MODE`

O `XHS_SERVER` só tem a ver com o fluxo antigo do Xiaohongshu.

### 6. Conferir se a CLI funciona

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

Se o comando não for encontrado, confira primeiro:

- se o ambiente virtual está ativado
- se você rodou o `uv pip install -e .`

### 7. Exemplo com o Douyin

```bash
sau douyin login --account <account_name>
sau douyin check --account <account_name>
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
Texto do post, opção 1:
$noteText = @"texto do post"@
sau douyin upload-note --account <account_name> --images videos/demo1.png videos/demo2.png --title "Título do post" --note $noteText --tags 'tag1,tag2'
Texto do post, opção 2:
sau douyin upload-note --account <account_name> --images videos/demo1.png videos/demo2.png --title "Título do post" --notef 'caminho do arquivo com o texto' --tags 'tag1,tag2'
Trilha sonora (opcional):
sau douyin upload-note --account <account_name> --images videos/demo1.png videos/demo2.png --title "Título do post" --note $noteText --tags 'tag1,tag2' --bgm 'nome da música'
```

Sobre o código por SMS do Douyin:

- Se a publicação do vídeo disparar a verificação por SMS, o programa lê primeiro o `verify_code.txt` na raiz do projeto
- Num terminal interativo, sem `verify_code.txt`, a CLI pede o código direto no terminal
- Para agentes ou pontes automatizadas, continua valendo escrever o código no `verify_code.txt`
- Depois da verificação, o programa apaga o `verify_code.txt` sozinho

Douyin travado no login, pegando o cookie na mão:

- Use VNC no servidor de destino
- Entre na central do criador do Douyin pelo navegador: https://creator.douyin.com/
- Rode `bash export_douyin_cookie.sh --account <account_name>`
- Confira se o cookie serve com `sau douyin check --account <account_name>`

### 8. Exemplo com o Kuaishou

```bash
sau kuaishou login --account <account_name>
sau kuaishou check --account <account_name>
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
sau kuaishou upload-note --account <account_name> --images videos/demo1.png videos/demo2.png videos/demo.png --title "Título do post" --note "Texto do post"
```

### 9. Exemplo com o Xiaohongshu

```bash
sau xiaohongshu login --account <account_name>
sau xiaohongshu check --account <account_name>
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
sau xiaohongshu upload-note --account <account_name> --images videos/demo1.png videos/demo2.png videos/demo.png --title "Título do post" --note "Texto do post"
```

### 10. Exemplo com o Bilibili

```bash
sau bilibili login --account <account_name>
sau bilibili check --account <account_name>
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tid 249
```

Observações:

- Nomes como `creator` são só exemplos: o que você passa de verdade é o seu `account_name`
- Cada `account_name` corresponde a um arquivo de conta; dá para preparar várias contas e usá-las em paralelo
- Convenção de metadados nas plataformas que usam navegador:
- vídeo usa `title + desc + tags`
- post de imagens usa `title + note + tags`
- Não é preciso instalar o `biliup` na mão
- Na primeira execução de um comando do Bilibili, o programa baixa o `biliup`
- Nas seguintes, ele confere a release mais nova e atualiza sozinho
- O login do Bilibili é melhor o próprio usuário rodar num terminal de verdade; se o QR code sair cortado, abra o `qrcode.png` da pasta atual
- Se o acesso ao GitHub Release estiver lento, dá para usar `https://gh-proxy.com/` ou `https://gh-proxy.org/` na frente do endereço da release para investigar
- Exemplo:
  - `https://gh-proxy.org/https://github.com/biliup/biliup/releases/download/v1.1.29/biliupR-v1.1.29-aarch64-linux.tar.xz`

## For AI Agents

Se você é um agente que executa comandos, siga esta ordem:

1. Suponha que a raiz do repositório é o diretório de trabalho
2. Use o `uv` para o ambiente; não caia de volta no antigo `requirements.txt`
3. Para instalar, use:

```bash
uv pip install -e .
```

4. Para o navegador, use:

Windows PowerShell:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS:

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

5. Depois de instalar, confira:

```bash
sau --help
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
```

6. Se o objetivo for login, validação de cookie, envio de vídeo ou de post no Douyin ou no Kuaishou, use a CLI:

```bash
sau douyin login
sau douyin check
sau douyin upload-video
sau douyin upload-note

sau kuaishou login
sau kuaishou check
sau kuaishou upload-video
sau kuaishou upload-note

sau xiaohongshu login
sau xiaohongshu check
sau xiaohongshu upload-video
sau xiaohongshu upload-note

sau bilibili login
sau bilibili check
sau bilibili upload-video
```

7. Se o usuário estiver mesmo usando o sistema de skills, aponte para:

- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`
- `skills/xiaohongshu-upload/SKILL.md`
- `skills/xiaohongshu-upload/references/cli-contract.md`
- `skills/bilibili-upload/SKILL.md`
- `skills/bilibili-upload/references/cli-contract.md`

### Observações extras para agentes

- Quando o login gerar uma imagem de QR code, não mande só o caminho do arquivo
- Essa imagem existe para ser escaneada: mostre ou envie o arquivo direto para o usuário
- Se o ambiente permitir exibir imagens locais, exiba o QR code; o caminho é informação complementar
- O login do Bilibili não deve ser rodado por um agente em ambiente não interativo
- O certo é pedir ao usuário que rode `sau bilibili login --account <name>` no terminal dele; se o QR code sair cortado, peça que abra o `qrcode.png`
- O `requirements.txt` é compatibilidade histórica, não a instalação principal
- `uploader/` é a pasta com a implementação central
- `sau_cli.py` é a entrada da CLI
- `docs/legacy-web.md` descreve a versão Web antiga, sem garantia de funcionar hoje
- O Bilibili pode baixar o `biliup` na primeira execução
