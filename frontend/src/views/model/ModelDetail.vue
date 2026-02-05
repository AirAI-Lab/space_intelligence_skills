<template>
  <div class="model-detail" v-loading="loading">
    <!-- 返回按钮 -->
    <el-page-header @back="goBack" title="模型详情" class="header">
      <template #content>
        <div class="model-title">
          <el-tag :type="getStatusType(model?.status)" size="large">
            {{ getStatusText(model?.status) }}
          </el-tag>
          <span class="model-name">{{ model?.modelName }}</span>
        </div>
      </template>
    </el-page-header>

    <!-- 转换对话框 -->
    <el-dialog v-model="convertDialogVisible" title="模型格式转换" width="500px">
      <el-form label-width="100px">
        <el-form-item label="目标格式">
          <el-select v-model="selectedConversionType" style="width: 100%">
            <el-option label="PT → ONNX" value="PT_TO_ONNX" />
            <el-option label="ONNX → TensorRT FP16" value="ONNX_TO_ENGINE_FP16" />
            <el-option label="ONNX → TensorRT INT8" value="ONNX_TO_ENGINE_INT8" />
            <el-option label="ONNX → TensorRT FP32" value="ONNX_TO_ENGINE_FP32" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="convertDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startConversion" :loading="converting">开始转换</el-button>
      </template>
    </el-dialog>

    <!-- 一键部署对话框 -->
    <el-dialog v-model="deployDialogVisible" title="一键部署模型" width="800px">
      <el-steps :active="deployStep" align-center class="deploy-steps">
        <el-step title="选择设备" />
        <el-step title="兼容性检查" />
        <el-step title="确认部署" />
      </el-steps>

      <div class="deploy-content">
        <!-- 步骤1: 选择设备 -->
        <div v-if="deployStep === 0" class="step-content">
          <el-form label-width="100px">
            <el-form-item label="设备筛选">
              <el-select
                v-model="deviceFilter"
                placeholder="设备状态"
                clearable
                style="width: 150px"
                @change="loadDevices"
              >
                <el-option label="全部" value="" />
                <el-option label="在线" value="ONLINE" />
                <el-option label="离线" value="OFFLINE" />
              </el-select>
              <el-button type="primary" @click="loadDevices" style="margin-left: 10px">
                刷新
              </el-button>
            </el-form-item>

            <el-form-item label="选择设备">
              <el-table
                :data="devices"
                @selection-change="handleDeviceSelection"
                style="width: 100%"
                max-height="300"
              >
                <el-table-column type="selection" width="55" />
                <el-table-column prop="deviceId" label="设备ID" width="120" />
                <el-table-column prop="deviceName" label="设备名称" />
                <el-table-column prop="status" label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.status === 'ONLINE' ? 'success' : 'info'">
                      {{ row.status === 'ONLINE' ? '在线' : '离线' }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-form-item>
          </el-form>
        </div>

        <!-- 步骤2: 兼容性检查 -->
        <div v-if="deployStep === 1" class="step-content">
          <div v-if="checkingDevices" class="checking">
            <el-progress :percentage="checkProgress" :indeterminate="true" />
            <p style="text-align: center; margin-top: 10px">正在检查设备兼容性...</p>
          </div>
          <div v-else>
            <el-table :data="compatibilityList" style="width: 100%">
              <el-table-column prop="deviceName" label="设备" width="150" />
              <el-table-column prop="status" label="兼容性" width="120">
                <template #default="{ row }">
                  <el-tag
                    :type="getCompatibilityTagType(row.status)"
                    v-text="getCompatibilityText(row.status)"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="score" label="得分" width="100">
                <template #default="{ row }">
                  <el-progress
                    :percentage="row.score || 0"
                    :color="getScoreColor(row.score)"
                    :show-text="true"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 步骤3: 确认部署 -->
        <div v-if="deployStep === 2" class="step-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="模型名称">{{ model?.modelName }}</el-descriptions-item>
            <el-descriptions-item label="模型格式">{{ getDeployFormat() }}</el-descriptions-item>
            <el-descriptions-item label="部署设备数">{{ selectedDevices.length }}</el-descriptions-item>
            <el-descriptions-item label="兼容设备">
              {{ compatibleCount }} / {{ selectedDevices.length }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="deployDialogVisible = false">取消</el-button>
          <el-button
            v-if="deployStep > 0"
            @click="deployStep--"
            :disabled="deploying"
          >
            上一步
          </el-button>
          <el-button
            v-if="deployStep < 2"
            type="primary"
            @click="nextDeployStep"
            :disabled="deployStep === 0 && selectedDevices.length === 0"
          >
            下一步
          </el-button>
          <el-button
            v-if="deployStep === 2"
            type="primary"
            @click="executeDeploy"
            :loading="deploying"
            :disabled="compatibleCount === 0"
          >
            开始部署
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 基本信息 -->
    <el-card class="info-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">基本信息</span>
          <div class="actions">
            <el-button type="primary" @click="deployModel" :disabled="!isDeployable">
              <el-icon><Upload /></el-icon>
              部署
            </el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="模型ID">{{ model?.modelId }}</el-descriptions-item>
        <el-descriptions-item label="模型名称">{{ model?.modelName }}</el-descriptions-item>
        <el-descriptions-item label="模型类型">
          <el-tag>{{ model?.modelType }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="框架">{{ model?.framework }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ model?.version }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatSize(model?.fileSizeBytes) }}</el-descriptions-item>
        <el-descriptions-item label="mAP@0.5">
          <span v-if="model?.map50" class="metric-value">{{ (model.map50 * 100).toFixed(2) }}%</span>
          <span v-else-if="model?.map" class="metric-value">{{ (model.map * 100).toFixed(2) }}%</span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="推理时间">
          <span v-if="model?.inferenceTimeMs" class="metric-value">{{ model.inferenceTimeMs }} ms</span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="部署设备数">{{ model?.deployedCount || 0 }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ model?.createdAt }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 性能指标 -->
    <el-card class="metrics-card" shadow="never" v-if="model?.map">
      <template #header>
        <span class="card-title">性能指标</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="metric in metrics" :key="metric.label">
          <div class="metric-item">
            <div class="metric-label">{{ metric.label }}</div>
            <div class="metric-value" :style="{ color: metric.color }">
              {{ metric.value }}
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 模型格式 -->
    <el-card class="formats-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">可用格式</span>
        </div>
      </template>

      <el-table :data="formats" style="width: 100%">
        <el-table-column prop="format" label="格式" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.format }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="文件路径" />
        <el-table-column prop="size" label="文件大小" width="150">
          <template #default="{ row }">
            {{ formatSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="downloadFormat(row)" :disabled="!row.path">
              下载
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click="convertFormat"
              v-if="row.format === 'PT' && !formats.find(f => f.format === 'ONNX')?.path"
            >
              转换ONNX
            </el-button>
            <el-button
              size="small"
              type="warning"
              @click="reconvertFormat(row)"
              v-if="row.format === 'ONNX' && row.path"
            >
              重新转换
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 部署历史 -->
    <el-card class="history-card" shadow="never">
      <template #header>
        <span class="card-title">部署历史</span>
      </template>

      <el-timeline v-if="deploymentHistory.length > 0">
        <el-timeline-item
          v-for="item in deploymentHistory"
          :key="item.id"
          :timestamp="item.deployed_at"
          placement="top"
        >
          <el-card>
            <h4>{{ item.device_name }}</h4>
            <p>状态: <el-tag :type="item.status === 'active' ? 'success' : 'info'">{{ item.status }}</el-tag></p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无部署记录" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi, conversionApi, deviceApi, compatibilityApi, otaApi } from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const model = ref<any>(null)
const deploymentHistory = ref<any[]>([])
const convertDialogVisible = ref(false)
const converting = ref(false)
const selectedConversionType = ref('PT_TO_ONNX')

// 部署相关状态
const deployDialogVisible = ref(false)
const deploying = ref(false)
const devices = ref<any[]>([])
const selectedDevices = ref<string[]>([])
const deviceFilter = ref('')
const checkingDevices = ref(false)
const compatibilityResults = ref<Map<string, any>>(new Map())
const checkProgress = ref(0)
const deployStep = ref(0)
const deployStrategy = ref('immediate')
const gradualBatchSize = ref(5)
const gradualInterval = ref(30)
let refreshTimer: any = null

// 部署相关computed
const compatibilityList = computed(() => {
  return Array.from(compatibilityResults.value.values()).map(r => ({
    deviceId: r.deviceId,
    deviceName: r.deviceName,
    status: r.status,
    score: r.score,
    warnings: r.warnings,
    errors: r.errors
  }))
})

const compatibleCount = computed(() => {
  return Array.from(compatibilityResults.value.values()).filter(
    r => r.status === 'COMPATIBLE' || r.status === 'COMPATIBLE_WITH_WARNING'
  ).length
})

const incompatibleCount = computed(() => {
  return selectedDevices.value.length - compatibleCount.value
})

const metrics = computed(() => {
  if (!model.value) return []

  const m = []
  // 优先显示 mAP@0.5 (map50)，这是用户最关心的指标
  if (model.value.map50) {
    m.push({ label: 'mAP@0.5', value: (model.value.map50 * 100).toFixed(2) + '%', color: '#409EFF' })
  } else if (model.value.map) {
    // 如果没有 map50，使用 map (mAP50-95) 但标注清楚
    m.push({ label: 'mAP@0.5:0.95', value: (model.value.map * 100).toFixed(2) + '%', color: '#409EFF' })
  }
  if (model.value.precision) {
    m.push({ label: 'Precision', value: (model.value.precision * 100).toFixed(2) + '%', color: '#67C23A' })
  }
  if (model.value.recall) {
    m.push({ label: 'Recall', value: (model.value.recall * 100).toFixed(2) + '%', color: '#E6A23C' })
  }
  if (model.value.f1) {
    m.push({ label: 'F1 Score', value: model.value.f1.toFixed(3), color: '#F56C6C' })
  }
  return m
})

const formats = computed(() => {
  if (!model.value) return []

  const f = []
  if (model.value.ptFilePath) {
    f.push({ format: 'PT', path: model.value.ptFilePath, size: model.value.ptFileSizeBytes || 0 })
  }
  if (model.value.onnxFilePath) {
    f.push({ format: 'ONNX', path: model.value.onnxFilePath, size: model.value.onnxFileSizeBytes || 0 })
  }
  if (model.value.engineFilePath) {
    f.push({ format: 'TensorRT', path: model.value.engineFilePath, size: model.value.engineFileSizeBytes || 0 })
  }
  return f
})

const isDeployable = computed(() => {
  return model.value?.status === 'READY' && formats.value.length > 0
})

// 加载模型详情
const loadModelDetail = async () => {
  const modelId = route.params.id as string
  console.log('Loading model detail for ID:', modelId)
  loading.value = true
  try {
    const response = await modelApi.getDetail(modelId)
    model.value = response.data
    console.log('Model loaded successfully:', model.value?.modelName)

    // 如果模型正在转换，开始轮询
    if (model.value?.status === 'CONVERTING') {
      startPollingConversion()
    }
  } catch (error: any) {
    console.error('Failed to load model detail:', error)
    ElMessage.error('加载模型详情失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 格式化文件大小
const formatSize = (bytes: number) => {
  if (!bytes) return '-'
  if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(2) + ' KB'
  }
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    READY: 'success',
    TRAINING: 'warning',
    CONVERTING: 'primary',
    DEPLOYED: 'primary',
    ARCHIVED: 'info',
    ERROR: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    READY: '就绪',
    TRAINING: '训练中',
    CONVERTING: '转换中',
    DEPLOYED: '已部署',
    ARCHIVED: '已归档',
    ERROR: '错误'
  }
  return texts[status] || status
}

// 返回
const goBack = () => {
  router.push('/model')
}

// 下载模型
const downloadModel = () => {
  ElMessage.success('开始下载模型')
}

// 下载指定格式
const downloadFormat = async (format: any) => {
  if (!model.value?.modelId || !format.path) {
    ElMessage.warning('文件路径不存在')
    return
  }

  // 确定下载格式参数
  let downloadFormat = 'engine'
  if (format.format === 'PT') {
    downloadFormat = 'pt'
  } else if (format.format === 'ONNX') {
    downloadFormat = 'onnx'
  } else if (format.format === 'TensorRT') {
    downloadFormat = 'engine'
  }

  // 构建下载 URL
  const downloadUrl = `/api/v1/models/${model.value.modelId}/download?format=${downloadFormat}`

  try {
    // 使用 fetch API 获取二进制数据
    const response = await fetch(downloadUrl)

    if (!response.ok) {
      // 尝试解析错误信息
      const errorText = await response.text()
      let errorMessage = '下载失败'
      try {
        const errorJson = JSON.parse(errorText)
        errorMessage = errorJson.message || errorMessage
      } catch {
        errorMessage = errorText || errorMessage
      }
      ElMessage.error(errorMessage)
      return
    }

    // 检查响应类型是否为二进制
    const contentType = response.headers.get('Content-Type')
    if (contentType && contentType.includes('application/json')) {
      // 如果返回的是 JSON，说明服务器返回了错误
      const errorJson = await response.json()
      ElMessage.error(errorJson.message || '下载失败')
      return
    }

    // 获取文件名（从响应头或使用默认值）
    let filename = `${model.value.modelName}_${format.format.toLowerCase()}.${downloadFormat === 'engine' ? 'engine' : downloadFormat}`
    const contentDisposition = response.headers.get('Content-Disposition')
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '')
      }
    }

    // 获取二进制数据
    const blob = await response.blob()

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // 释放 URL 对象
    window.URL.revokeObjectURL(url)

    ElMessage.success(`开始下载 ${format.format} 格式`)
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败: ' + (error.message || '未知错误'))
  }
}

