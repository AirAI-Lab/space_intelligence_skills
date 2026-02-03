import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000  // 普通请求 60 秒超时
})

// 创建专用于文件上传的 axios 实例（更长超时）
const uploadRequest = axios.create({
  baseURL: '/api/v1',
  timeout: 300000  // 文件上传 5 分钟超时
})

// uploadRequest 响应拦截器
uploadRequest.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code !== 200) {
      ElMessage.error(res.message || '上传失败')
      return Promise.reject(new Error(res.message || '上传失败'))
    }
    return res
  },
  (error) => {
    console.error('上传错误:', error)
    ElMessage.error(error.message || '网络错误')
    return Promise.reject(error)
  }
)
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

// ==================== 设备 API ====================
export const deviceApi = {
  /**
   * 获取设备列表
   */
  getList: (params: { page?: number; pageSize?: number; status?: string }) =>
    request.get('/devices', { params }),

  /**
   * 获取设备状态
   */
  getStatus: (deviceId: string) =>
    request.get(`/devices/${deviceId}`),

  /**
   * 注册设备
   */
  register: (data: {
    deviceId: string
    deviceName: string
    deviceType: string
    groupId?: string
    ip?: string
    mac?: string
  }) => request.post('/devices', data),

  /**
   * 下发配置
   */
  setConfig: (deviceId: string, config: any) =>
    request.put(`/devices/${deviceId}`, config),

  /**
   * 删除设备
   */
  delete: (deviceId: string) =>
    request.delete(`/devices/${deviceId}`)
}

