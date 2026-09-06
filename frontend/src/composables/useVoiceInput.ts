import { ref, onUnmounted } from 'vue'

/**
 * 全局语音输入（Web Speech API）。
 * 仅 Chrome/Edge 完整支持；不支持时 supported=false，按钮自动隐藏。
 * 点击开始 → 停顿即停（continuous:false）→ onend 广播最终文本。
 */
export function useVoiceInput(opts: { lang?: string } = {}) {
  type OnEnd = (text: string, interim: string) => void

  const supported = ref(false)
  const listening = ref(false)
  const interim = ref('')
  const final = ref('')
  const error = ref('')

  let recognition: any = null
  let finalTranscript = ''
  let endHandler: OnEnd | null = null

  // 运行时检测（Safari/Firefox 前缀兼容）
  const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (SR) {
    supported.value = true
    recognition = new SR()
    recognition.lang = opts.lang || 'zh-CN'
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onstart = () => { listening.value = true; error.value = '' }
    recognition.onend = () => {
      listening.value = false
      interim.value = ''
      if (endHandler) { endHandler(finalTranscript, finalTranscript); finalTranscript = '' }
    }
    recognition.onerror = (e: any) => { error.value = e?.error || 'error'; listening.value = false }
    recognition.onresult = (e: any) => {
      let interimText = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const tr = e.results[i][0].transcript
        if (e.results[i].isFinal) finalTranscript += tr
        else interimText += tr
      }
      interim.value = interimText
      final.value = finalTranscript
    }
  }

  function start(onEnd?: OnEnd) {
    if (!supported.value) return
    if (onEnd) endHandler = onEnd
    finalTranscript = ''
    final.value = ''
    interim.value = ''
    try { recognition.start() } catch (e) { /* already started */ }
  }

  function stop() {
    if (!supported.value) return
    try { recognition.stop() } catch (e) { /* noop */ }
  }

  function toggle(onEnd?: OnEnd) {
    if (listening.value) stop()
    else start(onEnd)
  }

  onUnmounted(() => { try { recognition?.abort?.() } catch (e) { /* noop */ } })

  return { supported, listening, interim, final, error, start, stop, toggle }
}