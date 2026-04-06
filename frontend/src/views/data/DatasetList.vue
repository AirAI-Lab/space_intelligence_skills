<template>
  <div class="dataset-list">
    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-space>
            <el-input
              v-model="searchText"
              placeholder="搜索数据集名称或ID"
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
              placeholder="数据集状态"
              clearable
              style="width: 150px"
              @change="handleFilterChange"
            >
              <el-option label="全部" value="" />
              <el-option label="准备中" value="PREPARING" />
              <el-option label="就绪" value="READY" />
              <el-option label="使用中" value="IN_USE" />
              <el-option label="已完成" value="COMPLETED" />
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
          <el-button type="primary" @click="handleShowUploadDialog">
            <el-icon><Upload /></el-icon>
            上传数据集
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 数据集列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="datasets"
        style="width: 100%"
        stripe
        @row-click="handleViewDetail"
      >
        <el-table-column prop="datasetId" label="数据集ID" width="180" />
        <el-table-column prop="datasetName" label="数据集名称" width="200" />
        <el-table-column prop="datasetType" label="数据集类型" width="150">
          <template #default="{ row }">
            <el-tag>{{ row.datasetType || '通用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="taskType" label="任务类型" width="150">
          <template #default="{ row }">
            {{ getTaskTypeText(row.taskType) }}
          </template>
        </el-table-column>
        <el-table-column prop="sampleCount" label="样本数量" width="120" align="center">
          <template #default="{ row }">
            {{ formatNumber(row.sampleCount) }}
          </template>
        </el-table-column>
        <el-table-column prop="fileSize" label="文件大小" width="120" align="center">
          <template #default="{ row }">
            {{ formatFileSize(row.fileSize) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">
              查看详情
            </el-button>
            <el-button size="small" type="primary" @click.stop="handleUseForTraining(row)">
              用于训练
            </el-button>
            <el-button size="small" type="danger" @click.stop="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; justify-content: center"
      />
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传数据集"
      width="600px"
      @close="handleCloseUploadDialog"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="数据集名称">
          <el-input v-model="uploadForm.datasetName" placeholder="请输入数据集名称" />
        </el-form-item>
        <el-form-item label="数据集类型">
          <el-select v-model="uploadForm.datasetType" placeholder="请选择类型">
            <el-option label="图像分类" value="IMAGE_CLASSIFICATION" />
            <el-option label="目标检测" value="OBJECT_DETECTION" />
            <el-option label="语义分割" value="SEMANTIC_SEGMENTATION" />
            <el-option label="通用" value="GENERAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型">
          <el-select v-model="uploadForm.taskType" placeholder="请选择任务类型">
            <el-option label="训练" value="TRAINING" />
            <el-option label="验证" value="VALIDATION" />
            <el-option label="测试" value="TEST" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据集文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            accept=".zip,.tar,.tar.gz"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div style="color: #999; margin-top: 5px">
                支持 .zip、.tar、.tar.gz 格式，单个文件不超过 10GB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入数据集描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshLeft, Upload } from '@element-plus/icons-vue'
import type { UploadInstance, UploadUserFile } from 'element-plus'

const router = useRouter()

// 数据
const loading = ref(false)
const datasets = ref([])
const searchText = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 上传
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref<UploadInstance>()
const uploadForm = ref({
  datasetName: '',
  datasetType: '',
  taskType: '',
  description: '',
  file: null as File | null
})

// 获取数据集列表
const fetchDatasets = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取数据集列表
    // const response = await api.getDatasets({
    //   page: currentPage.value,
    //   size: pageSize.value,
    //   search: searchText.value,
    //   status: statusFilter.value
    // })
    // datasets.value = response.data
    // total.value = response.total

    // 模拟数据
    setTimeout(() => {
      datasets.value = [
        {
          datasetId: 'DS001',
          datasetName: '工地安全数据集',
          datasetType: 'OBJECT_DETECTION',
          taskType: 'TRAINING',
          sampleCount: 15000,
          fileSize: 2147483648,
          status: 'READY',
          createdAt: '2024-03-10 10:30:00'
        },
        {
          datasetId: 'DS002',
          datasetName: '人员检测数据集',
          datasetType: 'OBJECT_DETECTION',
          taskType: 'VALIDATION',
          sampleCount: 3000,
          fileSize: 536870912,
          status: 'IN_USE',
          createdAt: '2024-03-12 14:20:00'
        }
      ]
      total.value = 2
      loading.value = false
    }, 500)
  } catch (error) {
    ElMessage.error('获取数据集列表失败')
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  fetchDatasets()
}

// 重置
const handleReset = () => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  fetchDatasets()
}

// 过滤变化
const handleFilterChange = () => {
  currentPage.value = 1
  fetchDatasets()
}

// 分页变化
const handlePageChange = () => {
  fetchDatasets()
}

const handleSizeChange = () => {
  currentPage.value = 1
  fetchDatasets()
}

// 查看详情
const handleViewDetail = (row: any) => {
  router.push(`/data/datasets/${row.datasetId}`)
}

// 用于训练
const handleUseForTraining = (row: any) => {
  router.push({
    path: '/training',
    query: { datasetId: row.datasetId }
  })
}

// 删除
const handleDelete = (row: any) => {
  ElMessageBox.confirm(
    `确定要删除数据集 "${row.datasetName}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      // TODO: 调用API删除数据集
      // await api.deleteDataset(row.datasetId)
      ElMessage.success('删除成功')
      fetchDatasets()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 显示上传对话框
const handleShowUploadDialog = () => {
  uploadDialogVisible.value = true
}

// 关闭上传对话框
const handleCloseUploadDialog = () => {
  uploadForm.value = {
    datasetName: '',
    datasetType: '',
    taskType: '',
    description: '',
    file: null
  }
  uploadRef.value?.clearFiles()
}

// 文件变化
const handleFileChange = (file: UploadUserFile) => {
  uploadForm.value.file = file.raw as File
}

// 文件超出限制
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 上传
const handleUpload = async () => {
  if (!uploadForm.value.datasetName) {
    ElMessage.warning('请输入数据集名称')
    return
  }
  if (!uploadForm.value.file) {
    ElMessage.warning('请选择数据集文件')
    return
  }

  uploading.value = true
  try {
    // TODO: 调用API上传数据集
    // const formData = new FormData()
    // formData.append('file', uploadForm.value.file)
    // formData.append('datasetName', uploadForm.value.datasetName)
    // formData.append('datasetType', uploadForm.value.datasetType)
    // formData.append('taskType', uploadForm.value.taskType)
    // formData.append('description', uploadForm.value.description)
    // await api.uploadDataset(formData)

    setTimeout(() => {
      ElMessage.success('上传成功')
      uploadDialogVisible.value = false
      fetchDatasets()
      uploading.value = false
    }, 1000)
  } catch (error) {
    ElMessage.error('上传失败')
    uploading.value = false
  }
}

// 工具函数
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
  fetchDatasets()
})
</script>

<style scoped>
.dataset-list {
  padding: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.table-card {
  min-height: 400px;
}

.el-table {
  cursor: pointer;
}

.el-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
