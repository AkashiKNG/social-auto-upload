# Vue 3 + Vite

Projeto de frontend com Vue 3, Vite, Element Plus, Pinia, Vue Router e Axios.

## 🚀 O que tem aqui

- ⚡️ **Vite** — build rápido
- 🖖 **Vue 3** — framework progressivo de JavaScript
- 🎨 **Element Plus** — biblioteca de componentes para Vue 3
- 🗂 **Vue Router** — rotas oficiais (modo hash)
- 📦 **Pinia** — gerenciamento de estado
- 🔗 **Axios** — cliente HTTP (já encapsulado)
- 🎯 **Sass** — pré-processador de CSS
- 📁 **Estrutura organizada** — páginas em `views`, componentes em `components`
- 🔧 **Configuração completa** — ambientes de desenvolvimento e produção

## 📦 Instalação

```bash
# instalar as dependências
npm install

# subir o servidor de desenvolvimento
npm run dev

# gerar a versão de produção
npm run build

# pré-visualizar a versão de produção
npm run preview
```

## 📁 Estrutura

```
src/
├── api/                 # chamadas de API
│   ├── index.js        # exportação central
│   └── user.js         # API de usuário
├── components/          # componentes compartilhados
│   └── HelloWorld.vue  # componente de exemplo
├── router/             # rotas
│   └── index.js        # arquivo principal das rotas
├── stores/             # estado
│   ├── index.js        # configuração do Pinia
│   └── user.js         # estado do usuário
├── styles/             # estilos
│   ├── index.scss      # estilo principal
│   ├── reset.scss      # reset
│   └── variables.scss  # variáveis
├── utils/              # utilitários
│   └── request.js      # wrapper das requisições HTTP
├── views/              # páginas
│   ├── Home.vue        # início
│   └── About.vue       # sobre
├── App.vue             # componente raiz
└── main.js             # ponto de entrada
```

## 🔧 Configuração

### Variáveis de ambiente

- `.env` — comuns a todos os ambientes
- `.env.development` — desenvolvimento
- `.env.production` — produção

### Rotas

Vue Router 4 em modo hash; o arquivo fica em `src/router/index.js`.

### Estado

Pinia, com as stores em `src/stores/`.

### Requisições HTTP

O Axios já vem encapsulado, com:

- interceptadores de requisição e resposta
- tratamento de erro
- token adicionado automaticamente
- formato de resposta padronizado

Como usar:

```javascript
import { http } from '@/utils/request'

// GET
const data = await http.get('/api/users')

// POST
const result = await http.post('/api/users', { name: 'John' })
```

### Estilos

- Sass como pré-processador
- estilos padrão do navegador removidos
- variáveis e classes utilitárias prontas
- tema do Element Plus personalizável

## 🎨 Componentes

O Element Plus está integrado; todos os componentes podem ser usados direto:

```vue
<template>
  <el-button type="primary">Botão</el-button>
  <el-input v-model="input" placeholder="Digite algo"></el-input>
</template>
```

## 📝 Convenções

1. **Páginas** em `src/views/`
2. **Componentes compartilhados** em `src/components/`
3. **Sintaxe `setup`** nos componentes
4. **Estilos em Sass**, seguindo BEM
5. **Chamadas de API** em `src/api/`
6. **Estado** dividido por módulo, em `src/stores/`

## 🚀 Publicação

```bash
# gerar a versão de produção
npm run build

# o resultado fica em dist/ e pode ir para qualquer servidor de arquivos estáticos
```

## 📄 Licença

MIT
