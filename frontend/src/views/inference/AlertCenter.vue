<template>
  <div class="alert-center">
    <!-- 过滤栏 -->
    <el-card class="filter-bar">
      <el-row :gutter="16">
        <el-col :span="8">
          <el-checkbox-group v-model="selectedLevels">
            <el-checkbox label="critical">严重</el-checkbox>
            <el-checkbox label="warning">警告</el-checkbox>
            <el-checkbox label="info">信息</el-checkbox>
          </el-checkbox-group>
        </el-col>
        <el-col :span="10">
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
          <el-button type="primary" @click="loadAlerts">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
        </el-col>
        <el-col :span="3" style="text-align: right">
          <el-button @click="loadAlerts">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-col>
        <el-col :span="3" style="text-align: right">
          <el-button type="danger" plain @click="handleClearAll">
            <el-icon><Delete /></el-icon>
            清空数据
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 告警统计 -->
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card class="stat-card critical">
          <div class="stat-value">{{ stats.critical || 0 }}</div>
          <div class="stat-label">严重告警</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card warning">
          <div class="stat-value">{{ stats.warning || 0 }}</div>
          <div class="stat-label">警告告警</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card info">
          <div class="stat-value">{{ stats.info || 0 }}</div>
          <div class="stat-label">信息告警</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警趋势图 -->
    <el-card>
      <template #header><span>告警趋势（24小时）</span></template>
      <div ref="trendChartRef" style="height: 280px"></div>
    </el-card>

    <!-- 告警列表 -->
    <el-card class="table-card">
      <el-table :data="alerts" v-loading="loading" style="width: 100%" @row-click="showDetail">
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
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column prop="device_id" label="设备ID" width="160" />
        <el-table-column prop="alert_level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="alertTagType(row.alert_level)" size="small" effect="dark">
              {{ alertLevelMap[row.alert_level] || row.alert_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_message" label="告警信息" min-width="250" />
        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            <el-tag :type="row.source === 'cloud' ? 'success' : 'primary'" size="small">
              {{ row.source === 'cloud' ? '云端' : '边缘' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model_name" label="模型" width="140" />
      </el-table>

      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end"
        @size-change="loadAlerts"
        @current-change="loadAlerts"
      />
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="告警详情" width="700px">
      <div v-if="currentDetail">
        <div v-if="currentDetail.image_url" style="margin-bottom: 16px; text-align: center">
          <el-image :src="currentDetail.image_url" :preview-src-list="[currentDetail.image_url]" fit="contain" style="max-height: 360px" preview-teleported />
        </div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="时间">{{ formatTime(currentDetail.time) }}</el-descriptions-item>
          <el-descriptions-item label="设备ID">{{ currentDetail.device_id }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="currentDetail.source === 'cloud' ? 'success' : 'primary'" size="small">
              {{ currentDetail.source === 'cloud' ? '云端' : '边缘' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="级别">
            <el-tag :type="alertTagType(currentDetail.alert_level)" size="small" effect="dark">
              {{ alertLevelMap[currentDetail.alert_level] || currentDetail.alert_level }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentDetail.alert_message" label="告警信息" :span="2">
            {{ currentDetail.alert_message }}
          </el-descriptions-item>
          <el-descriptions-item label="模型">{{ currentDetail.model_name }}</el-descriptions-item>
          <el-descriptions-item label="推理耗时">{{ currentDetail.inference_time_ms?.toFixed(1) || '-' }} ms</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { inferenceResultApi } from '../../api'
import { Search, Refresh, Delete } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const loading = ref(false)
const alerts = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const selectedLevels = ref<string[]>(['critical', 'warning', 'info'])
const timeRange = ref<string[]>([])
const stats = ref<Record<string, number>>({})
const trendChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null
const detailVisible = ref(false)
const currentDetail = ref<any>(null)

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

function showDetail(row: any) {
  currentDetail.value = row
  detailVisible.value = true
}

async function loadAlerts() {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value
    }
    if (selectedLevels.value.length > 0) {
      params.levels = selectedLevels.value
    }
    const res = await inferenceResultApi.getAlerts(params) as any
    alerts.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    console.error('加载告警失败', e)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const res = await inferenceResultApi.getStats() as any
    const levelData = res.data?.alertsByLevel || {}
    stats.value = levelData
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

async function loadTrend() {
  try {
    if (typeof inferenceResultApi.getTrend !== 'function') return
    const res = await inferenceResultApi.getTrend() as any
    const hourly = res.data?.hourly || []
    await nextTick()
    if (!trendChartRef.value) return
    if (!trendChart) trendChart = echarts.init(trendChartRef.value)
    const hours = hourly.map((d: any) => d.hour?.slice(-5) || '')
    const counts = hourly.map((d: any) => d.alertCount || 0)
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: hours },
      yAxis: { type: 'value', name: '告警数' },
      series: [{
        name: '告警数', type: 'bar', data: counts,
        itemStyle: { color: '#e6a23c' }
      }]
    })
  } catch (e) {
    console.error('加载趋势失败', e)
  }
}

async function handleClearAll() {
  try {
    await ElMessageBox.confirm('确定要清空所有推理结果和告警数据？此操作不可恢复。', '清空确认', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const res = await inferenceResultApi.clearAll() as any
    ElMessage.success(`已清空 ${res.data?.deleted ?? 0} 条记录`)
    loadAlerts()
    loadStats()
    loadTrend()
  } catch {
    // 用户取消
  }
}

onMounted(() => {
  loadAlerts()
  loadStats()
  loadTrend()
})

onUnmounted(() => {
  if (trendChart) {
    trendChart.dispose()
    trendChart = null
  }
})
</script>

<style scoped>
.alert-center {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.stat-card {
  text-align: center;
  padding: 10px 0;
}
.stat-card .stat-value {
  font-size: 32px;
  font-weight: 700;
}
.stat-card .stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
.stat-card.critical .stat-value { color: #f56c6c; }
.stat-card.warning .stat-value { color: #e6a23c; }
.stat-card.info .stat-value { color: #909399; }
</style>
