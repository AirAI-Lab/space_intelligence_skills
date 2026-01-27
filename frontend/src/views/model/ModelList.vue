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
              style="width: 250px;"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select v-model="statusFilter" placeholder="模型状态" clearable style="width: 150px;">
              <el-option label="全部" value="" />
              <el-option label="已发布" value="published" />
              <el-option label="草稿" value="draft" />
              <el-option label="已归档" value="archived" />
            </el-select>
            <el-button type="primary" @click="loadModels">
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
          <el-button type="primary" @click="showImportDialog">
            <el-icon><Upload /></el-icon>
            导入模型
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 模型列表 -->
    <el-card class="table-card">
      <el-table :data="models" v-loading="loading" style="width: 100%">
        <el-table-column prop="model_name" label="模型名称" width="200" />
        <el-table-column prop="model_type" label="模型类型" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.model_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="framework" label="框架" width="100" />
        <el-table-column prop="version" label="版本" width="100" />
        <el-table-column prop="map" label="mAP" width="100">
          <template #default="{ row }">
            <span v-if="row.map">{{ (row.map * 100).toFixed(1) }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deployed_count" label="部署设备" width="100" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewDetail(row)">
              详情
            </el-button>
            <el-button size="small" type="primary" @click="deployModel(row)">
              部署
            </el-button>
            <el-button size="small" @click="downloadModel(row)">
              下载
            </el-button>
            <el-button size="small" type="danger" @click="deleteModel(row)">
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
    <el-dialog v-model="importDialogVisible" title="导入模型" width="600px">
      <el-form :model="modelForm" label-width="100px">
        <el-form-item label="模型名称">
          <el-input v-model="modelForm.model_name" placeholder="例如：安全帽检测模型v2" />
        </el-form-item>
        <el-form-item label="模型类型">
          <el-select v-model="modelForm.model_type" style="width: 100%;">
            <el-option label="YOLOv8" value="YOLOv8" />
            <el-option label="YOLOv5" value="YOLOv5" />
            <el-option label="ResNet" value="ResNet" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型文件">
          <el-upload
            class="upload-area"
            drag
            action="/api/v1/models/upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 .pt / .onnx 格式，文件大小不超过 500MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="importModel">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, RefreshLeft, Upload, UploadFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const searchText = ref('')
const statusFilter = ref('')
const models = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const importDialogVisible = ref(false)
const modelForm = ref({
  model_name: '',
  model_type: 'YOLOv8'
})

// 模拟数据
const mockModels = [
  {
    model_id: 'M001',
    model_name: '安全帽检测v2',
    model_type: 'YOLOv8',
    framework: 'PyTorch',
    version: '2.1.0',
    map: 0.892,
    file_size: 6240000,
    status: 'published',
    deployed_count: 12,
    updated_at: '2026-01-26 16:00:00'
  },
  {
    model_id: 'M002',
    model_name: '车辆检测模型',
    model_type: 'YOLOv8',
    framework: 'PyTorch',
    version: '1.5.0',
    map: 0.856,
    file_size: 12400000,
    status: 'published',
    deployed_count: 8,
    updated_at: '2026-01-25 14:30:00'
  },
  {
    model_id: 'M003',
    model_name: '人员识别模型',
    model_type: 'YOLOv8',
    framework: 'ONNX',
    version: '1.0.0',
    map: 0.785,
    file_size: 15600000,
    status: 'draft',
    deployed_count: 0,
    updated_at: '2026-01-27 10:00:00'
  }
]

// 加载模型列表
const loadModels = async () => {
  loading.value = true
  setTimeout(() => {
    models.value = mockModels
    total.value = mockModels.length
    loading.value = false
  }, 500)
}

// 重置筛选
const resetFilter = () => {
  searchText.value = ''
  statusFilter.value = ''
  currentPage.value = 1
  loadModels()
}

// 格式化文件大小
const formatSize = (bytes: number) => {
  if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(2) + ' KB'
  }
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    published: 'success',
    draft: 'info',
    archived: 'info'
  }
  return types[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    published: '已发布',
    draft: '草稿',
    archived: '已归档'
  }
  return texts[status] || status
}

// 查看详情
const viewDetail = (model: any) => {
  ElMessage.info(`查看模型详情: ${model.model_name}`)
}

// 部署模型
const deployModel = (model: any) => {
  router.push('/device')
  ElMessage.success(`准备部署模型: ${model.model_name}`)
}

// 下载模型
const downloadModel = (model: any) => {
  ElMessage.success(`开始下载: ${model.model_name}`)
}

// 删除模型
const deleteModel = (model: any) => {
  ElMessageBox.confirm(
    `确定要删除模型 "${model.model_name}" 吗？`,
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    ElMessage.success('模型删除成功')
    loadModels()
  })
}

// 显示导入对话框
const showImportDialog = () => {
  modelForm.value = {
    model_name: '',
    model_type: 'YOLOv8'
  }
  importDialogVisible.value = true
}

// 导入模型
const importModel = () => {
  if (!modelForm.value.model_name) {
    ElMessage.warning('请填写模型名称')
    return
  }
  ElMessage.success('模型导入成功')
  importDialogVisible.value = false
  loadModels()
}

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
  min-height: calc(100vh - 300px);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.upload-area {
  width: 100%;
}
</style>
