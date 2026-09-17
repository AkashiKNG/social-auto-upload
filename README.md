# social-auto-upload

`social-auto-upload` é uma ferramenta de automação para quem cria conteúdo: ela publica seus vídeos, de uma vez, nas principais redes sociais.
O projeto envia vídeos e agenda publicações no `Douyin`, `Bilibili`, `Xiaohongshu`, `Kuaishou`, `Canal do WeChat`, `Baijiahao`, `Alipay (conta de vida)`, `Weibo`, `Hupu`, `TikTok` e `YouTube`.
Cada plataforma tem o seu módulo em `uploader`, então dá para configurar e acrescentar plataformas com facilidade, usando os scripts de exemplo como ponto de partida.

> **Tradução para português do Brasil.** Este fork traduz a interface, as mensagens e a documentação. Textos em chinês que
> são **conteúdo dos próprios sites** (botões que o robô procura na página, nomes de categoria enviados no formulário)
> continuam no original de propósito: traduzi-los quebraria o login e o envio.

<img src="media/show/tkupload.gif" alt="tiktok show" width="800"/>

## 💎 Patrocinadores

<table width="100%">
 <tr>
    <td width="25%" align="center" valign="middle">
      <a href="https://chilltion.com/?ref=1y5k5k">
        <img src="static/DolOffer.png" alt="DolOffer Sponsor" width="180">
      </a>
    </td>
    <td width="75%" align="left" valign="middle">
      Obrigado à <a href="https://doloffer.com/" target="_blank">DolOffer</a> pelo apoio ao projeto! Para quem trabalha com várias contas, distribuição multiplataforma e automação com IA, ferramentas como ChatGPT, Claude, YouTube Premium, Spotify, Apple Music, Notion e Office viram um custo fixo. A DolOffer oferece assinaturas e recargas dessas ferramentas de IA, vídeo, música e produtividade por menos. Mais detalhes no <a href="https://github.com/Doloffer-g/guide" target="_blank">DolOffer Guide</a>. Com o cupom <code>AI8888</code> há 10% de desconto adicional; preços e regras valem os do site oficial.
    </td>
  </tr>
  <tr>
    <td width="25%" align="center" valign="middle">
      <a href="https://chilltion.com/?ref=1y5k5k">
        <img src="static/chilltion.png" alt="chilltion Sponsor" width="180">
      </a>
    </td>
    <td width="75%" align="left" valign="middle">
      Chilltion AI: animações em motion graphics a partir de uma frase, boas para vídeos de conhecimento, divulgação científica, explicações, tutoriais e apresentações — a um custo de cerca de 1% do de ferramentas como o Seedance. Quem se <a href="https://chilltion.com/?ref=1y5k5k">cadastrar</a> agora ganha 1500 créditos.
    </td>
  </tr>
    <tr>
        <td width="25%" align="center" valign="middle">
          <a href="http://t.clawpower.vip/1005">
            <img src="static/clawpower.png" alt="ClawPower Sponsor" width="180">
          </a>
        </td>
        <td width="75%" align="left" valign="middle">
          A ClawPower é um provedor estável de acesso a modelos de IA, com mais de 60 modelos (Claude, GPT, Gemini). Serve tanto para automação com agentes (OpenClaw, Hermes) e ferramentas de programação (Claude Code, Codex) quanto para criar conteúdo. Custa a partir de 30% do preço oficial; clique para <a href="http://t.clawpower.vip/1005">receber 5 dólares de crédito</a> e testar.
        </td>
      </tr>
  <tr>
    <td width="25%" align="center" valign="middle">
      <img src="static/wechat.png" alt="Sponsor Contact" width="150">
    </td>
    <td width="75%" align="left" valign="middle">
      <strong>Quer patrocinar?</strong><br>
      Escaneie o QR code do WeChat ao lado (ao adicionar, escreva o motivo: <strong>patrocínio</strong>).
    </td>
  </tr>
</table>

---

## Índice

