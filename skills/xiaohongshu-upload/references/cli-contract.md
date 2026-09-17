# Contrato da CLI do Xiaohongshu

Esta skill parte do princípio de que o comando `sau` já está instalado e disponível.

## Lista de comandos

### Entrar na conta

```bash
sau xiaohongshu login --account <account>
```

- Obrigatório:
  - `--account`
- O que faz:
  - inicia o login no Xiaohongshu e gera ou renova o arquivo de cookie da conta
  - se o login gerar uma imagem de QR code, mostre ou envie a imagem ao usuário em vez de devolver só o caminho
- Sobre a conta:
  - o `--account` recebe o `account_name` escolhido pelo usuário; não precisa se chamar `creator`
  - cada `account_name` corresponde a um arquivo de conta, o que permite várias contas e tarefas em paralelo

### Validar o cookie

```bash
sau xiaohongshu check --account <account>
```

- Obrigatório:
  - `--account`
- Saída esperada:
  - `valid`: o cookie serve
  - `invalid`: o cookie sumiu ou expirou

### Enviar vídeo

```bash
sau xiaohongshu upload-video \
  --account <account> \
  --file <video-path> \
  --title "<title>" \
  [--desc "<description>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [--thumbnail <image-path>] \
  [--debug] \
  [--headless | --headed]
```

- Obrigatório:
  - `--account`
  - `--file`
  - `--title`
- Opcional:
  - `--desc`
  - `--tags`
  - `--schedule`
  - `--thumbnail`
  - `--debug`
  - `--headless`
  - `--headed`

### Enviar post de imagens

```bash
sau xiaohongshu upload-note \
  --account <account> \
  --images <image-1> [image-2 ...] \
  --title "<title>" \
  [--note "<content>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [--debug] \
  [--headless | --headed]
```

- Obrigatório:
  - `--account`
  - `--images`
  - `--title`
- Opcional:
  - `--note`
  - `--tags`
  - `--schedule`
  - `--debug`
  - `--headless`
  - `--headed`

## Estratégia de publicação

- Sem `--schedule`, a CLI publica na hora
- Com `--schedule`, a CLI muda para publicação agendada
- O formato de data e hora é:

```text
YYYY-MM-DD HH:MM
```

## Observações

- cada `upload-video` aceita um único arquivo de vídeo
- cada `upload-note` aceita várias imagens
- a descrição do vídeo é sempre o `--desc`
- o texto do post é sempre o `--note`
