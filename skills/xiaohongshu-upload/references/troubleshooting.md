# Solução de problemas

## O comando `sau` não é encontrado

Tente assim:

```powershell
.\.venv\Scripts\Activate.ps1
sau xiaohongshu --help
```

```powershell
.\.venv\Scripts\sau.exe xiaohongshu --help
```

```bash
uv run sau xiaohongshu --help
```

Se o projeto ainda não estiver instalado no ambiente:

```bash
uv pip install -e .
```

## Cookie inválido ou expirado

Confira o estado primeiro:

```bash
sau xiaohongshu check --account <account>
```

Se estiver inválido, entre na conta de novo:

```bash
sau xiaohongshu login --account <account>
```

## QR code no login sem janela

Se o usuário não conseguir usar o QR code impresso no terminal:

- procure a imagem temporária de QR code que a CLI gerou
- não devolva só o caminho da imagem ao usuário
- mostre ou envie a imagem local direto para ele escanear

Se o QR code do terminal aparecer torto, use a imagem salva em vez de ficar mexendo nas configurações do terminal.

## Falta algum parâmetro no envio

### Envio de vídeo

O mínimo é:

- `--account`
- `--file`
- `--title`

### Envio de post de imagens

O mínimo é:

- `--account`
- `--images`
- `--title`

O `--note` é opcional.

## Publicação agendada

O formato de data e hora é:

```text
YYYY-MM-DD HH:MM
```

Sem publicação agendada, basta tirar o `--schedule` para publicar na hora.
