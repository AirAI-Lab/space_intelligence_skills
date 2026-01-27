<template>
  <div class="training-job">
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
              <el-option label="运行中" value="running" />
              <el-option label="已完成" value="completed" />
              <el-option label="等待中" value="pending" />
              <el-option label="失败" value="failed" />
            </el-select>
            <el-button type="primary" @click="loadJobs">
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
            创建训练任务
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="table-card">
      <el-table :data="jobs" v-loading="loading" style="width: 100%">
        <el-table-column prop="job_name" label="任务名称" width="200" />
        <el-table-column prop="model_name" label="模型" width="120" />
        <el-table-column prop="dataset_name" label="数据集" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="epoch" label="训练轮次" width="100">
          <template #default="{ row }">
            {{ row.current_epoch }} / {{ row.total_epochs }}
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
        <el-table-column prop="metrics" label="指标" width="150">
          <template #default="{ row }">
            <div class="metrics">
              <div>mAP: {{ row.map || '-' }}</div>
              <div>Loss: {{ row.loss || '-' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="warning"
              @click="stopJob(row)"
            >
              停止
            </el-button>
            <el-button
              v-if="row.status === 'completed'"
              size="small"
              type="success"
              @click="deployModel(row)"
            >
              部署
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
          @size-change="loadJobs"
          @current-change="loadJobs"
        />
      </div>
    </el-card>

    <!-- 创建训练任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建训练任务" width="700px">
      <el-form :model="jobForm" label-width="120px">
        <el-form-item label="任务名称">
          <el-input v-model="jobForm.job_name" placeholder="例如：安全帽检测v2训练" />
        </el-form-item>
        <el-form-item label="基础模型">
          <el-select v-model="jobForm.model_name" style="width: 100%;">
            <el-option label="YOLOv8n" value="yolov8n" />
            <el-option label="YOLOv8s" value="yolov8s" />
            <el-option label="YOLOv8m" value="yolov8m" />
            <el-option label="YOLOv8l" value="yolov8l" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据集">
          <el-select v-model="jobForm.dataset_id" style="width: 100%;">
            <el-option label="安全帽检测数据集" value="DS001" />
            <el-option label="车辆识别数据集" value="DS002" />
          </el-select>
        </el-form-item>
        <el-form-item label="训练轮次">
          <el-input-number v-model="jobForm.epochs" :min="1" :max="500" />
        </el-form-item>
        <el-form-item label="批次大小">
          <el-input-number v-model="jobForm.batch_size" :min="1" :max="128" />
        </el-form-item>
        <el-form-item label="图像大小">
          <el-select v-model="jobForm.img_size">
            <el-option label="640" :value="640" />
            <el-option label="1280" :value="1280" />
          </el-select>
        </el-form-item>
        <el-form-item label="使用GPU">
          <el-switch v-model="jobForm.use_gpu" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createJob">开始训练</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const jobs = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const createDialogVisible = ref(false)
const jobForm = ref({
  job_name: '',
  model_name: 'yolov8n',
  dataset_id: '',
  epochs: 100,
  batch_size: 16,
  img_size: 640,
  use_gpu: true
})

// 模拟数据
const mockJobs = [
  {
    job_id: 'JOB001',
    job_name: '安全帽检测v2',
    model_name: 'YOLOv8n',
    dataset_name: '安全帽检测数据集',
    status: 'running',
    current_epoch: 65,
    total_epochs: 100,
    progress: 65,
    map: 0.825,
    loss: 0.245,
    created_at: '2026-01-26 15:30:00'
  },
  {
    job_id: 'JOB002',
    job_name: '车辆检测训练',
    model_name: 'YOLOv8s',
    dataset_name: '车辆识别数据集',
    status: 'completed',
    current_epoch: 100,
    total_epochs: 100,
    progress: 100,
    map: 0.892,
    loss: 0.156,
    created_at: '2026-01-25 10:00:00'
  },
  {
    job_id: 'JOB003',
    job_name: '人员识别微调',
    model_name: 'YOLOv8m',
    dataset_name: '人员分类数据集',
    status: 'pending',
    current_epoch: 0,
    total_epochs: 50,
    progress: 0,
    map: null,
    loss: null,
    created_at: '2026-01-27 09:00:00'
  }
]

// 加载任务列表
const loadJobs = async () => {
  loading.value = true
  setTimeout(() => {
    jobs.value = mockJobs
    total.value = mockJobs.length
    loading.value = false
  }, 500)
}

// 重置筛选
const resetFilter = () => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadJobs()
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    running: 'primary',
    completed: 'success',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    pending: '等待中',
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
const viewDetail = (job: any) => {
  ElMessage.info(`查看任务详情: ${job.job_name}`)
}

// 停止任务
const stopJob = (job: any) => {
  ElMessageBox.confirm(
    `确定要停止训练任务 "${job.job_name}" 吗？`,
    '确认停止',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('任务已停止')
    loadJobs()
  })
}

// 部署模型
const deployModel = (job: any) => {
  router.push('/model')
  ElMessage.success(`准备部署模型: ${job.job_name}`)
}

// 显示创建对话框
const showCreateDialog = () => {
  jobForm.value = {
    job_name: '',
    model_name: 'yolov8n',
    dataset_id: '',
    epochs: 100,
    batch_size: 16,
    img_size: 640,
    use_gpu: true
  }
  createDialogVisible.value = true
}

// 创建任务
const createJob = () => {
  if (!jobForm.value.job_name || !jobForm.value.dataset_id) {
    ElMessage.warning('请填写完整信息')
    return
  }
  ElMessage.success('训练任务创建成功')
  createDialogVisible.value = false
  loadJobs()
}

onMounted(() => {
  loadJobs()
})
</script>

<style scoped>
.training-job {
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

.metrics {
  font-size: 12px;
  color: #666;
}

.percentage-value {
  font-size: 12px;
}
</style>
