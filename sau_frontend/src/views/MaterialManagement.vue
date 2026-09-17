<template>
  <div class="material-management">
    <div class="page-header">
      <h1>Materiais</h1>
    </div>
    
    <div class="material-list-container">
      <div class="material-search">
        <el-input
          v-model="searchKeyword"
          placeholder="Buscar por nome do arquivo"
          prefix-icon="Search"
          clearable
          @clear="handleSearch"
          @input="handleSearch"
        />
        <div class="action-buttons">
          <el-button type="primary" @click="handleUploadMaterial">envia um material</el-button>
          <el-button type="info" @click="fetchMaterials" :loading="false">
            <el-icon :class="{ 'is-loading': isRefreshing }"><Refresh /></el-icon>
            <span v-if="isRefreshing">Atualizando</span>
          </el-button>
        </div>
      </div>
      
      <div v-if="filteredMaterials.length > 0" class="material-list">
        <el-table :data="filteredMaterials" style="width: 100%">
          <el-table-column prop="uuid" label="UUID" width="180" />
          <el-table-column prop="filename" label="Arquivo" width="300" />
          <el-table-column prop="filesize" label="Tamanho" width="120">
            <template #default="scope">
              {{ scope.row.filesize }} MB
            </template>
          </el-table-column>
          <el-table-column prop="upload_time" label="Enviado em" width="180" />
          <el-table-column label="Ações">
            <template #default="scope">
              <el-button size="small" @click="handlePreview(scope.row)">Ver</el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.row)">Excluir</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div v-else class="empty-data">
        <el-empty description="Nenhum material ainda" />
      </div>
    </div>
    
    <!-- janela de envio -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="envia um material"
      width="40%"
      @close="handleUploadDialogClose"
    >
      <div class="upload-form">
        <el-form label-width="80px">
          <el-form-item label="Nome:">
            <el-input
              v-model="customFilename"
              placeholder="opcional (só vale quando é um arquivo só)"
              :disabled="customFilenameDisabled"
              clearable
            />
          </el-form-item>
          <el-form-item label="Escolher arquivos">
            <el-upload
              class="upload-demo"
              drag
              multiple
              :auto-upload="false"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :file-list="fileList"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                Arraste os arquivos até aqui, ou<em>clique para enviar</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  Aceita vídeos, imagens e outros formatos; dá para escolher vários de uma vez
                </div>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="Arquivos escolhidos" v-if="fileList.length > 0">
            <div class="upload-file-list">
              <div v-for="file in fileList" :key="file.uid" class="upload-file-item">
                <span class="file-name">{{ file.name }}</span>
                <el-progress
                  :percentage="uploadProgress[file.uid]?.percentage || 0"
                  :text-inside="true"
                  :stroke-width="20"
                  style="width: 100%; margin-top: 5px;"
                >
                  <span>{{ uploadProgress[file.uid]?.speed || '' }}</span>
                </el-progress>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">Cancelar</el-button>
          <el-button type="primary" @click="submitUpload" :loading="isUploading">
            {{ isUploading ? 'Enviando' : 'Enviar' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- janela de pré-visualização -->
    <el-dialog
      v-model="previewDialogVisible"
      title="Pré-visualização"
      width="50%"
      :top="'10vh'"
    >
      <div class="preview-container" v-if="currentMaterial">
        <div v-if="isVideoFile(currentMaterial.filename)" class="video-preview">
          <video controls style="max-width: 100%; max-height: 60vh;">
            <source :src="getPreviewUrl(currentMaterial.file_path)" type="video/mp4">
            Seu navegador não reproduz vídeo
          </video>
        </div>
        <div v-else-if="isImageFile(currentMaterial.filename)" class="image-preview">
          <img :src="getPreviewUrl(currentMaterial.file_path)" style="max-width: 100%; max-height: 60vh;" />
        </div>
        <div v-else class="file-info">
          <p>Arquivo: {{ currentMaterial.filename }}</p>
          <p>Tamanho: {{ currentMaterial.filesize }} MB</p>
          <p>Enviado em: {{ currentMaterial.upload_time }}</p>
          <el-button type="primary" @click="downloadFile(currentMaterial)">Baixar arquivo</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { materialApi } from '@/api/material'
import { useAppStore } from '@/stores/app'

// estado global da aplicação
const appStore = useAppStore()

// busca e estado da tela
const searchKeyword = ref('')
const isRefreshing = ref(false)
const isUploading = ref(false)

// controle das janelas
const uploadDialogVisible = ref(false)
const previewDialogVisible = ref(false)
const currentMaterial = ref(null)

// envio de arquivos
const fileList = ref([])
const customFilename = ref('')
const customFilenameDisabled = computed(() => fileList.value.length > 1)
const uploadProgress = ref({}); // { [uid]: { percentage: 0, speed: '' } }


watch(fileList, (newList) => {
  if (newList.length <= 1) {
    // If you want to clear the custom name when going back to single file, uncomment below
    // customFilename.value = ''
  }
});


// busca a lista de materiais
const fetchMaterials = async () => {
  isRefreshing.value = true
  try {
    const response = await materialApi.getAllMaterials()
    
    if (response.code === 200) {
      appStore.setMaterials(response.data)
      ElMessage.success('Lista atualizada')
    } else {
      ElMessage.error('Não consegui carregar os materiais')
    }
  } catch (error) {
    console.error('Erro ao carregar os materiais:', error)
    ElMessage.error('Não consegui carregar os materiais')
  } finally {
    isRefreshing.value = false
  }
}

// filtra os materiais
const filteredMaterials = computed(() => {
  if (!searchKeyword.value) return appStore.materials
  
  const keyword = searchKeyword.value.toLowerCase()
  return appStore.materials.filter(material => 
    material.filename.toLowerCase().includes(keyword)
  )
})

// trata a busca
const handleSearch = () => {
  // a busca já é feita por propriedade computada
}

// envia um material
const handleUploadMaterial = () => {
  // limpa os campos
  fileList.value = []
  customFilename.value = ''
  uploadProgress.value = {};
  uploadDialogVisible.value = true
}

// limpa os campos ao fechar a janela de envio
const handleUploadDialogClose = () => {
  fileList.value = []
  customFilename.value = ''
  uploadProgress.value = {};
}

// mudou a seleção de arquivos
const handleFileChange = (file, uploadFileList) => {
  fileList.value = uploadFileList;
  const newProgress = {};
  for (const f of uploadFileList) {
    newProgress[f.uid] = { percentage: 0, speed: '' };
  }
  uploadProgress.value = newProgress;
}

const handleFileRemove = (file, uploadFileList) => {
  fileList.value = uploadFileList;
  const newProgress = { ...uploadProgress.value };
  delete newProgress[file.uid];
  uploadProgress.value = newProgress;
}

// envia os arquivos
const submitUpload = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('Escolha os arquivos para enviar')
    return
  }
  
  isUploading.value = true
  
  for (const file of fileList.value) {
    try {
      // garante que o arquivo existe
      if (!file || !file.raw) {
        ElMessage.warning(`Arquivo ${file.name} inválido, pulado`)
        continue
      }
      
      const formData = new FormData()
      formData.append('file', file.raw)
      
      // o nome personalizado só vale quando há um único arquivo
      if (fileList.value.length === 1 && customFilename.value.trim()) {
        formData.append('filename', customFilename.value.trim())
      }
      
      let lastLoaded = 0;
      let lastTime = Date.now();

      const response = await materialApi.uploadMaterial(formData, (progressEvent) => {
        const progressData = uploadProgress.value[file.uid];
        if (!progressData) return;

        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        progressData.percentage = progress;

        const currentTime = Date.now();
        const timeDiff = (currentTime - lastTime) / 1000; // in seconds
        const loadedDiff = progressEvent.loaded - lastLoaded;

        if (timeDiff > 0.5) { // Update speed every 0.5 seconds
          const speed = loadedDiff / timeDiff; // bytes per second
          if (speed > 1024 * 1024) {
            progressData.speed = (speed / (1024 * 1024)).toFixed(2) + ' MB/s';
          } else {
            progressData.speed = (speed / 1024).toFixed(2) + ' KB/s';
          }
          lastLoaded = progressEvent.loaded;
          lastTime = currentTime;
        }
      })
      
      if (response.code === 200) {
        ElMessage.success(`Arquivo ${file.name} enviado`)
        const progressData = uploadProgress.value[file.uid];
        if(progressData) progressData.speed = 'concluído';
      } else {
        ElMessage.error(`Falha ao enviar ${file.name}: ${response.msg || 'erro desconhecido'}`)
      }
    } catch (error) {
      console.error(`envio do arquivo ${file.name} deu erro:`, error)
      ElMessage.error(`Falha ao enviar ${file.name}: ${error.message || 'erro desconhecido'}`)
    }
  }
  
  isUploading.value = false
  // Keep dialog open to show results
  // uploadDialogVisible.value = false 
  await fetchMaterials()
}

