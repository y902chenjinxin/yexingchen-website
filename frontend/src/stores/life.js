import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  listMembers, createMember, updateMember, deleteMember,
  listWeight, createWeight, deleteWeight,
  listMeals, createMeal, deleteMeal,
} from '@/api/life'

export const useLifeStore = defineStore('life', () => {
  const members = ref([])
  const weightList = ref([])
  const mealList = ref([])
  const loading = ref(false)

  async function fetchMembers() {
    const res = await listMembers()
    members.value = res?.data?.list || []
    return members.value
  }

  async function fetchWeight(params = {}) {
    loading.value = true
    try {
      const res = await listWeight(params)
      weightList.value = res?.data?.list || []
      return weightList.value
    } finally {
      loading.value = false
    }
  }

  async function fetchMeals(params = {}) {
    loading.value = true
    try {
      const res = await listMeals(params)
      mealList.value = res?.data?.list || []
      return mealList.value
    } finally {
      loading.value = false
    }
  }

  async function addWeight(payload) {
    const fd = new FormData()
    fd.append('member_id', payload.member_id)
    fd.append('weight_kg', payload.weight_kg)
    if (payload.measured_at) fd.append('measured_at', payload.measured_at)
    if (payload.note) fd.append('note', payload.note)
    return createWeight(fd)
  }

  async function removeWeight(id) {
    return deleteWeight(id)
  }

  async function addMeal(payload) {
    const fd = new FormData()
    fd.append('member_id', payload.member_id)
    fd.append('meal_type', payload.meal_type)
    if (payload.taken_at) fd.append('taken_at', payload.taken_at)
    if (payload.note) fd.append('note', payload.note)
    fd.append('photo', payload.photo)
    return createMeal(fd)
  }

  async function removeMeal(id) {
    return deleteMeal(id)
  }

  async function addMember(payload) {
    const fd = new FormData()
    fd.append('user_id', payload.user_id)
    fd.append('display_name', payload.display_name)
    if (payload.avatar) fd.append('avatar', payload.avatar)
    if (payload.birth_year) fd.append('birth_year', payload.birth_year)
    if (payload.height_cm) fd.append('height_cm', payload.height_cm)
    await createMember(fd)
    await fetchMembers()
  }

  async function editMember(id, payload) {
    const fd = new FormData()
    if (payload.display_name != null) fd.append('display_name', payload.display_name)
    if (payload.avatar != null) fd.append('avatar', payload.avatar)
    if (payload.birth_year != null) fd.append('birth_year', payload.birth_year)
    if (payload.height_cm != null) fd.append('height_cm', payload.height_cm)
    await updateMember(id, fd)
    await fetchMembers()
  }

  async function removeMember(id) {
    await deleteMember(id)
    await fetchMembers()
  }

  return {
    members, weightList, mealList, loading,
    fetchMembers, fetchWeight, fetchMeals,
    addWeight, removeWeight,
    addMeal, removeMeal,
    addMember, editMember, removeMember,
  }
})
