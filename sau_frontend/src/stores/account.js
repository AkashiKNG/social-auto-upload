import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAccountStore = defineStore('account', () => {
  // guarda todas as contas
  const accounts = ref([])
  
  // mapa dos tipos de plataforma
  const platformTypes = {
    1: 'Xiaohongshu',
    2: 'Canal do WeChat',
    3: 'Douyin',
    4: 'Kuaishou'
  }
  
  // define a lista de contas
  const setAccounts = (accountsData) => {
    // converte o formato devolvido pelo backend para o usado no frontend
    accounts.value = accountsData.map(item => {
      return {
        id: item[0],
        type: item[1],
        filePath: item[2],
        name: item[3],
        status: item[4] === -1 ? 'verificando' : (item[4] === 1 ? 'ok' : 'com erro'),
        platform: platformTypes[item[1]] || 'desconhecido'
      }
    })
  }
  
  // adiciona uma conta
  const addAccount = (account) => {
    accounts.value.push(account)
  }
  
  // atualiza uma conta
  const updateAccount = (id, updatedAccount) => {
    const index = accounts.value.findIndex(acc => acc.id === id)
    if (index !== -1) {
      accounts.value[index] = { ...accounts.value[index], ...updatedAccount }
    }
  }
  
  // remove uma conta
  const deleteAccount = (id) => {
    accounts.value = accounts.value.filter(acc => acc.id !== id)
  }
  
  // contas de uma plataforma
  const getAccountsByPlatform = (platform) => {
    return accounts.value.filter(acc => acc.platform === platform)
  }
  
  return {
    accounts,
    setAccounts,
    addAccount,
    updateAccount,
    deleteAccount,
    getAccountsByPlatform
  }
})