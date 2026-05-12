<template>
  <div class="device-list">
    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-space wrap>
            <el-input
              v-model="searchText"
              placeholder="搜索设备ID或名称"
              clearable
              style="width: 220px"
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
              style="width: 120px"
              @change="handleFilterChange"
            >
              <el-option label="全部" value="" />
              <el-option label="在线" value="ONLINE" />
              <el-option label="离线" value="OFFLINE" />
              <el-option label="升级中" value="UPGRADING" />
              <el-option label="错误" value="ERROR" />
            </el-select>
            <el-select
              v-model="typeFilter"
              placeholder="设备类型"
              clearable
              style="width: 140px"
              @change="handleFilterChange"
            >
              <el-option v-for="t in deviceTypes" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
            <el-select
              v-model="categoryFilter"
              placeholder="设备类别"
              clearable
              style="width: 130px"
              @change="handleFilterChange"
            >
              <el-option v-for="c in deviceCategories" :key="c.value" :label="c.label" :value="c.value" />
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
        <el-table-column prop="deviceName" label="设备名称" width="180" />
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-icon :size="16">
              <Monitor v-if="isEdgeCompute(row)" />
              <Position v-else-if="row.deviceCategory === 'UAV'" />
              <Promotion v-else-if="row.deviceCategory === 'ROBOTIC'" />
              <Van v-else-if="row.deviceCategory === 'VEHICLE'" />
              <Camera v-else />
            </el-icon>
            <span style="margin-left: 4px">{{ formatType(row.deviceType) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cpuUsage" label="CPU" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'ONLINE'"
              :percentage="row.cpuUsage"
              :color="getUsageColor(row.cpuUsage)"
              :stroke-width="14"
              :text-inside="true"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="gpuUsage" label="GPU" width="120" align="center">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'ONLINE'"
              :percentage="row.gpuUsage"
              :color="getUsageColor(row.gpuUsage)"
              :stroke-width="14"
              :text-inside="true"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="能力" width="160">
          <template #default="{ row }">
            <el-tag
              v-for="cap in parseCapabilities(row.capabilities).slice(0, 3)"
              :key="cap"
              size="small"
              type="info"
              style="margin: 1px"
            >
              {{ capLabel(cap) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastHeartbeat" label="最后心跳" width="170" />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">详情</el-button>
            <el-button size="small" type="danger" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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
    <el-dialog v-model="addDialogVisible" title="添加设备" width="500px" :close-on-click-modal="false">
      <el-form :model="deviceForm" label-width="100px">
        <el-form-item label="设备ID" required>
          <el-input v-model="deviceForm.deviceId" placeholder="EDGE_DEVICE_001" maxlength="50" />
        </el-form-item>
        <el-form-item label="设备名称" required>
          <el-input v-model="deviceForm.deviceName" placeholder="边缘设备1" maxlength="200" />
        </el-form-item>
        <el-form-item label="设备类型" required>
          <el-select v-model="deviceForm.deviceType" style="width: 100%">
            <el-option v-for="t in deviceTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属分组">
          <el-input v-model="deviceForm.groupId" placeholder="group_a" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Plus, Monitor, Position, Promotion, Van, Camera } from '@element-plus/icons-vue'
import { deviceApi } from '@/api'

// 设备类型枚举
const deviceTypes = [
  { value: 'JETSON_ORIN', label: 'Jetson Orin' },
  { value: 'JETSON_XAVIER', label: 'Jetson Xavier' },
  { value: 'JETSON_NANO', label: 'Jetson Nano' },
  { value: 'EDGE_BOX', label: '边缘盒子' },
  { value: 'DRONE', label: '无人机' },
  { value: 'ROBOT_DOG', label: '机器狗' },
  { value: 'VEHICLE', label: '无人车' },
  { value: 'SENSOR', label: '传感器' },
  { value: 'CAMERA', label: '摄像头' },
]

const deviceCategories = [
  { value: 'EDGE_COMPUTE', label: '边缘计算' },
  { value: 'UAV', label: '无人机' },
  { value: 'ROBOTIC', label: '机器人' },
  { value: 'VEHICLE', label: '车辆' },
  { value: 'SENSOR', label: '传感器' },
  { value: 'CAMERA', label: '摄像头' },
]

interface DeviceItem {
  deviceId: string
  deviceName: string
  deviceType: string
  deviceCategory?: string
  capabilities?: string
  groupId: string | null
  status: string
  cpuUsage: number
  gpuUsage: number
  lastHeartbeat: string
}

const router = useRouter()
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const typeFilter = ref('')
const categoryFilter = ref('')
const devices = ref<DeviceItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const addDialogVisible = ref(false)
const deviceForm = ref({ deviceId: '', deviceName: '', deviceType: '', groupId: '' })

const isEdgeCompute = (row: DeviceItem) =>
  ['EDGE_COMPUTE', undefined].includes(row.deviceCategory)

const formatType = (type: string) => {
  const found = deviceTypes.find(t => t.value === type)
  return found ? found.label : type
}

const parseCapabilities = (caps?: string) => {
  if (!caps) return []
  return caps.split(',').filter(Boolean)
}

const capLabel = (cap: string) => {
  const map: Record<string, string> = {
    VIDEO_INPUT: '视频', INFERENCE: '推理', CONTROL: '控制',
    SENSING: '传感', CLOUD_FORWARD: '转发', OTA_UPDATE: 'OTA', MULTI_CHANNEL: '多通道'
  }
  return map[cap] || cap
}

const getStatusType = (s: string) => ({ ONLINE: 'success', OFFLINE: 'info', UPGRADING: 'warning', ERROR: 'danger' }[s] || 'info')
const getStatusText = (s: string) => ({ ONLINE: '在线', OFFLINE: '离线', UPGRADING: '升级中', ERROR: '错误' }[s] || s)
const getUsageColor = (u: number) => u > 80 ? '#f56c6c' : u > 60 ? '#e6a23c' : '#67c23a'

const loadDevices = async () => {
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
    ElMessage.error(`加载失败: ${error.message || '未知错误'}`)
    devices.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => { currentPage.value = 1; loadDevices() }
const handleFilterChange = () => { currentPage.value = 1; loadDevices() }
const handleReset = () => {
  searchText.value = ''
  statusFilter.value = ''
  typeFilter.value = ''
  categoryFilter.value = ''
  currentPage.value = 1
  loadDevices()
}

const handleViewDetail = (row: DeviceItem) => router.push(`/device/${row.deviceId}`)

const handleDelete = (row: DeviceItem) => {
  ElMessageBox.confirm(`确定删除设备 "${row.deviceName}" 吗？`, '确认删除', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    await deviceApi.delete(row.deviceId)
    ElMessage.success('删除成功')
    await loadDevices()
  }).catch(() => {})
}

const handleShowAddDialog = () => {
  deviceForm.value = { deviceId: '', deviceName: '', deviceType: '', groupId: '' }
  addDialogVisible.value = true
}

const handleAdd = async () => {
  const f = deviceForm.value
  if (!f.deviceId.trim() || !f.deviceName.trim() || !f.deviceType) {
    ElMessage.warning('请填写完整信息')
    return
  }
  try {
    await deviceApi.register({
      deviceId: f.deviceId.trim(),
      deviceName: f.deviceName.trim(),
      deviceType: f.deviceType,
      groupId: f.groupId.trim() || undefined
    })
    ElMessage.success('添加成功')
    addDialogVisible.value = false
    await loadDevices()
  } catch (error: any) {
    ElMessage.error(`添加失败: ${error.message || '未知错误'}`)
  }
}

onMounted(loadDevices)
</script>

<style scoped>
.device-list {
  padding: 0;
}

.action-bar {
  margin-bottom: 16px;
}

:deep(.el-table__row) {
  cursor: pointer;
}
</style>
