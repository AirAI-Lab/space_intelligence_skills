<template>
  <div class="ota-task">
    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-space>
            <el-input
              v-model="searchText"
              placeholder="搜索任务名称"
              clearable
              style="width: 250px;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select v-model="statusFilter" placeholder="任务状态" clearable style="width: 150px;">
              <el-option label="全部" value="" />
              <el-option label="待升级" value="PENDING" />
              <el-option label="升级中" value="UPGRADING" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="失败" value="FAILED" />
            </el-select>
            <el-button type="primary" @click="loadTasks">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetFilter">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="6" style="text-align: right;">
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>
            创建升级任务
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="table-card">
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="taskName" label="任务名称" width="200" />
        <el-table-column prop="upgradeType" label="升级类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.upgradeType === 'MODEL' ? 'primary' : 'success'">
              {{ row.upgradeType === 'MODEL' ? '模型升级' : '固件升级' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="targetVersion" label="目标版本" width="150" />
        <el-table-column prop="targetDevices" label="目标设备数" width="120" />
        <el-table-column prop="completedCount" label="已完成" width="100">
          <template #default="{ row }">
            {{ row.completedCount }} / {{ row.targetDevices }}
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)">
              <template #default="{ percentage }">
                <span class="percentage-value">{{ percentage }}%</span>
              </template>
            </el-progress>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'PENDING'"
              size="small"
              type="primary"
              @click="startTask(row)"
            >
              开始
            </el-button>
            <el-button
              v-if="row.status === 'UPGRADING'"
              size="small"
              type="warning"
              @click="pauseTask(row)"
            >
              暂停
            </el-button>
            <el-button
              v-if="row.status === 'FAILED'"
              size="small"
              type="primary"
              @click="retryTask(row)"
            >
              重试
            </el-button>
            <el-button
              v-if="row.upgradeType === 'MODEL' && (row.status === 'COMPLETED' || row.status === 'UPGRADING')"
              size="small"
              type="success"
              @click="replaceModel(row)"
            >
              替换模型
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 创建升级任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建升级任务" width="700px">
      <el-form :model="taskForm" label-width="120px">
        <el-form-item label="任务名称">
          <el-input v-model="taskForm.taskName" placeholder="例如：设备批量模型升级" />
        </el-form-item>
        <el-form-item label="升级类型">
          <el-radio-group v-model="taskForm.upgradeType">
            <el-radio value="model">模型升级</el-radio>
            <el-radio value="firmware">固件升级</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目标模型" v-if="taskForm.upgradeType === 'model'">
          <el-select v-model="taskForm.modelId" style="width: 100%;" filterable>
            <el-option
              v-for="model in models"
              :key="model.modelId"
              :label="`${model.modelName} (${model.version})`"
              :value="model.modelId"
            />
            <el-option v-if="models.length === 0" label="无可用模型" value="" disabled />
          </el-select>
        </el-form-item>
        <el-form-item label="目标版本" v-if="taskForm.upgradeType === 'firmware'">
          <el-input v-model="taskForm.targetVersion" placeholder="例如：v2.1.0" />
        </el-form-item>
        <el-form-item label="目标设备">
          <el-select v-model="taskForm.deviceIds" multiple style="width: 100%;" filterable>
            <el-option
              v-for="device in devices"
              :key="device.deviceId"
              :label="`${device.deviceName} (${device.status})`"
              :value="device.deviceId"
            />
            <el-option v-if="devices.length === 0" label="无可用设备" value="" disabled />
          </el-select>
        </el-form-item>
        <el-form-item label="升级策略">
          <el-radio-group v-model="taskForm.strategy">
            <el-radio value="immediate">立即升级</el-radio>
            <el-radio value="scheduled">定时升级</el-radio>
            <el-radio value="manual">手动确认</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="定时时间" v-if="taskForm.strategy === 'scheduled'">
          <el-date-picker
            v-model="taskForm.scheduledTime"
            type="datetime"
            placeholder="选择日期时间"
            style="width: 100%;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">创建任务</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="任务详情" width="900px" @closed="deviceStatuses = []">
      <el-descriptions v-if="currentTask" :column="2" border class="task-info">
        <el-descriptions-item label="任务名称">{{ currentTask.taskName }}</el-descriptions-item>
        <el-descriptions-item label="升级类型">
          <el-tag :type="currentTask.upgradeType === 'MODEL' ? 'primary' : 'success'">
            {{ getUpgradeTypeText(currentTask.upgradeType) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="目标版本">{{ currentTask.targetVersion || '-' }}</el-descriptions-item>
        <el-descriptions-item label="任务状态">
          <el-tag :type="getStatusType(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="目标设备数">{{ currentTask.targetDevices }}</el-descriptions-item>
        <el-descriptions-item label="已完成">
          {{ currentTask.completedCount }} / {{ currentTask.targetDevices }}
        </el-descriptions-item>
        <el-descriptions-item label="进度" :span="2">
          <el-progress :percentage="currentTask.progress" :status="getProgressStatus(currentTask.status)" />
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ currentTask.createdAt }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">设备升级状态</el-divider>

      <el-table :data="deviceStatuses" v-loading="detailLoading" style="width: 100%" max-height="400">
        <el-table-column prop="deviceId" label="设备ID" width="150" />
        <el-table-column prop="deviceName" label="设备名称" width="150" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getDeviceStatusType(row.status)">
              {{ getDeviceStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress || 0" :status="row.status === 'COMPLETED' ? 'success' : row.status.includes('FAILED') ? 'exception' : undefined" />
          </template>
        </el-table-column>
        <el-table-column prop="errorMessage" label="错误信息" min-width="200">
          <template #default="{ row }">
            <span v-if="row.errorMessage" class="error-text">{{ row.errorMessage }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="180" />
      </el-table>

      <template #footer>
        <el-button type="primary" @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { otaApi, deviceApi, modelApi } from '@/api'

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const tasks = ref<any[]>([])
const devices = ref<any[]>([])
const models = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
let refreshTimer: any = null

const createDialogVisible = ref(false)
const creating = ref(false)
const taskForm = ref({
  taskName: '',
  upgradeType: 'model',
  modelId: '',
  targetVersion: '',
  deviceIds: [],
  strategy: 'immediate',
  scheduledTime: null
})

// 加载设备列表
const loadDevices = async () => {
  try {
    const response = await deviceApi.getList({ page: 1, pageSize: 100 })
    devices.value = response.data.items || []
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 加载模型列表
const loadModels = async () => {
  try {
    const response = await modelApi.getList({ page: 1, pageSize: 100 })
    models.value = response.data.items || []
  } catch (error) {
    console.error('加载模型列表失败:', error)
  }
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const response = await otaApi.getList({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined
    })
    tasks.value = response.data.items || []
    total.value = response.data.total || 0

    // 如果有搜索文本，进行客户端过滤
    if (searchText.value) {
      const filtered = tasks.value.filter((t: any) =>
        t.taskName?.toLowerCase().includes(searchText.value.toLowerCase())
      )
      tasks.value = filtered
    }
  } catch (error: any) {
    ElMessage.error('加载任务列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilter = () => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadTasks()
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    UPGRADING: 'primary',
    COMPLETED: 'success',
    PENDING: 'info',
    FAILED: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    UPGRADING: '升级中',
    COMPLETED: '已完成',
    PENDING: '待升级',
    FAILED: '失败'
  }
  return texts[status] || status
}

// 获取进度状态
const getProgressStatus = (status: string) => {
  const statuses: Record<string, any> = {
    COMPLETED: 'success',
    FAILED: 'exception'
  }
  return statuses[status] || undefined
}

// 详情对话框相关
const detailDialogVisible = ref(false)
const detailLoading = ref(false)
const currentTask = ref<any>(null)
const deviceStatuses = ref<any[]>([])

// 查看详情
const viewDetail = async (task: any) => {
  currentTask.value = task
  detailDialogVisible.value = true
  await loadTaskDeviceStatuses(task.taskId)
}

// 加载任务设备状态
const loadTaskDeviceStatuses = async (taskId: string) => {
  detailLoading.value = true
  try {
    const response = await otaApi.getTaskDeviceStatuses(taskId)
    deviceStatuses.value = response.data || []
  } catch (error: any) {
    console.error('加载设备状态失败:', error)
    ElMessage.error('加载设备状态失败: ' + (error.message || '未知错误'))
  } finally {
    detailLoading.value = false
  }
}

// 获取设备状态类型
const getDeviceStatusType = (status: string) => {
  const types: Record<string, string> = {
    PENDING: 'info',
    DOWNLOADING: 'primary',
    DOWNLOAD_FAILED: 'danger',
    INSTALLING: 'warning',
    INSTALL_FAILED: 'danger',
    COMPLETED: 'success',
    FAILED: 'danger'
  }
  return types[status] || 'info'
}

// 获取设备状态文本
const getDeviceStatusText = (status: string) => {
  const texts: Record<string, string> = {
    PENDING: '待升级',
    DOWNLOADING: '下载中',
    DOWNLOAD_FAILED: '下载失败',
    INSTALLING: '安装中',
    INSTALL_FAILED: '安装失败',
    COMPLETED: '已完成',
    FAILED: '失败'
  }
  return texts[status] || status
}

// 获取升级类型文本
const getUpgradeTypeText = (type: string) => {
  return type === 'MODEL' ? '模型升级' : '固件升级'
}

// 开始任务
const startTask = async (task: any) => {
  ElMessageBox.confirm(
    `确定要开始升级任务 "${task.taskName}" 吗？`,
    '确认开始',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await otaApi.start(task.taskId)
      ElMessage.success('任务已开始')
      loadTasks()
    } catch (error: any) {
      ElMessage.error('开始任务失败: ' + (error.message || '未知错误'))
    }
  })
}

// 暂停任务
const pauseTask = async (task: any) => {
  ElMessageBox.confirm(
    `确定要暂停升级任务 "${task.taskName}" 吗？`,
    '确认暂停',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await otaApi.pause(task.taskId)
      ElMessage.success('任务已暂停')
      loadTasks()
    } catch (error: any) {
      ElMessage.error('暂停任务失败: ' + (error.message || '未知错误'))
    }
  })
}

// 重试任务
const retryTask = async (task: any) => {
  ElMessageBox.confirm(
    `确定要重试失败设备 "${task.taskName}" 吗？`,
    '确认重试',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await otaApi.retryFailed(task.taskId)
      ElMessage.success('开始重试失败设备')
      loadTasks()
    } catch (error: any) {
      ElMessage.error('重试失败: ' + (error.message || '未知错误'))
    }
  })
}

// 替换模型（触发热加载）
const replaceModel = async (task: any) => {
  // 先获取设备列表
  try {
    const response = await otaApi.getTaskDeviceStatuses(task.taskId)
    const devices = response.data || []

    if (devices.length === 0) {
      ElMessage.warning('该任务没有关联的设备')
      return
    }

    // 如果只有一个设备，直接替换；如果有多个设备，让用户选择
    if (devices.length === 1) {
      await doReplaceModel(task.taskId, devices[0].deviceId, devices[0].deviceName)
    } else {
      // 显示设备选择对话框
      ElMessageBox({
        title: '选择要替换模型的设备',
        message: `请选择要触发热加载的设备：`,
        showCancelButton: true,
        confirmButtonText: '全部替换',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true,
        beforeClose: async (action: string, _instance: any, done: () => void) => {
          if (action === 'confirm') {
            // 全部替换
            for (const device of devices) {
              await doReplaceModel(task.taskId, device.deviceId, device.deviceName)
            }
            ElMessage.success(`已触发 ${devices.length} 台设备的模型热加载`)
            done()
          } else {
            done()
          }
        }
      })
    }
  } catch (error: any) {
    ElMessage.error('获取设备列表失败: ' + (error.message || '未知错误'))
  }
}

// 执行模型替换
const doReplaceModel = async (taskId: string, deviceId: string, deviceName: string) => {
  try {
    await otaApi.replaceModel(taskId, deviceId)
    ElMessage.success(`已触发设备 "${deviceName}" 的模型热加载`)
  } catch (error: any) {
    ElMessage.error(`触发热加载失败: ${error.message || '未知错误'}`)
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  taskForm.value = {
    taskName: '',
    upgradeType: 'model',
    modelId: '',
    targetVersion: '',
    deviceIds: [],
    strategy: 'immediate',
    scheduledTime: null
  }
  createDialogVisible.value = true
}

// 创建任务
const createTask = async () => {
  if (!taskForm.value.taskName || taskForm.value.deviceIds.length === 0) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (taskForm.value.upgradeType === 'model' && !taskForm.value.modelId) {
    ElMessage.warning('请选择目标模型')
    return
  }
  if (taskForm.value.upgradeType === 'firmware' && !taskForm.value.targetVersion) {
    ElMessage.warning('请输入目标版本')
    return
  }

  creating.value = true
  try {
    await otaApi.createTask({
      taskName: taskForm.value.taskName,
      upgradeType: taskForm.value.upgradeType === 'model' ? 'MODEL' : 'FIRMWARE',
      modelId: taskForm.value.modelId || undefined,
      targetVersion: taskForm.value.targetVersion || undefined,
      deviceIds: taskForm.value.deviceIds
    })
    ElMessage.success('升级任务创建成功')
    createDialogVisible.value = false
    loadTasks()
  } catch (error: any) {
    ElMessage.error('创建任务失败: ' + (error.message || '未知错误'))
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadTasks()
  loadDevices()
  loadModels()

  // 定时刷新运行中的任务
  refreshTimer = setInterval(() => {
    const hasRunning = tasks.value.some((t: any) => t.status === 'UPGRADING')
    if (hasRunning) {
      loadTasks()
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
.ota-task {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.table-card {
  min-height: calc(100vh - 300px);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.percentage-value {
  font-size: 12px;
}

.task-info {
  margin-bottom: 20px;
}

.error-text {
  color: #f56c6c;
}
</style>
