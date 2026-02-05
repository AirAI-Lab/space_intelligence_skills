<template>
  <div class="model-list">
    <!-- 操作栏 -->
    <el-card class="action-bar">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-space>
            <el-input
              v-model="searchText"
              placeholder="搜索模型名称"
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
              placeholder="模型状态"
              clearable
              style="width: 150px"
              @change="handleFilterChange"
            >
              <el-option label="全部" value="" />
              <el-option label="就绪" value="READY" />
              <el-option label="训练中" value="TRAINING" />
              <el-option label="已部署" value="DEPLOYED" />
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
          <el-button type="primary" @click="handleShowImportDialog">
            <el-icon><Upload /></el-icon>
            导入模型
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 模型列表 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="models"
        style="width: 100%"
        stripe
        @row-click="handleViewDetail"
      >
        <el-table-column prop="modelName" label="模型名称" width="200" />
        <el-table-column prop="modelType" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.modelType)">
              {{ getTypeText(row.modelType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="framework" label="框架" width="120" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="map50" label="mAP@0.5" width="100" align="center">
          <template #default="{ row }">
            {{ row.map50 ? (row.map50 * 100).toFixed(2) + '%' : (row.map ? (row.map * 100).toFixed(2) + '%' : '-') }}
          </template>
        </el-table-column>
        <el-table-column prop="inferenceTimeMs" label="推理时间" width="120" align="center">
          <template #default="{ row }">
            {{ row.inferenceTimeMs ? row.inferenceTimeMs + ' ms' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deployedCount" label="部署数" width="100" align="center" />
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleViewDetail(row)">
              查看详情
            </el-button>
            <el-button
              size="small"
              type="success"
              @click.stop="handleDeploy(row)"
              :disabled="row.status !== 'READY'"
            >
              部署
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click.stop="handleDownload(row)"
            >
              下载
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
          @size-change="loadModels"
          @current-change="loadModels"
        />
      </div>
    </el-card>

    <!-- 导入模型对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入模型"
      width="600px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
    >
      <el-form :model="modelForm" label-width="100px">
        <el-form-item label="模型名称" required>
          <el-input
            v-model="modelForm.modelName"
            placeholder="例如：YOLOv8安全帽检测"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="模型类型" required>
          <el-select v-model="modelForm.modelType" style="width: 100%">
            <el-option label="目标检测" value="DETECTION" />
            <el-option label="图像分类" value="CLASSIFICATION" />
            <el-option label="语义分割" value="SEGMENTATION" />
            <el-option label="姿态估计" value="POSE" />
          </el-select>
        </el-form-item>
        <el-form-item label="框架" required>
          <el-select v-model="modelForm.framework" style="width: 100%">
            <el-option label="PyTorch" value="PyTorch" />
            <el-option label="ONNX" value="ONNX" />
            <el-option label="TensorFlow" value="TensorFlow" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本" required>
          <el-input
            v-model="modelForm.version"
            placeholder="1.0.0"
            maxlength="50"
          />
        </el-form-item>
        <el-form-item label="模型文件" required>
          <el-upload
            class="upload-area"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            :file-list="fileList"
            accept=".pt,.pth,.onnx,.engine"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PyTorch (.pt/.pth) 或 ONNX (.onnx) 格式，文件大小不超过 500MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <div v-if="importing" class="upload-progress">
            <el-progress
              :percentage="uploadProgress"
              :status="uploadProgress === 100 ? 'success' : undefined"
            />
            <div class="progress-text">{{ uploadProgress }}%</div>
          </div>
          <div class="dialog-buttons">
            <el-button @click="handleCancelImport" :disabled="importing">
              取消
            </el-button>
            <el-button
              type="primary"
              @click="handleImport"
              :loading="importing"
              :disabled="!canImport"
            >
              {{ importing ? '上传中...' : '导入' }}
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// ==================== Vue 核心库 ====================
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'

// ==================== 第三方 UI 库 ====================
import { ElMessage, ElMessageBox, type UploadUserFile, type UploadProps } from 'element-plus'
import { Search, RefreshLeft, Upload, UploadFilled } from '@element-plus/icons-vue'

// ==================== API 服务 ====================
import { modelApi } from '@/api'

// ==================== 类型定义 ====================
interface ModelForm {
  modelName: string
  modelType: string
  framework: string
  version: string
}

interface ModelItem {
  modelId: string
  modelName: string
  modelType: string
  framework: string
  version: string
  parentModelId: string | null
  datasetId: string | null
  ptFilePath: string | null
  onnxFilePath: string | null
  engineFilePath: string | null
  map: number | null
  precision: number | null
  recall: number | null
  inferenceTimeMs: number | null
  inputWidth: number
  inputHeight: number
  classNames: string[] | null
  status: string
  fileSizeBytes: number | null
  deployedCount: number
  createdAt: string
  updatedAt: string
}

// ==================== 路由 ====================
const router = useRouter()

// ==================== 响应式状态 ====================
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const models = ref<ModelItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 导入相关状态
const importDialogVisible = ref(false)
const importing = ref(false)
const uploadProgress = ref(0)
const fileList = ref<UploadUserFile[]>([])

const modelForm = reactive<ModelForm>({
  modelName: '',
  modelType: 'DETECTION',
  framework: 'PyTorch',
  version: '1.0.0'
})

// ==================== 计算属性 ====================
const canImport = computed(() => {
  return modelForm.modelName.trim() !== '' &&
         modelForm.modelType !== '' &&
         modelForm.framework !== '' &&
         modelForm.version.trim() !== '' &&
         fileList.value.length > 0
})

// ==================== 类型映射 ====================
const getTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    'DETECTION': 'primary',
    'CLASSIFICATION': 'success',
    'SEGMENTATION': 'warning',
    'POSE': 'danger'
  }
  return colors[type] || 'info'
}

const getTypeText = (type: string): string => {
  const texts: Record<string, string> = {
    'DETECTION': '检测',
    'CLASSIFICATION': '分类',
    'SEGMENTATION': '分割',
    'POSE': '姿态'
  }
  return texts[type] || type
}

const getStatusType = (status: string): string => {
  const types: Record<string, string> = {
    'READY': 'success',
    'TRAINING': 'warning',
    'CONVERTING': 'info',
    'DEPLOYED': 'primary',
    'ARCHIVED': 'info',
    'ERROR': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    'READY': '就绪',
    'TRAINING': '训练中',
    'CONVERTING': '转换中',
    'DEPLOYED': '已部署',
    'ARCHIVED': '已归档',
    'ERROR': '错误'
  }
  return texts[status] || status
}

// ==================== 数据加载 ====================
const loadModels = async (): Promise<void> => {
  loading.value = true
  try {
    const response = await modelApi.getList({
      page: currentPage.value,
      pageSize: pageSize.value
    })
    models.value = response.data?.items || []
    total.value = response.data?.total || 0

    // 客户端搜索过滤
    if (searchText.value) {
      const filtered = models.value.filter((m: ModelItem) =>
        m.modelName?.toLowerCase().includes(searchText.value.toLowerCase())
      )
      models.value = filtered
    }

    // 客户端状态过滤
    if (statusFilter.value) {
      const filtered = models.value.filter((m: ModelItem) =>
        m.status === statusFilter.value
      )
      models.value = filtered
    }
  } catch (error: any) {
    console.error('加载模型列表失败:', error)
    ElMessage.error(`加载模型列表失败: ${error.message || '未知错误'}`)
    models.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ==================== 搜索和筛选 ====================
const handleSearch = (): void => {
  currentPage.value = 1
  loadModels()
}

const handleFilterChange = (): void => {
  currentPage.value = 1
  loadModels()
}

const handleReset = (): void => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadModels()
}

// ==================== 模型操作 ====================
const handleViewDetail = async (model: ModelItem): Promise<void> => {
  console.log('Viewing model detail:', model.modelId, model.modelName)
  try {
    await router.push(`/model/${model.modelId}`)
    console.log('Navigation successful')
  } catch (error) {
    console.error('Navigation failed:', error)
    ElMessage.error('页面跳转失败，请稍后重试')
  }
}

const handleDeploy = (model: ModelItem): void => {
  router.push({
    path: '/model',
    query: { deployModel: model.modelId }
  })
  // 然后打开模型详情页面
  router.push(`/model/${model.modelId}`)
}

const handleDownload = async (model: ModelItem): Promise<void> => {
  // 优先下载 ONNX 格式，如果没有则下载 PT
  let format = 'pt'
  if (model.onnxFilePath) {
    format = 'onnx'
  } else if (model.engineFilePath) {
    format = 'engine'
  }

  // 检查文件路径是否存在
  const filePath = format === 'onnx' ? model.onnxFilePath : (format === 'engine' ? model.engineFilePath : model.ptFilePath)
  if (!filePath) {
    ElMessage.warning(`模型没有 ${format.toUpperCase()} 文件，请先转换模型`)
    return
  }

  // 构建下载 URL
  const downloadUrl = `/api/v1/models/${model.modelId}/download?format=${format}`

  try {
    // 使用 fetch API 获取二进制数据
    const response = await fetch(downloadUrl)

    if (!response.ok) {
      // 尝试解析错误信息
      const errorText = await response.text()
      let errorMessage = '下载失败'
      try {
        const errorJson = JSON.parse(errorText)
        errorMessage = errorJson.message || errorMessage
      } catch {
        errorMessage = errorText || errorMessage
      }
      ElMessage.error(errorMessage)
      return
    }

    // 检查响应类型是否为二进制
    const contentType = response.headers.get('Content-Type')
    if (contentType && contentType.includes('application/json')) {
      // 如果返回的是 JSON，说明服务器返回了错误
      const errorJson = await response.json()
      ElMessage.error(errorJson.message || '下载失败')
      return
    }

    // 获取文件名
    let filename = `${model.modelName}_${format}`

    // 获取二进制数据
    const blob = await response.blob()

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // 释放 URL 对象
    window.URL.revokeObjectURL(url)

    ElMessage.success(`开始下载 ${model.modelName} (${format})`)
  } catch (error: any) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败: ' + (error.message || '未知错误'))
  }
}

const handleDelete = (model: ModelItem): void => {
  ElMessageBox.confirm(
    `确定要删除模型 "${model.modelName}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    if (model.deployedCount > 0) {
      ElMessage.warning('模型正在使用中，无法删除')
      return
    }

    try {
      await modelApi.delete(model.modelId)
      ElMessage.success('模型删除成功')
      await loadModels()
    } catch (error: any) {
      console.error('删除模型失败:', error)
      ElMessage.error(`删除失败: ${error.message || '未知错误'}`)
    }
  }).catch(() => {
    // 用户取消删除
  })
}

// ==================== 导入操作 ====================
const handleShowImportDialog = (): void => {
  // 重置表单
  Object.assign(modelForm, {
    modelName: '',
    modelType: 'DETECTION',
    framework: 'PyTorch',
    version: '1.0.0'
  })
  fileList.value = []
  uploadProgress.value = 0
  importDialogVisible.value = true
}

const handleFileChange: UploadProps['onChange'] = (uploadFile: any): void => {
  const file = uploadFile.raw
  if (file) {
    // 验证文件大小
    const maxSize = 500 * 1024 * 1024 // 500MB
    if (file.size > maxSize) {
      ElMessage.warning('文件大小不能超过 500MB')
      fileList.value = []
      return
    }

    // 验证文件类型
    const validExtensions = ['.pt', '.pth', '.onnx', '.engine']
    const hasValidExtension = validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
    if (!hasValidExtension) {
      ElMessage.warning('不支持的文件格式，请上传 PyTorch (.pt/.pth) 或 ONNX (.onnx) 格式的模型文件')
      fileList.value = []
      return
    }

    // 验证通过，添加到文件列表
    fileList.value = [uploadFile]
  }
}

const handleFileRemove: UploadProps['onRemove'] = (): void => {
  fileList.value = []
}

const handleCancelImport = (): void => {
  if (importing.value) {
    ElMessage.warning('导入中，请稍候...')
    return
  }
  importDialogVisible.value = false
  fileList.value = []
}

const handleImport = async (): Promise<void> => {
  if (!canImport.value) {
    ElMessage.warning('请填写完整信息并选择文件')
    return
  }

  const file = fileList.value[0]?.raw
  if (!file) {
    ElMessage.warning('请选择模型文件')
    return
  }

  importing.value = true
  uploadProgress.value = 0

  try {
    // 1. 创建模型记录
    const createResponse = await modelApi.create({
      modelName: modelForm.modelName.trim(),
      modelType: modelForm.modelType,
      framework: modelForm.framework,
      version: modelForm.version.trim()
    })
    const modelId = createResponse.data.modelId

    // 2. 上传模型文件（带进度）
    await modelApi.upload(modelId, file, (percent) => {
      uploadProgress.value = percent
    })

    ElMessage.success('模型导入成功')

    // 关闭对话框并重置表单
    importDialogVisible.value = false
    fileList.value = []
    uploadProgress.value = 0

    Object.assign(modelForm, {
      modelName: '',
      modelType: 'DETECTION',
      framework: 'PyTorch',
      version: '1.0.0'
    })

    // 刷新列表
    await loadModels()
  } catch (error: any) {
    console.error('导入模型失败:', error)
    ElMessage.error(`导入模型失败: ${error.message || '未知错误'}`)
  } finally {
    importing.value = false
  }
}

// ==================== 生命周期 ====================
onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.model-list {
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

.upload-area {
  width: 100%;
}

:deep(.el-upload-dragger) {
  padding: 20px;
}

.dialog-footer {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.upload-progress {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 0 20px;
}

.progress-text {
  min-width: 50px;
  text-align: right;
  font-weight: 500;
  color: var(--el-color-primary);
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

:deep(.el-table__row:hover) {
  background-color: var(--el-fill-color-light);
}
</style>