// pré-visualiza o material
const handlePreview = async (material) => {
  currentMaterial.value = null
  previewDialogVisible.value = true
  ElMessage.info('Carregando...')
  try {
    // espera um instante para a janela terminar de abrir
    await new Promise(resolve => setTimeout(resolve, 100))
    currentMaterial.value = material
  } catch (error) {
    console.error('Erro ao pré-visualizar o material:', error)
    ElMessage.error('Não consegui carregar a pré-visualização')
    previewDialogVisible.value = false
  }
}

// remove um material
const handleDelete = (material) => {
  ElMessageBox.confirm(
    `Remover o material ${material.filename}?`,
    'Atenção',
    {
      confirmButtonText: 'Confirmar',
      cancelButtonText: 'Cancelar',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        const response = await materialApi.deleteMaterial(material.id)
        
        if (response.code === 200) {
          appStore.removeMaterial(material.id)
          ElMessage.success('Removido')
        } else {
          ElMessage.error(response.msg || 'Não consegui remover')
        }
      } catch (error) {
        console.error('remove um materialdeu erro:', error)
        ElMessage.error('Não consegui remover')
      }
    })
    .catch(() => {
      // remoção cancelada
    })
}

// monta a URL de pré-visualização
const getPreviewUrl = (filePath) => {
  const filename = filePath.split('/').pop()
  return materialApi.getMaterialPreviewUrl(filename)
}

