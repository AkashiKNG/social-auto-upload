import axios from 'axios'
import { ElMessage } from 'element-plus'

// cria a instância do axios
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409',
  headers: {
    'Content-Type': 'application/json'
  }
})

// interceptador de requisição
request.interceptors.request.use(
  (config) => {
    // dá para acrescentar token e outras credenciais aqui
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    console.error('erro na requisição:', error)
    return Promise.reject(error)
  }
)

// interceptador de resposta
request.interceptors.response.use(
  (response) => {
    const { data } = response
    
    // trata a resposta conforme o contrato do backend
    if (data.code === 200 || data.success) {
      return data
    } else {
      ElMessage.error(data.msg || data.message || 'a requisição falhou')
      return Promise.reject(new Error(data.msg || data.message || 'a requisição falhou'))
    }
  },
  (error) => {
    console.error('erro na resposta:', error)
    
    // trata os códigos de erro HTTP
    if (error.response) {
      const { status } = error.response
      switch (status) {
        case 401:
          ElMessage.error('sem autorização, entre de novo')
          // aqui dá para redirecionar para o login
          break
        case 403:
          ElMessage.error('acesso negado')
          break
        case 404:
          ElMessage.error('endereço não encontrado')
          break
        case 500:
          ElMessage.error('erro interno do servidor')
          break
        default:
          ElMessage.error('erro de rede')
      }
    } else {
      ElMessage.error('falha na conexão de rede')
    }
    
    return Promise.reject(error)
  }
)

// atalhos para os métodos de requisição mais usados
export const http = {
  get(url, params) {
    return request.get(url, { params })
  },
  
  post(url, data, config = {}) {
    return request.post(url, data, config)
  },
  
  put(url, data, config = {}) {
    return request.put(url, data, config)
  },
  
  delete(url, params) {
    return request.delete(url, { params })
  },
  
  upload(url, formData, onUploadProgress) {
    return request.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress
    })
  }
}

export default request