// 打开转换对话框
const convertFormat = () => {
  convertDialogVisible.value = true
}

// 重新转换格式（删除旧文件并重新转换）
const reconvertFormat = async (format: any) => {
  if (!model.value?.modelId) {
    ElMessage.error('模型ID不存在')
    return
  }

  // 根据格式确定转换类型
  let conversionType: 'PT_TO_ONNX' | 'ONNX_TO_ENGINE_FP16' | 'ONNX_TO_ENGINE_INT8' | 'ONNX_TO_ENGINE_FP32' = 'PT_TO_ONNX'
  if (format.format === 'ONNX') {
    conversionType = 'PT_TO_ONNX'
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除旧的 ${format.format} 文件并重新转换吗？此操作不可恢复。`,
      '确认重新转换',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    converting.value = true
    await modelApi.reconvert(model.value.modelId, conversionType)

    ElMessage.success('重新转换任务已启动')

    // 开始轮询转换状态
    startPollingConversion()

    // 刷新模型详情
    await loadModelDetail()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重新转换失败: ' + (error.message || '未知错误'))
    }
  } finally {
    converting.value = false
  }
}

// 开始转换
const startConversion = async () => {
  if (!model.value?.modelId) {
    ElMessage.error('模型ID不存在')
    return
  }

  converting.value = true
  try {
    // 直接调用 modelApi.convert，它会创建并启动转换任务
    const result = await modelApi.convert(model.value.modelId, selectedConversionType.value)

    ElMessage.success('转换任务已启动')
    convertDialogVisible.value = false

    // 开始轮询转换状态
    startPollingConversion()

    // 刷新模型详情
    await loadModelDetail()
  } catch (error: any) {
    ElMessage.error('转换失败: ' + (error.message || '未知错误'))
  } finally {
    converting.value = false
  }
}

// 轮询转换状态
const startPollingConversion = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }

  refreshTimer = setInterval(async () => {
    await loadModelDetail()

    // 如果模型不再处于转换状态，停止轮询
    if (model.value?.status !== 'CONVERTING' && refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
      ElMessage.success('模型转换完成')
    }
  }, 3000)
}

// ==================== 部署相关函数 ====================

// 修改部署模型函数，打开部署对话框
const deployModel = () => {
  deployStep.value = 0
  selectedDevices.value = []
  compatibilityResults.value.clear()
  deployDialogVisible.value = true
  loadDevices()
}

// 加载设备列表
const loadDevices = async () => {
  try {
    const response = await deviceApi.getList({
      page: 1,
      pageSize: 100,
      status: deviceFilter.value || undefined
    })
    devices.value = response.data?.items || []
  } catch (error: any) {
    ElMessage.error('加载设备列表失败: ' + (error.message || '未知错误'))
  }
}

// 设备选择变化
const handleDeviceSelection = (selection: any[]) => {
  selectedDevices.value = selection.map((s: any) => s.deviceId)
}

// 下一步
const nextDeployStep = async () => {
  if (deployStep.value === 0) {
    // 进入兼容性检查
    await checkCompatibility()
  } else if (deployStep.value === 1) {
    // 进入确认步骤
    deployStep.value++
  }
}

// 检查兼容性
const checkCompatibility = async () => {
  if (selectedDevices.value.length === 0) {
    ElMessage.warning('请先选择设备')
    return
  }

  checkingDevices.value = true
  checkProgress.value = 0

  try {
    const response = await compatibilityApi.check({
      modelId: model.value.modelId,
      deviceIds: selectedDevices.value
    })

    compatibilityResults.value = new Map(
      Object.entries(response.data)
    )

    ElMessage.success('兼容性检查完成')
    deployStep.value++
  } catch (error: any) {
    ElMessage.error('兼容性检查失败: ' + (error.message || '未知错误'))
  } finally {
    checkingDevices.value = false
  }
}

// 获取兼容性标签类型
const getCompatibilityTagType = (status: string) => {
  const types: Record<string, string> = {
    COMPATIBLE: 'success',
    COMPATIBLE_WITH_WARNING: 'warning',
    NOT_COMPATIBLE: 'danger',
    UNKNOWN: 'info'
  }
  return types[status] || 'info'
}

// 获取兼容性文本
const getCompatibilityText = (status: string) => {
  const texts: Record<string, string> = {
    COMPATIBLE: '完全兼容',
    COMPATIBLE_WITH_WARNING: '兼容',
    NOT_COMPATIBLE: '不兼容',
    UNKNOWN: '未知'
  }
  return texts[status] || status
}

// 获取得分颜色
const getScoreColor = (score: number) => {
  if (score >= 80) return '#67C23A'
  if (score >= 50) return '#E6A23C'
  return '#F56C6C'
}

// 获取部署格式
const getDeployFormat = () => {
  if (model.value?.engineFilePath) return 'TensorRT Engine'
  if (model.value?.onnxFilePath) return 'ONNX'
  return 'PyTorch'
}

// 执行部署
const executeDeploy = async () => {
  if (compatibleCount.value === 0) {
    ElMessage.warning('没有兼容的设备可以部署')
    return
  }

  deploying.value = true
  try {
    // 筛选兼容的设备
    const compatibleDeviceIds = Array.from(compatibilityResults.value.entries())
      .filter(([_, r]) => r.status === 'COMPATIBLE' || r.status === 'COMPATIBLE_WITH_WARNING')
      .map(([deviceId, _]) => deviceId)

    await otaApi.createTask({
      taskName: `${model.value.modelName} 部署`,
      upgradeType: 'MODEL',
      modelId: model.value.modelId,
      deviceIds: compatibleDeviceIds,
      targetVersion: model.value.version || '1.0.0',
      description: deployStrategy.value === 'gradual' ? `灰度发布: 每批${gradualBatchSize.value}台` : undefined
    })

    ElMessage.success('部署任务已创建')
    deployDialogVisible.value = false

    // 跳转到OTA任务页面
    router.push('/ota')
  } catch (error: any) {
    ElMessage.error('创建部署任务失败: ' + (error.message || '未知错误'))
  } finally {
    deploying.value = false
  }
}

onMounted(async () => {
  await loadModelDetail()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.model-detail {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-name {
  font-size: 20px;
  font-weight: 600;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.info-card,
.metrics-card,
.formats-card,
.history-card {
  margin-bottom: 20px;
}

.metric-item {
  text-align: center;
  padding: 20px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
}

/* 部署对话框样式 */
.deploy-steps {
  margin-bottom: 20px;
  margin-top: 10px;
}

.step-content {
  min-height: 300px;
  padding: 20px 0;
}

.checking {
  padding: 40px 0;
  text-align: center;
}
</style>
