/** 日历数据（农历 / 节气 / 节日 / 法定假期，v2.40.36） */
import api from './index'

export const lunarApi = {
  /** 某月逐日数据；结果在前端按「年-月」缓存 */
  month: (year, month) => api.get('/lunar/month', { params: { year, month } }),
}
