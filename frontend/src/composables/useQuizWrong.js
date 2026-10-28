/**
 * 错题本（v2.46.273）
 *
 * 夜星：「按你推荐的来，全部一轮做完」——错题本是其中留存价值最高的一件：
 * 答完的题（尤其答错的）除了底部一个百分比，没有任何落点，每天都在产生、每天都在丢。
 *
 * 存**完整快照**而不是题号：
 *   1. 打开错题本不必再请求一次题库；
 *   2. 题库以后改题/删题，错题本里的解析仍然可读（那是当时你看到的内容）。
 *
 * 数据形状：{ id, date, q, options, answer, picked, why, trick, topic }
 * 上限 80 条，超出丢最早的 —— localStorage 只给 5MB，不清理迟早爆。
 */
const KEY = 'xh_quiz_wrong'
const MAX = 80

export function readWrong() {
  try {
    const arr = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

function write(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list.slice(-MAX)))
  } catch { /* 隐私模式 / 配额满：静默 */ }
  return list.slice(-MAX)
}

/** 错题入本；同一道题重复错只保留最新一次（按 id 去重，避免刷屏） */
export function addWrong(snap) {
  if (!snap || !snap.id) return readWrong()
  const rest = readWrong().filter(x => x.id !== snap.id)
  return write([...rest, snap])
}

export function removeWrong(id) {
  return write(readWrong().filter(x => x.id !== id))
}

export function clearWrong() {
  return write([])
}
