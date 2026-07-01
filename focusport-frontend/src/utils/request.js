/**
 * 馃寪 缁熶竴 Axios 璇锋眰瀹炰緥
 *
 * 浣跨敤鏂瑰紡锛? * import request from '@/utils/request'
 * const res = await request.get('/api/exams')
 */

import axios from 'axios'

// 浠庣幆澧冨彉閲忚鍙?API 鍩虹鍦板潃
// 鏈湴寮€鍙戞椂涓虹┖锛堜娇鐢ㄧ浉瀵硅矾寰勶級锛岀敓浜х幆澧冧负 cpolar 鍦板潃
const baseURL = import.meta.env.VITE_API_BASE_URL || ''

console.log('馃敆 API Base URL:', baseURL || '(鏈湴寮€鍙戞ā寮?')

// 鍒涘缓 axios 瀹炰緥
const request = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 璇锋眰鎷︽埅鍣?request.interceptors.request.use(
  (config) => {
    // 鍙湪姝ゆ坊鍔?token 绛夎璇佷俊鎭?    const username = localStorage.getItem('username')
    if (username) {
      config.headers['X-Username'] = username
    }
    return config
  },
  (error) => {
    console.error('璇锋眰閿欒:', error)
    return Promise.reject(error)
  }
)

// 鍝嶅簲鎷︽埅鍣?request.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 缁熶竴閿欒澶勭悊
    const message = error.response?.data?.detail || error.message || '缃戠粶閿欒'
    console.error('API 閿欒:', message)

    // 鍙互鍦ㄨ繖閲岀粺涓€寮瑰嚭閿欒鎻愮ず
    // ElMessage.error(message)

    return Promise.reject(error)
  }
)

export default request

// 瀵煎嚭甯哥敤鏂规硶
export const get = (url, params) => request.get(url, { params })
export const post = (url, data) => request.post(url, data)
export const put = (url, data) => request.put(url, data)
export const del = (url) => request.delete(url)
