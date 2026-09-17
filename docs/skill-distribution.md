# Distribuição e publicação das skills

Este documento serve para quando o `social-auto-upload` for distribuir skills de forma independente.

O repositório hoje tem duas camadas:

- uma CLI instalável: `sau`
- uma skill embutida, instalável no Codex: `douyin-cli`

Depois que o fluxo principal e as correções estiverem prontos, dá para seguir para a publicação no PyPI, melhorar a instalação e criar skills independentes para mais plataformas.

## Conclusão primeiro

Uma `skill` não precisa ser um pacote Python.

Ela pode ser:

- uma pasta de skill
- um repositório próprio
- um script instalador
- uma imagem Docker
- qualquer artefato instalável por um gerenciador de pacotes

Mas, pensando em "como o outro instala e usa mais rápido", o caminho mais comum continua sendo:

1. distribuir a capacidade real num pacote instalável
2. usar uma ação de instalação para colocar a skill na pasta de skills da ferramenta de IA

Para este projeto, a forma recomendada é:

- o pacote Python fornece o comando `sau`
- o `sau skill install` coloca a skill em `~/.codex/skills/`

Ou seja:

```bash
pip install social-auto-upload
sau skill install
```

## A skill precisa ser um pacote?

Não.

### 1. A skill é só uma pasta

É a forma mais simples e mais comum.

Em geral contém:

- `SKILL.md`
- `agents/openai.yaml`
- `references/`
- `scripts/`

Assim já é uma skill utilizável, sem precisar de empacotamento.

O problema:

- o usuário precisa saber para onde copiar
- a instalação é manual
- se a skill depende de scripts ou de um runtime, instalar fica chato

Serve bem para:

- times internos
- convenções de desenvolvimento dentro do repositório
- skills que ainda mudam muito

### 2. A skill é um repositório próprio

Também funciona.

Por exemplo:

- um repositório só com o `SKILL.md`
- com um `scripts/install.py`
- ou com um README explicando como copiar para `~/.codex/skills/`

Vantagens:

- a skill tem versionamento próprio
- não depende do repositório principal
- pode ser publicada separadamente

Desvantagens:

- o usuário provavelmente ainda precisa clonar
- ou rodar um script de instalação

Serve bem quando:

- a skill é mantida como produto à parte
- a skill e o código de negócio já estão bem separados

### 3. A skill viaja junto com um pacote

É o caminho que mais combina com este projeto.

A ideia:

- o pacote Python leva a skill dentro dele
- depois de instalar, basta rodar `sau skill install`
- CLI e skill são lançadas juntas

Vantagens:

- melhor experiência para o usuário
- a skill fica alinhada com o comando de verdade
- a correspondência de versões fica clara
- ninguém precisa clonar o repositório

Serve bem quando:

- existe uma CLI, SDK ou ferramenta real por trás da skill
- o usuário quer usar a capacidade, não apenas ler a documentação

### 4. A skill é entregue por Docker

Também dá.

O jeito comum:

- o Docker já traz o ambiente pronto
- a skill diz à IA para executar via `docker run ...`

Vantagens:

- ambiente muito consistente
- ótimo quando as dependências locais são complicadas

Desvantagens:

- o usuário precisa instalar o Docker
- automação de navegador, login na área de trabalho, cookies e arquivos locais ficam mais complicados
- para um fluxo como o do Douyin, que precisa do navegador local, não é necessariamente melhor

Neste projeto, o Docker cai melhor em:

- serviços de backend
- tarefas em lote
- ambiente de servidor

Não é a melhor entrega única para quem vai fazer o primeiro login no Douyin.

## Ambiente de instalação, script de partida, repositório — tudo isso é skill?

É, mas vale separar a "skill em si" do "meio de instalação e execução".

Dá para pensar assim:

- o `SKILL.md` é a skill em si
- repositório, pacote, Docker e script de instalação são meios de distribuição e execução

Então:

- a skill pode morar num repositório
- a skill pode viajar dentro de um pacote
- a skill pode usar Docker para o ambiente de que depende

Se no fim o usuário consegue:

1. instalar
2. fazer a IA descobrir a skill
3. usar de verdade a capacidade por trás dela

então está de pé.

## O que faz mais sentido para este projeto

### Recomendação atual

Primeira fase:

- continuar corrigindo o fluxo principal e os bugs neste repositório
- manter o comando `sau` estável
- manter a skill embutida alinhada com o contrato da CLI

Segunda fase:

- empacotar e publicar no PyPI
- o usuário instala com `pip install social-auto-upload`
- o usuário roda `sau skill install`

Terceira fase:

- separar mais plataformas em skills próprias, conforme a necessidade
- por exemplo, `douyin-cli`, `tencent-cli`, `tiktok-cli`

### Por que não começar pelo repositório de skill separado

Porque o problema central agora não é onde a skill mora, e sim:

- se o fluxo de envio está estável
- se o contrato da CLI está estável
- se o usuário consegue rodar tudo depois de instalar

Enquanto isso não fecha, distribuir a skill junto com o pacote é o caminho mais seguro.

## Três rotas possíveis de publicação

### Rota A: pacote no PyPI + skill dentro dele

O usuário instala:

```bash
pip install social-auto-upload
sau skill install
```

Vantagens:

- é o mais fácil de divulgar
- instalação simples
- versionamento claro

É a rota preferida hoje.

### Rota B: repositório de skill próprio + pacote no PyPI

O usuário instala a capacidade:

```bash
pip install social-auto-upload
```

E instala a skill:

- clonando o repositório da skill
- ou rodando o instalador que ela oferece

Vantagens:

- a skill evolui sozinha
- dá para manter metadados diferentes por ferramenta de IA

Desvantagem:

- a instalação fica mais longa

### Rota C: Docker + skill

O usuário:

- instala o Docker
- baixa a imagem
- instala a skill
- a skill chama comandos docker por dentro

Vantagem:

- ambiente mais estável

Desvantagem:

- ruim para automação de navegador e login interativo

Combina mais com tarefas de servidor; não é a escolha atual.

## Sugestão de publicação

Quando o fluxo principal estiver estável, siga esta ordem:

1. garanta que `sau douyin login/check/upload` funciona numa máquina real
2. confirme que a skill instalada por `sau skill install` é reconhecida pelo Codex
3. gere um wheel local e faça um teste de instalação do zero
4. só então publique no PyPI

O caminho sugerido para o usuário final:

```bash
pip install social-auto-upload
playwright install chromium
sau skill install
sau douyin login --account my-account
```

## Resumindo numa frase

Uma `skill` não precisa virar pacote, mas se você quer que os outros instalem rápido, entendam pouco e façam o mínimo à mão, é melhor distribuir a capacidade num pacote e deixar a `skill` ser instalada junto.

Para este projeto, a melhor forma não é publicar só um repositório de skill, e sim:

- `social-auto-upload` como pacote instalável
- `douyin-cli` como skill embutida
- `sau skill install` como ponte de instalação
