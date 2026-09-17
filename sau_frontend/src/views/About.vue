<template>
  <div class="about">
    <el-card class="about-card">
      <div class="about-header">
        <h1>Automação de redes sociais</h1>
        <p class="version">social-auto-upload</p>
      </div>

      <el-divider />

      <div class="about-section">
        <h3>O que é</h3>
        <p>
          Uma ferramenta de automação que publica seus vídeos em várias redes sociais de uma vez, para quem cria conteúdo e cuida de perfis.
          Envia vídeos, agenda publicações e mais.
        </p>
      </div>

      <div class="about-section">
        <h3>Plataformas</h3>
        <div class="platform-tags">
          <el-tag type="danger">Douyin</el-tag>
          <el-tag type="success">Kuaishou</el-tag>
          <el-tag type="warning">Canal do WeChat</el-tag>
          <el-tag type="info">Xiaohongshu</el-tag>
        </div>
      </div>

      <div class="about-section">
        <h3>Principais recursos</h3>
        <ul class="feature-list">
          <li>Contas de várias plataformas, com a sessão sempre válida</li>
          <li>Envio e organização dos vídeos</li>
          <li>Publicação em várias plataformas de uma vez</li>
          <li>Publicação agendada e em lote</li>
          <li>Cookie Importação e exportação</li>
        </ul>
      </div>

      <div class="about-section">
        <h3>Tecnologias</h3>
        <div class="tech-tags">
          <el-tag effect="plain">Vue 3</el-tag>
          <el-tag effect="plain">Element Plus</el-tag>
          <el-tag effect="plain">Pinia</el-tag>
          <el-tag effect="plain">Flask</el-tag>
          <el-tag effect="plain">Playwright</el-tag>
          <el-tag effect="plain">SQLite</el-tag>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
// componente da página Sobre
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.about {
  max-width: 700px;
  margin: 0 auto;

  .about-card {
    .about-header {
      text-align: center;

      h1 {
        color: $text-primary;
        margin: 0 0 8px 0;
        font-size: 24px;
      }

      .version {
        color: $text-secondary;
        font-size: 14px;
        margin: 0;
      }
    }

    .about-section {
      margin-bottom: 24px;

      h3 {
        font-size: 16px;
        color: $text-primary;
        margin: 0 0 12px 0;
      }

      p {
        color: $text-secondary;
        line-height: 1.8;
        margin: 0;
      }

      .platform-tags,
      .tech-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .feature-list {
        margin: 0;
        padding-left: 20px;
        color: $text-secondary;
        line-height: 2;
      }
    }
  }
}
</style>
