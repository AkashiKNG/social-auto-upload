# Unificação da CLI das plataformas de navegador e skill do Xiaohongshu

Data: 2026-03-25

## Resumo

Este projeto unifica a interface das três plataformas que usam automação de navegador:

- Douyin
- Kuaishou
- Xiaohongshu

A ideia não é reescrever o uploader nem criar mais uma camada de framework, e sim juntar num contrato único a CLI, as skills, a documentação e os exemplos que hoje existem de forma inconsistente.

O projeto resolve dois problemas reais ao mesmo tempo:

1. O Xiaohongshu já tem um uploader de navegador funcionando, mas não está na CLI `sau` e não tem skill.
2. O contrato atual de Douyin e Kuaishou ainda carrega campos históricos: o vídeo não tem um `--desc` próprio, e o nome do texto do post se mistura com a descrição do vídeo, o que atrapalha um contrato estável entre as três plataformas.

Depois da unificação, as entradas públicas são:

- `sau douyin ...`
- `sau kuaishou ...`
- `sau xiaohongshu ...`

E o envio de vídeo e de post nas três segue o mesmo modelo de parâmetros:

- vídeo: `title + desc + tags`
- post de imagens: `title + note + tags`

## Objetivos

- dar ao Xiaohongshu a CLI completa:
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`
- unificar o modelo de parâmetros de envio nas três plataformas de navegador
- criar a skill, o script de exemplo, o README, a documentação da CLI e os documentos de instalação e atualização do Xiaohongshu
- corrigir a falta de `desc` no contrato atual de Douyin e Kuaishou
- manter a lógica dos uploaders praticamente intacta, sem encapsular demais

## Fora do escopo

- não é uma refatoração da arquitetura dos uploaders
- não mexe no caminho Web antigo
- não mexe no contrato de envio do Bilibili
- não faz teste de integração com navegador
- não mantém o `--note` antigo como contrato público

## O que o projeto já tem

### Capacidades existentes

- Douyin e Kuaishou já estão no `sau_cli.py`
- Bilibili já tem CLI e skill
- o Xiaohongshu já faz:
  - login
  - validação de cookie
  - envio de vídeo
  - envio de post de imagens
  - publicação agendada
- por dentro, o uploader do Xiaohongshu já aceita:
  - vídeo: `title + desc + tags`
  - post: `title + desc + tags`
  - o `desc` do post é opcional

### O que está inconsistente

- vídeo do Douyin na CLI: `--title` e `--tags`, sem `--desc`
- vídeo do Kuaishou na CLI: `--title` e `--tags`, sem `--desc`
- post do Douyin na CLI: `--note` e `--tags`
- post do Kuaishou na CLI: `--note` e `--tags`
- o Xiaohongshu não tem CLI nem skill

Ou seja, as três plataformas não oferecem a mesma coisa, principalmente porque:

- a descrição do vídeo não aparece de forma uniforme como `desc`
- não está definido se o texto do post deve manter o nome `note`

## Desenho da CLI unificada

### Plataformas

- `douyin`
- `kuaishou`
- `xiaohongshu`

### Ações

Todas as plataformas passam a ter:

- `login`
- `check`
- `upload-video`
- `upload-note`

### Modelo de parâmetros unificado

#### Envio de vídeo

```bash
sau <platform> upload-video \
  --account <account_name> \
  --file <video-path> \
  --title "<title>" \
  [--desc "<description>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"] \
  [parâmetros específicos da plataforma...]
```

Regras gerais:

- `--title` obrigatório
- `--desc` opcional
- `--tags` opcional
- `--schedule` opcional

Parâmetros específicos:

- Douyin:
  - `--thumbnail`
  - `--product-link`
  - `--product-title`
- Kuaishou:
  - `--thumbnail`
- Xiaohongshu:
  - `--thumbnail`

#### Envio de post de imagens

```bash
sau <platform> upload-note \
  --account <account_name> \
  --images <image-1> [image-2 ...] \
  --title "<title>" \
  [--note "<content>"] \
  [--tags tag1,tag2] \
  [--schedule "YYYY-MM-DD HH:MM"]
```

Regras gerais:

- `--images` obrigatório
- `--title` obrigatório
- `--note` opcional
- `--tags` opcional
- `--schedule` opcional

Decisões explícitas:

- o texto do post se chama `note`
- a descrição do vídeo se chama `desc`
- documentação, skills e exemplos usam sempre:
  - vídeo: `--title + --desc + --tags`
  - post: `--title + --note + --tags`

## Modelo de dados

Para a correspondência entre a CLI e os uploaders ficar clara, cada plataforma mantém seu próprio dataclass de requisição, mas com os campos nomeados igual.

### Objeto de requisição de vídeo

Campos comuns:

- `account_name`
- `video_file`
- `title`
- `description`
- `tags`
- `publish_date`
- `publish_strategy`
- `debug`
- `headless`

Campos específicos:

- Douyin:
  - `thumbnail_file`
  - `product_link`
  - `product_title`
- Kuaishou:
  - `thumbnail_file`
- Xiaohongshu:
  - `thumbnail_file`

### Objeto de requisição de post

Campos comuns:

- `account_name`
- `image_files`
- `title`
- `note`
- `tags`
- `publish_date`
- `publish_strategy`
- `debug`
- `headless`

Aqui o `note` fica mesmo, porque combina melhor com o texto de um post e não deve ser forçado a reaproveitar o `description / desc` do vídeo.

## Correspondência com os uploaders atuais

### Douyin

- o envio de vídeo continua usando o `DouYinVideo`
- o vídeo do Douyin ganha a entrada de `desc`
- o envio de post passa a receber explicitamente `title + note + tags`
- na CLI, o `note` vai para o campo de texto do post no Douyin

### Kuaishou

- o envio de vídeo continua usando o `KSVideo`
- o vídeo do Kuaishou ganha a entrada de `desc`
- o envio de post passa a receber explicitamente `title + note + tags`

### Xiaohongshu

- login e validação ligam direto no `xiaohongshu_setup` / `cookie_auth`
- o envio de vídeo reaproveita o `XiaoHongShuVideo`
- o envio de post reaproveita o `XiaoHongShuNote`
- como o uploader já aceita `title + desc + tags`, a CLI só precisa mapear o `note` para o texto do post

## Compatibilidade e migração

A estratégia é unificar de uma vez, sem manter o contrato público antigo e ambíguo.

Na prática:

- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`
- `skills/douyin-upload/...`
- `skills/kuaishou-upload/...`
- o novo `skills/xiaohongshu-upload/...`
- `scripts/examples/...`

