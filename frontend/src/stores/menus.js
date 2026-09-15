import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { getPublicMenus } from '@/api/admin'

/**
 * 全站导航菜单（DB 驱动）。
 *
 * 背景：顶栏原来把 8 个入口**硬编码**在前端，数据库里的菜单只被用来「按角色过滤这批写死项」，
 * 于是超管在后台新建/排序/分组菜单都不生效，二级菜单更是完全没有渲染实现。
 * 现在改成：后端 `/api/admin/menus/public` 返回**已按角色过滤**的扁平列表，
 * 前端只负责组装成树并渲染。
 *
 * 约定：
 * - `parent_id === 0` 是一级；有子项的一级菜单视为**分组**，自身不可点（其 path 只是占位）
 * - 分组下的子项**全部被角色过滤掉**时，分组本身也不显示（避免出现空分组）
 * - 接口失败时 `loadedOk=false`，此时 `isPathAllowed()` 一律放行（宁可多显示，也不要因接口故障把导航清空）
 */

let inflight = null

export const useMenusStore = defineStore('menus', () => {
  const raw = ref([])
  const loading = ref(false)
  // 是否成功拿到过菜单；失败/未加载时不做过滤
  const loadedOk = ref(false)

  const bySort = (a, b) => (a.sort_order - b.sort_order) || (a.id - b.id)

  /** 顶层节点（含 children）；有 children 的是分组 */
  const tree = computed(() => {
    const tops = raw.value.filter(m => !m.parent_id).sort(bySort)
    const kids = raw.value.filter(m => m.parent_id)
    return tops.map(m => {
      const children = kids.filter(k => k.parent_id === m.id).sort(bySort)
      return { ...m, children, isGroup: children.length > 0 }
    })
  })

  /** 渲染用：分组 + 无子项的普通入口分开，普通入口聚成一行更紧凑 */
  const groups = computed(() => tree.value.filter(n => n.isGroup))
  const loose = computed(() => tree.value.filter(n => !n.isGroup))

  /** 当前用户可见的真实路由路径集合 */
  const allowedPaths = computed(() => new Set(raw.value.map(m => m.path).filter(Boolean)))

  /** 某个路由是否对当前用户可见（菜单未加载成功时不拦截） */
  function isPathAllowed(path) {
    if (!loadedOk.value) return true
    return allowedPaths.value.has(path)
  }

  async function load(force = false) {
    if (inflight) return inflight
    if (!force && loadedOk.value) return
    loading.value = true
    inflight = (async () => {
      try {
        const res = await getPublicMenus()
        const list = res?.data?.list || []
        raw.value = list
        loadedOk.value = list.length > 0
      } catch {
        raw.value = []
        loadedOk.value = false
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    return inflight
  }

  return { raw, loading, loadedOk, tree, groups, loose, allowedPaths, isPathAllowed, load }
})
