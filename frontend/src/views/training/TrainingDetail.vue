<template>
  <div class="training-detail" v-loading="loading">
    <!-- 页面头部 -->
    <el-page-header @back="goBack" title="返回" class="header">
      <template #content>
        <div class="title-content">
          <el-tag :type="getStatusType(job?.status)" size="large">
            {{ getStatusText(job?.status) }}
          </el-tag>
          <span class="job-name">{{ job?.jobName }}</span>
        </div>
      </template>
      <template #extra>
        <div class="header-actions">
          <el-button
            v-if="job?.status === 'RUNNING'"
            type="warning"
            @click="handleStop"
            :loading="stopping"
          >
            <el-icon><CircleClose /></el-icon>
            停止训练
          </el-button>
          <el-button
            v-if="job?.status === 'COMPLETED'"
            type="success"
            @click="handleDeploy"
          >
            <el-icon><Upload /></el-icon>
            部署模型
          </el-button>
          <el-button @click="loadJobDetail">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
    </el-page-header>

    <!-- 训练进度卡片 -->
    <el-card class="progress-card" shadow="never">
      <template #header>
        <span class="card-title">训练进度</span>
      </template>
      <div class="progress-content">
        <div class="progress-info">
          <div class="epoch-info">
            <span class="label">训练轮次:</span>
            <span class="value">{{ job?.currentEpoch || 0 }} / {{ job?.epochs || 0 }}</span>
          </div>
          <div class="time-info">
            <span class="label">开始时间:</span>
            <span class="value">{{ job?.startedAt || '-' }}</span>
          </div>
          <div class="time-info" v-if="job?.status === 'COMPLETED'">
            <span class="label">完成时间:</span>
            <span class="value">{{ job?.completedAt || '-' }}</span>
          </div>
        </div>
        <el-progress
          :percentage="(job?.progress || 0) * 100"
          :status="getProgressStatus(job?.status)"
          :stroke-width="20"
        >
          <template #default="{ percentage }">
            <span class="percentage-text">{{ percentage.toFixed(1) }}%</span>
          </template>
        </el-progress>
      </div>
    </el-card>

    <!-- 训练指标卡片 -->
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card class="metrics-card" shadow="never">
          <template #header>
            <span class="card-title">训练指标</span>
          </template>
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-label">mAP@0.5:0.95</div>
              <div class="metric-value success">{{ formatPercent(job?.finalMap) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">Loss</div>
              <div class="metric-value info">{{ formatFloat(job?.finalLoss) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">最佳轮次</div>
              <div class="metric-value primary">{{ job?.bestEpoch || '-' }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">当前轮次</div>
              <div class="metric-value warning">{{ job?.currentEpoch || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card class="config-card" shadow="never">
          <template #header>
            <span class="card-title">训练配置</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="基础模型">{{ job?.baseModel || job?.baseModelName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="数据集">{{ job?.datasetName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="训练轮次">{{ job?.epochs || 0 }}</el-descriptions-item>
            <el-descriptions-item label="批次大小">{{ job?.batchSize || 0 }}</el-descriptions-item>
            <el-descriptions-item label="图像大小">{{ job?.imgSize || 0 }}</el-descriptions-item>
            <el-descriptions-item label="使用 GPU">
              <el-tag :type="job?.useGpu ? 'success' : 'info'">
                {{ job?.useGpu ? '是' : '否' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ job?.createdAt || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 训练日志卡片 -->
    <el-card class="logs-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">训练日志</span>
          <el-button size="small" @click="loadLogs">
            <el-icon><Refresh /></el-icon>
            刷新日志
          </el-button>
        </div>
      </template>
      <div class="logs-container" ref="logsContainer">
        <div v-if="logs.length === 0" class="empty-logs">暂无日志</div>
        <div v-else class="logs-content">
          <div
            v-for="(log, index) in logs"
            :key="index"
            class="log-line"
            :class="getLogLevelClass(log)"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-level">{{ log.level }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleClose, Upload, Refresh } from '@element-plus/icons-vue'
import { trainingApi } from '@/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const stopping = ref(false)
const job = ref<any>(null)
const logs = ref<any[]>([])
const logsContainer = ref<HTMLElement>()
let refreshTimer: any = null

// 加载训练任务详情
const loadJobDetail = async () => {
  const jobId = route.params.id as string
  loading.value = true
  try {
    const response = await trainingApi.getJob(jobId)
    job.value = response.data
  } catch (error: any) {
    ElMessage.error('加载任务详情失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 加载训练日志
const loadLogs = async () => {
  const jobId = route.params.id as string
  try {
    const response = await trainingApi.getLogs(jobId, 100)
    // 处理不同的响应格式
    if (response.data?.data?.logs) {
      // 训练服务返回的格式: { data: { logs: [...] } }
      logs.value = response.data.data.logs
    } else if (response.data?.logs) {
      // 后端直接返回的格式: { logs: [...] }
      logs.value = response.data.logs
    } else {
      logs.value = []
    }
    await nextTick()
    scrollToBottom()
  } catch (error: any) {
    // 日志加载失败，显示提示信息
    logs.value = [{
      time: new Date().toLocaleTimeString(),
      level: 'INFO',
      message: '无法加载训练日志，请确保训练服务正在运行'
    }]
    console.error('加载日志失败:', error)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (logsContainer.value) {
    const container = logsContainer.value
    container.scrollTop = container.scrollHeight
  }
}

// 停止训练
const handleStop = async () => {
  ElMessageBox.confirm(
    `确定要停止训练任务 "${job.value.jobName}" 吗？`,
    '确认停止',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    stopping.value = true
    try {
      await trainingApi.stopJob(job.value.jobId)
      ElMessage.success('任务已停止')
      await loadJobDetail()
    } catch (error: any) {
      ElMessage.error('停止任务失败: ' + (error.message || '未知错误'))
    } finally {
      stopping.value = false
    }
  }).catch(() => {})
}

// 部署模型
const handleDeploy = () => {
  router.push({
    path: '/ota',
    query: { modelId: job.value.outputModelId }
  })
  ElMessage.success(`准备部署模型: ${job.value.jobName}`)
}

// 返回列表
const goBack = () => {
  router.push('/training')
}

// 格式化百分比
const formatPercent = (value: number | null) => {
  if (value === null || value === undefined) return '-'
  return (value * 100).toFixed(2) + '%'
}

// 格式化浮点数
const formatFloat = (value: number | null) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(6)
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    RUNNING: 'primary',
    COMPLETED: 'success',
    PENDING: 'info',
    FAILED: 'danger',
    PAUSED: 'warning',
    CANCELLED: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    RUNNING: '运行中',
    COMPLETED: '已完成',
    PENDING: '等待中',
    FAILED: '失败',
    PAUSED: '已暂停',
    CANCELLED: '已取消'
  }
  return texts[status] || status
}

// 获取进度状态
const getProgressStatus = (status: string) => {
  const statuses: Record<string, any> = {
    COMPLETED: 'success',
    FAILED: 'exception',
    CANCELLED: 'warning'
  }
  return statuses[status] || undefined
}

// 获取日志级别样式
const getLogLevelClass = (log: any) => {
  const level = log.level?.toLowerCase() || ''
  if (level === 'error') return 'log-error'
  if (level === 'warning') return 'log-warning'
  if (level === 'info') return 'log-info'
  return ''
}

onMounted(() => {
  loadJobDetail()
  loadLogs()  // 启用日志加载

  // 定时刷新运行中的任务
  refreshTimer = setInterval(() => {
    if (job.value?.status === 'RUNNING') {
      loadJobDetail()
      loadLogs()  // 启用日志加载
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.training-detail {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.title-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.job-name {
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.progress-card,
.metrics-card,
.config-card,
.logs-card {
  margin-bottom: 20px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-content {
  padding: 10px 0;
}

.progress-info {
  display: flex;
  gap: 30px;
  margin-bottom: 15px;
}

.epoch-info,
.time-info {
  display: flex;
  gap: 8px;
}

.epoch-info .label,
.time-info .label {
  color: var(--el-text-color-secondary);
}

.epoch-info .value,
.time-info .value {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.percentage-text {
  font-size: 14px;
  font-weight: 500;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.metric-item {
  text-align: center;
  padding: 15px;
  background: var(--el-bg-color-page);
  border-radius: 8px;
}

.metric-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: 600;
}

.metric-value.primary {
  color: #409EFF;
}

.metric-value.success {
  color: #67C23A;
}

.metric-value.warning {
  color: #E6A23C;
}

.metric-value.danger {
  color: #F56C6C;
}

.metric-value.info {
  color: #909399;
}

.logs-container {
  max-height: 400px;
  overflow-y: auto;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 10px;
}

.empty-logs {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 40px;
}

.logs-content {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.log-line {
  padding: 4px 8px;
  border-radius: 2px;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-time {
  color: #858585;
  margin-right: 8px;
}

.log-level {
  margin-right: 8px;
  font-weight: 500;
}

.log-error .log-level {
  color: #F56C6C;
}

.log-warning .log-level {
  color: #E6A23C;
}

.log-info .log-level {
  color: #409EFF;
}

.log-message {
  color: #d4d4d4;
}
</style>
