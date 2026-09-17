<template>
  <div class="dashboard">
    <div class="page-header">
      <h1>Automação de redes sociais</h1>
    </div>

    <div class="dashboard-content">
      <el-row :gutter="20">
        <!-- cartão com o resumo das contas -->
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon">
                <el-icon><User /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ accountStats.total }}</div>
                <div class="stat-label">Total de contas</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>ok: {{ accountStats.normal }}</span>
                <span>com erro: {{ accountStats.abnormal }}</span>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- cartão com o resumo das plataformas -->
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon platform-icon">
                <el-icon><Platform /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ platformStats.total }}</div>
                <div class="stat-label">Plataformas conectadas</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <el-tooltip content="Contas Kuaishou" placement="top">
                  <el-tag size="small" type="success">{{ platformStats.kuaishou }}</el-tag>
                </el-tooltip>
                <el-tooltip content="Contas Douyin" placement="top">
                  <el-tag size="small" type="danger">{{ platformStats.douyin }}</el-tag>
                </el-tooltip>
                <el-tooltip content="Contas Canal do WeChat" placement="top">
                  <el-tag size="small" type="warning">{{ platformStats.channels }}</el-tag>
                </el-tooltip>
                <el-tooltip content="Contas Xiaohongshu" placement="top">
                  <el-tag size="small" type="info">{{ platformStats.xiaohongshu }}</el-tag>
                </el-tooltip>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- cartão com o resumo dos materiais -->
        <el-col :span="8">
          <el-card class="stat-card">
            <div class="stat-card-content">
              <div class="stat-icon content-icon">
                <el-icon><Document /></el-icon>
              </div>
              <div class="stat-info">
                <div class="stat-value">{{ contentStats.total }}</div>
                <div class="stat-label">Total de materiais</div>
              </div>
            </div>
            <div class="stat-footer">
              <div class="stat-detail">
                <span>Vídeos: {{ contentStats.videos }}</span>
                <span>Imagens: {{ contentStats.images }}</span>
                <span>Outros: {{ contentStats.others }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- área de atalhos -->
      <div class="quick-actions">
        <h2>Atalhos</h2>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/account-management')">
              <div class="action-icon">
                <el-icon><UserFilled /></el-icon>
              </div>
              <div class="action-title">Contas</div>
              <div class="action-desc">Gerencie as contas de todas as plataformas</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/material-management')">
              <div class="action-icon">
                <el-icon><Upload /></el-icon>
              </div>
              <div class="action-title">Materiais</div>
              <div class="action-desc">Envie e organize os vídeos</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/publish-center')">
              <div class="action-icon">
                <el-icon><Timer /></el-icon>
              </div>
              <div class="action-title">Publicação</div>
              <div class="action-desc">Publique o conteúdo nas plataformas</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="action-card" @click="navigateTo('/about')">
              <div class="action-icon">
                <el-icon><DataAnalysis /></el-icon>
              </div>
              <div class="action-title">Sobre o sistema</div>
              <div class="action-desc">Veja as informações do sistema</div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- lista de materiais -->
      <div class="recent-tasks">
        <div class="section-header">
          <h2>Materiais enviados recentemente</h2>
          <el-button text @click="navigateTo('/material-management')">Ver todos</el-button>
        </div>

        <el-table :data="recentMaterials" style="width: 100%" v-loading="loading">
          <el-table-column prop="filename" label="Arquivo" width="300" />
          <el-table-column prop="filesize" label="Tamanho" width="120">
            <template #default="scope">
              {{ scope.row.filesize }} MB
            </template>
          </el-table-column>
          <el-table-column prop="upload_time" label="Enviado em" width="200" />
          <el-table-column label="Tipo" width="100">
            <template #default="scope">
              <el-tag
                :type="getFileTypeTag(scope.row.filename)"
                effect="plain"
                size="small"
              >
                {{ getFileType(scope.row.filename) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!loading && recentMaterials.length === 0" description="Nenhum material ainda" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  User, UserFilled, Platform, Document,
  Upload, Timer, DataAnalysis
} from '@element-plus/icons-vue'
import { accountApi } from '@/api/account'
import { materialApi } from '@/api/material'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const accountStore = useAccountStore()
const appStore = useAppStore()
const loading = ref(false)

// resumo das contas, calculado a partir dos dados reais
const accountStats = computed(() => {
  const accounts = accountStore.accounts
  const normal = accounts.filter(a => a.status === 'ok').length
  const abnormal = accounts.filter(a => a.status !== 'ok' && a.status !== 'verificando').length
  return {
    total: accounts.length,
    normal,
    abnormal
  }
})

// resumo das plataformas, calculado a partir dos dados reais
const platformStats = computed(() => {
  const accounts = accountStore.accounts
  const kuaishou = accounts.filter(a => a.platform === 'Kuaishou').length
  const douyin = accounts.filter(a => a.platform === 'Douyin').length
  const channels = accounts.filter(a => a.platform === 'Canal do WeChat').length
  const xiaohongshu = accounts.filter(a => a.platform === 'Xiaohongshu').length
  // quantas plataformas têm alguma conta
  const total = [kuaishou, douyin, channels, xiaohongshu].filter(n => n > 0).length
  return { total, kuaishou, douyin, channels, xiaohongshu }
})

// resumo dos materiais, calculado a partir dos dados reais
const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

const contentStats = computed(() => {
  const materials = appStore.materials
  const videos = materials.filter(m => videoExtensions.some(ext => m.filename.toLowerCase().endsWith(ext))).length
  const images = materials.filter(m => imageExtensions.some(ext => m.filename.toLowerCase().endsWith(ext))).length
  return {
    total: materials.length,
    videos,
    images,
    others: materials.length - videos - images
  }
})

// materiais enviados por último (no máximo 5)
const recentMaterials = computed(() => {
  return [...appStore.materials]
    .sort((a, b) => new Date(b.upload_time) - new Date(a.upload_time))
    .slice(0, 5)
})

// descobre o tipo do arquivo
const getFileType = (filename) => {
  if (videoExtensions.some(ext => filename.toLowerCase().endsWith(ext))) return 'Vídeos'
  if (imageExtensions.some(ext => filename.toLowerCase().endsWith(ext))) return 'Imagens'
  return 'Outros'
}

// cor da etiqueta conforme o tipo do arquivo
const getFileTypeTag = (filename) => {
  const type = getFileType(filename)
  return { 'Vídeos': 'success', 'Imagens': 'warning', 'Outros': 'info' }[type] || 'info'
}

// navega para uma rota
const navigateTo = (path) => {
  router.push(path)
}

// carrega os dados
const fetchDashboardData = async () => {
  loading.value = true
  try {
    // busca contas e materiais em paralelo
    const [accountRes, materialRes] = await Promise.allSettled([
      accountApi.getAccounts(),
      materialApi.getAllMaterials()
    ])

    if (accountRes.status === 'fulfilled' && accountRes.value.code === 200) {
      accountStore.setAccounts(accountRes.value.data)
    }
    if (materialRes.status === 'fulfilled' && materialRes.value.code === 200) {
      appStore.setMaterials(materialRes.value.data)
    }
  } catch (error) {
    console.error('não consegui carregar os dados do painel:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard {
  .page-header {
    margin-bottom: 20px;

    h1 {
      font-size: 24px;
      color: $text-primary;
      margin: 0;
    }
  }

  .dashboard-content {
    .stat-card {
      height: 140px;
      margin-bottom: 20px;

      .stat-card-content {
        display: flex;
        align-items: center;
        margin-bottom: 15px;

        .stat-icon {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background-color: rgba($primary-color, 0.1);
          display: flex;
          justify-content: center;
          align-items: center;
          margin-right: 15px;

          .el-icon {
            font-size: 30px;
            color: $primary-color;
          }

          &.platform-icon {
            background-color: rgba($success-color, 0.1);

            .el-icon {
              color: $success-color;
            }
          }

          &.content-icon {
            background-color: rgba($info-color, 0.1);

            .el-icon {
              color: $info-color;
            }
          }
        }

        .stat-info {
          .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: $text-primary;
            line-height: 1.2;
          }

          .stat-label {
            font-size: 14px;
            color: $text-secondary;
          }
        }
      }

      .stat-footer {
        border-top: 1px solid $border-lighter;
        padding-top: 10px;

        .stat-detail {
          display: flex;
          justify-content: space-between;
          color: $text-secondary;
          font-size: 13px;

          .el-tag {
            margin-right: 5px;
          }
        }
      }
    }

    .quick-actions {
      margin: 20px 0 30px;

      h2 {
        font-size: 18px;
        margin-bottom: 15px;
        color: $text-primary;
      }

      .action-card {
        height: 160px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.3s;

        &:hover {
          transform: translateY(-5px);
          box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }

        .action-icon {
          width: 50px;
          height: 50px;
          border-radius: 50%;
          background-color: rgba($primary-color, 0.1);
          display: flex;
          justify-content: center;
          align-items: center;
          margin-bottom: 15px;

          .el-icon {
            font-size: 24px;
            color: $primary-color;
          }
        }

        .action-title {
          font-size: 16px;
          font-weight: bold;
          color: $text-primary;
          margin-bottom: 5px;
        }

        .action-desc {
          font-size: 13px;
          color: $text-secondary;
          text-align: center;
        }
      }
    }

    .recent-tasks {
      margin-top: 30px;

      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;

        h2 {
          font-size: 18px;
          color: $text-primary;
          margin: 0;
        }
      }
    }
  }
}
</style>
