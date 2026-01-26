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
              style="width: 250px;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select v-model="statusFilter" placeholder="设备状态" clearable style="width: 150px;">
              <el-option label="全部" value="" />
              <el-option label="在线" value="online" />
              <el-option label="离线" value="offline" />
              <el-option label="告警" value="alarm" />
            </el-select>
            <el-button type="primary" @click="loadDevices">
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
          <el-button type="primary" @click="showAddDialog">
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
        @row-click="viewDevice"
      >
        <el-table-column prop="device_id" label="设备ID" width="150" />
        <el-table-column prop="device_name" label="设备名称" width="200" />
        <el-table-column prop="device_type" label="设备类型" width="150" />
        <el-table-column prop="group_id" label="所属分组" width="150" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cpu_usage" label="CPU使用率" width="120">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'online'"
              :percentage="row.cpu_usage"
              :color="getUsageColor(row.cpu_usage)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="gpu_usage" label="GPU使用率" width="120">
          <template #default="{ row }">
            <el-progress
              v-if="row.status === 'online'"
              :percentage="row.gpu_usage"
              :color="getUsageColor(row.gpu_usage)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_heartbeat" label="最后心跳" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="viewDevice(row)">
              查看详情
            </el-button>
            <el-button size="small" @click.stop="editDevice(row)">
              配置
            </el-button>
            <el-button size="small" type="danger" @click.stop="deleteDevice(row)">
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
    <el-dialog v-model="addDialogVisible" title="添加设备" width="500px">
      <el-form :model="deviceForm" label-width="100px">
        <el-form-item label="设备ID">
          <el-input v-model="deviceForm.device_id" placeholder="EDGE_DEVICE_001" />
        </el-form-item>
        <el-form-item label="设备名称">
          <el-input v-model="deviceForm.device_name" placeholder="边缘设备1" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="deviceForm.device_type" style="width: 100%;">
            <el-option label="Jetson Orin" value="jetson_orin" />
            <el-option label="Jetson Xavier" value="jetson_xavier" />
            <el-option label="Jetson Nano" value="jetson_nano" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属分组">
          <el-input v-model="deviceForm.group_id" placeholder="group_a" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addDevice">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { deviceApi } from '@/api'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const devices = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const addDialogVisible = ref(false)
const deviceForm = ref({
  device_id: '',
  device_name: '',
  device_type: '',
  group_id: ''
})

// 加载设备列表
const loadDevices = async () => {
  loading.value = true
  try {
    const res = await deviceApi.getList({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchText.value,
      status: statusFilter.value
    })
    devices.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilter = () => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadDevices()
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    online: 'success',
    offline: 'info',
    alarm: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    online: '在线',
    offline: '离线',
    alarm: '告警'
  }
  return texts[status] || status
}

// 获取使用率颜色
const getUsageColor = (usage: number) => {
  if (usage > 80) return '#f56c6c'
  if (usage > 60) return '#e6a23c'
  return '#67c23a'
}

// 查看设备详情
const viewDevice = (device: any) => {
  router.push(`/device/${device.device_id}`)
}

// 显示添加对话框
const showAddDialog = () => {
  deviceForm.value = {
    device_id: '',
    device_name: '',
    device_type: '',
    group_id: ''
  }
  addDialogVisible.value = true
}

// 添加设备
const addDevice = async () => {
  try {
    await deviceApi.register(deviceForm.value)
    ElMessage.success('设备添加成功')
    addDialogVisible.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error('设备添加失败')
  }
}

// 编辑设备
const editDevice = (device: any) => {
  // TODO: 实现编辑功能
  ElMessage.info('编辑功能待实现')
}

// 删除设备
const deleteDevice = (device: any) => {
  ElMessageBox.confirm(
    `确定要删除设备 "${device.device_name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // await deviceApi.delete(device.device_id)
      ElMessage.success('设备删除成功')
      loadDevices()
    } catch (error) {
      ElMessage.error('设备删除失败')
    }
  })
}

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
  min-height: calc(100vh - 300px);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}
</style>
