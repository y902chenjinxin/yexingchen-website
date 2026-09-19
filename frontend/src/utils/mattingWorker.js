/* MODNet 人像分割 WebWorker
 * 独立线程完成 onnxruntime-web 推理。wasm 与模型均同源自托管。
 * 协议：启动回 {type:'ready'}；每个请求按 id 回传结果。
 */
import * as ort from 'onnxruntime-web/wasm'

// 自托管：WASM 运行时走确定性同源路径
ort.env.wasm.wasmPaths = '/models/modnet/wasm/'

let session = null
let sessionErr = null

self.postMessage({ type: 'ready' })

async function ensureSession() {
  if (session) return session
  if (sessionErr) throw sessionErr
  try {
    session = await ort.InferenceSession.create('/models/modnet/model.onnx', {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    })
    return session
  } catch (err) {
    sessionErr = err
    throw err
  }
}

// 保持比例缩放到 512×512 居中黑边，RGB 归一化 [0,1]
function preprocess(imageData, W, H) {
  const sw = imageData.width, sh = imageData.height
  const ratio = Math.min(W / sw, H / sh)
  const nw = Math.max(1, Math.round(sw * ratio))
  const nh = Math.max(1, Math.round(sh * ratio))
  const ox = Math.round((W - nw) / 2)
  const oy = Math.round((H - nh) / 2)

  const src = imageData.data
  const inArr = new Float32Array(W * H * 3)
  for (let y = 0; y < nh; y++) {
    const sy = Math.min(sh - 1, Math.floor(y * sh / nh))
    for (let x = 0; x < nw; x++) {
      const sx = Math.min(sw - 1, Math.floor(x * sw / nw))
      const si = (sy * sw + sx) * 4
      const di = ((oy + y) * W + (ox + x)) * 3
      inArr[di] = src[si] / 255
      inArr[di + 1] = src[si + 1] / 255
      inArr[di + 2] = src[si + 2] / 255
    }
  }
  return new ort.Tensor('float32', inArr, [1, 3, W, H])
}

function toMatte(out, sw, sh) {
  const W = 512, H = 512
  const matte = new Uint8ClampedArray(sw * sh)
  const ratio = Math.min(W / sw, H / sh)
  const nw = Math.max(1, Math.round(sw * ratio))
  const nh = Math.max(1, Math.round(sh * ratio))
  const ox = Math.round((W - nw) / 2)
  const oy = Math.round((H - nh) / 2)
  for (let y = 0; y < sh; y++) {
    const my = Math.min(nh - 1, Math.floor(y * nh / sh))
    for (let x = 0; x < sw; x++) {
      const mx = Math.min(nw - 1, Math.floor(x * nw / sw))
      const mi = (oy + my) * W + ox + mx
      matte[y * sw + x] = Math.round(out[mi] * 255)
    }
  }
  return matte
}

self.onmessage = async (ev) => {
  const { id, imageData, type } = ev.data
  try {
    // 纯预热：仅创建 session（下载模型+wasm），结果不投递给主线程
    if (type === 'preload') {
      await ensureSession()
      return
    }
    await ensureSession()
    const res = await session.run({ input: preprocess(imageData, 512, 512) })
    const out = res.output.data
    self.postMessage({ id, ok: true, matte: toMatte(out, imageData.width, imageData.height) })
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) })
  }
}