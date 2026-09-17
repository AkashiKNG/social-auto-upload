<template>
  <div class="publish-center">
    <!-- Tabárea das abas -->
    <div class="tab-management">
      <div class="tab-header">
        <div class="tab-list">
          <div 
            v-for="tab in tabs" 
            :key="tab.name"
            :class="['tab-item', { active: activeTab === tab.name }]"
            @click="activeTab = tab.name"
          >
            <span>{{ tab.label }}</span>
            <el-icon 
              v-if="tabs.length > 1"
              class="close-icon" 
              @click.stop="removeTab(tab.name)"
            >
              <Close />
            </el-icon>
          </div>
        </div>
        <div class="tab-actions">
          <el-button 
            type="primary" 
            size="small" 
            @click="addTab"
            class="add-tab-btn"
          >
            <el-icon><Plus /></el-icon>
            Nova aba
          </el-button>
          <el-button 
            type="success" 
            size="small" 
            @click="batchPublish"
            :loading="batchPublishing"
            class="batch-publish-btn"
          >
            Publicar em lote
          </el-button>
        </div>
      </div>
    </div>

    <!-- área de conteúdo -->
    <div class="publish-content">
      <div class="tab-content-wrapper">
        <div 
          v-for="tab in tabs" 
          :key="tab.name"
          v-show="activeTab === tab.name"
          class="tab-content"
        >
          <!-- aviso do estado da publicação -->
          <div v-if="tab.publishStatus" class="publish-status">
            <el-alert
              :title="tab.publishStatus.message"
              :type="tab.publishStatus.type"
              :closable="false"
              show-icon
            />
          </div>

          <!-- Vídeosárea de envio -->
          <div class="upload-section">
            <h3>Vídeos</h3>
            <div class="upload-options">
              <el-button type="primary" @click="showUploadOptions(tab)" class="upload-btn">
                <el-icon><Upload /></el-icon>
                Enviar vídeo
              </el-button>
            </div>
            
            <!-- lista de arquivos enviados -->
            <div v-if="tab.fileList.length > 0" class="uploaded-files">
              <h4>Arquivos enviados:</h4>
              <div class="file-list">
                <div v-for="(file, index) in tab.fileList" :key="index" class="file-item">
                  <el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
                  <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }}MB</span>
                  <el-button type="danger" size="small" @click="removeFile(tab, index)">Excluir</el-button>
                </div>
              </div>
            </div>
          </div>

          <!-- janela com as opções de envio -->
          <el-dialog
            v-model="uploadOptionsVisible"
            title="Como quer enviar?"
            width="400px"
            class="upload-options-dialog"
          >
            <div class="upload-options-content">
              <el-button type="primary" @click="selectLocalUpload" class="option-btn">
                <el-icon><Upload /></el-icon>
                Do computador
              </el-button>
              <el-button type="success" @click="selectMaterialLibrary" class="option-btn">
                <el-icon><Folder /></el-icon>
                Biblioteca
              </el-button>
            </div>
          </el-dialog>

          <!-- janela de envio do computador -->
          <el-dialog
            v-model="localUploadVisible"
            title="Do computador"
            width="600px"
            class="local-upload-dialog"
          >
            <el-upload
              class="video-upload"
              drag
              :auto-upload="true"
              :action="`${apiBaseUrl}/upload`"
              :on-success="(response, file) => handleUploadSuccess(response, file, currentUploadTab)"
              :on-error="handleUploadError"
              multiple
              accept="video/*"
              :headers="authHeaders"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                Arraste o vídeo até aqui, ou<em>clique para enviar</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  Aceita MP4, AVI e outros formatos de vídeo; dá para enviar vários
                </div>
              </template>
            </el-upload>
          </el-dialog>

          <!-- janela de progresso da publicação em lote -->
          <el-dialog
            v-model="batchPublishDialogVisible"
            title="Progresso da publicação em lote"
            width="500px"
            :close-on-click-modal="false"
            :close-on-press-escape="false"
            :show-close="false"
          >
            <div class="publish-progress">
              <el-progress 
                :percentage="publishProgress"
                :status="publishProgress === 100 ? 'success' : ''"
              />
              <div v-if="currentPublishingTab" class="current-publishing">
                Publicando:{{ currentPublishingTab.label }}
              </div>
              
              <!-- lista de resultados -->
              <div class="publish-results" v-if="publishResults.length > 0">
                <div 
                  v-for="(result, index) in publishResults" 
                  :key="index"
                  :class="['result-item', result.status]"
                >
                  <el-icon v-if="result.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
                  <el-icon v-else><InfoFilled /></el-icon>
                  <span class="label">{{ result.label }}</span>
                  <span class="message">{{ result.message }}</span>
                </div>
              </div>
            </div>
            
            <template #footer>
              <div class="dialog-footer">
                <el-button 
                  @click="cancelBatchPublish" 
                  :disabled="publishProgress === 100"
                >
                  Cancelar publicação
                </el-button>
                <el-button 
                  type="primary" 
                  @click="batchPublishDialogVisible = false"
                  v-if="publishProgress === 100"
                >
                  Fechar
                </el-button>
              </div>
            </template>
          </el-dialog>

          <!-- janela da biblioteca de materiais -->
          <el-dialog
            v-model="materialLibraryVisible"
            title="Escolher materiais"
            width="800px"
            class="material-library-dialog"
          >
            <div class="material-library-content">
              <el-checkbox-group v-model="selectedMaterials">
                <div class="material-list">
                  <div
                    v-for="material in materials"
                    :key="material.id"
                    class="material-item"
                  >
                    <el-checkbox :label="material.id" class="material-checkbox">
                      <div class="material-info">
                        <div class="material-name">{{ material.filename }}</div>
                        <div class="material-details">
                          <span class="file-size">{{ material.filesize }}MB</span>
                          <span class="upload-time">{{ material.upload_time }}</span>
                        </div>
                      </div>
                    </el-checkbox>
                  </div>
                </div>
              </el-checkbox-group>
            </div>
            <template #footer>
              <div class="dialog-footer">
                <el-button @click="materialLibraryVisible = false">Cancelar</el-button>
                <el-button type="primary" @click="confirmMaterialSelection">Confirmar</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- escolha de contas -->
          <div class="account-section">
            <h3>Contas</h3>
            <div class="account-display">
              <div class="selected-accounts">
                <el-tag
                  v-for="(account, index) in tab.selectedAccounts"
                  :key="index"
                  closable
                  @close="removeAccount(tab, index)"
                  class="account-tag"
                >
                  {{ getAccountDisplayName(account) }}
                </el-tag>
              </div>
              <el-button 
                type="primary" 
                plain 
                @click="openAccountDialog(tab)"
                class="select-account-btn"
              >
                Escolher contas
              </el-button>
            </div>
          </div>

          <!-- janela de escolha de contas -->
          <el-dialog
            v-model="accountDialogVisible"
            title="Escolher contas"
            width="600px"
            class="account-dialog"
          >
            <div class="account-dialog-content">
              <el-checkbox-group v-model="tempSelectedAccounts">
                <div class="account-list">
                  <el-checkbox
                    v-for="account in availableAccounts"
                    :key="account.id"
                    :label="account.id"
                    class="account-item"
                  >
                    <div class="account-info">
                      <span class="account-name">{{ account.name }}</span>                      
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="accountDialogVisible = false">Cancelar</el-button>
                <el-button type="primary" @click="confirmAccountSelection">Confirmar</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- escolha da plataforma -->
          <div class="platform-section">
            <h3>Plataforma</h3>
            <el-radio-group v-model="tab.selectedPlatform" class="platform-radios">
              <el-radio 
                v-for="platform in platforms" 
                :key="platform.key"
                :label="platform.key"
                class="platform-radio"
              >
                {{ platform.name }}
              </el-radio>
            </el-radio-group>
          </div>

          <!-- declaração de conteúdo original -->
          <div class="original-section">
            <el-checkbox
              v-model="tab.isOriginal"
              label="Conteúdo original"
              class="original-checkbox"
            />
          </div>

          <!-- opção de rascunho (só aparece no Canal do WeChat) -->
          <div v-if="tab.selectedPlatform === 2" class="draft-section">
            <el-checkbox
              v-model="tab.isDraft"
              label="Canal do WeChatSó salvar rascunho(publicar pelo celular)"
              class="draft-checkbox"
            />
          </div>

          <!-- Etiquetas (só aparece no Douyin) -->
          <div v-if="tab.selectedPlatform === 3" class="product-section">
            <h3>Link do produto</h3>
            <el-input
              v-model="tab.productTitle"
              type="text"
              :rows="1"
              placeholder="Nome do produto"
              maxlength="200"
              class="product-name-input"
            />
            <el-input
              v-model="tab.productLink"
              type="text"
              :rows="1"
              placeholder="Link do produto"
              maxlength="200"
              class="product-link-input"
            />
          </div>

          <!-- campo do título -->
          <div class="title-section">
            <h3>Título</h3>
            <el-input
              v-model="tab.title"
              type="textarea"
              :rows="3"
              placeholder="Digite o título"
              maxlength="100"
              show-word-limit
              class="title-input"
            />
          </div>

          <!-- campo de hashtags -->
          <div class="topic-section">
            <h3>Hashtags</h3>
            <div class="topic-display">
              <div class="selected-topics">
                <el-tag
                  v-for="(topic, index) in tab.selectedTopics"
                  :key="index"
                  closable
                  @close="removeTopic(tab, index)"
                  class="topic-tag"
                >
                  #{{ topic }}
                </el-tag>
              </div>
              <el-button 
                type="primary" 
                plain 
                @click="openTopicDialog(tab)"
                class="select-topic-btn"
              >
                Hashtags
              </el-button>
            </div>
          </div>

          <!-- janela de hashtags -->
          <el-dialog
            v-model="topicDialogVisible"
            title="Hashtags"
            width="600px"
            class="topic-dialog"
          >
            <div class="topic-dialog-content">
              <!-- hashtag personalizada -->
              <div class="custom-topic-input">
                <el-input
                  v-model="customTopic"
                  placeholder="Digite uma hashtag"
                  class="custom-input"
                >
                  <template #prepend>#</template>
                </el-input>
                <el-button type="primary" @click="addCustomTopic">Adicionar</el-button>
              </div>

              <!-- Sugestões -->
              <div class="recommended-topics">
                <h4>Sugestões</h4>
                <div class="topic-grid">
                  <el-button
                    v-for="topic in recommendedTopics"
                    :key="topic"
                    :type="currentTab?.selectedTopics?.includes(topic) ? 'primary' : 'default'"
                    @click="toggleRecommendedTopic(topic)"
                    class="topic-btn"
                  >
                    {{ topic }}
                  </el-button>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="topicDialogVisible = false">Cancelar</el-button>
                <el-button type="primary" @click="confirmTopicSelection">Confirmar</el-button>
              </div>
            </template>
          </el-dialog>

          <!-- publicação agendada -->
          <div class="schedule-section">
            <h3>Agendar</h3>
            <div class="schedule-controls">
              <el-switch
                v-model="tab.scheduleEnabled"
                active-text="Agendar"
                inactive-text="Publicar agora"
              />
              <div v-if="tab.scheduleEnabled" class="schedule-settings">
                <div class="schedule-item">
                  <span class="label">Vídeos por dia:</span>
                  <el-select v-model="tab.videosPerDay" placeholder="Quantos por dia">
                    <el-option
                      v-for="num in 55"
                      :key="num"
                      :label="num"
                      :value="num"
                    />
                  </el-select>
                </div>
                <div class="schedule-item">
                  <span class="label">Horários:</span>
                  <el-time-select
                    v-for="(time, index) in tab.dailyTimes"
                    :key="index"
                    v-model="tab.dailyTimes[index]"
                    start="00:00"
                    step="00:30"
                    end="23:30"
                    placeholder="Escolha o horário"
                  />
                  <el-button
                    v-if="tab.dailyTimes.length < tab.videosPerDay"
                    type="primary"
                    size="small"
                    @click="tab.dailyTimes.push('10:00')"
                  >
                    Adicionar horário
                  </el-button>
                </div>
                <div class="schedule-item">
                  <span class="label">Começar em:</span>
                  <el-select v-model="tab.startDays" placeholder="Escolha o dia">
                    <el-option label="Amanhã" :value="0" />
                    <el-option label="Depois de amanhã" :value="1" />
                  </el-select>
                </div>
              </div>
            </div>
          </div>

          <!-- botões -->
          <div class="action-buttons">
            <el-button size="small" @click="cancelPublish(tab)">Cancelar</el-button>
            <el-button
              size="small"
              type="primary"
              @click="confirmPublish(tab)"
              :loading="tab.publishing || false"
            >
              {{ tab.publishing ? 'Publicando...' : 'Publicar' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { Upload, Plus, Close, Folder } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { http } from '@/utils/request'

// API base URL
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

// Authorization headers
const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// aba ativa
const activeTab = ref('tab1')

// tabcontador
let tabCounter = 1

// store da aplicação
const appStore = useAppStore()

// estado do envio
const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)

// estado da publicação em lote
const batchPublishing = ref(false)
const batchPublishMessage = ref('')
const batchPublishType = ref('info')

// plataformas, na ordem do campo type do backend
const platforms = [
  { key: 3, name: 'Douyin' },
  { key: 4, name: 'Kuaishou' },
  { key: 2, name: 'Canal do WeChat' },
  { key: 1, name: 'Xiaohongshu' }
]

const defaultTabInit = {
  name: 'tab1',
  label: 'Publicação 1',
  fileList: [], // arquivos devolvidos pelo backend
  displayFileList: [], // lista de arquivos exibida
  selectedAccounts: [], // ids das contas escolhidas
  selectedPlatform: 1, // plataforma escolhida (só uma)
  title: '',
  productLink: '', // Link do produto
  productTitle: '', // nome do produto
  selectedTopics: [], // lista de hashtags (sem o #)
  scheduleEnabled: false, // liga/desliga o agendamento
  videosPerDay: 1, // quantos vídeos por dia
  dailyTimes: ['10:00'], // horários de publicação de cada dia
  startDays: 0, // dias a partir de hoje: 0 = amanhã, 1 = depois de amanhã
  publishStatus: null, // estado da publicação (mensagem e tipo)
  publishing: false, // estado da publicação, usado no loading do botão
  isDraft: false, // salvar como rascunho (só no Canal do WeChat)
  isOriginal: false // marcar como conteúdo original
}

// helper to create a fresh deep-copied tab from defaultTabInit
const makeNewTab = () => {
  // prefer structuredClone when available (newer browsers/node), fallback to JSON
  try {
    return typeof structuredClone === 'function' ? structuredClone(defaultTabInit) : JSON.parse(JSON.stringify(defaultTabInit))
  } catch (e) {
    return JSON.parse(JSON.stringify(defaultTabInit))
  }
}

// tabdados das abas (começa com uma) (use deep copy to avoid shared refs)
const tabs = reactive([
  makeNewTab()
])

// estado das contas
const accountDialogVisible = ref(false)
const tempSelectedAccounts = ref([])
const currentTab = ref(null)

// store das contas
const accountStore = useAccountStore()

// contas disponíveis na plataforma escolhida
const availableAccounts = computed(() => {
  const platformMap = {
    3: 'Douyin',
    2: 'Canal do WeChat',
    1: 'Xiaohongshu',
    4: 'Kuaishou'
  }
  const currentPlatform = currentTab.value ? platformMap[currentTab.value.selectedPlatform] : null
  return currentPlatform ? accountStore.accounts.filter(acc => acc.platform === currentPlatform) : []
})

// estado das hashtags
const topicDialogVisible = ref(false)
const customTopic = ref('')

// hashtags sugeridas
const recommendedTopics = [
  'jogos', 'cinema', 'música', 'comida', 'viagem', 'cultura',
  'tecnologia', 'estilo de vida', 'entretenimento', 'esportes', 'educação', 'arte',
  'saúde', 'moda', 'beleza', 'fotografia', 'pets', 'carros'
]

// adiciona uma aba
const addTab = () => {
  tabCounter++
  const newTab = makeNewTab()
  newTab.name = `tab${tabCounter}`
  newTab.label = `Publicar${tabCounter}`
  tabs.push(newTab)
  activeTab.value = newTab.name
}

// remove a aba
const removeTab = (tabName) => {
  const index = tabs.findIndex(tab => tab.name === tabName)
  if (index > -1) {
    tabs.splice(index, 1)
    // se a aba removida era a ativa, volta para a primeira
    if (activeTab.value === tabName && tabs.length > 0) {
      activeTab.value = tabs[0].name
    }
  }
}

// arquivo enviado com sucesso
const handleUploadSuccess = (response, file, tab) => {
  if (response.code === 200) {
    // caminho do arquivo
    const filePath = response.data.path || response.data
    // tira o nome do arquivo do caminho
    const filename = filePath.split('/').pop()
    
    // guarda o arquivo em fileList, com caminho e o resto das informações
    const fileInfo = {
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename), // monta a URL de pré-visualização com getMaterialPreviewUrl
      path: filePath,
      size: file.size,
      type: file.type
    }
    
    // adiciona à lista de arquivos
    tab.fileList.push(fileInfo)
    
    // atualiza a lista exibida
    tab.displayFileList = [...tab.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
    
    ElMessage.success('Arquivo enviado')
  } else {
    ElMessage.error(response.msg || 'Falha no envio')
  }
}

// falha no envio do arquivo
const handleUploadError = (error) => {
  ElMessage.error('Falha ao enviar o arquivo')
}

// remove um arquivo enviado
const removeFile = (tab, index) => {
  // tira da lista de arquivos
  tab.fileList.splice(index, 1)
  
  // atualiza a lista exibida
  tab.displayFileList = [...tab.fileList.map(item => ({
    name: item.name,
    url: item.url
  }))]
  
  ElMessage.success('Arquivo removido')
}

// funções das hashtags
// abre a janela de hashtags
const openTopicDialog = (tab) => {
  currentTab.value = tab
  topicDialogVisible.value = true
}

// adiciona a hashtag digitada
const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning('Digite a hashtag')
    return
  }
  if (currentTab.value && !currentTab.value.selectedTopics.includes(customTopic.value.trim())) {
    currentTab.value.selectedTopics.push(customTopic.value.trim())
    customTopic.value = ''
    ElMessage.success('Hashtag adicionada')
  } else {
    ElMessage.warning('Essa hashtag já está na lista')
  }
}