// ==================== 数据集 API ====================
export const dataApi = {
  /**
   * 上传数据集（支持文件上传和本地路径）
   */
  uploadDataset: (
    file: File | null,
    params: {
      datasetName: string
      datasetType: string
      format?: string
      description?: string
      datasetSource?: string
      localPath?: string
    },
    onProgress?: (percent: number) => void
  ) => {
    const formData = new FormData()
    if (file) formData.append('file', file)
    formData.append('datasetName', params.datasetName)
    formData.append('datasetType', params.datasetType)
    if (params.format) formData.append('format', params.format)
    if (params.description) formData.append('description', params.description)
    if (params.datasetSource) formData.append('datasetSource', params.datasetSource)
    if (params.localPath) formData.append('localPath', params.localPath)

    return uploadRequest.post('/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  },

  /**
   * 获取数据集列表
   */
  getList: (params: { page: number; pageSize?: number; search?: string }) =>
    request.get('/datasets', { params }),

  /**
   * 获取数据集详情
   */
  getDetail: (datasetId: string) =>
    request.get(`/datasets/${datasetId}`),

  /**
   * 删除数据集
   */
  delete: (datasetId: string) =>
    request.delete(`/datasets/${datasetId}`),

  /**
   * 重新验证数据集
   */
  validate: (datasetId: string) =>
    request.post(`/datasets/${datasetId}/validate`)
}

// ==================== 训练 API ====================
export const trainingApi = {
  /**
   * 创建训练任务
   */
  createJob: (data: {
    jobName: string
    baseModel?: string  // 预训练模型名称（yolov8n.pt 等）
    baseModelId?: string  // 可选：仅在微调已有模型时需要
    datasetId: string
    epochs: number
    batchSize: number
    imgSize: number
    useGpu: boolean
    // 超参数（YOLOv8）
    optimizer?: string
    lr0?: number
    weightDecay?: number
    workers?: number
    warmupEpochs?: number
    savePeriod?: number
    mosaic?: number
    mixup?: number
  }) => request.post('/training', data),

  /**
   * 获取训练任务列表
   */
  getList: (params: {
    page: number
    pageSize?: number
    status?: string
  }) => request.get('/training', { params }),

  /**
   * 获取训练任务详情
   */
  getJob: (jobId: string) =>
    request.get(`/training/${jobId}`),

  /**
   * 启动训练任务
   */
  startJob: (jobId: string) =>
    request.post(`/training/${jobId}/start`),

  /**
   * 停止训练
   */
  stopJob: (jobId: string) =>
    request.post(`/training/${jobId}/stop`),

  /**
   * 暂停训练
   */
  pauseJob: (jobId: string) =>
    request.post(`/training/${jobId}/pause`),

  /**
   * 恢复训练
   */
  resumeJob: (jobId: string) =>
    request.post(`/training/${jobId}/resume`),

  /**
   * 获取训练日志
   */
  getLogs: (jobId: string, lines?: number) =>
    request.get(`/training/${jobId}/logs`, { params: { lines } }),

  /**
   * 验证模型
   */
  val: (data: any) => request.post('/training/val', data),

  /**
   * 导出模型
   */
  export: (data: any) => request.post('/training/export', data),

  /**
   * AutoTrain - 自动化训练
   */
  autoTrain: (data: {
    jobName: string
    datasetId: string
    taskType: 'detect' | 'classify' | 'segment' | 'pose'
    optimizationTarget: 'map50_95' | 'map50' | 'precision' | 'recall'
    maxEpochs: number
    maxTrials: number
    baseModel?: string
  }) => request.post('/training/autotrain', data),

  /**
   * 超参数调优
   */
  tuneHyperparameters: (
    jobId: string,
    data: {
      nTrials: number
      timeout?: number
      studyName?: string
      direction?: 'maximize' | 'minimize'
    }
  ) => request.post(`/training/${jobId}/tune`, data),

  /**
   * 获取验证结果
   */
  getValidationResults: (jobId: string) =>
    request.get(`/training/${jobId}/validation/results`),

  /**
   * 获取训练指标历史
   */
  getMetricsHistory: (jobId: string) =>
    request.get(`/training/${jobId}/metrics/history`),

  /**
   * 删除训练任务
   */
  deleteJob: (jobId: string) =>
    request.delete(`/training/${jobId}`),

  /**
   * 部署训练好的模型
   */
  deployModel: (jobId: string, deviceIds: string[]) =>
    request.post(`/training/${jobId}/deploy`, { deviceIds }),

  /**
   * 获取任务的实际训练进度（从 results.csv 读取，用于续训）
   * 通过后端代理调用训练服务
   */
  getActualProgress: (jobId: string) =>
    request.get(`/training/${jobId}/actual-progress`)
}

// ==================== 模型 API ====================
export const modelApi = {
  /**
   * 创建模型记录
   */
  create: (data: {
    modelName: string
    modelType: string
    framework: string
    version: string
  }) => request.post('/models', data),

  /**
   * 上传模型文件
   */
  upload: (
    modelId: string,
    file: File,
    onProgress?: (percent: number) => void
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    return uploadRequest.post(`/models/${modelId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  },

  /**
   * 获取模型列表
   */
  getList: (params: {
    page?: number
    pageSize?: number
    type?: string
    status?: string
  }) => request.get('/models', { params }),

  /**
   * 获取模型详情
   */
  getDetail: (modelId: string) =>
    request.get(`/models/${modelId}`),

  /**
   * 获取可部署模型列表
   */
  getDeployable: () =>
    request.get('/models/deployable'),

  /**
   * 转换模型格式
   */
  convert: (
    modelId: string,
    conversionType: 'ONNX' | 'TENSORRT'
  ) => request.post(`/models/${modelId}/convert`, null, {
    params: { conversionType }
  }),

  /**
   * 部署模型
   */
  deploy: (data: {
    modelId: string
    deviceIds: string[]
  }) => request.post('/models/deploy', data),

  /**
   * 获取模型指标
   */
  getMetrics: (modelId: string) =>
    request.get(`/models/${modelId}`),

  /**
   * 删除模型
   */
  delete: (modelId: string) =>
    request.delete(`/models/${modelId}`)
}

// ==================== OTA API ====================
export const otaApi = {
  /**
   * 创建升级任务
   */
  createTask: (data: {
    taskName: string
    upgradeType: 'model' | 'firmware'
    modelId?: string
    deviceIds: string[]
    description?: string
  }) => request.post('/ota/tasks', data),

  /**
   * 开始升级
   */
  start: (taskId: string) =>
    request.post(`/ota/tasks/${taskId}/start`),

  /**
   * 获取升级任务列表
   */
  getList: (params: {
    page?: number
    pageSize?: number
    status?: string
  }) => request.get('/ota/tasks', { params }),

  /**
   * 获取任务详情
   */
  getDetail: (taskId: string) =>
    request.get(`/ota/tasks/${taskId}`),

  /**
   * 获取任务设备列表
   */
  getDevices: (taskId: string) =>
    request.get(`/ota/tasks/${taskId}/devices`),

  /**
   * 获取升级进度
   */
  getProgress: (taskId: string) =>
    request.get(`/ota/tasks/${taskId}`),

  /**
   * 回滚
   */
  rollback: (taskId: string, deviceId: string) =>
    request.post(`/ota/tasks/${taskId}/devices/${deviceId}/rollback`),

  /**
   * 重试失败设备
   */
  retryFailed: (taskId: string) =>
    request.post(`/ota/tasks/${taskId}/retry`),

  /**
   * 重试单个设备
   */
  retryDevice: (taskId: string, deviceId: string) =>
    request.post(`/ota/tasks/${taskId}/devices/${deviceId}/retry`),

  /**
   * 暂停任务
   */
  pause: (taskId: string) =>
    request.post(`/ota/tasks/${taskId}/pause`),

  /**
   * 恢复任务
   */
  resume: (taskId: string) =>
    request.post(`/ota/tasks/${taskId}/resume`),

  /**
   * 删除任务
   */
  delete: (taskId: string) =>
    request.delete(`/ota/tasks/${taskId}`)
}

// ==================== 设备兼容性检查 API ====================
export const compatibilityApi = {
  /**
   * 批量检查设备兼容性
   */
  check: (data: {
    modelId: string
    deviceIds: string[]
  }) => request.post('/compatibility/check', data),

  /**
   * 检查单个设备兼容性
   */
  checkSingle: (deviceId: string, modelId: string) =>
    request.get(`/compatibility/check/${deviceId}/${modelId}`),

  /**
   * 获取支持的设备类型列表
   */
  getDeviceTypes: () =>
    request.get('/compatibility/device-types')
}

// ==================== 推理 API ====================
export const inferenceApi = {
  /**
   * 启动推理
   */
  start: (data: { deviceId: string; modelId: string }) =>
    request.post('/inference/start', data),

  /**
   * 停止推理
   */
  stop: (data: { deviceId: string }) =>
    request.post('/inference/stop', data),

  /**
   * 获取推理状态
   */
  getStatus: (deviceId: string) =>
    request.get(`/inference/status`, { params: { deviceId } }),

  /**
   * 预测
   */
  predict: (data: any) =>
    request.post('/inference/predict', data)
}

// ==================== 数据集统计 API ====================
export const datasetStatsApi = {
  /**
   * 获取数据集统计
   */
  getStats: () =>
    request.get('/datasets/stats'),

  /**
   * 获取可用数据集列表
   */
  getAvailable: () =>
    request.get('/datasets/available')
}

// ==================== 模型转换 API ====================
export const conversionApi = {
  /**
   * 启动转换任务
   */
  start: (taskId: string) =>
    request.post(`/conversion/${taskId}/start`),

  /**
   * 获取转换任务详情
   */
  getTask: (taskId: string) =>
    request.get(`/conversion/tasks/${taskId}`),

  /**
   * 根据模型ID查询转换任务
   */
  getTasksByModel: (modelId: string) =>
    request.get(`/conversion/models/${modelId}/tasks`),

  /**
   * 分页查询转换任务
   */
  getList: (params: {
    page?: number
    pageSize?: number
    status?: string
  }) => request.get('/conversion/tasks', { params }),

  /**
   * 删除转换任务
   */
  delete: (taskId: string) =>
    request.delete(`/conversion/tasks/${taskId}`)
}