- [💡 Recursos](#recursos)
- [💾 Instalação](#instalação)
- [🤖 Agentes de IA](#agentes-de-ia)
- [🏁 Primeiros passos](#primeiros-passos)
- [🗂️ Refatoração em andamento](#️refatoração-em-andamento)
- [📣 Situação do projeto](#situação-do-projeto)
- [🐇 De onde veio o projeto](#de-onde-veio-o-projeto)
- [📃 Documentação](#documentação)
- [🐾 Comunidade e apoio](#comunidade-e-apoio)
- [🤝 Como contribuir](#como-contribuir)
- [📜 Licença](#licença)
- [⭐ Star History](#star-history)

## 💡Recursos

| Plataforma | Login | Vídeo | Imagem + texto | Agendamento | CLI | Skill | Observação |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Douyin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | a mais completa na refatoração atual |
| Bilibili | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | prepara o `biliup` sozinho |
| Xiaohongshu (navegador) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | automação de navegador, com CLI e Skill |
| Kuaishou | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | automação de navegador; CLI e Skill em versão inicial |
| Canal do WeChat | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | automação de navegador (`tencent_uploader`) |
| Baijiahao | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | automação de navegador |
| Alipay (conta de vida) | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | automação de navegador, com vídeo na conta de vida |
| Weibo | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | automação de navegador; título de até 30 caracteres |
| Hupu | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | automação de navegador; título de 4 a 40 caracteres |
| TikTok | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | o exemplo atual usa a versão Chrome |
| YouTube | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | automação do Studio, com playlist e visibilidade |

> A **interface web** cobre só Xiaohongshu, Canal do WeChat, Douyin e Kuaishou. As outras plataformas — YouTube
> inclusive — funcionam pela **linha de comando** (`sau youtube upload-video ...`).

### Com a IA tão boa, por que este projeto?

Um agente de navegador precisa reler a página, tirar print e decidir na hora, a cada execução.
Este projeto já foi validado à exaustão: enviar vídeo é trabalho repetitivo e chato, e disso quem cuida melhor é um script.

## 💾Instalação

### Instalando por conta própria

Se você é um usuário comum e não vai usar um agente, veja a documentação, que reúne instalação, atualização e preparo do ambiente:

- [Instalação](./docs/install.md)
- [Atualização](./docs/update.md)

### Agentes de IA

```
Não trave na hora de instalar e usar: entregue essa parte a um agente de IA.
```

Se quiser entregar o repositório direto ao `OpenClaw`, `Codex` ou `Claude Code`:

mande o repositório para o agente e, junto, este prompt inicial:

- [Prompt inicial para agentes](./docs/agent-bootstrap.md)

Esse prompt orienta o agente a:

- instalar seguindo a linha principal do projeto
- usar `uv`, a CLI `sau` e as `skills/`
- conferir primeiro se `bilibili`, `douyin`, `kuaishou` e `xiaohongshu` estão funcionando

### Mais links

- Uso da CLI: [documentação da CLI](./docs/CLI.md)
- Para usar em `OpenClaw`, `Codex` ou `Claude Code`: [prompt inicial para agentes](./docs/agent-bootstrap.md)
- Skill do Douyin: [Douyin Upload Skill](./skills/douyin-upload/SKILL.md)
- Skill do Kuaishou: [Kuaishou Upload Skill](./skills/kuaishou-upload/SKILL.md)
- Skill do Xiaohongshu: [Xiaohongshu Upload Skill](./skills/xiaohongshu-upload/SKILL.md)
- Skill do Bilibili: [Bilibili Upload Skill](./skills/bilibili-upload/SKILL.md)
- Versão web antiga: [documentação da web legada](./docs/legacy-web.md)
- Outras skills, por plataforma e integradas, ainda estão em desenvolvimento
- O `requirements.txt` existe por compatibilidade com o caminho antigo; quem está começando não precisa dele

## 📣Situação do projeto

`24/03/2026`

Andei focado em empreender, com projetos ainda no meio do caminho, e por um bom tempo não consegui dedicar a este repositório a atenção que ele merecia.

O projeto passou de `9 mil estrelas` sem que eu percebesse, e a comunidade já tem mais de `2 mil` pessoas. Ver que ele ajuda de verdade me deixa feliz — obrigado pelo apoio e pelos retornos de sempre.

Então resolvi parar um pouco e dedicar um tempo a uma refatoração caprichada.

Nas próximas semanas o repositório deve entrar em uma fase de atualizações frequentes. O que mais quero fazer agora:

1. Usar uma automação mais discreta e estável, para reduzir o risco de detecção pelas plataformas
2. Completar o envio de imagem + texto nas plataformas mais usadas, com CLI e Skill
3. Publicar em mais lojas de skills, para fechar o último elo entre IA e redes sociais

Se você achava que o projeto andava devagar, provavelmente vai ficar bem mais rápido. Fique de olho: vem um período de conserto, atualização e refatoração contínuos.

## 🗂️Refatoração em andamento

O projeto passa por uma refatoração geral, com foco em:

- padronizar a estrutura dos uploaders
- unificar tudo na CLI
- virar skill para OpenClaw, Codex, Claude Code e afins
- trocar o driver para `patchright`, com mais compatibilidade e discrição
- priorizar o modo sem janela

"Modo sem janela" (headless) quer dizer que o navegador roda em segundo plano, sem abrir uma janela visível, mas a automação acontece do mesmo jeito. É o que serve para CLI, servidor, tarefas automáticas e agentes.

O código da versão web continua no repositório, mas não é mais a linha principal: não há garantia de que rode direto nem de que esteja sincronizado com o uploader/CLI atuais.

## 🏁Primeiros passos

### Opção 1: pela CLI

Douyin, Kuaishou, Xiaohongshu, Bilibili, Canal do WeChat, Baijiahao, Alipay, Weibo e Hupu já estão na CLI:

```bash
sau douyin login --account <nome_da_conta>
sau douyin check --account <nome_da_conta>
sau douyin upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
sau douyin upload-note --account <nome_da_conta> --images videos/1.png videos/2.png --title "Título do post" --note "Texto do post"

sau kuaishou login --account <nome_da_conta>
sau kuaishou check --account <nome_da_conta>
sau kuaishou upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
sau kuaishou upload-note --account <nome_da_conta> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Texto do post"

sau xiaohongshu login --account <nome_da_conta>
sau xiaohongshu check --account <nome_da_conta>
sau xiaohongshu upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo"
sau xiaohongshu upload-note --account <nome_da_conta> --images videos/1.png videos/2.png videos/3.png --title "Título do post" --note "Texto do post"

sau bilibili login --account <nome_da_conta>
sau bilibili check --account <nome_da_conta>
sau bilibili upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tid 249

sau tencent login --account <nome_da_conta>
sau tencent check --account <nome_da_conta>
sau tencent upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2

sau baijiahao login --account <nome_da_conta>
sau baijiahao check --account <nome_da_conta>
sau baijiahao upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2

sau alipay login --account <nome_da_conta>
sau alipay check --account <nome_da_conta>
sau alipay upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2

sau weibo login --account <nome_da_conta>
sau weibo check --account <nome_da_conta>
sau weibo upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2

sau hupu login --account <nome_da_conta>
sau hupu check --account <nome_da_conta>
sau hupu upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2

sau youtube login --account <nome_da_conta>
sau youtube check --account <nome_da_conta>
sau youtube upload-video --account <nome_da_conta> --file videos/demo.mp4 --title "Título de exemplo" --desc "Descrição de exemplo" --tags tag1,tag2 --playlist "Minha série" --visibility public
```

> Sobre o YouTube: o login é interativo (conta Google, feito no navegador, sem QR code). Aqui é automação de
> navegador em vez da API oficial porque **vídeo enviado por um projeto de API que não passou pela revisão do
> Google fica travado como privado e não dá para tornar público** — inútil para quem tem um canal só.
> A automação de navegador não tem essa limitação: publica direto em público e segue o mesmo esquema de cookies
> das outras plataformas do projeto.
> O `--playlist` serve para séries; o `--visibility` aceita `public`, `unlisted` ou `private`.
> O envio **espera chegar a 100% antes de publicar** (o upload depende da janela aberta; publicar no meio corta a transferência).
> Em regiões onde o youtube.com é bloqueado: defina `YT_PROXY = "http://127.0.0.1:7890"` no `conf.py` (o chromium
> ignora o proxy do sistema, precisa ser explícito).

Observações:

- nomes como `creator` são só exemplos; o que vale é o `account_name`
- cada `account_name` tem um arquivo de conta próprio: dá para ter várias contas e rodar tarefas em paralelo por nome
- se a publicação no Douyin pedir verificação por SMS, o programa lê antes o arquivo `verify_code.txt` na raiz do projeto; rodando a CLI num terminal interativo, também dá para digitar o código no próprio terminal
- nas plataformas por navegador vale sempre a mesma convenção:
- vídeo usa `title + desc + tags`
- imagem + texto usa `title + note + tags`
- a CLI do Bilibili não exige instalar o `biliup` à mão
- na primeira execução o programa baixa o `biliup` sozinho
- nas seguintes, confere a release mais nova e atualiza
- o login do Bilibili é melhor feito no seu terminal de verdade; se o QR code sair cortado, abra o `qrcode.png` na pasta atual e escaneie por lá

### Opção 2: pelos exemplos

Em `examples/` há dois tipos de script:

- exemplos que chamam a CLI atual
- exemplos antigos que falam direto com o uploader

Para Douyin, Kuaishou, Xiaohongshu e Bilibili, prefira os comandos `sau ...` acima.
Os scripts abaixo são os exemplos diretos (ou pontos de depuração):

- `examples/upload_to_douyin.py`
- `examples/upload_video_to_bilibili.py`
- `examples/upload_to_kuaishou.py`
- `examples/upload_video_to_tencent.py`
- `examples/upload_video_to_baijiahao.py`
- `examples/get_alipay_cookie.py`
- `examples/test_alipay_upload.py`
- `examples/upload_video_to_tiktok.py`
- `examples/upload_video_to_xiaohongshu.py`

## 🐇De onde veio o projeto

No começo era uma ferramenta pessoal para automatizar as minhas publicações. Como eu costumava agendar sempre para o dia seguinte, boa parte da lógica de agendamento calcula os horários a partir de "amanhã".

Se você precisa publicar na hora ou seguir outra estratégia, dá uma olhada no código ou pergunte na comunidade.

## 📃Documentação

A documentação está atrasada em relação ao código, que passa por uma refatoração rápida. O caminho mais fácil hoje é entregar o repositório ao seu agente de IA (qwen code, codex, cc, openclaw e afins) e deixar que ele instale e use.

Documentação completa: [documentação oficial do social-auto-upload](https://sap-doc.nasdaddy.com/)

## 🐾Comunidade e apoio

[☕ Donate as u like](https://www.buymeacoffee.com/hysn2001m) — se o projeto te ajudou, considere apoiar.

Se você também é desenvolvedor independente ou entusiasta e curte os assuntos #monetização #startups de IA #comércio internacional #automação #criação de vídeo, entra na comunidade.

### Criador

<table>
    <td align="center">
        <a href="https://sap-doc.nasdaddy.com/">
            <img src="media/mp.jpg" width="200px" alt="conta oficial NasDaddy"/>
            <br />
            <sub><b>Conta oficial no WeChat</b></sub>
        </a>
        <br />
        <a href="https://github.com/dreammis/social-auto-upload/commits?author=dreammis" title="Code">💻</a>
        <br />
        Siga a conta e responda `上传` (literalmente "upload") para receber o convite do grupo
    </td>
    <td align="center">
        <a href="https://sap-doc.nasdaddy.com/">
            <img src="media/QR.png" width="200px" alt="QR de apoio e entrada no grupo"/>
            <br />
            <sub><b>Grupo da comunidade (pela conta oficial)</b></sub>
        </a>
        <br />
        <a href="https://sap-doc.nasdaddy.com/" title="Documentation">📖</a>
        <br />
        Se o projeto te serviu, considere apoiar
    </td>
</table>

## 🤝Como contribuir

Toda contribuição é bem-vinda, entre elas:

- abrir relatos de bug e pedidos de recurso
- melhorar código e documentação
- compartilhar experiências e tutoriais

Para contribuir com código:

1. Faça um fork do repositório.
2. Crie uma branch (`git checkout -b feature/SuaFeature` ou `bugfix/SeuBugfix`).
3. Faça o commit (`git commit -m 'Add some feature'`).
4. Envie a branch (`git push origin feature/SuaFeature`).
5. Abra um Pull Request.

Antes de enviar código ou documentação, confirme que você tem o direito de fazê-lo e concorda em publicar sob a licença MIT deste projeto. Ao enviar código de terceiros, diga de onde veio e sob qual licença.

## Principais contribuidores

<a href="https://github.com/dreammis/social-auto-upload/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=dreammis/social-auto-upload" />
</a>

## 🙏Agradecimentos

O envio para o Bilibili é feito em cima do projeto `biliup`.
Obrigado ao `biliup` e a quem contribui com ele:

- https://github.com/biliup/biliup

Os componentes de terceiros usados aqui continuam sob as licenças deles. Ao redistribuir ou integrar este projeto, confira e preserve os avisos de direito autoral, licença e NOTICE exigidos por esses componentes.

## 📜Licença

Este projeto usa a [licença MIT](LICENSE). Fora os componentes de terceiros, o código pode ser usado em software comercial, inclusive fechado, desde que os termos da licença sejam respeitados.

## ⭐Star-History

> Se o projeto te ajudou, deixa uma ⭐!

[![Star History Chart](https://star-history.dera.page/svg?repos=dreammis/social-auto-upload&type=Date)](https://star-history.dera.page/#dreammis/social-auto-upload&Date)
