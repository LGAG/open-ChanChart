import request from './request'

/**
 * Get favorite stocks list
 */
export function getFavorites() {
  return request({
    url: '/api/favorite/list',
    method: 'get'
  })
}

/**
 * Add a stock to favorites
 * @param {{code:string,name:string,market:string}} stock
 */
export function addFavorite(stock) {
  return request({
    url: '/api/favorite/add',
    method: 'post',
    data: stock
  })
}

/**
 * Remove a stock from favorites
 * @param {{code:string,market:string}} stock
 */
export function removeFavorite(stock) {
  return request({
    url: '/api/favorite/remove',
    method: 'delete',
    params: { code: stock.code, market: stock.market }
  })
}
