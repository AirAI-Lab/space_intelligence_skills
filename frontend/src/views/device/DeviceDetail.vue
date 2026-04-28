<template>
  <div class="device-detail">
    <el-page-header @back="goBack" :content="'设备: ' + deviceId" />

    <el-tabs v-model="activeTab" style="margin-top: 20px">
      <el-tab-pane label="设备信息" name="info">
        <el-card v-loading="loading">
          <el-descriptions v-if="device" :column="2" border>
            <el-descriptions-item label="设备ID">{{ device.deviceId }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">{{ device.deviceName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="设备类型">{{ device.deviceType || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="device.status === 'ONLINE' ? 'success' : 'info'" size="small">
                {{ device.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="CPU">{{ device.cpuUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="GPU">{{ device.gpuUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="内存">{{ device.memoryUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="当前模型">{{ device.currentModelId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最后心跳">{{ device.lastHeartbeat || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="推理结果" name="inference">
        <el-table :data="results" v-loading="inferLoading" style="width: 100%">
          <el-table-column prop="time" label="时间" width="180">
            <template #default="{ row }">
              {{ row.time?.replace('T', ' ').substring(0, 19) }}
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="100">
            <template #default="{ row }">
              <el-tag :type="row.source === 'cloud' ? 'success' : 'primary'" size="small">
                {{ row.source === 'cloud' ? '云端' : '边缘' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="model_name" label="模型" width="140" />
          <el-table-column prop="detection_count" label="检出数" width="90" />
          <el-table-column prop="alert_level" label="告警" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.alert_level" :type="alertTagType(row.alert_level)" size="small">
                {{ alertLevelMap[row.alert_level] || row.alert_level }}
              </el-tag>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="inference_time_ms" label="耗时(ms)" width="100">
            <template #default="{ row }">
              {{ row.inference_time_ms?.toFixed(1) || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="summary_text" label="摘要" min-width="200" />
        </el-table>
        <el-pagination
          v-model:current-page="inferPage"
          v-model:page-size="inferPageSize"
          :total="inferTotal"
          layout="total, prev, pager, next"
          style="margin-top: 16px; justify-content: flex-end"
          @current-change="loadInferenceResults"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { deviceApi, inferenceResultApi } from '@/api'

const route = useRoute()
const router = useRouter()
const deviceId = computed(() => route.params.id as string)
const activeTab = ref('info')
const loading = ref(false)
const device = ref<any>(null)

const inferLoading = ref(false)
const results = ref<any[]>([])
const inferPage = ref(1)
const inferPageSize = ref(10)
const inferTotal = ref(0)

const alertLevelMap: Record<string, string> = { critical: '严重', warning: '警告', info: '信息' }

function alertTagType(level: string) {
  return { critical: 'danger', warning: 'warning', info: 'info' }[level] || 'info'
}

const goBack = () => router.back()

async function loadDevice() {
  loading.value = true
  try {
    const res = await deviceApi.getStatus(deviceId.value) as any
    device.value = res.data
  } catch (e) {
    console.error('加载设备失败', e)
  } finally {
    loading.value = false
  }
}

async function loadInferenceResults() {
  inferLoading.value = true
  try {
    const res = await inferenceResultApi.getList({
      page: inferPage.value,
      page_size: inferPageSize.value,
      device_id: deviceId.value
    }) as any
    results.value = res.data?.items || []
    inferTotal.value = res.data?.total || 0
  } catch (e) {
    console.error('加载推理结果失败', e)
  } finally {
    inferLoading.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'inference') loadInferenceResults()
})

onMounted(() => {
  loadDevice()
})
</script>

<style scoped>
.device-detail {
  padding: 20px;
}
</style>
