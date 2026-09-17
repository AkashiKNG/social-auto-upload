# Agent Bootstrap Prompt

Este documento é para quem usa clientes de agente como `OpenClaw`, `Codex` e `Claude Code / cc`.

A ideia não é o agente ler o repositório inteiro, e sim deixar o `social-auto-upload` instalado, funcionando e pronto para receber tarefas.

Plataformas já integradas:

- `bilibili`
- `douyin`
- `kuaishou`
- `xiaohongshu`

## Que problema este documento resolve

O repositório já tem:

- instruções de instalação
- documentação da CLI
- skills por plataforma

Só que tudo isso fala do "o que o agente faz depois de entrar no repositório".

Este documento cobre o outro lado: "o que o usuário deve dizer na primeira vez que entrega o repositório ao agente".

## Como usar

1. Dê o repositório inteiro ao seu cliente de agente.
2. Mande o texto de partida abaixo, inteiro.
3. Quando o agente terminar a instalação e a conferência da CLI, passe as tarefas de login, envio e agendamento.

## Texto de partida

Copie o bloco inteiro e mande ao seu agente:

```text
Você está trabalhando num repositório chamado `social-auto-upload`.

É um projeto de publicação automática em várias redes sociais. Já estão integrados:

- bilibili
- douyin
- kuaishou
- xiaohongshu

Seu primeiro objetivo não é ler todo o código nem rodar os exemplos antigos, e sim deixar o projeto instalado, conferido e pronto para receber tarefas.

Siga estas regras:

1. Considere a raiz do repositório como o diretório de trabalho.
2. Use o `uv` para o ambiente Python; não caia de volta no antigo `requirements.txt`.
3. Use a CLI atual: `sau`.
4. Consulte primeiro estes documentos:
   - `docs/install.md`
   - `docs/CLI.md`
   - `docs/update.md`
5. Para operações por plataforma, consulte estas skills:
   - `skills/douyin-upload/`
   - `skills/kuaishou-upload/`
   - `skills/xiaohongshu-upload/`
   - `skills/bilibili-upload/`
6. Não use os `examples/` antigos nem o caminho da Web antiga, a menos que a CLI não esteja disponível.
7. Se o login gerar uma imagem de QR code, não devolva só o caminho: mostre a imagem ou diga com clareza qual arquivo local devo abrir para escanear.
8. No login do Bilibili, não tente rodar por mim em ambiente não interativo; me oriente a rodar no meu terminal.
9. Depois de instalar, confira estes comandos:
   - `sau --help`
   - `sau douyin --help`
   - `sau kuaishou --help`
   - `sau xiaohongshu --help`
   - `sau bilibili --help`
10. Ao terminar, diga claramente:
   - quais comandos você rodou
   - o que passou na conferência
   - se o projeto já está pronto para login e envio
   - o que você recomenda como próximo passo

Se aparecer algum erro, não pule: explique o erro e diga qual será seu próximo passo.
```

## O que dizer depois da instalação

Exemplos de tarefas para mandar ao agente em seguida.

### Fazer um login

```text
Entre na minha conta do Xiaohongshu, com janela aberta, usando o nome de conta `creator`.
```

```text
Entre na minha conta do Douyin, sem janela, usando o nome de conta `creator`.
```

### Conferir a CLI

```text
Confira se a CLI funciona nas quatro plataformas — bilibili, douyin, kuaishou e xiaohongshu — e me diga que dependências faltam.
```

### Fazer um envio de verdade

```text
Use a CLI do xiaohongshu para enviar um rascunho de post de imagens com publicação agendada, sem publicar na hora.
```

```text
Use a CLI do douyin para enviar um vídeo pelo caminho atual, sem usar os exemplos antigos.
```

## Dicas por cliente

### OpenClaw

- Dá para colar o texto de partida inteiro
- Se der para montar o repositório como diretório de trabalho, monte antes de mandar o texto
- Se o cliente exibe arquivos locais, deixe o agente mostrar a imagem do QR code

### Codex

- Peça primeiro o bootstrap e só depois as tarefas por plataforma
- Faça-o usar `docs/install.md`, `docs/CLI.md` e `skills/`
- Não o deixe explorar o repositório livremente no começo, ou ele acaba nos caminhos antigos

### Claude Code / cc

- Deixe o repositório como workspace atual
- Mande o texto de partida completo
- Depois siga a ordem: instalar → conferir → entrar na conta → enviar

## Por que não quatro textos, um por plataforma

Porque hoje o projeto tem uma CLI única.

Na primeira vez que alguém entrega o repositório a um agente, o que importa é que ele:

- saiba qual é a entrada principal
- saiba qual caminho seguir
- saiba o que é caminho antigo
- entregue um resultado claro depois de instalar

Na hora de executar, aí sim o agente escolhe conforme o seu objetivo:

- `bilibili`
- `douyin`
- `kuaishou`
- `xiaohongshu`

Isso é mais estável e mais fácil de manter do que quatro prompts diferentes.