mudam todos na mesma rodada, para não acontecer de:

- uma parte da documentação chamar o texto do post de `--note`
- outra parte chamar de `--desc`

O preço é que os comandos dos exemplos antigos param de valer; em troca, o contrato fica realmente uniforme:

- vídeo é sempre `desc`
- post é sempre `note`

## Desenho das skills

Novos arquivos:

- `skills/xiaohongshu-upload/SKILL.md`
- `skills/xiaohongshu-upload/references/cli-contract.md`
- `skills/xiaohongshu-upload/references/runtime-requirements.md`
- `skills/xiaohongshu-upload/references/troubleshooting.md`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.ps1`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_commands.sh`
- `skills/xiaohongshu-upload/scripts/examples/xiaohongshu_cli_template.py`

E, junto:

- `skills/douyin-upload/SKILL.md`
- `skills/douyin-upload/references/cli-contract.md`
- `skills/kuaishou-upload/SKILL.md`
- `skills/kuaishou-upload/references/cli-contract.md`

Os princípios das skills continuam:

- use o `sau` primeiro
- o agente não deve começar lendo o código do uploader
- só olhe o guia de problemas quando a CLI falhar
- a imagem do QR code deve ser mostrada direto ao usuário

## Documentação

Precisam mudar pelo menos:

- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`

O discurso passa a ser:

- as três plataformas de navegador estão na CLI
- as três plataformas de navegador têm skill
- campos do envio de vídeo:
  - `title`
  - `desc`
  - `tags`
- campos do envio de post:
  - `title`
  - `note`
  - `tags`
- o `account_name` é o nome que o usuário escolhe; não precisa ser `creator`
- cada `account_name` corresponde a um arquivo de conta, o que permite várias contas em paralelo

## Exemplos

Os exemplos ficam em duas categorias:

1. exemplos da CLI
2. exemplos históricos, chamando o uploader direto

O Xiaohongshu precisa chegar ao mesmo nível das outras plataformas:

- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`
- se for preciso, um exemplo mais próximo do contrato da CLI

O README e os docs devem deixar claro:

- use `sau xiaohongshu ...`
- os exemplos que chamam o uploader direto servem só para depuração

## Tratamento de erros

### Erros de parâmetro

Ficam com o parser da CLI:

- arquivo inexistente
- formato de data inválido
- falta o `--title`
- falta o `--images`

### Erros de negócio

Ficam com o uploader e as validações que já existem:

- cookie ausente
- cookie expirado
- falha no envio
- estrutura da página fora do esperado

### QR code

As três plataformas mantêm a mesma observação:

- se o login gerar uma imagem de QR code, o agente deve mostrar ou enviar a imagem ao usuário, não devolver só o caminho

## Estratégia de teste

Só a verificação mínima que vale a pena no nível da CLI, sem teste de integração com navegador.

Testes a acrescentar:

- o parser reconhece `xiaohongshu`
- o contrato novo é lido certo nas três plataformas:
  - `upload-video --title --desc --tags`
  - `upload-note --images --title --note --tags`
- o dispatch converte os parâmetros na requisição certa
- as ramificações `login/check/upload-video/upload-note` do Xiaohongshu são roteadas certo

Continua valendo:

- `tests/test_xiaohongshu_uploader.py`

## Arquivos afetados

### Precisam mudar

- `sau_cli.py`
- `README.md`
- `docs/CLI.md`
- `docs/install.md`
- `docs/update.md`

### Novos

- toda a pasta `skills/xiaohongshu-upload/`
- o arquivo de teste unitário da CLI

### Mudam junto

- `skills/douyin-upload/...`
- `skills/kuaishou-upload/...`
- `examples/get_xiaohongshu_cookie.py`
- `examples/upload_video_to_xiaohongshu.py`

## Ordem sugerida de implementação

1. mudar o `sau_cli.py` e os modelos de requisição
2. ligar as rotas da CLI do Xiaohongshu
3. acrescentar o `desc` e os novos campos de post em Douyin e Kuaishou
4. escrever os testes unitários da CLI
5. criar a skill do Xiaohongshu
6. atualizar os contratos das skills de Douyin e Kuaishou
7. atualizar README, CLI, install e update
8. atualizar os exemplos

## Conclusão

- as três plataformas de navegador passam a ter as mesmas ações:
  - `login`
  - `check`
  - `upload-video`
  - `upload-note`
- e o mesmo modelo de metadados:
  - vídeo: `title + desc + tags`
  - post: `title + note + tags`
- o Xiaohongshu ganha CLI e skill
- Douyin e Kuaishou ganham o `desc` e passam a chamar o texto do post de `note`
- a implementação fica leve, sem encapsulamento demais