// liga/desliga uma hashtag sugerida
const toggleRecommendedTopic = (topic) => {
  if (!currentTab.value) return
  
  const index = currentTab.value.selectedTopics.indexOf(topic)
  if (index > -1) {
    currentTab.value.selectedTopics.splice(index, 1)
  } else {
    currentTab.value.selectedTopics.push(topic)
  }
}

// remove a hashtag
const removeTopic = (tab, index) => {
  tab.selectedTopics.splice(index, 1)
}

// confirma as hashtags
const confirmTopicSelection = () => {
  topicDialogVisible.value = false
  customTopic.value = ''
  currentTab.value = null
  ElMessage.success('Hashtags atualizadas')
}

// escolha de contas
// abre a janela de contas
const openAccountDialog = (tab) => {
  currentTab.value = tab
  tempSelectedAccounts.value = [...tab.selectedAccounts]
  accountDialogVisible.value = true
}

// confirma as contas
const confirmAccountSelection = () => {
  if (currentTab.value) {
    currentTab.value.selectedAccounts = [...tempSelectedAccounts.value]
  }
  accountDialogVisible.value = false
  currentTab.value = null
  ElMessage.success('Contas escolhidas')
}

// remove a conta escolhida
const removeAccount = (tab, index) => {
  tab.selectedAccounts.splice(index, 1)
}

