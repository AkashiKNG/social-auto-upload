# Guia da CLI

O projeto tem uma CLI única, o comando `sau`. As plataformas já integradas são:

- `douyin`
- `kuaishou`
- `xiaohongshu`
- `bilibili`
- `tencent`
- `baijiahao`
- `alipay`
- `weibo`
- `hupu`
- `youtube`

Sobre a implementação:

- `sau_cli.py` é a entrada principal da CLI e o único arquivo de implementação relevante
- `sau.exe` é o atalho gerado no ambiente virtual do Windows depois da instalação; no fundo ele chama o `sau_cli.py`
- Para uso com agentes (OpenClaw, Codex e afins), veja as skills do próprio repositório:
  - `skills/douyin-upload/`
  - `skills/kuaishou-upload/`
  - `skills/xiaohongshu-upload/`
  - `skills/bilibili-upload/`

Channels (视频号), Baijiahao e a conta de vida do Alipay só têm entrada pela CLI: ainda não existe skill para eles.

## Instalar o comando `sau`

Se você quiser usar o comando `sau` direto, em vez de rodar `python sau_cli.py`, instale uma vez na raiz do projeto:

```bash
uv pip install -e .
```

Depois disso é só usar:

```bash
sau douyin --help
sau kuaishou --help
sau xiaohongshu --help
sau bilibili --help
sau tencent --help
sau baijiahao --help
sau alipay --help
sau weibo --help
sau hupu --help
sau youtube --help
```

## Instalar o navegador do patchright

No Windows vale apontar um espelho antes de instalar o Chromium:

```powershell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"; patchright install chromium
```

## Subcomandos do Douyin

```bash
sau douyin login --account <account_name>
sau douyin login --account <account_name> --headless
sau douyin check --account <account_name>
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags esporte,treino
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "Título do post" --note "Post de exemplo" --tags post,teste
```

Sobre o código por SMS do Douyin:

- Se a publicação do vídeo disparar a verificação por SMS, a CLI lê primeiro o `verify_code.txt` na raiz do projeto
- Sem o `verify_code.txt`, e estando num terminal interativo, a CLI pede o código direto no terminal
- Para agentes, tarefas automáticas e pontes remotas, continua valendo escrever o código no `verify_code.txt`
- Depois da verificação, o programa apaga o `verify_code.txt` sozinho

## Subcomandos do Kuaishou

```bash
sau kuaishou login --account <account_name>
sau kuaishou check --account <account_name>
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags esporte,treino
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Post de exemplo" --tags post,teste
```

## Subcomandos do Xiaohongshu

```bash
sau xiaohongshu login --account <account_name>
sau xiaohongshu check --account <account_name>
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags xiaohongshu,video
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Post de exemplo" --tags post,teste
```

Fora da China, se não der para entrar no painel de criador padrão, dá para trocar o domínio para o RedNote por variável de ambiente. Isso vale para o login, a validação do cookie e o envio de vídeos e de posts:

```bash
SAU_XHS_CREATOR_BASE_URL=https://creator.rednote.com sau xiaohongshu login --account <account_name>
```

## Subcomandos do Bilibili

```bash
sau bilibili login --account <account_name>
sau bilibili check --account <account_name>
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tid 249 --tags futebol,teste --thumbnail covers/demo.png
```

Observações:

- Nomes como `creator` são só exemplos: o que você passa de verdade é o seu `account_name`
- Cada `account_name` corresponde a um arquivo de conta; dá para preparar várias contas e usá-las em paralelo
- Convenção de metadados nas plataformas que usam navegador:
- vídeo usa `title + desc + tags`
- post de imagens usa `title + note + tags`
- `sau bilibili ...` prepara o `biliup` sozinho
- Se o `biliup` não estiver instalado, a primeira execução baixa
- Se houver versão nova no GitHub Release, a execução atualiza antes
- `sau bilibili login --account <name>` é melhor o próprio usuário rodar num terminal de verdade; se o QR code sair cortado no terminal, abra o `qrcode.png` da pasta atual

## Subcomandos do Channels (视频号)

```bash
sau tencent login --account <account_name>
sau tencent check --account <account_name>
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags channels,teste
```

O Channels aceita publicação agendada, rascunho, coletânea e capa em duas proporções:

```bash
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --schedule "2026-03-24 21:30" --thumbnail-landscape covers/landscape.png --thumbnail-portrait covers/portrait.png --collection "Minha coletânea"
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --draft
```

O login e o envio no Channels dependem da sessão do navegador. Sem janela, quando o QR code é necessário, a CLI gera uma imagem temporária; para acompanhar a página à vista, use `--headed`.

## Subcomandos do Baijiahao

```bash
sau baijiahao login --account <account_name>
sau baijiahao check --account <account_name>
sau baijiahao upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags baijiahao,teste
```

O Baijiahao aceita login, checagem de conta e envio de vídeo; aceita `--thumbnail` e `--collection`, mas ainda não aceita `--schedule`. Antes de enviar, é preciso entrar na conta Baidu e salvar o arquivo de conta.

## Subcomandos da conta de vida do Alipay

```bash
sau alipay login --account <account_name>
sau alipay check --account <account_name>
sau alipay upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags alipay,teste
```

