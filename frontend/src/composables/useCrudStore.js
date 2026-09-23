import { ref } from 'vue'

/**
 * 通用CRUD Store Composable
 * @param {string} entityName - 实体名称（用于调试）
 * @param {object} api - API对象 { getList, upload, update, delete }
 */
export function useCrudStore(entityName, api) {
  const list = ref([])
  const total = ref(0)
  const page = ref(1)
  const size = ref(20)
  const loading = ref(false)

  async function fetchList(params = {}) {
    loading.value = true
    try {
      // 允许 params 覆盖内置的 page/size（前端组件可传 size=200 一次性拉全）
      const reqParams = { page: page.value, size: size.value, ...params }
      const res = await api.getList(reqParams)
      list.value = res.data.list
      total.value = res.data.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function upload(data) {
    return await api.upload(data)
  }

  async function update(id, data) {
    return await api.update(id, data)
  }

  async function remove(id) {
    return await api.delete(id)
  }

  return { list, total, page, size, loading, fetchList, upload, update, remove }
}