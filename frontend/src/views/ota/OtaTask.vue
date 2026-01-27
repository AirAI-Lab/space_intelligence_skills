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
              <el-option label="待升级" value="pending" />
              <el-option label="升级中" value="upgrading" />
              <el-option label="已完成" value="completed" />
              <el-option label="失败" value="failed" />
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
        <el-table-column prop="task_name" label="任务名称" width="200" />
        <el-table-column prop="upgrade_type" label="升级类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.upgrade_type === 'model' ? 'primary' : 'success'">
              {{ row.upgrade_type === 'model' ? '模型升级' : '固件升级' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="target_version" label="目标版本" width="150" />
        <el-table-column prop="target_devices" label="目标设备数" width="120" />
        <el-table-column prop="completed_count" label="已完成" width="100">
          <template #default="{ row }">
            {{ row.completed_count }} / {{ row.target_devices }}
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
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'pending'"
              size="small"
              type="primary"
              @click="startTask(row)"
            >
              开始
            </el-button>
            <el-button
              v-if="row.status === 'upgrading'"
              size="small"
              type="warning"
              @click="pauseTask(row)"
            >
              暂停
            </el-button>
            <el-button
              v-if="row.status === 'failed'"
              size="small"
              type="primary"
              @click="retryTask(row)"
            >
              重试
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
          <el-input v-model="taskForm.task_name" placeholder="例如：设备批量模型升级" />
        </el-form-item>
        <el-form-item label="升级类型">
          <el-radio-group v-model="taskForm.upgrade_type">
            <el-radio label="model">模型升级</el-radio>
            <el-radio label="firmware">固件升级</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="目标模型" v-if="taskForm.upgrade_type === 'model'">
          <el-select v-model="taskForm.model_id" style="width: 100%;">
            <el-option label="安全帽检测v2" value="M001" />
            <el-option label="车辆检测模型" value="M002" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标版本" v-if="taskForm.upgrade_type === 'firmware'">
          <el-input v-model="taskForm.target_version" placeholder="例如：v2.1.0" />
        </el-form-item>
        <el-form-item label="目标设备">
          <el-select v-model="taskForm.device_ids" multiple style="width: 100%;">
            <el-option label="机载设备1号" value="EDGE_001" />
            <el-option label="机载设备2号" value="EDGE_002" />
            <el-option label="机载设备3号" value="EDGE_003" />
          </el-select>
        </el-form-item>
        <el-form-item label="升级策略">
          <el-radio-group v-model="taskForm.strategy">
            <el-radio label="immediate">立即升级</el-radio>
            <el-radio label="scheduled">定时升级</el-radio>
            <el-radio label="manual">手动确认</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="定时时间" v-if="taskForm.strategy === 'scheduled'">
          <el-date-picker
            v-model="taskForm.scheduled_time"
            type="datetime"
            placeholder="选择日期时间"
            style="width: 100%;"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTask">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const tasks = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const createDialogVisible = ref(false)
const taskForm = ref({
  task_name: '',
  upgrade_type: 'model',
  model_id: '',
  target_version: '',
  device_ids: [],
  strategy: 'immediate',
  scheduled_time: null
})

// 模拟数据
const mockTasks = [
  {
    task_id: 'OTA001',
    task_name: '设备批量模型升级',
    upgrade_type: 'model',
    target_version: 'v2.1.0',
    target_devices: 15,
    completed_count: 12,
    progress: 80,
    status: 'upgrading',
    created_at: '2026-01-27 08:00:00'
  },
  {
    task_id: 'OTA002',
    task_name: '固件升级批次1',
    upgrade_type: 'firmware',
    target_version: 'v1.5.2',
    target_devices: 8,
    completed_count: 8,
    progress: 100,
    status: 'completed',
    created_at: '2026-01-26 14:00:00'
  },
  {
    task_id: 'OTA003',
    task_name: '新设备初始化',
    upgrade_type: 'model',
    target_version: 'v2.0.0',
    target_devices: 5,
    completed_count: 0,
    progress: 0,
    status: 'pending',
    created_at: '2026-01-27 10:00:00'
  }
]

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  setTimeout(() => {
    tasks.value = mockTasks
    total.value = mockTasks.length
    loading.value = false
  }, 500)
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
    upgrading: 'primary',
    completed: 'success',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    upgrading: '升级中',
    completed: '已完成',
    pending: '待升级',
    failed: '失败'
  }
  return texts[status] || status
}

// 获取进度状态
const getProgressStatus = (status: string) => {
  const statuses: Record<string, any> = {
    completed: 'success',
    failed: 'exception'
  }
  return statuses[status] || undefined
}

// 查看详情
const viewDetail = (task: any) => {
  ElMessage.info(`查看任务详情: ${task.task_name}`)
}

// 开始任务
const startTask = (task: any) => {
  ElMessageBox.confirm(
    `确定要开始升级任务 "${task.task_name}" 吗？`,
    '确认开始',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(() => {
    ElMessage.success('任务开始执行')
    loadTasks()
  })
}

// 暂停任务
const pauseTask = (task: any) => {
  ElMessageBox.confirm(
    `确定要暂停任务 "${task.task_name}" 吗？`,
    '确认暂停',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('任务已暂停')
    loadTasks()
  })
}

// 重试任务
const retryTask = (task: any) => {
  ElMessage.success(`开始重试任务: ${task.task_name}`)
  loadTasks()
}

// 显示创建对话框
const showCreateDialog = () => {
  taskForm.value = {
    task_name: '',
    upgrade_type: 'model',
    model_id: '',
    target_version: '',
    device_ids: [],
    strategy: 'immediate',
    scheduled_time: null
  }
  createDialogVisible.value = true
}

// 创建任务
const createTask = () => {
  if (!taskForm.value.task_name || taskForm.value.device_ids.length === 0) {
    ElMessage.warning('请填写完整信息')
    return
  }
  ElMessage.success('升级任务创建成功')
  createDialogVisible.value = false
  loadTasks()
}

onMounted(() => {
  loadTasks()
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
</style>
