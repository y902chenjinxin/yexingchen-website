/**
 * 表格行拖拽排序（PC 端：按住左键上下拖，松手保存）
 *
 * 设计取舍：**不画跟随鼠标的浮层**，而是在拖动过程中实时重排数据数组 ——
 * 行会跟着整体上下挪动，视觉上就是「把这一行拖到了那个位置」，跟 iOS 列表拖拽一致。
 * 好处是不用算 transform/占位，也不会和 el-table 的固定列打架。
 *
 * 用法：
 *   const { onRowMouseDown } = useRowDragSort({
 *     getTableEl: () => tableRef.value?.$el,
 *     getRows: () => list.value,
 *     onCommit: () => api.reorder({ ids: list.value.map(r => r.id) }),
 *   })
 *   <el-table ref="tableRef" @row-click="..." ... > 上绑 @mousedown="onRowMouseDown"
 *
 * 注意：首次 data 加载后顺序来自后端 sort_order，前端只负责「拖动时改数组 + 松手提交」。
 */
import { onBeforeUnmount } from 'vue'

const DRAG_THRESHOLD = 5 // px：小于这个距离算点击，不启动拖拽

export function useRowDragSort({ getTableEl, getRows, getOffset, onCommit, enabled }) {
  let dragging = false
  let moved = false
  let startIdx = -1
  let curIdx = -1
  let startY = 0
  let rowH = 44

  function bodyRows() {
    const root = getTableEl?.()
    if (!root) return []
    return Array.from(root.querySelectorAll('.el-table__body tbody tr'))
  }

  function onDown(e) {
    if (e.button !== 0) return
    // 手机端不启用：拖拽会和纵向滚动抢手势
    if (typeof enabled === 'function' && !enabled()) return
    const root = getTableEl && getTableEl()
    if (!root) return
    // 只处理落在本表格里的按下；页面上有多个表格时互不干扰
    if (!root.contains(e.target)) return
    const tr = e.target && e.target.closest ? e.target.closest('tbody tr') : null
    if (!tr) return
    // 点在交互控件上不启动拖拽，否则会干扰勾选/按钮/输入
    if (e.target.closest('button, a, input, textarea, select, .el-checkbox, .el-switch, .el-input, .el-select, [contenteditable]')) return
    const rows = bodyRows()
    const idx = rows.indexOf(tr)
    if (idx < 0) return

    dragging = true
    moved = false
    // 分页场景：表格里看到的是当前页切片，索引要换算成「源数组里的全局位置」
    const off = (typeof getOffset === 'function' ? getOffset() : 0) || 0
    startIdx = off + idx
    curIdx = startIdx
    startY = e.clientY
    rowH = tr.getBoundingClientRect().height || 44
    document.body.classList.add('is-row-dragging')
  }

  function onMove(e) {
    if (!dragging) return
    const dy = e.clientY - startY
    if (!moved && Math.abs(dy) < DRAG_THRESHOLD) return
    moved = true
    const list = getRows()
    if (!Array.isArray(list) || !list.length) return
    const off = (typeof getOffset === 'function' ? getOffset() : 0) || 0
    const target = Math.max(off, Math.min(list.length - 1, startIdx + Math.round(dy / rowH)))
    if (target === curIdx) return
    const [item] = list.splice(curIdx, 1)
    list.splice(target, 0, item)
    curIdx = target
  }

  function onUp() {
    if (!dragging) return
    dragging = false
    document.body.classList.remove('is-row-dragging')
    if (moved && curIdx !== startIdx) {
      try { onCommit && onCommit() } catch { /* 提交失败不阻塞 UI，顺序仍在本地 */ }
    }
    startIdx = -1
    curIdx = -1
    moved = false
  }

  // v2.46.188：用 document 级监听而不是模板上的 @mousedown ——
  // el-table 内部会拦一部分鼠标事件，挂在组件根上实测收不到。
  document.addEventListener('mousedown', onDown)
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)

  onBeforeUnmount(() => {
    document.removeEventListener('mousedown', onDown)
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    document.body.classList.remove('is-row-dragging')
  })

  // 保留导出名，模板上继续绑也安全（内部已去重：两次按下只会有一个真正开始拖）
  return { onRowMouseDown: () => {} }
}
