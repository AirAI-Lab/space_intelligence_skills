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
              <el-option label="运行中" value="RUNNING" />
              <el-option label="已完成" value="COMPLETED" />
              <el-option label="等待中" value="PENDING" />
              <el-option label="失败" value="FAILED" />
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
        <el-table-column prop="jobName" label="任务名称" width="200" />
        <el-table-column label="模型" width="120">
          <template #default="{ row }">
            {{ row.baseModel || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="datasetName" label="数据集" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="epoch" label="训练轮次" width="100">
          <template #default="{ row }">
            {{ row.currentEpoch || 0 }} / {{ row.epochs || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="(row.progress || 0) * 100" :status="getProgressStatus(row.status)">
              <template #default="{ percentage }">
                <span class="percentage-value">{{ percentage }}%</span>
              </template>
            </el-progress>
          </template>
        </el-table-column>
        <el-table-column prop="metrics" label="指标" width="150">
          <template #default="{ row }">
            <div class="metrics">
              <div>mAP@0.5:0.95: {{ row.finalMap || '-' }}</div>
              <div>Loss: {{ row.finalLoss || '-' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              查看详情
            </el-button>
            <el-button
              v-if="row.status === 'PENDING'"
              size="small"
              type="success"
              @click="startJob(row)"
            >
              启动
            </el-button>
            <el-button
              v-if="row.status === 'RUNNING'"
              size="small"
              type="warning"
              @click="stopJob(row)"
            >
              停止
            </el-button>
            <el-button
              v-if="row.status === 'RUNNING' || row.status === 'CANCELLED' || row.status === 'FAILED'"
              size="small"
              type="primary"
              @click="resumeJob(row)"
            >
              继续训练
            </el-button>
            <el-button
              v-if="row.status === 'COMPLETED'"
              size="small"
              type="success"
              @click="deployModel(row)"
            >
              部署
            </el-button>
            <el-button
              v-if="row.status !== 'RUNNING'"
              size="small"
              type="danger"
              @click="deleteJob(row)"
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
          @size-change="loadJobs"
          @current-change="loadJobs"
        />
      </div>
    </el-card>

    <!-- 创建训练任务对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建训练任务" width="1000px">
      <el-form :model="jobForm" label-width="110px">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="任务名称">
          <el-input v-model="jobForm.jobName" placeholder="例如：安全帽检测v2训练" />
        </el-form-item>

        <el-form-item label="数据集来源">
          <el-radio-group v-model="jobForm.datasetSource" @change="onDatasetSourceChange">
            <el-radio label="backend">管理后台上传</el-radio>
            <el-radio label="url">URL下载</el-radio>
            <el-radio label="local">本地路径</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 管理后台上传的数据集 -->
        <el-form-item v-if="jobForm.datasetSource === 'backend'" label="选择数据集">
          <el-select v-model="jobForm.datasetId" style="width: 100%;" filterable placeholder="请选择数据集">
            <el-option
              v-for="dataset in datasets"
              :key="dataset.datasetId"
              :label="`${dataset.datasetName} (${dataset.sampleCount || 0}样本)`"
              :value="dataset.datasetId"
            />
            <el-option v-if="datasets.length === 0" label="无可用数据集" value="" disabled />
          </el-select>
        </el-form-item>

        <!-- URL 下载数据集 -->
        <el-form-item v-if="jobForm.datasetSource === 'url'" label="数据集 URL">
          <el-input v-model="jobForm.datasetUrl" placeholder="输入数据集下载地址（支持 http/https/git）" />
          <div class="form-tip">支持：直接下载链接、Git仓库、COCO/TensorFlow 数据集</div>
        </el-form-item>

        <!-- 本地路径数据集 -->
        <el-form-item v-if="jobForm.datasetSource === 'local'" label="本地路径">
          <el-input v-model="jobForm.datasetPath" placeholder="输入数据集在训练服务器上的绝对路径" />
          <div class="form-tip">例如：/datasets/my_dataset（需要已包含 YOLO 格式的 data.yaml）</div>
        </el-form-item>

        <el-form-item v-if="jobForm.datasetSource !== 'backend'" label="数据集名称">
          <el-input v-model="jobForm.customDatasetName" placeholder="输入数据集名称" />
        </el-form-item>

        <!-- 模型配置 -->
        <el-divider content-position="left">模型配置</el-divider>

        <el-form-item label="预训练模型">
          <el-select v-model="jobForm.baseModel" style="width: 100%;" placeholder="选择预训练模型">
            <el-option label="YOLOv8n (最快，640x640)" value="yolov8n.pt" />
            <el-option label="YOLOv8s (小型，640x640)" value="yolov8s.pt" />
            <el-option label="YOLOv8m (中型，640x640)" value="yolov8m.pt" />
            <el-option label="YOLOv8l (大型，640x640)" value="yolov8l.pt" />
            <el-option label="自定义模型" value="" />
          </el-select>
        </el-form-item>

        <!-- 训练参数 -->
        <el-divider content-position="left">训练参数</el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="训练轮次">
              <el-input-number v-model="jobForm.epochs" :min="1" :max="500" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="批次大小">
              <el-input-number v-model="jobForm.batchSize" :min="1" :max="128" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="图像尺寸">
              <el-select v-model="jobForm.imgSize" style="width: 100%;">
                <el-option label="320 (快速训练)" :value="320" />
                <el-option label="480 (平衡)" :value="480" />
                <el-option label="640 (标准)" :value="640" />
                <el-option label="960 (高精度)" :value="960" />
                <el-option label="1024 (超高精度)" :value="1024" />
                <el-option label="1280 (最高精度)" :value="1280" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优化器">
              <el-select v-model="jobForm.optimizer" style="width: 100%;">
                <el-option label="SGD" value="SGD" />
                <el-option label="Adam" value="Adam" />
                <el-option label="AdamW" value="AdamW" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="初始学习率">
              <el-input-number v-model="jobForm.lr0" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最终学习率">
              <el-input-number v-model="jobForm.lrf" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="权重衰减">
              <el-input-number v-model="jobForm.weightDecay" :min="0" :max="0.001" :step="0.0001" :precision="4" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 高级参数 -->
        <el-divider content-position="left">高级参数</el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="工作线程">
              <el-input-number v-model="jobForm.workers" :min="1" :max="16" style="width: 160px;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="预热轮次">
              <el-input-number v-model="jobForm.warmupEpochs" :min="0" :max="10" style="width: 160px;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="保存频率">
              <el-input-number v-model="jobForm.savePeriod" :min="1" :max="100" style="width: 160px;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="早停耐心值">
              <el-input-number v-model="jobForm.patience" :min="5" :max="100" style="width: 160px;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Mosaic增强">
              <el-switch v-model="jobForm.mosaic" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Mixup增强">
              <el-switch v-model="jobForm.mixup" />
              <span style="margin-left: 10px; color: #909399; font-size: 12px;">推荐开启（0.15）</span>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="硬件配置">
          <el-checkbox-group v-model="jobForm.hardware">
            <el-checkbox label="使用 GPU">使用 GPU</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="设备说明">
          <el-alert type="info" show-icon :closable="false">
            <template #title>
              <ul style="margin: 0; padding-left: 20px;">
                <li>YOLOv8n: 最快速度，适合实时检测</li>
                <li>YOLOv8s/m: 速度与精度的平衡</li>
                <li>YOLOv8l: 最高精度，适合离线训练</li>
                <li>建议批大小：GPU显存 6GB 使用 16，8GB 使用 32</li>
              </ul>
            </template>
          </el-alert>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createJob" :loading="creating">创建任务</el-button>
      </template>
    </el-dialog>

    <!-- 继续训练对话框 -->
    <el-dialog v-model="resumeDialogVisible" title="继续训练" width="600px">
      <el-alert
        type="info"
        show-icon
        :closable="false"
        style="margin-bottom: 20px;"
      >
        <template #title>
          <div>从任务 <strong>{{ selectedJob?.jobName }}</strong> 的第 {{ selectedJob?.currentEpoch || 0 }} 轮继续训练</div>
        </template>
      </el-alert>

      <el-form :model="resumeForm" label-width="110px">
        <el-form-item label="训练轮次">
          <el-input-number v-model="resumeForm.epochs" :min="selectedJob?.currentEpoch || 1" :max="500" style="width: 100%;" />
          <div class="form-tip">将训练到第 {{ resumeForm.epochs }} 轮（当前已完成 {{ selectedJob?.currentEpoch || 0 }} 轮）</div>
        </el-form-item>

        <el-form-item label="参数策略">
          <el-radio-group v-model="resumeForm.enableSmartOptimization">
            <el-radio :value="false" size="large">使用指定参数</el-radio>
            <el-radio :value="true" size="large">智能优化（推荐）</el-radio>
          </el-radio-group>
          <div class="form-tip">
            <span v-if="!resumeForm.enableSmartOptimization">完全使用下方设定的训练参数</span>
            <span v-else>根据当前训练阶段（初期/中期/后期）和指标趋势，自动调整学习率、patience 等参数以获得最佳效果</span>
          </div>
        </el-form-item>

        <el-divider content-position="left">{{ resumeForm.enableSmartOptimization ? '参考参数（智能优化可能调整）' : '训练参数' }}</el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="批次大小">
              <el-input-number v-model="resumeForm.batchSize" :min="1" :max="128" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="图像尺寸">
              <el-select v-model="resumeForm.imgSize" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;">
                <el-option label="320" :value="320" />
                <el-option label="480" :value="480" />
                <el-option label="640" :value="640" />
                <el-option label="960" :value="960" />
                <el-option label="1024" :value="1024" />
                <el-option label="1280" :value="1280" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="优化器">
              <el-select v-model="resumeForm.optimizer" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;">
                <el-option label="SGD" value="SGD" />
                <el-option label="Adam" value="Adam" />
                <el-option label="AdamW" value="AdamW" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="初始学习率">
              <el-input-number v-model="resumeForm.lr0" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最终学习率">
              <el-input-number v-model="resumeForm.lrf" :min="0.0001" :max="0.1" :step="0.0001" :precision="4" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="权重衰减">
              <el-input-number v-model="resumeForm.weightDecay" :min="0" :max="0.001" :step="0.0001" :precision="4" :disabled="resumeForm.enableSmartOptimization" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="使用 GPU">
          <el-switch v-model="resumeForm.useGpu" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resumeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResume" :loading="resuming">继续训练</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, RefreshLeft, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { trainingApi, dataApi } from '@/api'

const router = useRouter()

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const jobs = ref<any[]>([])
const datasets = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
let refreshTimer: any = null

const createDialogVisible = ref(false)
const creating = ref(false)
const jobForm = ref({
  jobName: '',
  baseModel: 'yolov8n.pt',
  datasetSource: 'backend',  // backend, url, local
  datasetId: '',
  datasetUrl: '',           // URL 下载数据集
  datasetPath: '',          // 本地路径
  customDatasetName: '',    // 自定义数据集名称
  epochs: 100,
  batchSize: 16,
  imgSize: 640,
  optimizer: 'AdamW',       // 优化器：默认 AdamW 更快收敛
  lr0: 0.01,                // 初始学习率
  lrf: 0.001,               // 最终学习率（学习率衰减）
  weightDecay: 0.0005,
  workers: 8,
  warmupEpochs: 3,
  savePeriod: 10,
  patience: 30,             // 早停耐心值
  mosaic: true,
  mixup: true,              // Mixup增强：默认开启
  hardware: ['使用 GPU']
})

// 继续训练相关
const resumeDialogVisible = ref(false)
const selectedJob = ref<any>(null)
const resumeForm = ref({
  epochs: 100,
  batchSize: 16,
  imgSize: 640,
  useGpu: true,
  optimizer: 'AdamW',
  lr0: 0.01,
  lrf: 0.001,
  weightDecay: 0.0005,
  workers: 8,
  warmupEpochs: 3,
  savePeriod: 10,
  mosaic: 1.0,
  mixup: 0.15,
  patience: 30,
  enableSmartOptimization: true  // 默认启用智能优化
})
const resuming = ref(false)

// 数据集来源切换事件
const onDatasetSourceChange = (source: string) => {
  // 清空其他来源的字段
  if (source !== 'backend') jobForm.value.datasetId = ''
  if (source !== 'url') jobForm.value.datasetUrl = ''
  if (source !== 'local') jobForm.value.datasetPath = ''
}

// 加载数据集列表
const loadDatasets = async () => {
  try {
    const response = await dataApi.getList({ page: 1, pageSize: 100 })
    datasets.value = response.data.items || []
    console.log('已加载数据集:', datasets.value.length, '个')
  } catch (error) {
    console.error('加载数据集失败:', error)
  }
}

// 加载任务列表
const loadJobs = async () => {
  loading.value = true
  try {
    const response = await trainingApi.getList({
      page: currentPage.value,
      pageSize: pageSize.value,
      status: statusFilter.value || undefined
    })
    jobs.value = response.data.items || []
    total.value = response.data.total || 0

    // 如果有搜索文本，进行客户端过滤
    if (searchText.value) {
      const filtered = jobs.value.filter((job: any) =>
        job.jobName?.toLowerCase().includes(searchText.value.toLowerCase())
      )
      jobs.value = filtered
    }

    // 对于已取消/失败的任务，获取实际训练进度（从 results.csv）
    await fetchActualProgressForJobs()
  } catch (error: any) {
    ElMessage.error('加载任务列表失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 获取已取消/失败任务的实际训练进度
const fetchActualProgressForJobs = async () => {
  // 只处理已取消或失败的任务
  const jobsNeedingUpdate = jobs.value.filter((job: any) =>
    (job.status === 'CANCELLED' || job.status === 'FAILED') && job.currentEpoch === 0
  )

  if (jobsNeedingUpdate.length === 0) return

  // 并发获取所有任务的实际进度
  const promises = jobsNeedingUpdate.map(async (job: any) => {
    try {
      const result = await trainingApi.getActualProgress(job.jobId)
      if (result.data?.exists && result.data.current_epoch > 0) {
        // 更新任务的 currentEpoch
        job.currentEpoch = result.data.current_epoch
        // 同时更新 progress
        job.progress = Math.min(result.data.current_epoch / job.epochs, 1.0)
        console.log(`任务 ${job.jobId} 实际进度: epoch=${job.currentEpoch}`)
      }
    } catch (error) {
      console.warn(`获取任务 ${job.jobId} 实际进度失败:`, error)
    }
  })

  await Promise.allSettled(promises)
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

// 查看详情
const viewDetail = (job: any) => {
  router.push(`/training/${job.jobId}`)
}

// 启动任务
const startJob = async (job: any) => {
  ElMessageBox.confirm(
    `确定要启动训练任务 "${job.jobName}" 吗？`,
    '确认启动',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(async () => {
    try {
      await trainingApi.startJob(job.jobId)
      ElMessage.success('任务已启动')
      loadJobs()
    } catch (error: any) {
      ElMessage.error('启动任务失败: ' + (error.message || '未知错误'))
    }
  })
}

// 停止任务
const stopJob = async (job: any) => {
  ElMessageBox.confirm(
    `确定要停止训练任务 "${job.jobName}" 吗？`,
    '确认停止',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await trainingApi.stopJob(job.jobId)
      ElMessage.success('任务已停止')
      loadJobs()
    } catch (error: any) {
      ElMessage.error('停止任务失败: ' + (error.message || '未知错误'))
    }
  })
}

// 部署模型
const deployModel = (job: any) => {
  // 检查是否有输出模型ID
  if (job.outputModelId) {
    // 跳转到模型详情页面
    router.push(`/model/${job.outputModelId}`)
    ElMessage.success(`准备部署模型: ${job.jobName}`)
  } else {
    // 任务未完成，提示用户
    ElMessage.warning(`训练任务 "${job.jobName}" 尚未完成，请等待训练完成后再部署`)
  }
}

// 继续训练
const resumeJob = async (job: any) => {
  selectedJob.value = job

  // 获取原任务的实际训练进度（从 results.csv 读取）
  let actualEpoch = job.currentEpoch || 0
  try {
    const result = await trainingApi.getActualProgress(job.jobId)
    if (result.status === 'success' && result.data.exists) {
      actualEpoch = result.data.current_epoch
      console.log(`原任务 ${job.jobId} 实际训练进度: epoch=${actualEpoch}`)
    }
  } catch (error) {
    console.warn('获取实际进度失败，使用数据库记录:', error)
  }

  // 更新原任务的 epoch 显示（用于对话框提示）
  selectedJob.value = { ...job, currentEpoch: actualEpoch }

  resumeDialogVisible.value = true
  // 默认使用相同的训练参数
  resumeForm.value = {
    epochs: job.epochs,
    batchSize: job.batchSize,
    imgSize: job.imgSize,
    useGpu: job.useGpu,
    optimizer: job.hyperparameters?.optimizer || 'AdamW',
    lr0: job.hyperparameters?.lr0 || 0.01,
    lrf: job.hyperparameters?.lrf || 0.001,
    weightDecay: job.hyperparameters?.weight_decay || 0.0005,
    workers: job.hyperparameters?.workers || 8,
    warmupEpochs: job.hyperparameters?.warmup_epochs || 3,
    savePeriod: job.hyperparameters?.save_period || 10,
    mosaic: job.hyperparameters?.mosaic || 1.0,
    mixup: job.hyperparameters?.mixup || 0.15,
    patience: job.hyperparameters?.patience || 30,
    enableSmartOptimization: true  // 默认启用智能优化
  }
}

// 提交继续训练
const submitResume = async () => {
  if (!selectedJob.value) return

  resuming.value = true
  try {
    // 构建请求数据，设置 resume=true 和 resumeJobId
    const requestData: any = {
      jobName: `${selectedJob.value.jobName} (续训)`,
      baseModel: selectedJob.value.baseModel,
      epochs: resumeForm.value.epochs,
      batchSize: resumeForm.value.batchSize,
      imgSize: resumeForm.value.imgSize,
      useGpu: resumeForm.value.useGpu,
      // 断点续训参数
      resume: true,
      resumeJobId: selectedJob.value.jobId,
      // 智能优化开关
      enableSmartOptimization: resumeForm.value.enableSmartOptimization,
      // 超参数
      optimizer: resumeForm.value.optimizer,
      lr0: resumeForm.value.lr0,
      lrf: resumeForm.value.lrf,
      weightDecay: resumeForm.value.weightDecay,
      workers: resumeForm.value.workers,
      warmupEpochs: resumeForm.value.warmupEpochs,
      savePeriod: resumeForm.value.savePeriod,
      patience: resumeForm.value.patience,
      mosaic: resumeForm.value.mosaic,
      mixup: resumeForm.value.mixup
    }

    // 设置数据集来源（与原任务相同）
    requestData.datasetSource = selectedJob.value.datasetSource
    if (selectedJob.value.datasetSource === 'backend') {
      requestData.datasetId = selectedJob.value.datasetId
    } else if (selectedJob.value.datasetSource === 'url') {
      requestData.datasetUrl = selectedJob.value.datasetUrl
      requestData.datasetName = selectedJob.value.datasetName
    } else if (selectedJob.value.datasetSource === 'local') {
      requestData.datasetPath = selectedJob.value.datasetPath
      requestData.datasetName = selectedJob.value.datasetName
    }

    await trainingApi.createJob(requestData)
    ElMessage.success('续训任务创建成功，请启动任务')
    resumeDialogVisible.value = false
    loadJobs()
  } catch (error: any) {
    ElMessage.error('创建续训任务失败: ' + (error.message || '未知错误'))
  } finally {
    resuming.value = false
  }
}

// 删除任务
const deleteJob = async (job: any) => {
  ElMessageBox.confirm(
    `确定要删除训练任务 "${job.jobName}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await trainingApi.deleteJob(job.jobId)
      ElMessage.success('任务已删除')
      loadJobs()
    } catch (error: any) {
      ElMessage.error('删除任务失败: ' + (error.message || '未知错误'))
    }
  })
}

// 显示创建对话框
const showCreateDialog = () => {
  jobForm.value = {
    jobName: '',
    baseModel: 'yolov8n.pt',
    datasetSource: 'backend',
    datasetId: '',
    datasetUrl: '',
    datasetPath: '',
    customDatasetName: '',
    epochs: 100,
    batchSize: 16,
    imgSize: 640,
    optimizer: 'AdamW',       // 优化器：默认 AdamW 更快收敛
    lr0: 0.01,                // 初始学习率
    lrf: 0.001,               // 最终学习率（学习率衰减）
    weightDecay: 0.0005,
    workers: 8,
    warmupEpochs: 3,
    savePeriod: 10,
    patience: 30,             // 早停耐心值
    mosaic: true,
    mixup: true,              // Mixup增强：默认开启
    hardware: ['使用 GPU']
  }
  createDialogVisible.value = true
}

// 创建任务
const createJob = async () => {
  // 验证必填字段
  if (!jobForm.value.jobName) {
    ElMessage.warning('请填写任务名称')
    return
  }

  // 根据数据集来源验证
  if (jobForm.value.datasetSource === 'backend' && !jobForm.value.datasetId) {
    ElMessage.warning('请选择数据集')
    return
  }
  if (jobForm.value.datasetSource === 'url' && !jobForm.value.datasetUrl) {
    ElMessage.warning('请输入数据集 URL')
    return
  }
  if (jobForm.value.datasetSource === 'local' && !jobForm.value.datasetPath) {
    ElMessage.warning('请输入本地路径')
    return
  }
  if (jobForm.value.datasetSource !== 'backend' && !jobForm.value.customDatasetName) {
    ElMessage.warning('请填写数据集名称')
    return
  }

  creating.value = true
  try {
    // 构建请求数据 - 包含所有 YOLOv8 训练参数
    const requestData: any = {
      jobName: jobForm.value.jobName,
      baseModel: jobForm.value.baseModel,
      epochs: jobForm.value.epochs,
      batchSize: jobForm.value.batchSize,
      imgSize: jobForm.value.imgSize,
      useGpu: jobForm.value.hardware.includes('使用 GPU'),
      // 超参数
      optimizer: jobForm.value.optimizer,
      lr0: jobForm.value.lr0,
      lrf: jobForm.value.lrf,            // 最终学习率（学习率衰减）
      weightDecay: jobForm.value.weightDecay,
      workers: jobForm.value.workers,
      warmupEpochs: jobForm.value.warmupEpochs,
      savePeriod: jobForm.value.savePeriod,
      patience: jobForm.value.patience,  // 早停耐心值
      mosaic: jobForm.value.mosaic ? 1.0 : 0.0,
      mixup: jobForm.value.mixup ? 0.15 : 0.0  // Mixup 使用 0.15 而不是 1.0
    }

    // 设置数据集来源（重要：后端根据此字段判断如何处理数据集）
    requestData.datasetSource = jobForm.value.datasetSource

    // 根据数据集来源添加相应字段
    if (jobForm.value.datasetSource === 'backend') {
      requestData.datasetId = jobForm.value.datasetId
    } else if (jobForm.value.datasetSource === 'url') {
      requestData.datasetUrl = jobForm.value.datasetUrl
      requestData.datasetName = jobForm.value.customDatasetName
    } else if (jobForm.value.datasetSource === 'local') {
      requestData.datasetPath = jobForm.value.datasetPath
      requestData.datasetName = jobForm.value.customDatasetName
    }

    await trainingApi.createJob(requestData)
    ElMessage.success('训练任务创建成功')
    createDialogVisible.value = false
    loadJobs()
  } catch (error: any) {
    ElMessage.error('创建任务失败: ' + (error.message || '未知错误'))
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  loadJobs()
  loadDatasets()

  // 定时刷新运行中的任务
  refreshTimer = setInterval(() => {
    const hasRunning = jobs.value.some((j: any) => j.status === 'RUNNING')
    if (hasRunning) {
      loadJobs()
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

.form-tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* 确保数值输入框有足够宽度显示完整数值 */
:deep(.el-input-number) {
  min-width: 140px !important;
}

:deep(.el-input-number .el-input__inner) {
  text-align: left;
  padding-left: 10px;
}

/* 对话框内容区可滚动，适应不同分辨率 */
:deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
