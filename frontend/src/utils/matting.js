/* MODNet 人像分割封装（浏览器本地 / 自托管模型）
 * 提供 segmentImage(imageData) → matte(Uint8ClampedArray 0-255，与 imageData 同尺寸)
 * 首次调用懒加载 WebWorker + 模型；失败返回 null，调用方回退算法抠图。
 *
 * 协议：
 *  - Worker 启动后立即回 { type:'ready' }（不依赖模型加载，保证不悬挂）
 *  - 每个推理请求带递增 id；结果按 id 回传
 *  - 模型在首次真实推理时加载（worker 内 ensureSession）
 */

let worker = null
let readyTimer = null
let seq = 0

function getWorker() {
  if (worker) return Promise.resolve(worker)
  return new Promise((resolve, reject) => {
    try {
      const w = new Worker(new URL('./mattingWorker.js', import.meta.url), { type: 'module' })
      let settled = false
      w.onerror = (e) => {
        if (!settled) { settled = true; reject(new Error(e.message || 'matting worker 加载失败')) }
      }
      w.onmessage = (ev) => {
        if (ev.data && ev.data.type === 'ready') {
          if (!settled) { settled = true; resolve(w) }
        }
      }
      // 超时保护：worker 卡死也不让调用方无限等待
      readyTimer = setTimeout(() => {
        if (!settled) { settled = true; reject(new Error('matting worker 就绪超时')) }
      }, 15000)
      worker = w
    } catch (err) {
      reject(err)
    }
  })
}

export async function warmupMatting() {
  try { await getWorker() } catch { /* ignore */ }
}

/* 后台预加载模型：创建 session 并下载 onnx/wasm，尽量在用户点「生成」前就绪。
 * 幂等、失败静默（不影响 getMatte 的算法兜底）。 */
export async function preloadMatting() {
  try {
    const w = await getWorker()
    w.postMessage({ type: 'preload' })
    return true
  } catch {
    return false
  }
}

export async function segmentImage(imageData) {
  const id = ++seq
  let w
  try {
    w = await getWorker()
  } catch {
    return null
  }
  const result = await new Promise((resolve) => {
    const onMsg = (ev) => {
      if (ev.data && ev.data.id === id) {
        w.onmessage = null
        resolve(ev.data)
      }
    }
    w.onmessage = onMsg
    w.postMessage({ id, imageData })
  })
  if (clearTimeout) clearTimeout(readyTimer)
  if (!result || !result.ok) {
    if (result && result.error) console.error('[matting] wasm error:', result.error)
    return null
  }
  return result.matte
}

export default { segmentImage, warmupMatting, preloadMatting }