/** 日历月度数据缓存（v2.40.37）。
 *
 * 月历面板（LunarCalendar）与日期选择器（LunarDatePicker）共用同一份缓存，
 * 同一个「年-月」在一次会话里只请求一次；失败也缓存空数组，避免反复重试打后端。
 */
import { lunarApi } from '@/api/lunar'

const cache = new Map()          // 'Y-M' → Promise<days[]>

/** 取某月逐日数据（带缓存）；force=true 时绕过缓存重新请求 */
export function getMonthDays(year, month, force = false) {
  const key = `${year}-${month}`
  if (force || !cache.has(key)) {
    cache.set(
      key,
      lunarApi.month(year, month)
        .then(res => res?.data?.days || [])
        .catch(() => []),
    )
  }
  return cache.get(key)
}

/** 取某天的日历信息（自动定位所属月份）；查不到返回 null */
export async function getDayInfo(dateStr) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr || '')) return null
  const [y, m] = dateStr.split('-').map(Number)
  const days = await getMonthDays(y, m)
  return days.find(d => d.date === dateStr) || null
}
