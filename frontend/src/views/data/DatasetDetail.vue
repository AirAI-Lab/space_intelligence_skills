<template>
  <div class="dataset-detail">
    <!-- 返回按钮 -->
    <el-button @click="handleBack" style="margin-bottom: 20px">
      <el-icon><ArrowLeft /></el-icon>
      返回列表
    </el-button>

    <!-- 加载状态 -->
    <div v-if="loading" v-loading="loading" style="min-height: 400px"></div>

    <template v-else>
      <!-- 基本信息 -->
      <el-card class="info-card">
        <template #header>
          <div class="card-header">
            <span>数据集详情</span>
            <el-space>
              <el-button type="primary" @click="handleEdit">
                <el-icon><Edit /></el-icon>
                编辑
              </el-button>
              <el-button type="success" @click="handleUseForTraining">
                <el-icon><VideoPlay /></el-icon>
                用于训练
              </el-button>
              <el-button type="danger" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                删除
              </el-button>
            </el-space>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="数据集ID">
            {{ dataset.datasetId }}
          </el-descriptions-item>
          <el-descriptions-item label="数据集名称">
            {{ dataset.datasetName }}
          </el-descriptions-item>
          <el-descriptions-item label="数据集类型">
            <el-tag>{{ getDatasetTypeText(dataset.datasetType) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="任务类型">
            {{ getTaskTypeText(dataset.taskType) }}
          </el-descriptions-item>
          <el-descriptions-item label="样本数量">
            {{ formatNumber(dataset.sampleCount) }}
          </el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ formatFileSize(dataset.fileSize) }}
          </el-descriptions-item>
          <el-descriptions-item label="标签数量">
            {{ dataset.labelCount || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(dataset.status)">
              {{ getStatusText(dataset.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间" :span="2">
            {{ dataset.createdAt }}
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            {{ dataset.description || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 数据统计 -->
      <el-card class="stats-card">
        <template #header>
          <span>数据统计</span>
        </template>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-statistic title="总样本数" :value="dataset.sampleCount" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="训练集" :value="dataset.trainCount || 0" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="验证集" :value="dataset.valCount || 0" />
          </el-col>
          <el-col :span="6">
            <el-statistic title="测试集" :value="dataset.testCount || 0" />
          </el-col>
        </el-row>

        <!-- 类别分布 -->
        <div v-if="dataset.labelDistribution" style="margin-top: 30px">
          <h4>类别分布</h4>
          <el-table :data="dataset.labelDistribution" style="margin-top: 10px">
            <el-table-column prop="label" label="类别" width="200" />
            <el-table-column prop="count" label="数量" align="center" />
            <el-table-column prop="percentage" label="占比" align="center">
              <template #default="{ row }">
                {{ (row.percentage * 100).toFixed(2) }}%
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-card>

      <!-- 使用记录 -->
      <el-card class="usage-card">
        <template #header>
          <span>使用记录</span>
        </template>

        <el-table :data="dataset.usageHistory || []" stripe>
          <el-table-column prop="jobId" label="任务ID" width="180" />
          <el-table-column prop="jobName" label="任务名称" width="200" />
          <el-table-column prop="usedAt" label="使用时间" width="180" />
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'COMPLETED' ? 'success' : 'warning'">
                {{ row.status === 'COMPLETED' ? '已完成' : '进行中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" align="center">
            <template #default="{ row }">
              <el-button size="small" @click="viewTrainingJob(row.jobId)">
                查看详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 预览 -->
      <el-card class="preview-card" v-if="dataset.previewImages">
        <template #header>
          <span>数据预览</span>
        </template>

        <el-image
          v-for="(img, index) in dataset.previewImages"
          :key="index"
          :src="img.url"
          :preview-src-list="dataset.previewImages.map(i => i.url)"
          :initial-index="index"
          fit="cover"
          style="width: 150px; height: 150px; margin: 10px; border-radius: 4px"
        />
      </el-card>
    </template>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑数据集" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="数据集名称">
          <el-input v-model="editForm.datasetName" placeholder="请输入数据集名称" />
        </el-form-item>
        <el-form-item label="数据集类型">
          <el-select v-model="editForm.datasetType" placeholder="请选择类型">
            <el-option label="图像分类" value="IMAGE_CLASSIFICATION" />
            <el-option label="目标检测" value="OBJECT_DETECTION" />
            <el-option label="语义分割" value="SEMANTIC_SEGMENTATION" />
            <el-option label="通用" value="GENERAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="editForm.taskType" placeholder="请选择任务类型">
            <el-option label="训练" value="TRAINING" />
            <el-option label="验证" value="VALIDATION" />
            <el-option label="测试" value="TEST" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入数据集描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Edit, Delete, VideoPlay } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const datasetId = route.params.id as string

// 数据
const loading = ref(false)
const saving = ref(false)
const editDialogVisible = ref(false)
const dataset = ref<any>({
  datasetId: '',
  datasetName: '',
  datasetType: '',
  taskType: '',
  sampleCount: 0,
  fileSize: 0,
  labelCount: 0,
  status: '',
  createdAt: '',
  description: '',
  trainCount: 0,
  valCount: 0,
  testCount: 0,
  labelDistribution: [],
  usageHistory: [],
  previewImages: []
})

const editForm = ref({
  datasetName: '',
  datasetType: '',
  taskType: '',
  description: ''
})

// 获取数据集详情
const fetchDatasetDetail = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取数据集详情
    // const response = await api.getDatasetDetail(datasetId)
    // dataset.value = response.data

    // 模拟数据
    setTimeout(() => {
      dataset.value = {
        datasetId: 'DS001',
        datasetName: '工地安全数据集',
        datasetType: 'OBJECT_DETECTION',
        taskType: 'TRAINING',
        sampleCount: 15000,
        fileSize: 2147483648,
        labelCount: 5,
        status: 'READY',
        createdAt: '2024-03-10 10:30:00',
        description: '用于工地安全检测的数据集，包含人员、安全帽、安全带等类别',
        trainCount: 12000,
        valCount: 2000,
        testCount: 1000,
        labelDistribution: [
          { label: '人员', count: 6000, percentage: 0.4 },
          { label: '安全帽', count: 4500, percentage: 0.3 },
          { label: '安全带', count: 3000, percentage: 0.2 },
          { label: '反光衣', count: 1500, percentage: 0.1 }
        ],
        usageHistory: [
          {
            jobId: 'JOB001',
            jobName: 'YOLOv8训练',
            usedAt: '2024-03-12 09:00:00',
            status: 'COMPLETED'
          }
        ],
        previewImages: [
          { url: 'https://via.placeholder.com/150' },
          { url: 'https://via.placeholder.com/150' },
          { url: 'https://via.placeholder.com/150' },
          { url: 'https://via.placeholder.com/150' }
        ]
      }
      loading.value = false
    }, 500)
  } catch (error) {
    ElMessage.error('获取数据集详情失败')
    loading.value = false
  }
}

// 返回
const handleBack = () => {
  router.back()
}

// 编辑
const handleEdit = () => {
  editForm.value = {
    datasetName: dataset.value.datasetName,
    datasetType: dataset.value.datasetType,
    taskType: dataset.value.taskType,
    description: dataset.value.description
  }
  editDialogVisible.value = true
}

// 保存
const handleSave = async () => {
  saving.value = true
  try {
    // TODO: 调用API更新数据集
    // await api.updateDataset(datasetId, editForm.value)

    setTimeout(() => {
      dataset.value = {
        ...dataset.value,
        ...editForm.value
      }
      ElMessage.success('保存成功')
      editDialogVisible.value = false
      saving.value = false
    }, 500)
  } catch (error) {
    ElMessage.error('保存失败')
    saving.value = false
  }
}

// 用于训练
const handleUseForTraining = () => {
  router.push({
    path: '/training',
    query: { datasetId: dataset.value.datasetId }
  })
}

// 删除
const handleDelete = () => {
  ElMessageBox.confirm(
    `确定要删除数据集 "${dataset.value.datasetName}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // TODO: 调用API删除数据集
      // await api.deleteDataset(datasetId)
      ElMessage.success('删除成功')
      router.push('/data')
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 查看训练任务
const viewTrainingJob = (jobId: string) => {
  router.push(`/training/${jobId}`)
}

// 工具函数
const getDatasetTypeText = (type: string) => {
  const map: Record<string, string> = {
    IMAGE_CLASSIFICATION: '图像分类',
    OBJECT_DETECTION: '目标检测',
    SEMANTIC_SEGMENTATION: '语义分割',
    GENERAL: '通用'
  }
  return map[type] || type
}

const getTaskTypeText = (type: string) => {
  const map: Record<string, string> = {
    TRAINING: '训练',
    VALIDATION: '验证',
    TEST: '测试'
  }
  return map[type] || type
}

const getStatusType = (status: string) => {
  const map: Record<string, any> = {
    PREPARING: 'info',
    READY: 'success',
    IN_USE: 'warning',
    COMPLETED: ''
  }
  return map[status] || ''
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    PREPARING: '准备中',
    READY: '就绪',
    IN_USE: '使用中',
    COMPLETED: '已完成'
  }
  return map[status] || status
}

const formatNumber = (num: number) => {
  return num?.toLocaleString() || '0'
}

const formatFileSize = (bytes: number) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let index = 0
  let size = bytes
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index++
  }
  return `${size.toFixed(2)} ${units[index]}`
}

onMounted(() => {
  fetchDatasetDetail()
})
</script>

<style scoped>
.dataset-detail {
  padding: 20px;
}

.info-card,
.stats-card,
.usage-card,
.preview-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
