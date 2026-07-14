import request from './request'

/**
 * Get Chan theory analysis data
 */
export function getChanAnalysis(params) {
  return request({
    url: '/api/chan/analysis',
    method: 'get',
    params
  })
}

/**
 * Get supported periods (synced from backend single source of truth)
 */
export function getPeriods() {
  return request({
    url: '/api/chan/periods',
    method: 'get'
  })
}
