<template>
  <div class="account-management">
    <div class="page-header">
      <h1>Contas</h1>
    </div>
    
    <div class="account-tabs">
      <el-tabs v-model="activeTab" class="account-tabs-nav">
        <el-tab-pane label="Todas" name="all">
          <div class="account-list-container">
            <div class="account-search">
              <el-input
                v-model="searchKeyword"
                placeholder="Buscar por nome ou conta"
                prefix-icon="Search"
                clearable
                @clear="handleSearch"
                @input="handleSearch"
              />
              <div class="action-buttons">
                <el-button type="primary" @click="handleAddAccount">adiciona uma conta</el-button>
                <el-button type="info" @click="fetchAccounts" :loading="false">
                  <el-icon :class="{ 'is-loading': appStore.isAccountRefreshing }"><Refresh /></el-icon>
                  <span v-if="appStore.isAccountRefreshing">Atualizando</span>
                </el-button>
              </div>
            </div>
            
            <div v-if="filteredAccounts.length > 0" class="account-list">
              <el-table :data="filteredAccounts" style="width: 100%">
                <el-table-column label="Foto" width="80">
                  <template #default="scope">
                    <el-avatar :src="getDefaultAvatar(scope.row.name)" :size="40" />
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="Nome" width="180" />
                <el-table-column prop="platform" label="Plataforma">
                  <template #default="scope">
                    <el-tag
                      :type="getPlatformTagType(scope.row.platform)"
                      effect="plain"
                    >
                      {{ scope.row.platform }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Estado">
                  <template #default="scope">
                    <el-tag
                      :type="getStatusTagType(scope.row.status)"
                      effect="plain"
                      :class="{'clickable-status': isStatusClickable(scope.row.status)}"
                      @click="handleStatusClick(scope.row)"
                    >
                      <el-icon :class="scope.row.status === 'verificando' ? 'is-loading' : ''" v-if="scope.row.status === 'verificando'">
                        <Loading />
                      </el-icon>
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Ações">
                  <template #default="scope">
                    <el-button size="small" @click="handleEdit(scope.row)">Editar</el-button>
                    <el-button size="small" type="primary" :icon="Download" @click="handleDownloadCookie(scope.row)">Baixar cookies</el-button>
                    <el-button size="small" type="info" :icon="Upload" @click="handleUploadCookie(scope.row)">Enviar cookies</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div v-else class="empty-data">
              <el-empty description="Nenhuma conta ainda" />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="Kuaishou" name="kuaishou">
          <div class="account-list-container">
            <div class="account-search">
              <el-input
                v-model="searchKeyword"
                placeholder="Buscar por nome ou conta"
                prefix-icon="Search"
                clearable
                @clear="handleSearch"
                @input="handleSearch"
              />
              <div class="action-buttons">
                <el-button type="primary" @click="handleAddAccount">adiciona uma conta</el-button>
                <el-button type="info" @click="fetchAccounts" :loading="false">
                  <el-icon :class="{ 'is-loading': appStore.isAccountRefreshing }"><Refresh /></el-icon>
                  <span v-if="appStore.isAccountRefreshing">Atualizando</span>
                </el-button>
              </div>
            </div>
            
            <div v-if="filteredKuaishouAccounts.length > 0" class="account-list">
              <el-table :data="filteredKuaishouAccounts" style="width: 100%">
                <el-table-column label="Foto" width="80">
                  <template #default="scope">
                    <el-avatar :src="getDefaultAvatar(scope.row.name)" :size="40" />
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="Nome" width="180" />
                <el-table-column prop="platform" label="Plataforma">
                  <template #default="scope">
                    <el-tag
                      :type="getPlatformTagType(scope.row.platform)"
                      effect="plain"
                    >
                      {{ scope.row.platform }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Estado">
                  <template #default="scope">
                    <el-tag
                      :type="getStatusTagType(scope.row.status)"
                      effect="plain"
                      :class="{'clickable-status': isStatusClickable(scope.row.status)}"
                      @click="handleStatusClick(scope.row)"
                    >
                      <el-icon :class="scope.row.status === 'verificando' ? 'is-loading' : ''" v-if="scope.row.status === 'verificando'">
                        <Loading />
                      </el-icon>
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Ações">
                  <template #default="scope">
                    <el-button size="small" @click="handleEdit(scope.row)">Editar</el-button>
                    <el-button size="small" type="primary" :icon="Download" @click="handleDownloadCookie(scope.row)">Baixar cookies</el-button>
                    <el-button size="small" type="info" :icon="Upload" @click="handleUploadCookie(scope.row)">Enviar cookies</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div v-else class="empty-data">
              <el-empty description="Nenhuma conta Kuaishou ainda" />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="Douyin" name="douyin">
          <div class="account-list-container">
            <div class="account-search">
              <el-input
                v-model="searchKeyword"
                placeholder="Buscar por nome ou conta"
                prefix-icon="Search"
                clearable
                @clear="handleSearch"
                @input="handleSearch"
              />
              <div class="action-buttons">
                <el-button type="primary" @click="handleAddAccount">adiciona uma conta</el-button>
                <el-button type="info" @click="fetchAccounts" :loading="false">
                  <el-icon :class="{ 'is-loading': appStore.isAccountRefreshing }"><Refresh /></el-icon>
                  <span v-if="appStore.isAccountRefreshing">Atualizando</span>
                </el-button>
              </div>
            </div>
            
            <div v-if="filteredDouyinAccounts.length > 0" class="account-list">
              <el-table :data="filteredDouyinAccounts" style="width: 100%">
                <el-table-column label="Foto" width="80">
                  <template #default="scope">
                    <el-avatar :src="getDefaultAvatar(scope.row.name)" :size="40" />
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="Nome" width="180" />
                <el-table-column prop="platform" label="Plataforma">
                  <template #default="scope">
                    <el-tag
                      :type="getPlatformTagType(scope.row.platform)"
                      effect="plain"
                    >
                      {{ scope.row.platform }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Estado">
                  <template #default="scope">
                    <el-tag
                      :type="getStatusTagType(scope.row.status)"
                      effect="plain"
                      :class="{'clickable-status': isStatusClickable(scope.row.status)}"
                      @click="handleStatusClick(scope.row)"
                    >
                      <el-icon :class="scope.row.status === 'verificando' ? 'is-loading' : ''" v-if="scope.row.status === 'verificando'">
                        <Loading />
                      </el-icon>
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Ações">
                  <template #default="scope">
                    <el-button size="small" @click="handleEdit(scope.row)">Editar</el-button>
                    <el-button size="small" type="primary" :icon="Download" @click="handleDownloadCookie(scope.row)">Baixar cookies</el-button>
                    <el-button size="small" type="info" :icon="Upload" @click="handleUploadCookie(scope.row)">Enviar cookies</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div v-else class="empty-data">
              <el-empty description="Nenhuma conta Douyin ainda" />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="Canal do WeChat" name="channels">
          <div class="account-list-container">
            <div class="account-search">
              <el-input
                v-model="searchKeyword"
                placeholder="Buscar por nome ou conta"
                prefix-icon="Search"
                clearable
                @clear="handleSearch"
                @input="handleSearch"
              />
              <div class="action-buttons">
                <el-button type="primary" @click="handleAddAccount">adiciona uma conta</el-button>
                <el-button type="info" @click="fetchAccounts" :loading="false">
                  <el-icon :class="{ 'is-loading': appStore.isAccountRefreshing }"><Refresh /></el-icon>
                  <span v-if="appStore.isAccountRefreshing">Atualizando</span>
                </el-button>
              </div>
            </div>
            
            <div v-if="filteredChannelsAccounts.length > 0" class="account-list">
              <el-table :data="filteredChannelsAccounts" style="width: 100%">
                <el-table-column label="Foto" width="80">
                  <template #default="scope">
                    <el-avatar :src="getDefaultAvatar(scope.row.name)" :size="40" />
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="Nome" width="180" />
                <el-table-column prop="platform" label="Plataforma">
                  <template #default="scope">
                    <el-tag
                      :type="getPlatformTagType(scope.row.platform)"
                      effect="plain"
                    >
                      {{ scope.row.platform }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Estado">
                  <template #default="scope">
                    <el-tag
                      :type="getStatusTagType(scope.row.status)"
                      effect="plain"
                      :class="{'clickable-status': isStatusClickable(scope.row.status)}"
                      @click="handleStatusClick(scope.row)"
                    >
                      <el-icon :class="scope.row.status === 'verificando' ? 'is-loading' : ''" v-if="scope.row.status === 'verificando'">
                        <Loading />
                      </el-icon>
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Ações">
                  <template #default="scope">
                    <el-button size="small" @click="handleEdit(scope.row)">Editar</el-button>
                    <el-button size="small" type="primary" :icon="Download" @click="handleDownloadCookie(scope.row)">Baixar cookies</el-button>
                    <el-button size="small" type="info" :icon="Upload" @click="handleUploadCookie(scope.row)">Enviar cookies</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div v-else class="empty-data">
              <el-empty description="Nenhuma conta do Canal do WeChat ainda" />
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="Xiaohongshu" name="xiaohongshu">
          <div class="account-list-container">
            <div class="account-search">
              <el-input
                v-model="searchKeyword"
                placeholder="Buscar por nome ou conta"
                prefix-icon="Search"
                clearable
                @clear="handleSearch"
                @input="handleSearch"
              />
              <div class="action-buttons">
                <el-button type="primary" @click="handleAddAccount">adiciona uma conta</el-button>
                <el-button type="info" @click="fetchAccounts" :loading="false">
                  <el-icon :class="{ 'is-loading': appStore.isAccountRefreshing }"><Refresh /></el-icon>
                  <span v-if="appStore.isAccountRefreshing">Atualizando</span>
                </el-button>
              </div>
            </div>
            
            <div v-if="filteredXiaohongshuAccounts.length > 0" class="account-list">
              <el-table :data="filteredXiaohongshuAccounts" style="width: 100%">
                <el-table-column label="Foto" width="80">
                  <template #default="scope">
                    <el-avatar :src="getDefaultAvatar(scope.row.name)" :size="40" />
                  </template>
                </el-table-column>
                <el-table-column prop="name" label="Nome" width="180" />
                <el-table-column prop="platform" label="Plataforma">
                  <template #default="scope">
                    <el-tag
                      :type="getPlatformTagType(scope.row.platform)"
                      effect="plain"
                    >
                      {{ scope.row.platform }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="Estado">
                  <template #default="scope">
                    <el-tag
                      :type="getStatusTagType(scope.row.status)"
                      effect="plain"
                      :class="{'clickable-status': isStatusClickable(scope.row.status)}"
                      @click="handleStatusClick(scope.row)"
                    >
                      <el-icon :class="scope.row.status === 'verificando' ? 'is-loading' : ''" v-if="scope.row.status === 'verificando'">
                        <Loading />
                      </el-icon>
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="Ações">
                  <template #default="scope">
                    <el-button size="small" @click="handleEdit(scope.row)">Editar</el-button>
                    <el-button size="small" type="primary" :icon="Download" @click="handleDownloadCookie(scope.row)">Baixar cookies</el-button>
                    <el-button size="small" type="info" :icon="Upload" @click="handleUploadCookie(scope.row)">Enviar cookies</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            
            <div v-else class="empty-data">
              <el-empty description="Nenhuma conta Xiaohongshu ainda" />
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <!-- janela de criar/editar conta -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? 'adiciona uma conta' : 'Editar conta'"
      width="500px"
      :close-on-click-modal="false"
      :close-on-press-escape="!sseConnecting"
      :show-close="!sseConnecting"
    >
      <el-form :model="accountForm" label-width="80px" :rules="rules" ref="accountFormRef">
        <el-form-item label="Plataforma" prop="platform">
          <el-select 
            v-model="accountForm.platform" 
            placeholder="Escolha a plataforma" 
            style="width: 100%"
            :disabled="dialogType === 'edit' || sseConnecting"
          >
            <el-option label="Kuaishou" value="Kuaishou" />
            <el-option label="Douyin" value="Douyin" />
            <el-option label="Canal do WeChat" value="Canal do WeChat" />
            <el-option label="Xiaohongshu" value="Xiaohongshu" />
          </el-select>
        </el-form-item>
        <el-form-item label="Nome" prop="name">
          <el-input 
            v-model="accountForm.name" 
            placeholder="Digite o nome da conta" 
            :disabled="sseConnecting"
          />
        </el-form-item>
        
        <!-- área do QR code -->
        <div v-if="sseConnecting" class="qrcode-container">
          <div v-if="qrCodeData && !loginStatus" class="qrcode-wrapper">
            <p class="qrcode-tip">Escaneie o QR code com o aplicativo da plataforma para entrar</p>
            <img :src="qrCodeData" alt="QR code de login" class="qrcode-image" />
          </div>
          <div v-else-if="!qrCodeData && !loginStatus" class="loading-wrapper">
            <el-icon class="is-loading"><Refresh /></el-icon>
            <span>Aguarde...</span>
          </div>
          <div v-else-if="loginStatus === '200'" class="success-wrapper">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>Conta adicionada</span>
          </div>
          <div v-else-if="loginStatus === '500'" class="error-wrapper">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>Não consegui adicionar; tente de novo</span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">Cancelar</el-button>
          <el-button 
            type="primary" 
            @click="submitAccountForm" 
            :loading="sseConnecting" 
            :disabled="sseConnecting"
          >
            {{ sseConnecting ? 'Aguarde' : 'Confirmar' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { Refresh, CircleCheckFilled, CircleCloseFilled, Download, Upload, Loading } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { accountApi } from '@/api/account'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { http } from '@/utils/request'

// store das contas
const accountStore = useAccountStore()
// store da aplicação
const appStore = useAppStore()

// aba ativa
const activeTab = ref('all')

// texto da busca
const searchKeyword = ref('')

// busca as contas (rápido, sem verificar)
const fetchAccountsQuick = async () => {
  try {
    const res = await accountApi.getAccounts()
    if (res.code === 200 && res.data) {
      // marca todas as contas como"verificando"
      const accountsWithPendingStatus = res.data.map(account => {
        const updatedAccount = [...account];
        updatedAccount[4] = -1; // -1 estado temporário de verificação
        return updatedAccount;
      });
      accountStore.setAccounts(accountsWithPendingStatus);
    }
  } catch (error) {
    console.error('falha na busca rápida das contas:', error)
  }
}

// busca as contas (com verificação)
const fetchAccounts = async () => {
  if (appStore.isAccountRefreshing) return

  appStore.setAccountRefreshing(true)

  try {
    const res = await accountApi.getValidAccounts()
    if (res.code === 200 && res.data) {
      accountStore.setAccounts(res.data)
      ElMessage.success('contas carregadas')
      // marca a página como visitada
      if (appStore.isFirstTimeAccountManagement) {
        appStore.setAccountManagementVisited()
      }
    } else {
      ElMessage.error('não consegui carregar as contas')
    }
  } catch (error) {
    console.error('não consegui carregar as contas:', error)
    ElMessage.error('não consegui carregar as contas')
  } finally {
    appStore.setAccountRefreshing(false)
  }
}

// verifica todas as contas em segundo plano (com setTimeout, para não travar a tela)
const validateAllAccountsInBackground = async () => {
  // joga a verificação para o próximo ciclo de eventos, para não travar a tela
  setTimeout(async () => {
    try {
      const res = await accountApi.getValidAccounts()
      if (res.code === 200 && res.data) {
        accountStore.setAccounts(res.data)
      }
    } catch (error) {
      console.error('falha ao verificar as contas em segundo plano:', error)
    }
  }, 0)
}

// busca as contas quando a página abre
onMounted(() => {
  // lista rápida (sem verificar) para mostrar na hora
  fetchAccountsQuick()

  // verifica todas as contas em segundo plano
  setTimeout(() => {
    validateAllAccountsInBackground()
  }, 100) // um respiro, para o carregamento rápido aparecer
})

// tipo da etiqueta da plataforma
const getPlatformTagType = (platform) => {
  const typeMap = {
    'Kuaishou': 'success',
    'Douyin': 'danger',
    'Canal do WeChat': 'warning',
    'Xiaohongshu': 'info'
  }
  return typeMap[platform] || 'info'
}

// diz se dá para clicar no estado (só quando está com erro)
const isStatusClickable = (status) => {
  return status === 'com erro'; // só o estado com erro é clicável; verificando não é
}

// tipo da etiqueta de estado
const getStatusTagType = (status) => {
  if (status === 'verificando') {
    return 'info'; // verificandocinza
  } else if (status === 'ok') {
    return 'success'; // okverde
  } else {
    return 'danger'; // vermelho quando inválida
  }
}

// trata o clique no estado
const handleStatusClick = (row) => {
  if (isStatusClickable(row.status)) {
    // dispara o login de novo
    handleReLogin(row)
  }
}

// lista de contas filtrada
const filteredAccounts = computed(() => {
  if (!searchKeyword.value) return accountStore.accounts
  return accountStore.accounts.filter(account =>
    account.name.includes(searchKeyword.value)
  )
})

// contas filtradas por plataforma
const filteredKuaishouAccounts = computed(() => {
  return filteredAccounts.value.filter(account => account.platform === 'Kuaishou')
})

const filteredDouyinAccounts = computed(() => {
  return filteredAccounts.value.filter(account => account.platform === 'Douyin')
})

const filteredChannelsAccounts = computed(() => {
  return filteredAccounts.value.filter(account => account.platform === 'Canal do WeChat')
})

const filteredXiaohongshuAccounts = computed(() => {
  return filteredAccounts.value.filter(account => account.platform === 'Xiaohongshu')
})

// trata a busca
const handleSearch = () => {
  // a busca já é feita por propriedade computada
}

// janelas
const dialogVisible = ref(false)
const dialogType = ref('add') // 'add' ou 'edit'
const accountFormRef = ref(null)

// formulário da conta
const accountForm = reactive({
  id: null,
  name: '',
  platform: '',
  status: 'ok'
})

// regras de validação do formulário
const rules = {
  platform: [{ required: true, message: 'Escolha a plataforma', trigger: 'change' }],
  name: [{ required: true, message: 'Digite o nome da conta', trigger: 'blur' }]
}

// SSEestado da conexão
const sseConnecting = ref(false)
const qrCodeData = ref('')
const loginStatus = ref('')

// adiciona uma conta
const handleAddAccount = () => {
  dialogType.value = 'add'
  Object.assign(accountForm, {
    id: null,
    name: '',
    platform: '',
    status: 'ok'
  })
  // zera o estado do SSE
  sseConnecting.value = false
  qrCodeData.value = ''
  loginStatus.value = ''
  dialogVisible.value = true
}

// Editar conta
const handleEdit = (row) => {
  dialogType.value = 'edit'
  Object.assign(accountForm, {
    id: row.id,
    name: row.name,
    platform: row.platform,
    status: row.status
  })
  dialogVisible.value = true
}

// remove uma conta
const handleDelete = (row) => {
  ElMessageBox.confirm(
    `Remover a conta ${row.name} ?`,
    'Atenção',
    {
      confirmButtonText: 'Confirmar',
      cancelButtonText: 'Cancelar',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        // chama a API para remover a conta
        const response = await accountApi.deleteAccount(row.id)

        if (response.code === 200) {
          // tira a conta da store
          accountStore.deleteAccount(row.id)
          ElMessage({
            type: 'success',
            message: 'Conta removida',
          })
        } else {
          ElMessage.error(response.msg || 'Não consegui remover')
        }
      } catch (error) {
        console.error('remove uma contafalhou:', error)
        ElMessage.error('remove uma contafalhou')
      }
    })
    .catch(() => {
      // remoção cancelada
    })
}

// baixa o arquivo de cookies
const handleDownloadCookie = (row) => {
  // baixa o arquivo de cookies do backend
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'
  const downloadUrl = `${baseUrl}/downloadCookie?filePath=${encodeURIComponent(row.filePath)}`

  // cria um link escondido para disparar o download
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = `${row.name}_cookie.json`
  link.target = '_blank'
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// envia o arquivo de cookies
const handleUploadCookie = (row) => {
  // cria um campo de arquivo escondido
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.style.display = 'none'
  document.body.appendChild(input)

  input.onchange = async (event) => {
    const file = event.target.files[0]
    if (!file) return

    // confere o tipo do arquivo
    if (!file.name.endsWith('.json')) {
      ElMessage.error('Escolha um arquivo de cookies em JSON')
      document.body.removeChild(input)
      return
    }

    try {
      // monta o FormData
      const formData = new FormData()
      formData.append('file', file)
      formData.append('id', row.id)
      formData.append('platform', row.platform)

      // envia pelo mesmo wrapper http do resto da aplicação
      const result = await http.upload('/uploadCookie', formData)

      ElMessage.success('CookieArquivo enviado')
      // atualiza a lista para mostrar a mudança
      fetchAccounts()
    } catch (error) {
      ElMessage.error('CookieFalha ao enviar o arquivo')
    } finally {
      document.body.removeChild(input)
    }
  }

  input.click()
}

// entra de novo na conta
const handleReLogin = (row) => {
  // preenche o formulário
  dialogType.value = 'edit'
  Object.assign(accountForm, {
    id: row.id,
    name: row.name,
    platform: row.platform,
    status: row.status
  })

  // zera o estado do SSE
  sseConnecting.value = false
  qrCodeData.value = ''
  loginStatus.value = ''

  // abre a janela
  dialogVisible.value = true

  // começa o login na hora
  setTimeout(() => {
    connectSSE(row.platform, row.name)
  }, 300)
}

// foto padrão
const getDefaultAvatar = (name) => {
  // foto padrão simples; a cor pode sair do nome de usuário
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random`
}

// SSEobjeto do EventSource
let eventSource = null

// fecha a conexão SSE
const closeSSEConnection = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

// abre a conexão SSE
const connectSSE = (platform, name) => {
  // fecha qualquer conexão aberta
  closeSSEConnection()

  // define o estado da conexão
  sseConnecting.value = true
  qrCodeData.value = ''
  loginStatus.value = ''

  // número do tipo da plataforma
  const platformTypeMap = {
    'Xiaohongshu': '1',
    'Canal do WeChat': '2',
    'Douyin': '3',
    'Kuaishou': '4'
  }

  const type = platformTypeMap[platform] || '1'

  // cria a conexão SSE
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'
  const url = `${baseUrl}/login?type=${type}&id=${encodeURIComponent(name)}`

  eventSource = new EventSource(url)

  // escuta as mensagens
  eventSource.onmessage = (event) => {
    const data = event.data

    // sem QR code ainda e com dado longo: trata como QR code
    if (!qrCodeData.value && data.length > 100) {
      try {
        if (data.startsWith('data:image')) {
          qrCodeData.value = data
        } else {
          qrCodeData.value = `data:image/png;base64,${data}`
        }
      } catch (error) {
        // erro ao tratar o QR code
      }
    }
    // se veio um código de estado
    else if (data === '200' || data === '500') {
      loginStatus.value = data

      // se o login deu certo
      if (data === '200') {
        setTimeout(() => {
          // fecha a conexão
          closeSSEConnection()

          // 1segundos depois fecha a janela e atualiza
          setTimeout(() => {
            dialogVisible.value = false
            sseConnecting.value = false

            // mensagem diferente quando é um login repetido
            ElMessage.success(dialogType.value === 'edit' ? 'Login refeito' : 'Conta adicionada')

            // mostra o aviso de conta atualizada
            ElMessage({
              type: 'info',
              message: 'Sincronizando os dados da conta...',
              duration: 0
            })

            // dispara a atualização
            fetchAccounts().then(() => {
              // fecha o aviso quando a atualização terminar
              ElMessage.closeAll()
              ElMessage.success('Dados da conta atualizados')
            })
          }, 1000)
        }, 1000)
      } else {
        // login falhou, fechando a conexão
        closeSSEConnection()

        // 2segundos depois zera o estado para tentar de novo
        setTimeout(() => {
          sseConnecting.value = false
          qrCodeData.value = ''
          loginStatus.value = ''
        }, 2000)
      }
    }
  }

  // escuta os erros
  eventSource.onerror = (error) => {
    console.error('SSEerro de conexão:', error)
    ElMessage.error('Não consegui falar com o servidor; tente de novo')
    closeSSEConnection()
    sseConnecting.value = false
  }
}

// envia o formulário da conta
const submitAccountForm = () => {
  accountFormRef.value.validate(async (valid) => {
    if (valid) {
      if (dialogType.value === 'add') {
        // abre a conexão SSE
        connectSSE(accountForm.platform, accountForm.name)
      } else {
        // fluxo de edição da conta
        try {
          // converte o nome da plataforma no número do tipo
          const platformTypeMap = {
            'Xiaohongshu': 1,
            'Canal do WeChat': 2,
            'Douyin': 3,
            'Kuaishou': 4
          };
          const type = platformTypeMap[accountForm.platform] || 1;

          const res = await accountApi.updateAccount({
            id: accountForm.id,
            type: type,
            userName: accountForm.name
          })
          if (res.code === 200) {
            // atualiza a conta na store
            const updatedAccount = {
              id: accountForm.id,
              name: accountForm.name,
              platform: accountForm.platform,
              status: accountForm.status // Keep the existing status
            };
            accountStore.updateAccount(accountForm.id, updatedAccount)
            ElMessage.success('Conta atualizada')
            dialogVisible.value = false
            // atualiza a lista de contas
            fetchAccounts()
          } else {
            ElMessage.error(res.msg || 'atualiza uma contafalhou')
          }
        } catch (error) {
          console.error('atualiza uma contafalhou:', error)
          ElMessage.error('atualiza uma contafalhou')
        }
      }
    } else {
      return false
    }
  })
}

// fecha o SSE antes de desmontar o componente
onBeforeUnmount(() => {
  closeSSEConnection()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.account-management {
  .page-header {
    margin-bottom: 20px;
    
    h1 {
      font-size: 24px;
      color: $text-primary;
      margin: 0;
    }
  }
  
  .account-tabs {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: $box-shadow-light;
    
    .account-tabs-nav {
      padding: 20px;
    }
  }
  
  .account-list-container {
    .account-search {
      display: flex;
      justify-content: space-between;
      margin-bottom: 20px;
      
      .el-input {
        width: 300px;
      }
      
      .action-buttons {
        display: flex;
        gap: 10px;
        
        .el-icon.is-loading {
          animation: rotate 1s linear infinite;
        }
      }
    }
    
    .account-list {
      margin-bottom: 20px;
    }
    
    .empty-data {
      padding: 40px 0;
    }
  }
  
  // estilo da caixa do QR code
  .clickable-status {
    cursor: pointer;
    transition: all 0.3s;

    &:hover {
      transform: scale(1.05);
      box-shadow: 0 0 8px rgba(0, 0, 0, 0.15);
    }
  }

  .qrcode-container {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 250px;
    
    .qrcode-wrapper {
      text-align: center;
      
      .qrcode-tip {
        margin-bottom: 15px;
        color: #606266;
      }
      
      .qrcode-image {
        max-width: 200px;
        max-height: 200px;
        border: 1px solid #ebeef5;
        background-color: black;
      }
    }
    
    .loading-wrapper, .success-wrapper, .error-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      
      .el-icon {
        font-size: 48px;
        
        &.is-loading {
          animation: rotate 1s linear infinite;
        }
      }
      
      span {
        font-size: 16px;
      }
    }
    
    .success-wrapper .el-icon {
      color: #67c23a;
    }
    
    .error-wrapper .el-icon {
      color: #f56c6c;
    }
  }
}
</style>