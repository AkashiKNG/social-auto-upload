# Contrato da CLI do Bilibili

Esta skill parte do princípio de que o comando `sau` já está instalado e disponível.

## Lista de comandos

### Entrar na conta

```bash
sau bilibili login --account <account>
```

- Obrigatório:
  - `--account`
- O que faz:
  - prepara o `biliup` sozinho
  - inicia o login no Bilibili
- Sobre a conta:
  - o `--account` recebe o `account_name` escolhido pelo usuário; não precisa se chamar `creator`
  - cada `account_name` corresponde a um arquivo de conta, o que permite várias contas e tarefas em paralelo
- Sobre o login:
  - este comando deve ser rodado pelo próprio usuário, num terminal de verdade
  - se o QR code sair cortado no terminal, basta abrir o `qrcode.png` da pasta atual
  - o agente não deve forçar este comando em ambiente não interativo

### Validar a conta

```bash
sau bilibili check --account <account>
```

- Obrigatório:
  - `--account`
- Saída esperada:
  - `valid`
  - `invalid`

### Enviar vídeo

```bash
sau bilibili upload-video \
  --account <account> \
  --file <video-path> \
  --title "<title>" \
  --desc "<desc>" \
  --tid <category-id> \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"]
```

- Obrigatório:
  - `--account`
  - `--file`
  - `--title`
  - `--desc`
  - `--tid`
- Opcional:
  - `--tags`
  - `--schedule`

## Observações

- o `--tid` é obrigatório nesta primeira versão
- as `--tags` vão separadas por vírgula
- o `--schedule` usa o mesmo formato de data e hora do `sau`
- o programa prepara e atualiza o `biliup` sozinho
