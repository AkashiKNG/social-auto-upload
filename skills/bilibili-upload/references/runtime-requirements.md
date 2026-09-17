# Pré-requisitos

Esta skill parte do princípio de que o ambiente já tem:

- o `social-auto-upload` instalado
- o comando `sau` disponível, ou ao menos o `python sau_cli.py`
- acesso à internet, na primeira execução, para o GitHub Release

## Ponto importante

O usuário não precisa instalar o `biliup`.

Quando você roda `sau bilibili ...`:

- se o `biliup` não estiver na máquina, o programa baixa
- se houver versão nova no GitHub Release, o programa atualiza antes de seguir

## Formas de chamar

### Com o `sau` no PATH

```bash
sau bilibili --help
```

### Direto pelo repositório

PowerShell:

```powershell
.\.venv\Scripts\python.exe sau_cli.py bilibili --help
```

bash / zsh:

```bash
python sau_cli.py bilibili --help
```

## Na primeira execução

- pode demorar mais que nas outras plataformas, porque o `biliup` está sendo preparado
- sem acesso ao GitHub Release, os comandos do Bilibili falham
- depois que o `biliup` estiver na máquina, os comandos seguintes o reaproveitam
- o `sau bilibili login --account <name>` precisa ser rodado pelo próprio usuário num terminal de verdade
- se o QR code sair cortado no terminal, em geral basta abrir o `qrcode.png` da pasta atual
- se o acesso ao GitHub Release estiver lento, dá para usar `https://gh-proxy.com/` ou `https://gh-proxy.org/` na frente do endereço da release para investigar
- Exemplo:
  - `https://gh-proxy.org/https://github.com/biliup/biliup/releases/download/v1.1.29/biliupR-v1.1.29-aarch64-linux.tar.xz`