// Baixar arquivo
const downloadFile = (material) => {
  const url = materialApi.downloadMaterial(material.file_path)
  window.open(url, '_blank')
}

// descobre o tipo do arquivo
const isVideoFile = (filename) => {
  const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
  return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext))
}

const isImageFile = (filename) => {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
  return imageExtensions.some(ext => filename.toLowerCase().endsWith(ext))
}

// busca a lista de materiais quando o componente monta
onMounted(() => {
  // só busca quando a store está vazia
  if (appStore.materials.length === 0) {
    fetchMaterials()
  }
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

.material-management {
  
  .page-header {
    margin-bottom: 20px;
    
    h1 {
      font-size: 24px;
      font-weight: 500;
      color: $text-primary;
      margin: 0;
    }
  }
  
  .material-list-container {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    
    .material-search {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      
      .el-input {
        width: 300px;
      }
      
      .action-buttons {
        display: flex;
        gap: 10px;
        
        .is-loading {
          animation: rotate 1s linear infinite;
        }
      }
    }
    
    .material-list {
      margin-top: 20px;
    }
    
    .empty-data {
      padding: 40px 0;
    }
  }
  
  .material-upload {
    width: 100%;
  }
  
  .preview-container {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    padding: 0 20px;
    
    .file-info {
      text-align: center;
      margin-top: 20px;
    }
  }
}

.upload-form {
  padding: 0 20px;
  
  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 5px;
  }
  
  .upload-demo {
    width: 100%;
  }
}

.dialog-footer {
  padding: 0 20px;
  display: flex;
  justify-content: flex-end;
}

.upload-file-list {
  width: 100%;
}

.upload-file-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 10px;
}

.upload-file-item .file-name {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
  display: block;
}

/* sobrescreve o estilo das janelas do Element Plus */
:deep(.el-dialog__body) {
  padding: 20px 0;
}

:deep(.el-dialog__header) {
  padding-left: 20px;
  padding-right: 20px;
  margin-right: 0;
}

:deep(.el-dialog__footer) {
  padding-top: 10px;
  padding-bottom: 15px;
}

/* estilo da barra de progresso do envio */
:deep(.el-progress__text) {
  color: #303133 !important; /* cinza escuro, legível em qualquer fundo */
  font-size: 12px;
}

:deep(.el-progress--line) {
  margin-bottom: 10px;
}

.upload-file-item {
  border: 1px solid #dcdfe6;
  border-radius: 6px; /* cantos mais arredondados */
  padding: 12px; /* mais espaçamento interno */
  margin-bottom: 12px; /* mais espaçamento externo */
  background-color: #fafafa; /* fundo bem leve */
  transition: box-shadow 0.3s; /* com transição */
}

.upload-file-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); /* efeito ao passar o mouse */
}

.upload-file-item .file-name {
  font-size: 14px;
  color: #303133; /* fonte cinza escuro */
  margin-bottom: 8px; /* mais espaço embaixo */
  display: block;
  font-weight: 500;
}
</style>
