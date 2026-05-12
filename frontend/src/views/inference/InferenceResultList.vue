<template>
  <div class="inference-result-list">
    <!-- 过滤栏 -->
    <el-card class="filter-bar">
      <el-row :gutter="16" align="middle">
        <el-col :span="4">
          <el-input v-model="filters.device_id" placeholder="设备ID" clearable />
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.source" placeholder="来源" clearable>
            <el-option label="全部" value="" />
            <el-option label="边缘端" value="edge" />
            <el-option label="云端" value="cloud" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="filters.alert_level" placeholder="告警级别" clearable>
            <el-option label="全部" value="" />
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="-"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-col>
        <el-col :span="3">
          <el-button type="primary" @click="loadResults">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </el-col>
        <el-col :span="3">
          <el-button type="danger" plain @click="handleClearAll">
            <el-icon><Delete /></el-icon>
            清空数据
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 结果列表 -->
    <el-card class="table-card">
      <el-table :data="results" v-loading="loading" style="width: 100%" @row-click="showDetail">
        <el-table-column label="图片" width="90">
          <template #default="{ row }">
            <el-image
              v-if="row.image_url"
              :src="row.image_url"
              :preview-src-list="[row.image_url]"
              fit="cover"
              style="width: 60px; height: 40px; border-radius: 4px"
              preview-teleported
              @click.stop
            />
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备ID" width="160" />
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source === 'cloud' ? 'success' : 'primary'" size="small">
              {{ row.source === 'cloud' ? '云端' : '边缘' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" width="140" />
        <el-table-column prop="task_type" label="任务类型" width="100">
          <template #default="{ row }">
            {{ taskTypeMap[row.task_type] || row.task_type }}
          </template>
        </el-table-column>
        <el-table-column prop="detection_count" label="检出数" width="90" />
        <el-table-column prop="alert_level" label="告警" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.alert_level" :type="alertTagType(row.alert_level)" size="small">
              {{ alertLevelMap[row.alert_level] || row.alert_level }}
            </el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="inference_time_ms" label="耗时(ms)" width="100">
          <template #default="{ row }">
            {{ row.inference_time_ms ? row.inference_time_ms.toFixed(1) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="summary_text" label="摘要" min-width="180" />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @size-change="loadResults"
        @current-change="loadResults"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="推理结果详情" width="760px">
      <div v-if="currentDetail">
        <div v-if="currentDetail.image_url" style="margin-bottom: 16px; text-align: center">
          <el-image
            :src="currentDetail.image_url"
            :preview-src-list="[currentDetail.image_url]"
            fit="contain"
            style="max-height: 360px"
            preview-teleported
          />
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间">{{ formatTime(currentDetail.time) }}</el-descriptions-item>
          <el-descriptions-item label="设备ID">{{ currentDetail.device_id }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="currentDetail.source === 'cloud' ? 'success' : 'primary'" size="small">
              {{ currentDetail.source === 'cloud' ? '云端' : '边缘' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模型">{{ currentDetail.model_name }}</el-descriptions-item>
          <el-descriptions-item label="任务类型">{{ taskTypeMap[currentDetail.task_type] || currentDetail.task_type }}</el-descriptions-item>
          <el-descriptions-item label="推理耗时">{{ currentDetail.inference_time_ms?.toFixed(1) || '-' }} ms</el-descriptions-item>
          <el-descriptions-item label="检出数">{{ currentDetail.detection_count }}</el-descriptions-item>
          <el-descriptions-item label="告警级别">
            <el-tag v-if="currentDetail.alert_level" :type="alertTagType(currentDetail.alert_level)" size="small">
              {{ alertLevelMap[currentDetail.alert_level] || currentDetail.alert_level }}
            </el-tag>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentDetail.alert_message" label="告警信息" :span="2">
            {{ currentDetail.alert_message }}
          </el-descriptions-item>
        </el-descriptions>
        <h4 style="margin-top: 16px">完整结果</h4>
        <el-input
          type="textarea"
          :model-value="JSON.stringify(currentDetail.result_json, null, 2)"
          :rows="12"
          readonly
          style="font-family: monospace"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { inferenceResultApi } from '../../api'
import { Search, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const loading = ref(false)
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const currentDetail = ref<any>(null)

const filters = ref({
  device_id: '',
  source: '',
  alert_level: ''
})
const timeRange = ref<string[]>([])

const taskTypeMap: Record<string, string> = {
  detect: '检测',
  segment: '分割',
  classify: '分类'
}
const alertLevelMap: Record<string, string> = {
  critical: '严重',
  warning: '警告',
  info: '信息'
}

function alertTagType(level: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || 'info'
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').substring(0, 19)
}

async function loadResults() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value
    }
    if (filters.value.device_id) params.device_id = filters.value.device_id
    if (filters.value.source) params.source = filters.value.source
    if (filters.value.alert_level) params.alert_level = filters.value.alert_level
    params.has_alert = true
    if (timeRange.value?.length === 2) {
      params.start_time = timeRange.value[0]
      params.end_time = timeRange.value[1]
    }
    const res = await inferenceResultApi.getList(params) as any
    results.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    console.error('加载推理结果失败', e)
  } finally {
    loading.value = false
  }
}

function showDetail(row: any) {
  currentDetail.value = row
  detailVisible.value = true
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有推理结果数据？此操作不可恢复。', '清空确认', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await inferenceResultApi.clearAll() as any
    ElMessage.success(`已清空 ${res.data?.deleted ?? 0} 条记录`)
    loadResults()
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadResults()
})
</script>

<style scoped>
.inference-result-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.text-muted {
  color: #909399;
}
</style>
