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
sau kuaishou --help
```

### Se o ambiente virtual existe mas não está ativado

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
sau kuaishou --help
```

### Se você quer chamar o executável direto

PowerShell:

```powershell
.\.venv\Scripts\sau.exe kuaishou --help
```

### Se você prefere o uv

```bash
uv run sau kuaishou --help
```

## Com e sem janela

- `--headless` roda sem janela
- `--headed` roda com janela
- A CLI do Kuaishou roda sem janela por padrão
- Só passe para `--headed` se o usuário pedir a janela do navegador ou se o QR code realmente não funcionar
- Se o login gerar uma imagem de QR code, mostre ou envie a imagem ao usuário em vez de só informar o caminho