A conta de vida do Alipay aceita login, checagem de conta e envio de vídeo; aceita `--thumbnail` e `--collection`, mas ainda não aceita post de imagens nem `--schedule`. Antes do primeiro uso, entre no painel de criação de conteúdo do Alipay e confirme que a conta tem permissão de criação na conta de vida.

## Subcomandos do YouTube

```bash
sau youtube login --account <account_name>
sau youtube check --account <account_name>
sau youtube upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2 --playlist "Minha playlist" --visibility public
```

O login do YouTube é feito na conta Google pelo navegador, sem QR code. O `--visibility` aceita `public`, `unlisted` ou `private`, e o `--playlist` é opcional.

## Subcomandos do Weibo

```bash
sau weibo login --account <account_name>
sau weibo check --account <account_name>
sau weibo upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags weibo,teste --thumbnail covers/demo.png
```

O Weibo aceita login, checagem de conta e envio de vídeo; o título tem no máximo 30 caracteres, a capa deve ficar abaixo de 5 MB e ainda não há post de imagens nem `--schedule`.

## Subcomandos do Hupu (虎扑)

```bash
sau hupu login --account <account_name>
sau hupu check --account <account_name>
sau hupu upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags hupu,teste --thumbnail covers/demo.png
```

O Hupu aceita login, checagem de conta e envio de vídeo; o título precisa ter de 4 a 40 caracteres e ainda não há post de imagens nem `--schedule`. O login pode exigir conta QQ ou número de celular no navegador; para acompanhar a página, use `--headed`.

## Sobre o QR code de login

- No login de Douyin, Kuaishou, Xiaohongshu, Channels, Baijiahao, conta de vida do Alipay, Weibo e Hupu, a CLI ou o uploader pode gerar uma imagem temporária de QR code
- Para uma pessoa, basta abrir a imagem e escanear
- Para um agente com acesso aos arquivos locais, não basta mandar o caminho da imagem
- Essa imagem existe para ser escaneada, então o agente deve mostrar ou enviar o arquivo direto para o usuário
- Bilibili e YouTube não usam esse caminho de QR code local: siga as observações de cada plataforma acima

## Publicação agendada

Vídeos e posts de Douyin, Kuaishou, Xiaohongshu e Channels, além do vídeo do Bilibili, aceitam `--schedule`. Passando `--schedule`, a CLI muda para a estratégia de agendamento da plataforma; sem ele, publica na hora. Baijiahao, conta de vida do Alipay, Weibo e Hupu ainda não aceitam `--schedule`.

```bash
sau douyin upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --schedule "2026-03-24 21:30"
sau douyin upload-note --account <account_name> --images videos/1.png videos/2.png --title "Título do post" --note "Post de exemplo" --schedule "2026-03-24 21:30"
sau kuaishou upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --schedule "2026-03-24 21:30"
sau kuaishou upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Post de exemplo" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --schedule "2026-03-24 21:30"
sau xiaohongshu upload-note --account <account_name> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Post de exemplo" --schedule "2026-03-24 21:30"
sau bilibili upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tid 249 --schedule "2026-03-24 21:30"
sau tencent upload-video --account <account_name> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --schedule "2026-03-24 21:30"
```

## Parâmetros de execução

Na CLI, `debug` e `headless` são duas coisas independentes:

```bash
--debug
--headless
--headed
```

- `--debug`: liga o modo de depuração, por exemplo guardando mais informação quando algo falha
- `--headless`: roda sem janela
- `--headed`: roda com janela

Sem nenhum dos dois, a CLI roda com `headless=True`.

Complementando:

- A CLI de Douyin e Kuaishou roda sem janela por padrão
- Só passe `--headed` quando o usuário pedir a janela do navegador ou quando for mesmo preciso olhar a página

## Parâmetros do envio de vídeo

```bash
--file videos/demo.mp4
--title "Título de exemplo"
--desc "Descrição de exemplo"
--tags esporte,treino
--thumbnail videos/demo.png
--thumbnail-landscape videos/cover-4x3.png
--thumbnail-portrait videos/cover-3x4.png
```

Douyin e Channels aceitam as duas proporções de capa ao mesmo tempo:

- `--thumbnail-landscape`: capa horizontal 4:3
- `--thumbnail-portrait`: capa vertical 3:4
- `--thumbnail`: parâmetro antigo, equivale à capa vertical 3:4

Channels, Baijiahao e conta de vida do Alipay aceitam `--collection` para apontar uma coletânea existente; Baijiahao e Alipay também aceitam `--thumbnail` para a capa.

O Douyin ainda aceita:

```bash
--product-link https://example.com/item
--product-title Produto de exemplo
```

O Bilibili exige a mais:

```bash
--tid 249
```

- `--tid` é obrigatório nesta primeira versão
- `--tags` vira `biliup upload --tag`
- `--schedule` vira o timestamp que o Bilibili espera

## Parâmetros do post de imagens

```bash
--images videos/1.png videos/2.png videos/3.png
--title "Título do post"
--note "Conteúdo do post"
--tags post,teste
```

Limites atuais do post de imagens:

- Douyin: no máximo 35 imagens, sem GIF
- Kuaishou: aceita várias imagens; mande arquivos diferentes de verdade, não o mesmo caminho repetido
- Xiaohongshu: aceita várias imagens, o `--note` é opcional, mas vale sempre passar o `--title`

Para mexer na CLI daqui em diante, olhe `sau_cli.py`, `uploader/` e `skills/`.
