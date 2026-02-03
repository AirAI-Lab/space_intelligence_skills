<template>
  <div class="device-list">
    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-space>
            <el-input
              v-model="searchText"
              placeholder="搜索设备ID或名称"
              clearable
              style="width: 250px"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select
              v-model="statusFilter"
              placeholder="设备状态"
              clearable
              style="width: 150px"
              @change="handleFilterChange"
            >
              <el-option label="全部" value="" />
              <el-option label="在线" value="ONLINE" />
              <el-option label="离线" value="OFFLINE" />
              <el-option label="升级中" value="UPGRADING" />
              <el-option label="错误" value="ERROR" />
            </el-select>
            <el-button type="primary" @click="handleSearch">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleReset">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="6" style="text-align: right">
          <el-button type="primary" @click="handleShowAddDialog">
            <el-icon><Plus /></el-icon>
            添加设备
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 设备列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="devices"
        style="width: 100%"
        stripe
        @row-click="handleViewDetail"
      >
        <el-table-column prop="deviceId" label="设备ID" width="150" />
        <el-table-column prop="deviceName" label="设备名称" width="200" />
        <el-table-column prop="deviceType" label="设备类型" width="150" />
        <el-table-column prop="groupId" label="所属分组" width="150">
          <template #default="{ row }">
            {{ row.groupId || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cpuUsage" label="CPU使用率" width="140" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'ONLINE'"
              :percentage="row.cpuUsage"
              :color="getUsageColor(row.cpuUsage)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="gpuUsage" label="GPU使用率" width="140" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'ONLINE'"
              :percentage="row.gpuUsage"
              :color="getUsageColor(row.gpuUsage)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="lastHeartbeat" label="最后心跳" width="180" />
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">
              查看详情
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click.stop="handleConfig(row)"
            >
              配置
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click.stop="handleDelete(row)"
            >
              删除
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
          @size-change="loadDevices"
          @current-change="loadDevices"
        />
      </div>
    </el-card>

    <!-- 添加设备对话框 -->
    <el-dialog
      v-model="addDialogVisible"
      title="添加设备"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="deviceForm" label-width="100px">
        <el-form-item label="设备ID" required>
          <el-input
            v-model="deviceForm.deviceId"
            placeholder="EDGE_DEVICE_001"
            maxlength="50"
          />
        </el-form-item>
        <el-form-item label="设备名称" required>
          <el-input
            v-model="deviceForm.deviceName"
            placeholder="边缘设备1"
            maxlength="200"
          />
        </el-form-item>
        <el-form-item label="设备类型" required>
          <el-select v-model="deviceForm.deviceType" style="width: 100%">
            <el-option label="Jetson Orin" value="jetson_orin" />
            <el-option label="Jetson Xavier" value="jetson_xavier" />
            <el-option label="Jetson Nano" value="jetson_nano" />
            <el-option label="边缘盒子" value="EDGE_BOX" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属分组">
          <el-input
            v-model="deviceForm.groupId"
            placeholder="group_a"
            maxlength="50"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleCancelAdd">取消</el-button>
        <el-button type="primary" @click="handleAdd">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// ==================== Vue 核心库 ====================
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'

// ==================== 第三方 UI 库 ====================
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'

// ==================== API 服务 ====================
import { deviceApi } from '@/api'

// ==================== 类型定义 ====================
interface DeviceForm {
  deviceId: string
  deviceName: string
  deviceType: string
  groupId: string
}

interface DeviceItem {
  deviceId: string
  deviceName: string
  deviceType: string
  groupId: string | null
  ip: string | null
  mac: string | null
  status: string
  cpuUsage: number
  gpuUsage: number
  memoryUsage: number
  diskUsage: number | null
  currentModelId: string | null
  currentVersion: string | null
  mqttTopic: string | null
  lastHeartbeat: string
  createdAt: string
  updatedAt: string
}

// ==================== 路由 ====================
const router = useRouter()

// ==================== 响应式状态 ====================
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const devices = ref<DeviceItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 添加对话框状态
const addDialogVisible = ref(false)

const deviceForm = reactive<DeviceForm>({
  deviceId: '',
  deviceName: '',
  deviceType: '',
  groupId: ''
})

// ==================== 计算属性 ====================
const canAddDevice = computed(() => {
  return deviceForm.deviceId.trim() !== '' &&
         deviceForm.deviceName.trim() !== '' &&
         deviceForm.deviceType !== ''
})

// ==================== 工具函数 ====================
const getUsageColor = (usage: number): string => {
  if (usage > 80) return '#f56c6c'
  if (usage > 60) return '#e6a23c'
  return '#67c23a'
}

// ==================== 类型映射 ====================
const getStatusType = (status: string): string => {
  const types: Record<string, string> = {
    'ONLINE': 'success',
    'OFFLINE': 'info',
    'UPGRADING': 'warning',
    'ERROR': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    'ONLINE': '在线',
    'OFFLINE': '离线',
    'UPGRADING': '升级中',
    'ERROR': '错误'
  }
  return texts[status] || status
}

// ==================== 数据加载 ====================
const loadDevices = async (): Promise<void> => {
  loading.value = true
  try {
    const response = await deviceApi.getList({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined
    })
    devices.value = response.data.items || []
    total.value = response.data.total || 0
  } catch (error: any) {
    console.error('加载设备列表失败:', error)
    ElMessage.error(`加载设备列表失败: ${error.message || '未知错误'}`)
    devices.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ==================== 搜索和筛选 ====================
const handleSearch = (): void => {
  currentPage.value = 1
  loadDevices()
}

const handleFilterChange = (): void => {
  currentPage.value = 1
  loadDevices()
}

const handleReset = (): void => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadDevices()
}

// ==================== 设备操作 ====================
const handleViewDetail = (device: DeviceItem): void => {
  router.push(`/device/${device.deviceId}`)
}

const handleConfig = (device: DeviceItem): void => {
  // TODO: 实现设备配置功能
  ElMessage.info(`配置设备: ${device.deviceName}`)
}

const handleDelete = (device: DeviceItem): void => {
  ElMessageBox.confirm(
    `确定要删除设备 "${device.deviceName}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deviceApi.delete(device.deviceId)
      ElMessage.success('设备删除成功')
      await loadDevices()
    } catch (error: any) {
      console.error('删除设备失败:', error)
      ElMessage.error(`删除失败: ${error.message || '未知错误'}`)
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// ==================== 添加设备操作 ====================
const handleShowAddDialog = (): void => {
  // 重置表单
  Object.assign(deviceForm, {
    deviceId: '',
    deviceName: '',
    deviceType: '',
    groupId: ''
  })
  addDialogVisible.value = true
}

const handleCancelAdd = (): void => {
  addDialogVisible.value = false
}

const handleAdd = async (): Promise<void> => {
  if (!canAddDevice.value) {
    ElMessage.warning('请填写完整信息')
    return
  }

  try {
    await deviceApi.register({
      deviceId: deviceForm.deviceId.trim(),
      deviceName: deviceForm.deviceName.trim(),
      deviceType: deviceForm.deviceType,
      groupId: deviceForm.groupId.trim() || undefined
    })
    ElMessage.success('设备添加成功')
    addDialogVisible.value = false

    // 重置表单
    Object.assign(deviceForm, {
      deviceId: '',
      deviceName: '',
      deviceType: '',
      groupId: ''
    })

    // 刷新列表
    await loadDevices()
  } catch (error: any) {
    console.error('添加设备失败:', error)
    ElMessage.error(`设备添加失败: ${error.message || '未知错误'}`)
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadDevices()
})
</script>

<style scoped>
.device-list {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.table-card {
  min-height: calc(100vh - 280px);
}

.pagination {
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
