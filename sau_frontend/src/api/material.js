import { http } from '@/utils/request'

// API de materiais
export const materialApi = {
  // lista todos os materiais
  getAllMaterials: () => {
    return http.get('/getFiles')
  },
  
  // envia um material
  uploadMaterial: (formData, onUploadProgress) => {
    // usa http.upload, que já manda o Content-Type certo
    return http.upload('/uploadSave', formData, onUploadProgress)
  },
  
  // remove um material
  deleteMaterial: (id) => {
    return http.get(`/deleteFile?id=${id}`)
  },
  
  // baixa um material
  downloadMaterial: (filePath) => {
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'}/download/${filePath}`
  },
  
  // URL de pré-visualização do material
  getMaterialPreviewUrl: (filename) => {
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'}/getFile?filename=${filename}`
  }
}