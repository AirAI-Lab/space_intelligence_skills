import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 可以在这里添加 token
    // config.headers['Authorization'] = 'Bearer ' + token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)

export default request

// API 方法
export const deviceApi = {
  // 获取设备列表
  getList: (params: any) => request.get('/device/list', { params }),
  // 获取设备状态
  getStatus: (deviceId: string) => request.get(`/device/${deviceId}/status`),
  // 注册设备
  register: (data: any) => request.post('/device/register', data),
  // 下发配置
  setConfig: (deviceId: string, config: any) => request.put(`/device/${deviceId}/config`, config)
}

export const dataApi = {
  // 上传数据
  upload: (file: File, path: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('path', path)
    return request.post('/data/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 创建数据集
  createDataset: (data: any) => request.post('/data/dataset/create', data),
  // 获取数据集列表
  getDatasetList: (params: any) => request.get('/data/dataset/list', { params }),
  // 启动AI标注
  startAiAnnotation: (data: any) => request.post('/data/annotation/ai', data),
  // 获取标注结果
  getAnnotationResult: (taskId: string) => request.get(`/data/annotation/${taskId}`)
}

export const trainingApi = {
  // 创建训练任务
  createJob: (data: any) => request.post('/training/job/create', data),
  // 获取训练任务详情
  getJob: (jobId: string) => request.get(`/training/job/${jobId}`),
  // 停止训练
  stopJob: (jobId: string) => request.post(`/training/job/${jobId}/stop`),
  // 获取训练日志
  getLogs: (jobId: string, lines?: number) => request.get(`/training/job/${jobId}/logs`, { params: { lines } }),
  // 验证模型
  val: (data: any) => request.post('/training/val', data),
  // 导出模型
  export: (data: any) => request.post('/training/export', data)
}

export const modelApi = {
  // 上传模型
  upload: (file: File, config: any) => {
    const formData = new FormData()
    formData.append('model_file', file)
    formData.append('config', JSON.stringify(config))
    return request.post('/model/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 获取模型列表
  getList: (params: any) => request.get('/model/versions', { params }),
  // 部署模型
  deploy: (data: any) => request.post('/model/deploy', data),
  // 获取模型指标
  getMetrics: (modelId: string) => request.get(`/model/${modelId}/metrics`)
}

export const otaApi = {
  // 创建升级任务
  createTask: (data: any) => request.post('/ota/create', data),
  // 开始升级
  start: (taskId: string) => request.post(`/ota/${taskId}/start`),
  // 获取升级进度
  getProgress: (taskId: string) => request.get(`/ota/${taskId}/progress`),
  // 回滚
  rollback: (taskId: string) => request.post(`/ota/${taskId}/rollback`)
}

export const inferenceApi = {
  // 启动推理
  start: (data: any) => request.post('/inference/start', data),
  // 停止推理
  stop: (data: any) => request.post('/inference/stop', data),
  // 获取推理状态
  getStatus: (deviceId: string) => request.get(`/inference/status?device_id=${deviceId}`),
  // 预测
  predict: (data: any) => request.post('/inference/predict', data)
}
