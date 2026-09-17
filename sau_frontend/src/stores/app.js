import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  // primeira visita à página de contas
  const isFirstTimeAccountManagement = ref(true)
  
  // primeira visita à página de materiais
  const isFirstTimeMaterialManagement = ref(true)

  // estado de atualização da página de contas
  const isAccountRefreshing = ref(false)

  // lista de materiais
  const materials = ref([])
  
  // marca a página de contas como visitada
  const setAccountManagementVisited = () => {
    isFirstTimeAccountManagement.value = false
  }
  
  // marca a página de materiais como visitada
  const setMaterialManagementVisited = () => {
    isFirstTimeMaterialManagement.value = false
  }
  
  // limpa o estado de visita (ao entrar de novo ou recarregar a aplicação)
  const resetVisitStatus = () => {
    isFirstTimeAccountManagement.value = true
    isFirstTimeMaterialManagement.value = true
  }

  // atualiza a lista de materiais
  const setMaterials = (materialList) => {
    materials.value = materialList
  }

  // adiciona um material
  const addMaterial = (material) => {
    materials.value.push(material)
  }

  // remove um material
  const removeMaterial = (materialId) => {
    const index = materials.value.findIndex(m => m.id === materialId)
    if (index > -1) {
      materials.value.splice(index, 1)
    }
  }
  
  // define o estado de atualização da página de contas
  const setAccountRefreshing = (status) => {
    isAccountRefreshing.value = status
  }

  return {
    isFirstTimeAccountManagement,
    isFirstTimeMaterialManagement,
    isAccountRefreshing,
    materials,
    setAccountManagementVisited,
    setMaterialManagementVisited,
    resetVisitStatus,
    setMaterials,
    addMaterial,
    removeMaterial,
    setAccountRefreshing
  }
})