// nome da conta para exibir
const getAccountDisplayName = (accountId) => {
  const account = accountStore.accounts.find(acc => acc.id === accountId)
  return account ? account.name : accountId
}

// Cancelar publicação
const cancelPublish = (tab) => {
  ElMessage.info('Publicação cancelada')
}

// confirma a publicação
const confirmPublish = async (tab) => {
  // evita clique repetido
  if (tab.publishing) {
    throw new Error('Publicando, aguarde...')
  }

  tab.publishing = true // marca a publicação como em andamento

  // validação dos dados
  if (tab.fileList.length === 0) {
    ElMessage.error('Envie um vídeo primeiro')
    tab.publishing = false
    throw new Error('Envie um vídeo primeiro')
  }
  if (!tab.title.trim()) {
    ElMessage.error('Digite o título')
    tab.publishing = false
    throw new Error('Digite o título')
  }
  if (!tab.selectedPlatform) {
    ElMessage.error('Escolha a plataforma')
    tab.publishing = false
    throw new Error('Escolha a plataforma')
  }
  if (tab.selectedAccounts.length === 0) {
    ElMessage.error('Escolha as contas')
    tab.publishing = false
    throw new Error('Escolha as contas')
  }

  // monta os dados no formato da API do backend
  const publishData = {
    type: tab.selectedPlatform,
    title: tab.title,
    tags: tab.selectedTopics, // lista de hashtags sem o #
    fileList: tab.fileList.map(file => file.path), // manda só o caminho do arquivo
    accountList: tab.selectedAccounts.map(accountId => {
      const account = accountStore.accounts.find(acc => acc.id === accountId)
      return account ? account.filePath : accountId
    }), // manda o caminho do arquivo de cada conta
    enableTimer: tab.scheduleEnabled ? 1 : 0,
    videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
    dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
    startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
    category: tab.isOriginal ? 1 : 0, // 1 = conteúdo original, 0 = não original
    productLink: tab.productLink.trim() || '',
    productTitle: tab.productTitle.trim() || '',
    isDraft: tab.isDraft
  }

  // chama a API de publicação (pelo wrapper http)
  try {
    const data = await http.post('/postVideo', publishData)
    tab.publishStatus = {
      message: 'Publicado',
      type: 'success'
    }
    // limpa os dados da aba atual
    tab.fileList = []
    tab.displayFileList = []
    tab.title = ''
    tab.selectedTopics = []
    tab.selectedAccounts = []
    tab.scheduleEnabled = false
  } catch (error) {
    console.error('erro na publicação:', error)
    tab.publishStatus = {
      message: `Falha na publicação: ${error.message || 'confira a conexão'}`,
      type: 'error'
    }
    throw error
  } finally {
    tab.publishing = false
  }
}

