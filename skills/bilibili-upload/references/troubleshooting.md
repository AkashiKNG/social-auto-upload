# Problemas comuns do Bilibili

## 1. A primeira execução está muito lenta

É normal.

Em geral o programa está baixando o `biliup`.

## 2. O download automático falhou

Confira:

- se a rede alcança o GitHub
- se o GitHub Release está acessível
- se a pasta local tem permissão de escrita
- se o acesso estiver lento, dá para usar `https://gh-proxy.com/` ou `https://gh-proxy.org/` na frente do endereço da release para investigar
- Exemplo:
  - `https://gh-proxy.org/https://github.com/biliup/biliup/releases/download/v1.1.29/biliupR-v1.1.29-aarch64-linux.tar.xz`

## 3. O `check` devolve `invalid`

Causas comuns:

- o arquivo de conta não existe
- os dados de login expiraram
- o `biliup renew` falhou

Sugestão:

```bash
sau bilibili login --account <account>
```

## 4. O login reclama de `not a terminal`

Causas comuns:

- o `sau bilibili login` foi disparado em ambiente não interativo
- por exemplo, o executor de comandos de um agente, um pipe ou um processo com a saída padrão capturada

Sugestão:

- deixe o próprio usuário rodar num terminal de verdade:

```bash
sau bilibili login --account <account>
```

- se o QR code sair cortado no terminal, abra o `qrcode.png` da pasta atual

## 5. O envio falhou

Confira primeiro:

- se o `--tid` está certo
- se o arquivo de vídeo existe mesmo
- se título, descrição e tags cabem nas regras da plataforma
- se os dados de login ainda valem

## 6. O comportamento mudou depois de uma atualização

A integração com o Bilibili acompanha a release mais nova do `biliup`.

Se o comportamento da ferramenta mudar lá em cima, a CLI do Bilibili daqui pode ser afetada.

Ao investigar, confira também:

- qual versão do `biliup` foi baixada
- se houve mudança recente na release de origem
