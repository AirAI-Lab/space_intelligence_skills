<template>
  <div class="deployment-record">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <h2>部署记录</h2>
          <div class="header-actions">
            <el-button type="danger" @click="handleClearCompleted" :icon="Delete">清空已完成</el-button>
            <el-button type="primary" @click="fetchRecords" :icon="Refresh">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="模型">
          <el-select v-model="filters.modelId" placeholder="全部模型" clearable @change="handleFilterChange">
            <el-option
              v-for="model in modelOptions"
              :key="model.modelId"
              :label="model.modelName"
              :value="model.modelId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="设备">
          <el-select v-model="filters.deviceId" placeholder="全部设备" clearable @change="handleFilterChange">
            <el-option
              v-for="device in deviceOptions"
              :key="device.deviceId"
              :label="device.deviceName"
              :value="device.deviceId"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable @change="handleFilterChange">
            <el-option label="部署中" value="DEPLOYING" />
            <el-option label="成功" value="SUCCESS" />
            <el-option label="失败" value="FAILED" />
            <el-option label="已回滚" value="ROLLED_BACK" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署类型">
          <el-select v-model="filters.deploymentType" placeholder="全部类型" clearable @change="handleFilterChange">
            <el-option label="单设备部署" value="SINGLE" />
            <el-option label="批量部署" value="BATCH" />
            <el-option label="灰度发布" value="GRADUAL" />
            <el-option label="A/B测试" value="AB_TEST" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            @change="handleDateChange"
          />
        </el-form-item>
      </el-form>

      <!-- 部署记录表格 -->
      <el-table
        v-loading="loading"
        :data="records"
        stripe
        style="width: 100%"
        @row-click="showDetail"
      >
        <el-table-column prop="deploymentId" label="部署ID" width="180" />
        <el-table-column prop="modelName" label="模型" width="150" />
        <el-table-column prop="deviceName" label="设备" width="150" />
        <el-table-column prop="typeText" label="部署类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTagType(row.deploymentType)" size="small">
              {{ row.typeText }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="statusText" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small">
              {{ row.statusText }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deployedAt" label="部署时间" width="170" />
        <el-table-column prop="durationText" label="耗时" width="100" />
        <el-table-column prop="deployedBy" label="操作者" width="100" />
        <el-table-column prop="inferenceFps" label="推理FPS" width="100">
          <template #default="{ row }">
            <span v-if="row.inferenceFps">{{ row.inferenceFps.toFixed(1) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              link
              @click.stop="showDetail(row)"
            >
              详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              link
              @click.stop="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 部署详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="部署详情"
      width="600px"
      @close="closeDetail"
    >
      <el-descriptions v-if="currentRecord" :column="2" border>
        <el-descriptions-item label="部署ID">{{ currentRecord.deploymentId }}</el-descriptions-item>
        <el-descriptions-item label="部署类型">
          <el-tag :type="getTypeTagType(currentRecord.deploymentType)" size="small">
            {{ currentRecord.typeText }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="模型">{{ currentRecord.modelName }}</el-descriptions-item>
        <el-descriptions-item label="设备">{{ currentRecord.deviceName }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTagType(currentRecord.status)" size="small">
            {{ currentRecord.statusText }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作者">{{ currentRecord.deployedBy || '-' }}</el-descriptions-item>
        <el-descriptions-item label="部署时间">{{ currentRecord.deployedAt }}</el-descriptions-item>
        <el-descriptions-item label="完成时间">
          {{ currentRecord.completedAt || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="部署耗时">
          {{ currentRecord.durationText || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="推理FPS">
          {{ currentRecord.inferenceFps ? currentRecord.inferenceFps.toFixed(1) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="内存使用">
          {{ currentRecord.memoryUsageMb ? `${currentRecord.memoryUsageMb} MB` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="GPU利用率">
          {{ currentRecord.gpuUtilization ? `${(currentRecord.gpuUtilization * 100).toFixed(1)}%` : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="OTA任务ID" :span="2">
          {{ currentRecord.otaTaskId || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="原模型" :span="2">
          {{ currentRecord.previousModelName || '-' }}
        </el-descriptions-item>
        <el-descriptions-item v-if="currentRecord.errorMessage" label="错误信息" :span="2">
          <el-text type="danger">{{ currentRecord.errorMessage }}</el-text>
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="closeDetail">关闭</el-button>
        <el-button
          v-if="currentRecord?.status === 'FAILED' && currentRecord?.otaTaskId"
          type="warning"
          @click="handleRetry"
        >
          重试
        </el-button>
        <el-button
          v-if="currentRecord?.status === 'SUCCESS' && !currentRecord?.rollbackAt"
          type="danger"
          @click="handleRollback"
        >
          回滚
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Refresh, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deploymentApi } from '@/api'
import { modelApi } from '@/api'
import { deviceApi } from '@/api'
import { otaApi } from '@/api'

// 筛选条件
const filters = reactive({
  modelId: '',
  deviceId: '',
  status: '',
  deploymentType: ''
})

const dateRange = ref<[string, string] | null>(null)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 列表数据
const records = ref<any[]>([])
const loading = ref(false)

// 选项数据
const modelOptions = ref<any[]>([])
const deviceOptions = ref<any[]>([])

// 详情
const detailVisible = ref(false)
const currentRecord = ref<any>(null)

// 获取状态标签类型
const getStatusTagType = (status: string) => {
  const map: Record<string, any> = {
    DEPLOYING: 'warning',
    SUCCESS: 'success',
    FAILED: 'danger',
    ROLLED_BACK: 'info'
  }
  return map[status] || ''
}

// 获取类型标签类型
const getTypeTagType = (type: string) => {
  const map: Record<string, any> = {
    SINGLE: '',
    BATCH: 'primary',
    GRADUAL: 'warning',
    AB_TEST: 'success'
  }
  return map[type] || ''
}

// 获取部署记录列表
const fetchRecords = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.page,
      pageSize: pagination.pageSize
    }

    if (filters.modelId) params.modelId = filters.modelId
    if (filters.deviceId) params.deviceId = filters.deviceId
    if (filters.status) params.status = filters.status
    if (filters.deploymentType) params.deploymentType = filters.deploymentType
    if (dateRange.value) {
      params.startTime = dateRange.value[0]
      params.endTime = dateRange.value[1]
    }

    const res = await deploymentApi.getList(params)
    records.value = res.data.items || []
    pagination.total = res.data.total || 0
  } catch (error) {
    console.error('获取部署记录失败:', error)
    ElMessage.error('获取部署记录失败')
  } finally {
    loading.value = false
  }
}

// 获取模型选项
const fetchModelOptions = async () => {
  try {
    const res = await modelApi.getList({ page: 1, pageSize: 1000 })
    modelOptions.value = res.data.items || []
  } catch (error) {
    console.error('获取模型列表失败:', error)
  }
}

// 获取设备选项
const fetchDeviceOptions = async () => {
  try {
    const res = await deviceApi.getList({ page: 1, pageSize: 1000 })
    deviceOptions.value = res.data.items || []
  } catch (error) {
    console.error('获取设备列表失败:', error)
  }
}

// 筛选条件变化
const handleFilterChange = () => {
  pagination.page = 1
  fetchRecords()
}

// 日期范围变化
const handleDateChange = () => {
  pagination.page = 1
  fetchRecords()
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  fetchRecords()
}

// 页码变化
const handlePageChange = (page: number) => {
  pagination.page = page
  fetchRecords()
}

// 显示详情
const showDetail = (row: any) => {
  currentRecord.value = row
  detailVisible.value = true
}

// 关闭详情
const closeDetail = () => {
  detailVisible.value = false
  currentRecord.value = null
}

// 重试
const handleRetry = async () => {
  if (!currentRecord.value?.otaTaskId) return

  try {
    await ElMessageBox.confirm('确认重试此部署？', '提示', {
      type: 'warning'
    })

    await otaApi.retryFailed(currentRecord.value.otaTaskId)
    ElMessage.success('重试成功')
    closeDetail()
    fetchRecords()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重试失败:', error)
      ElMessage.error('重试失败')
    }
  }
}

// 回滚
const handleRollback = async () => {
  if (!currentRecord.value?.deviceId || !currentRecord.value?.otaTaskId) return

  try {
    await ElMessageBox.confirm('确认回滚此部署？设备将恢复到之前的模型版本。', '警告', {
      type: 'warning',
      confirmButtonText: '确认回滚',
      cancelButtonText: '取消'
    })

    await otaApi.rollback(currentRecord.value.otaTaskId, currentRecord.value.deviceId)
    ElMessage.success('回滚命令已发送')
    closeDetail()
    fetchRecords()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('回滚失败:', error)
      ElMessage.error('回滚失败')
    }
  }
}

// 删除部署记录
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除部署记录 "${row.deploymentId}" 吗？删除后将无法恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deploymentApi.delete(row.deploymentId)
    ElMessage.success('部署记录已删除')
    fetchRecords()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败: ' + (error.response?.data?.message || error.message || '未知错误'))
    }
  }
}

// 清空所有已完成/失败/已回滚的部署记录
const handleClearCompleted = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要清空所有已完成、失败和已回滚的部署记录吗？正在进行的部署记录不会被删除。此操作不可恢复。',
      '确认清空',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const res = await deploymentApi.clearCompleted()
    ElMessage.success(`清空完成: 删除 ${res.data.deleted} 条，跳过 ${res.data.skipped} 条`)
    fetchRecords()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('清空失败:', error)
      ElMessage.error('清空失败: ' + (error.response?.data?.message || error.message || '未知错误'))
    }
  }
}

onMounted(() => {
  fetchRecords()
  fetchModelOptions()
  fetchDeviceOptions()
})
</script>

<style scoped>
.deployment-record {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: var(--el-fill-color-light);
}
</style>
