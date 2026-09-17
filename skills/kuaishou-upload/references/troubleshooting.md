# Solução de problemas

## O comando `sau` não é encontrado

Tente assim:

```powershell
.\.venv\Scripts\Activate.ps1
sau kuaishou --help
```

```powershell
.\.venv\Scripts\sau.exe kuaishou --help
```

```bash
uv run sau kuaishou --help
```

Se o projeto ainda não estiver instalado no ambiente:

```bash
uv pip install -e .
```

## Cookie inválido ou expirado

Confira o estado primeiro:

```bash
sau kuaishou check --account <account>
```

Se estiver inválido, entre na conta de novo:

```bash
sau kuaishou login --account <account>
```

## Problemas com o QR code do login

Se o usuário disser que o QR code do terminal está difícil de escanear:

- use primeiro a imagem de QR code gerada pela CLI ou pelo uploader
- só passe para `--headed` se ele pedir a janela do navegador ou se a imagem também não resolver
- se a CLI ou o uploader já gerou a imagem temporária, não devolva só o caminho
- mostre ou envie a imagem local direto para ele escanear
- o caminho é informação complementar

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

## O post de imagens só aceitou uma

Se o usuário mandou várias imagens e a página reconheceu só uma, confira:

- se o `--images` recebeu arquivos realmente diferentes
- se não é o mesmo caminho repetido várias vezes

## Publicação agendada

O formato de data e hora é:

```text
YYYY-MM-DD HH:MM
```

Sem publicação agendada, basta tirar o `--schedule` para publicar na hora.
