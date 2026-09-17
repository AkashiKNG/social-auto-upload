# Pré-requisitos

Esta skill parte do princípio de que o ambiente já tem:

- o `social-auto-upload` instalado
- o comando `sau` disponível, ou uma forma equivalente de chamá-lo
- o Chromium instalado para o `patchright`

## Instalação recomendada

Na raiz do projeto:

```bash
uv pip install -e .
```

## Instalar o navegador do patchright

Windows PowerShell:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

Linux / macOS (bash / zsh):

```bash
PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright" patchright install chromium
```

## Formas de chamar

### Se o `sau` já está no PATH

```bash
sau xiaohongshu --help
```

### Se o ambiente virtual existe mas não está ativado

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
sau xiaohongshu --help
```

### Se você quer chamar o executável direto

PowerShell:

```powershell
.\.venv\Scripts\sau.exe xiaohongshu --help
```

### Se você prefere o uv

```bash
uv run sau xiaohongshu --help
```

## Com e sem janela

- `--headless` roda sem janela
- `--headed` roda com janela
- Quando o usuário pedir login sem janela, espere que a CLI informe o QR code pelo console ou pelo caminho de uma imagem temporária
- Se o login gerar uma imagem de QR code, mostre ou envie a imagem ao usuário em vez de só informar o caminho
