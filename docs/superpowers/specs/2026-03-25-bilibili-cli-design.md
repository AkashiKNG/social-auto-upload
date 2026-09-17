# Projeto da CLI do Bilibili

Data: 2026-03-25

## Resumo

Este projeto coloca o `bilibili` embaixo do `sau`, com uma experiência o mais parecida possível com a de `douyin` e `kuaishou`.

Só há duas restrições centrais:

- o usuário não precisa instalar o `biliup`
- por fora, tudo passa por `sau bilibili ...`

O programa trata o `biliup` como uma dependência interna de execução:

- `sau bilibili ...` é a única entrada pública
- sem o `biliup` na máquina, ele é baixado sozinho
- toda execução confere a versão mais nova no GitHub Release
- havendo atualização, ela é aplicada antes de o comando seguir

O projeto é propositalmente leve: não reinventa a semântica de envio ao Bilibili, e sim reaproveita o modelo que já existe no repositório.

## Objetivos

- deixar `sau bilibili ...` com a mesma lógica de `sau douyin ...` e `sau kuaishou ...`
- esconder os detalhes de instalação do `biliup`, reduzindo o custo de uso
- reaproveitar o que já existe: arquivos de conta, `VideoZoneTypes`, publicação agendada
- não empacotar demais

## Fora do escopo

- a primeira versão não coloca o binário do `biliup` dentro do repositório
- a primeira versão não mantém um manifesto local de releases
- a primeira versão não faz post de imagens no Bilibili
- a primeira versão não refaz o modelo de envio que já existe

## O que o projeto já tem

O repositório já sabe enviar vídeos ao Bilibili:

- `uploader/bilibili_uploader/main.py` embrulha diretamente o `biliup.plugins.bili_webup`
- `examples/upload_video_to_bilibili.py` já usa os parâmetros de envio atuais
- `utils/constant.py` já define os `VideoZoneTypes` completos

Ou seja, a semântica de envio ao Bilibili já está clara, e no centro dela estão:

- `file`
- `title`
- `desc`
- `tid`
- `tags`
- `dtime`

Então a primeira versão da CLI não precisa de um modelo novo: usa esse mesmo.

## Desenho da CLI

### Comandos

- `sau bilibili login`
- `sau bilibili check`
- `sau bilibili upload-video`

### Contrato dos comandos

#### `sau bilibili login`

O que faz:

- prepara o `biliup`
- atualiza, se houver versão nova
- chama o `biliup` para fazer o login
- salva os dados da conta seguindo a regra de arquivos de conta do projeto

Comportamento na primeira versão:

- sem o `biliup` na máquina, baixa a release mais nova
- com o `biliup` desatualizado, atualiza
- terminada a atualização, segue com o login

#### `sau bilibili check`

O que faz:

- prepara o `biliup`
- confere se a conta atual está utilizável

Comportamento na primeira versão:

- decide juntando a existência do arquivo de conta e o resultado real do `biliup`
- a saída segue o padrão das outras plataformas:
  - `valid`
  - `invalid`

#### `sau bilibili upload-video`

O que faz:

- prepara o `biliup`
- envia o vídeo usando os parâmetros de envio que o projeto já tem

Parâmetros da primeira versão:

- `--account` obrigatório
- `--file` obrigatório
- `--title` obrigatório
- `--desc` obrigatório
- `--tid` obrigatório
- `--tags` opcional
- `--schedule` opcional

Decisão explícita:

- o `tid` é obrigatório nesta primeira versão
- não há categoria padrão, para não haver adivinhação nem erro silencioso

## Estratégia da dependência de execução

### Solução escolhida

O `biliup` não entra no repositório e também não exige instalação manual.

O `sau bilibili ...` cuida dele em tempo de execução:

1. procura o `biliup` na máquina
2. confere a versão mais nova no GitHub Release
3. se faltar ou estiver velho, baixa a mais nova
4. substitui a cópia local
5. segue com o comando atual

### Por que essa solução

- o repositório fica mais limpo
- o usuário não precisa caçar e baixar a release
- por fora continua havendo uma entrada única, o `sau`
- não é preciso usar `git submodule`

### O preço aceito