// mostra as opções de envio
const showUploadOptions = (tab) => {
  currentUploadTab.value = tab
  uploadOptionsVisible.value = true
}

// envio do computador
const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

// escolha na biblioteca
const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false
  
  // se a biblioteca está vazia, busca os materiais
  if (materials.value.length === 0) {
    try {
      const response = await materialApi.getAllMaterials()
      if (response.code === 200) {
        appStore.setMaterials(response.data)
      } else {
        ElMessage.error('Não consegui carregar os materiais')
        return
      }
    } catch (error) {
      console.error('Erro ao carregar os materiais:', error)
      ElMessage.error('Não consegui carregar os materiais')
      return
    }
  }
  
  selectedMaterials.value = []
  materialLibraryVisible.value = true
}

// confirma os materiais escolhidos
const confirmMaterialSelection = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('Escolha pelo menos um material')
    return
  }
  
  if (currentUploadTab.value) {
    // põe os materiais escolhidos na lista da aba atual
    selectedMaterials.value.forEach(materialId => {
      const material = materials.value.find(m => m.id === materialId)
      if (material) {
        const fileInfo = {
          name: material.filename,
          url: materialApi.getMaterialPreviewUrl(material.file_path.split('/').pop()),
          path: material.file_path,
          size: material.filesize * 1024 * 1024, // converte para bytes
          type: 'video/mp4'
        }
        
        // vê se o arquivo já está na lista
        const exists = currentUploadTab.value.fileList.some(file => file.path === fileInfo.path)
        if (!exists) {
          currentUploadTab.value.fileList.push(fileInfo)
        }
      }
    })
    
    // atualiza a lista exibida
    currentUploadTab.value.displayFileList = [...currentUploadTab.value.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
  }
  
  const addedCount = selectedMaterials.value.length
  materialLibraryVisible.value = false
  selectedMaterials.value = []
  currentUploadTab.value = null
  ElMessage.success(`${addedCount} material(is) adicionado(s)`)
}

