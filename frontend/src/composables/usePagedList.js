/**
 * 客户端分页状态（v2.46.161）
 *
 * 为什么要有它：8 个页面各写一份
 *   `const page = ref(1); const pageSize = ref(10); const paged = computed(slice...)`
 *   + `onSizeChange/onPageChange`，切页大小的默认值还各不相同（10 / 24），
 *   而且**没有一处做了越界修正** —— 删掉最后一页的最后一条，页面就停在空白表格上，
 *   用户会以为数据全没了。
 *
 * 用法（客户端分页：数据已全量在手）：
 *   const { page, pageSize, total, paged, onPageChange, onSizeChange } = usePagedList(filteredRows, {
 *     defaultSize: 24,
 *   })
 *   <el-pagination :total="total" :page-size="pageSize" :current-page="page"
 *     :page-sizes="sizes" @current-change="onPageChange" @size-change="onSizeChange" />
 *
 * 注意：**后端分页**（total 来自接口、翻页要重新请求）不要用这个，
 * 那种场景 page 是请求参数，`paged` 没有意义。目前资讯/日志属于后者，未接入。
 */
import { computed, ref, watch } from 'vue'

export function usePagedList(source, options = {}) {
  const { defaultSize = 10, sizes = [10, 20, 50], resetOnChange = true } = options

  const page = ref(1)
  const pageSize = ref(defaultSize)

  const total = computed(() => {
    const v = source?.value
    return Array.isArray(v) ? v.length : 0
  })

  const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

  const paged = computed(() => {
    const all = source?.value
    if (!Array.isArray(all)) return []
    const start = (page.value - 1) * pageSize.value
    return all.slice(start, start + pageSize.value)
  })

  /* 越界修正：数据变少（删除 / 搜索 / 取消勾选筛选）后页码可能超出总页数。
     原来 8 个页面都没处理，表现为「停在空白页」。 */
  watch([total, pageSize], () => {
    if (page.value > pageCount.value) page.value = pageCount.value
    if (page.value < 1) page.value = 1
  })

  function onPageChange(p) {
    page.value = Number(p) || 1
  }

  /** 切每页条数：默认回到第 1 页（避免停在一个不存在的页码上） */
  function onSizeChange(sz) {
    pageSize.value = Number(sz) || defaultSize
    if (resetOnChange) page.value = 1
  }

  /** 数据源被外部替换（比如重新拉取）时回到第 1 页 */
  function reset() {
    page.value = 1
  }

  return { page, pageSize, pageCount, total, paged, sizes, onPageChange, onSizeChange, reset }
}