A solução assume um fato:

- toda execução consulta a release de origem
- se o comportamento da ferramenta mudar lá em cima, essa camada é afetada

Por isso a resposta não é embrulhar mais, e sim manter o wrapper fino, reduzindo a manutenção reativa.

## Armazenamento e resolução

O `biliup` deve ficar num diretório de cache de execução, não no diretório do código-fonte.

O diretório de cache só precisa:

- ter permissão de escrita para o usuário atual
- ser reaproveitável entre comandos
- ficar fora do git

O resolvedor deve:

- identificar o sistema operacional
- escolher o asset da release correspondente
- baixar e substituir o executável
- devolver o caminho final do executável

## Limites do encapsulamento

Para não exagerar, a primeira versão se divide em três partes bem finas.

### 1. Resolver

Responsabilidade:

- ver se o `biliup` já está na máquina
- conferir a versão mais nova no GitHub Release
- baixar ou atualizar o executável
- devolver o caminho final do executável

### 2. Runner

Responsabilidade:

- chamar o `biliup` resolvido
- coletar código de saída, saída padrão e saída de erro
- converter os erros mais evidentes de processo em mensagens amigáveis do projeto

### 3. Subcomando bilibili no `sau_cli.py`

Responsabilidade:

- interpretar os parâmetros de `sau bilibili ...`
- traduzi-los para a lógica de execução de baixo nível
- manter o texto de ajuda no mesmo estilo das outras plataformas

A primeira versão não precisa de mais camadas nem de um framework unificado e pesado.

## Correspondência com o que já existe

### Arquivos de conta

O Bilibili continua usando o mecanismo de apelido de conta do projeto:

- o usuário passa `--account <name>`
- o programa resolve o caminho do arquivo de conta

### Categoria

O `tid` continua sendo parâmetro de primeira classe.

Os `VideoZoneTypes` seguem existindo e servindo para:

- os exemplos
- a documentação
- possíveis ferramentas auxiliares

### Publicação agendada

O `--schedule` funciona como nas outras plataformas do `sau`:

- sem ele, publica na hora
- com ele, publica agendado

Como isso vira a execução real no Bilibili é problema do adaptador, não do usuário.

## Tratamento de erros

A primeira versão trata erros de forma direta, sem enfeite:

- falha no download: diz claramente que o download automático do `biliup` falhou
- falha na atualização: diz claramente que não deu para preparar a release mais nova
- falha no login: mantém o contexto de erro do `biliup`
- falha na checagem: imprime `invalid`
- falha no envio: devolve código de saída diferente de zero e mostra o resumo do erro de origem

A primeira versão não tenta traduzir todo texto de erro do `biliup`.

## Documentação afetada

Concluída a implementação, é preciso atualizar pelo menos:

- `README.md`
- `docs/CLI.md`
- os documentos de instalação e atualização
- uma skill de Bilibili correspondente
- um script de exemplo do Bilibili

A mensagem para fora deve ser sempre a mesma:

- o usuário usa `sau bilibili ...`
- o `biliup` é preparado pelo programa

## Estratégia de teste

A primeira versão precisa verificar pelo menos:

- `sau bilibili login --account <name>`
- `sau bilibili check --account <name>`
- `sau bilibili upload-video ...`
- baixar o `biliup` quando ele não existe na máquina
- atualizar antes de executar quando a versão local está velha
- reaproveitar direto quando a versão local já é a mais nova

Como login e envio envolvem uma plataforma externa de verdade, verificação manual é aceitável nesta primeira versão.

## Ordem sugerida de implementação

1. adicionar o subcomando `bilibili` no `sau_cli.py`
2. criar um resolvedor mínimo do `biliup`
3. criar um executor mínimo do `biliup`
4. ligar `login / check / upload-video`
5. escrever documentação, exemplo e skill

## Conclusão

- a entrada pública é `sau bilibili ...`
- a primeira versão cobre `login`, `check` e `upload-video`
- o `tid` é obrigatório
- o usuário não precisa instalar o `biliup`
- toda execução confere o GitHub Release
- havendo versão nova, ela é aplicada antes de o comando seguir
- a implementação fica leve, sem encapsulamento demais