// estado da janela de publicação em lote
const batchPublishDialogVisible = ref(false)
const currentPublishingTab = ref(null)
const publishProgress = ref(0)
const publishResults = ref([])
const isCancelled = ref(false)

// cancela a publicação em lote
const cancelBatchPublish = () => {
  isCancelled.value = true
  ElMessage.info('Cancelando a publicação...')
}

// publicação em lote
const batchPublish = async () => {
  if (batchPublishing.value) return
  
  batchPublishing.value = true
  currentPublishingTab.value = null
  publishProgress.value = 0
  publishResults.value = []
  isCancelled.value = false
  batchPublishDialogVisible.value = true
  
  try {
    for (let i = 0; i < tabs.length; i++) {
      if (isCancelled.value) {
        publishResults.value.push({
          label: tabs[i].label,
          status: 'cancelled',
          message: 'cancelada'
        })
        continue
      }

      const tab = tabs[i]
      currentPublishingTab.value = tab
      publishProgress.value = Math.floor((i / tabs.length) * 100)
      
      try {
        await confirmPublish(tab)
        publishResults.value.push({
          label: tab.label,
          status: 'success',
          message: 'Publicado'
        })
      } catch (error) {
        publishResults.value.push({
          label: tab.label,
          status: 'error',
          message: error.message
        })
        // não sai na hora: continua mostrando o resultado
      }
    }
    
    publishProgress.value = 100
    
    // conta os resultados
    const successCount = publishResults.value.filter(r => r.status === 'success').length
    const failCount = publishResults.value.filter(r => r.status === 'error').length
    const cancelCount = publishResults.value.filter(r => r.status === 'cancelled').length
    
    if (isCancelled.value) {
      ElMessage.warning(`Publicação cancelada: ${successCount} com sucesso, ${failCount} com falha, ${cancelCount} não executadas`)
    } else if (failCount > 0) {
      ElMessage.error(`Publicação concluída: ${successCount} com sucesso, ${failCount} com falha`)
    } else {
      ElMessage.success('Todas as abas publicadas')
      setTimeout(() => {
        batchPublishDialogVisible.value = false
      }, 1000)
    }
    
  } catch (error) {
    console.error('erro na publicação em lote:', error)
    ElMessage.error('Erro na publicação em lote; tente de novo')
  } finally {
    batchPublishing.value = false
    isCancelled.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-center {
  display: flex;
  flex-direction: column;
  height: 100%;
  
  // Tabárea das abas
  .tab-management {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
    padding: 15px 20px;
    
    .tab-header {
      display: flex;
      align-items: flex-start;
      gap: 15px;
      
      .tab-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        flex: 1;
        min-width: 0;
        
        .tab-item {
           display: flex;
           align-items: center;
           gap: 6px;
           padding: 6px 12px;
           background-color: #f5f7fa;
           border: 1px solid #dcdfe6;
           border-radius: 4px;
           cursor: pointer;
           transition: all 0.3s;
           font-size: 14px;
           height: 32px;
           
           &:hover {
             background-color: #ecf5ff;
             border-color: #b3d8ff;
           }
           
           &.active {
             background-color: #409eff;
             border-color: #409eff;
             color: #fff;
             
             .close-icon {
               color: #fff;
               
               &:hover {
                 background-color: rgba(255, 255, 255, 0.2);
               }
             }
           }
           
           .close-icon {
             padding: 2px;
             border-radius: 2px;
             cursor: pointer;
             transition: background-color 0.3s;
             font-size: 12px;
             
             &:hover {
               background-color: rgba(0, 0, 0, 0.1);
             }
           }
         }
       }
       
      .tab-actions {
        display: flex;
        gap: 10px;
        flex-shrink: 0;
        
        .add-tab-btn,
        .batch-publish-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
        }
      }
    }
  }
  
  // estilo da janela de progresso da publicação em lote
  .publish-progress {
    padding: 20px;
    
    .current-publishing {
      margin: 15px 0;
      text-align: center;
      color: #606266;
    }

    .publish-results {
      margin-top: 20px;
      border-top: 1px solid #EBEEF5;
      padding-top: 15px;
      max-height: 300px;
      overflow-y: auto;

      .result-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #606266;

        .el-icon {
          margin-right: 8px;
        }

        .label {
          margin-right: 10px;
          font-weight: 500;
        }

        .message {
          color: #909399;
        }

        &.success {
          color: #67C23A;
        }

        &.error {
          color: #F56C6C;
        }

        &.cancelled {
          color: #909399;
        }
      }
    }
  }

  .dialog-footer {
    text-align: right;
  }
  
  // área de conteúdo
  .publish-content {
    flex: 1;
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    
    .tab-content-wrapper {
      display: flex;
      justify-content: center;
      
      .tab-content {
        width: 100%;
        max-width: 800px;
        
        h3 {
          font-size: 16px;
          font-weight: 500;
          color: $text-primary;
          margin: 0 0 10px 0;
        }
        
        .upload-section,
        .account-section,
        .platform-section,
        .title-section,
        .product-section,
        .topic-section,
        .schedule-section {
          margin-bottom: 30px;
        }

        .product-section {
          .product-name-input,
          .product-link-input {
            margin-bottom: 5px;
          }
        }
        
        .video-upload {
          width: 100%;
          
          :deep(.el-upload-dragger) {
            width: 100%;
            height: 180px;
          }
        }
        
        .account-input {
          max-width: 400px;
        }
        
        .platform-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          
          .platform-btn {
            min-width: 80px;
          }
        }
        
        .title-input {
          max-width: 600px;
        }
        
        .topic-display {
          display: flex;
          flex-direction: column;
          gap: 12px;
          
          .selected-topics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            min-height: 32px;
            
            .topic-tag {
              font-size: 14px;
            }
          }
          
          .select-topic-btn {
            align-self: flex-start;
          }
        }
        
        .schedule-controls {
          display: flex;
          flex-direction: column;
          gap: 15px;

          .schedule-settings {
            margin-top: 15px;
            padding: 15px;
            background-color: #f5f7fa;
            border-radius: 4px;

            .schedule-item {
              display: flex;
              align-items: center;
              margin-bottom: 15px;

              &:last-child {
                margin-bottom: 0;
              }

              .label {
                min-width: 120px;
                margin-right: 10px;
              }

              .el-time-select {
                margin-right: 10px;
              }

              .el-button {
                margin-left: 10px;
              }
            }
          }
        }
        
        .action-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #ebeef5;
        }

        .draft-section {
          margin: 20px 0;

          .draft-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .original-section {
          margin: 10px 0 20px;

          .original-checkbox {
            display: block;
            margin: 10px 0;
          }
        }
      }
    }
  }

  // estilo da lista de arquivos enviados
  .uploaded-files {
    margin-top: 20px;
    
    h4 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #303133;
    }
    
    .file-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      
      .file-item {
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background-color: #f5f7fa;
        border-radius: 4px;
        
        .el-link {
          margin-right: 10px;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        
        .file-size {
          color: #909399;
          font-size: 13px;
          margin-right: auto;
        }
      }
    }
  }
  
  // estilo da janela de hashtags
  .topic-dialog {
    .topic-dialog-content {
      .custom-topic-input {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;
        
        .custom-input {
          flex: 1;
        }
      }
      
      .recommended-topics {
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }
        
        .topic-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
          gap: 12px;
          
          .topic-btn {
            height: 36px;
            font-size: 14px;
            border-radius: 6px;
            min-width: 100px;
            padding: 0 12px;
            white-space: nowrap;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
            
            &.el-button--primary {
              background-color: #409eff;
              border-color: #409eff;
              color: white;
            }
          }
        }
      }
    }
    
    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}
</style>
