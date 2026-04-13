/**
 * 🌐 统一 Axios 请求实例
 *
 * 使用方式：
 * import request from '@/utils/request'
 * const res = await request.get('/api/exams')
 */

import axios from 'axios'

// 从环境变量读取 API 基础地址
// 本地开发时为空（使用相对路径），生产环境为 cpolar 地址
const baseURL = import.meta.env.VITE_API_BASE_URL || ''

console.log('🔗 API Base URL:', baseURL || '(本地开发模式)')

// 创建 axios 实例
const request = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 可在此添加 token 等认证信息
    const username = localStorage.getItem('username')
    if (username) {
      config.headers['X-Username'] = username
    }
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 统一错误处理
    const message = error.response?.data?.detail || error.message || '网络错误'
    console.error('API 错误:', message)

    // 可以在这里统一弹出错误提示
    // ElMessage.error(message)

    return Promise.reject(error)
  }
)

export default request

// 导出常用方法
export const get = (url, params) => request.get(url, { params })
export const post = (url, data) => request.post(url, data)
export const put = (url, data) => request.put(url, data)
export const del = (url) => request.delete(url)
