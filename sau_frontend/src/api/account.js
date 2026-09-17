import { http } from '@/utils/request'

// API de contas
export const accountApi = {
  // lista as contas válidas (com verificação)
  getValidAccounts() {
    return http.get('/getValidAccounts')
  },

  // lista as contas (sem verificação, carrega rápido)
  getAccounts() {
    return http.get('/getAccounts')
  },

  // adiciona uma conta
  addAccount(data) {
    return http.post('/account', data)
  },

  // atualiza uma conta
  updateAccount(data) {
    return http.post('/updateUserinfo', data)
  },

  // remove uma conta
  deleteAccount(id) {
    return http.get(`/deleteAccount?id=${id}`)
  }
}