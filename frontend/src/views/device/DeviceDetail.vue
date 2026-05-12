<template>
  <div class="device-detail">
    <el-page-header @back="goBack" :content="'设备: ' + deviceId" />

    <el-tabs v-model="activeTab" style="margin-top: 16px">
      <!-- Tab 1: 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <el-card v-loading="loading">
          <el-descriptions v-if="device" :column="2" border>
            <el-descriptions-item label="设备ID">{{ device.deviceId }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">{{ device.deviceName || '-' }}</el-descriptions-item>
            <el-descriptions-item label="设备类型">
              <el-tag size="small">{{ formatType(device.deviceType) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="设备类别">
              <el-tag v-if="device.deviceCategory" size="small" type="warning">
                {{ categoryLabel(device.deviceCategory) }}
              </el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(device.status)" size="small">
                {{ statusText(device.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="通信协议">
              {{ device.protocol || 'MQTT_REST' }}
            </el-descriptions-item>
            <el-descriptions-item label="能力">
              <el-tag
                v-for="cap in parseCapabilities(device.capabilities)"
                :key="cap"
                size="small"
                type="info"
                style="margin: 1px"
              >
                {{ capLabel(cap) }}
              </el-tag>
              <span v-if="!device.capabilities">-</span>
            </el-descriptions-item>
            <el-descriptions-item label="当前模型">{{ device.currentModelId || '-' }}</el-descriptions-item>
            <el-descriptions-item label="CPU">{{ device.cpuUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="GPU">{{ device.gpuUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="内存">{{ device.memoryUsage || 0 }}%</el-descriptions-item>
            <el-descriptions-item label="GPU型号">{{ device.gpuModel || '-' }}</el-descriptions-item>
            <el-descriptions-item label="最后心跳">{{ device.lastHeartbeat || '-' }}</el-descriptions-item>
            <el-descriptions-item label="IP">{{ device.ip || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- Tab 2: 标签管理 -->
      <el-tab-pane label="标签管理" name="tags">
        <el-card>
          <div style="margin-bottom: 12px; display: flex; justify-content: space-between">
            <span style="font-weight: 500">设备标签</span>
            <el-button type="primary" size="small" @click="showAddTagDialog">添加标签</el-button>
          </div>
          <el-table :data="tags" v-loading="tagsLoading" stripe>
            <el-table-column prop="tagKey" label="Key" width="200" />
            <el-table-column prop="tagValue" label="Value" min-width="300" />
            <el-table-column prop="createdAt" label="创建时间" width="180">
              <template #default="{ row }">
                {{ row.createdAt?.replace('T', ' ').substring(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" align="center">
              <template #default="{ row }">
                <el-button size="small" type="danger" link @click="handleDeleteTag(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="addTagVisible" title="添加标签" width="400px" :close-on-click-modal="false">
          <el-form :model="tagForm" label-width="60px">
            <el-form-item label="Key" required>
              <el-input v-model="tagForm.key" placeholder="location" />
            </el-form-item>
            <el-form-item label="Value">
              <el-input v-model="tagForm.value" placeholder="工地A区" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="addTagVisible = false">取消</el-button>
            <el-button type="primary" @click="handleAddTag">确定</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <!-- Tab 3: 命令历史 -->
      <el-tab-pane label="命令历史" name="commands">
        <el-card>
          <el-table :data="commands" v-loading="commandsLoading" stripe>
            <el-table-column prop="commandType" label="命令类型" width="150" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="cmdStatusType(row.status)" size="small">
                  {{ cmdStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="commandId" label="命令ID" width="200" show-overflow-tooltip />
            <el-table-column prop="createdAt" label="创建时间" width="180">
              <template #default="{ row }">
                {{ row.createdAt?.replace('T', ' ').substring(0, 19) }}
              </template>
            </el-table-column>
            <el-table-column prop="acknowledgedAt" label="确认时间" width="180">
              <template #default="{ row }">
                {{ row.acknowledgedAt?.replace('T', ' ').substring(0, 19) || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button size="small" link @click="showCommandDetail(row)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="cmdDetailVisible" title="命令详情" width="500px">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="命令ID">{{ cmdDetail.commandId }}</el-descriptions-item>
            <el-descriptions-item label="命令类型">{{ cmdDetail.commandType }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ cmdDetail.status }}</el-descriptions-item>
            <el-descriptions-item label="关联任务">{{ cmdDetail.taskId || '-' }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="cmdDetail.params" style="margin-top: 12px">
            <div style="font-weight: 500; margin-bottom: 4px">参数</div>
            <el-input type="textarea" :rows="4" :model-value="formatJson(cmdDetail.params)" readonly />
          </div>
          <div v-if="cmdDetail.result" style="margin-top: 12px">
            <div style="font-weight: 500; margin-bottom: 4px">结果</div>
            <el-input type="textarea" :rows="4" :model-value="formatJson(cmdDetail.result)" readonly />
          </div>
        </el-dialog>
      </el-tab-pane>

      <!-- Tab 4: 推理结果 -->
      <el-tab-pane label="推理结果" name="inference">
        <el-table :data="results" v-loading="inferLoading" stripe>
          <el-table-column prop="time" label="时间" width="180">
            <template #default="{ row }">{{ row.time?.replace('T', ' ').substring(0, 19) }}</template>
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
          <el-table-column prop="inference_time_ms" label="耗时(ms)" width="100">
            <template #default="{ row }">{{ row.inference_time_ms?.toFixed(1) || '-' }}</template>
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
import { ref, computed, onMounted, watch, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { deviceApi, inferenceResultApi } from '@/api'

const route = useRoute()
const router = useRouter()
const deviceId = computed(() => route.params.id as string)
const activeTab = ref('info')
const loading = ref(false)
const device = ref<any>(null)

// ---- 标签管理 ----
const tags = ref<any[]>([])
const tagsLoading = ref(false)
const addTagVisible = ref(false)
const tagForm = reactive({ key: '', value: '' })

// ---- 命令历史 ----
const commands = ref<any[]>([])
const commandsLoading = ref(false)
const cmdDetailVisible = ref(false)
const cmdDetail = ref<any>({})

// ---- 推理结果 ----
const inferLoading = ref(false)
const results = ref<any[]>([])
const inferPage = ref(1)
const inferPageSize = ref(10)
const inferTotal = ref(0)

// ---- 工具函数 ----
const deviceTypeMap: Record<string, string> = {
  JETSON_ORIN: 'Jetson Orin', JETSON_XAVIER: 'Jetson Xavier', JETSON_NANO: 'Jetson Nano',
  EDGE_BOX: '边缘盒子', DRONE: '无人机', ROBOT_DOG: '机器狗',
  VEHICLE: '无人车', SENSOR: '传感器', CAMERA: '摄像头'
}
const categoryMap: Record<string, string> = {
  EDGE_COMPUTE: '边缘计算', UAV: '无人机', ROBOTIC: '机器人',
  VEHICLE: '车辆', SENSOR: '传感器', CAMERA: '摄像头'
}
const capMap: Record<string, string> = {
  VIDEO_INPUT: '视频', INFERENCE: '推理', CONTROL: '控制',
  SENSING: '传感', CLOUD_FORWARD: '转发', OTA_UPDATE: 'OTA', MULTI_CHANNEL: '多通道'
}
const cmdStatusMap: Record<string, { type: string; text: string }> = {
  PENDING: { type: 'warning', text: '待发送' },
  SENT: { type: 'primary', text: '已发送' },
  ACKNOWLEDGED: { type: 'success', text: '已确认' },
  EXPIRED: { type: 'info', text: '已过期' },
  FAILED: { type: 'danger', text: '失败' }
}

const formatType = (t: string) => deviceTypeMap[t] || t
const categoryLabel = (c: string) => categoryMap[c] || c
const parseCapabilities = (caps?: string) => caps ? caps.split(',').filter(Boolean) : []
const capLabel = (c: string) => capMap[c] || c
const statusTagType = (s: string) => ({ ONLINE: 'success', OFFLINE: 'info', UPGRADING: 'warning', ERROR: 'danger' }[s] || 'info')
const statusText = (s: string) => ({ ONLINE: '在线', OFFLINE: '离线', UPGRADING: '升级中', ERROR: '错误' }[s] || s)
const cmdStatusType = (s: string) => cmdStatusMap[s]?.type || 'info'
const cmdStatusText = (s: string) => cmdStatusMap[s]?.text || s
const formatJson = (s: string) => { try { return JSON.stringify(JSON.parse(s), null, 2) } catch { return s } }

const goBack = () => router.back()

// ---- 数据加载 ----
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

async function loadTags() {
  tagsLoading.value = true
  try {
    const res = await deviceApi.getTags(deviceId.value) as any
    tags.value = res.data || []
  } catch (e) {
    console.error('加载标签失败', e)
  } finally {
    tagsLoading.value = false
  }
}

async function loadCommands() {
  commandsLoading.value = true
  try {
    const res = await deviceApi.getCommands(deviceId.value) as any
    commands.value = res.data || []
  } catch (e) {
    console.error('加载命令失败', e)
  } finally {
    commandsLoading.value = false
  }
}

async function loadInferenceResults() {
  inferLoading.value = true
  try {
    const res = await inferenceResultApi.getList({
      page: inferPage.value, page_size: inferPageSize.value, device_id: deviceId.value
    }) as any
    results.value = res.data?.items || []
    inferTotal.value = res.data?.total || 0
  } catch (e) {
    console.error('加载推理结果失败', e)
  } finally {
    inferLoading.value = false
  }
}

// ---- 标签操作 ----
const showAddTagDialog = () => {
  tagForm.key = ''
  tagForm.value = ''
  addTagVisible.value = true
}

const handleAddTag = async () => {
  if (!tagForm.key.trim()) { ElMessage.warning('请输入 Key'); return }
  try {
    await deviceApi.addTag(deviceId.value, { key: tagForm.key.trim(), value: tagForm.value.trim() })
    ElMessage.success('标签添加成功')
    addTagVisible.value = false
    await loadTags()
  } catch (error: any) {
    ElMessage.error(`添加失败: ${error.message}`)
  }
}

const handleDeleteTag = (row: any) => {
  ElMessageBox.confirm(`确定删除标签 "${row.tagKey}"？`, '确认', {
    confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    await deviceApi.deleteTag(deviceId.value, row.tagKey)
    ElMessage.success('删除成功')
    await loadTags()
  }).catch(() => {})
}

const showCommandDetail = (row: any) => {
  cmdDetail.value = row
  cmdDetailVisible.value = true
}

// ---- Tab 切换加载 ----
watch(activeTab, (tab) => {
  if (tab === 'tags' && tags.value.length === 0) loadTags()
  else if (tab === 'commands' && commands.value.length === 0) loadCommands()
  else if (tab === 'inference') loadInferenceResults()
})

onMounted(loadDevice)
</script>

<style scoped>
.device-detail {
  padding: 0;
}
</style>
