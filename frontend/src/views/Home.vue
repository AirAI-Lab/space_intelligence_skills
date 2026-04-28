<template>
  <div class="home">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="4" v-for="stat in statistics" :key="stat.key" style="margin-bottom:8px">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: stat.color }">
              <el-icon :size="30" :color="stat.iconColor">
                <component :is="stat.icon" />
              </el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 设备状态图表 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>设备状态分布</span>
          </template>
          <div ref="deviceStatusChart" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- 训练任务进度 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近训练任务</span>
          </template>
          <el-table :data="recentTrainings" style="width: 100%">
            <el-table-column prop="jobName" label="任务名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :status="getProgressStatus(row.status)" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 推理趋势 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>推理趋势（24小时）</span>
          </template>
          <div ref="inferenceTrendChart" style="height: 300px;"></div>
        </el-card>
      </el-col>

      <!-- 最近告警 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>最近告警</span>
              <el-button size="small" text @click="router.push('/alerts')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentAlerts" style="width: 100%" max-height="300">
            <el-table-column prop="time" label="时间" width="160">
              <template #default="{ row }">
                {{ row.time?.replace('T', ' ').substring(0, 19) || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="alert_level" label="级别" width="80">
              <template #default="{ row }">
                <el-tag :type="row.alert_level === 'critical' ? 'danger' : row.alert_level === 'warning' ? 'warning' : 'info'" size="small" effect="dark">
                  {{ { critical: '严重', warning: '警告', info: '信息' }[row.alert_level as string] || row.alert_level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="device_id" label="设备" width="130" />
            <el-table-column prop="alert_message" label="告警信息" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 在线设备列表 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>在线设备</span>
          </template>
          <el-table :data="onlineDevices" style="width: 100%">
            <el-table-column prop="deviceId" label="设备ID" width="150" />
            <el-table-column prop="deviceName" label="设备名称" />
            <el-table-column prop="cpuUsage" label="CPU使用率" width="120">
              <template #default="{ row }">
                {{ row.cpuUsage }}%
              </template>
            </el-table-column>
            <el-table-column prop="gpuUsage" label="GPU使用率" width="120">
              <template #default="{ row }">
                {{ row.gpuUsage }}%
              </template>
            </el-table-column>
            <el-table-column prop="memoryUsage" label="内存使用" width="120">
              <template #default="{ row }">
                {{ row.memoryUsage }}GB
              </template>
            </el-table-column>
            <el-table-column prop="lastHeartbeat" label="最后心跳" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="viewDevice(row.deviceId)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Monitor, DataLine, Box, FolderOpened, Bell } from '@element-plus/icons-vue'
import { deviceApi, dataApi, modelApi, trainingApi, inferenceResultApi } from '@/api'

const router = useRouter()

// 统计数据
const statistics = ref([
  {
    key: 'devices',
    label: '在线设备',
    value: 0,
    icon: Monitor,
    color: '#ecf5ff',
    iconColor: '#409eff'
  },
  {
    key: 'datasets',
    label: '数据集',
    value: 0,
    icon: FolderOpened,
    color: '#f0f9ff',
    iconColor: '#67c23a'
  },
  {
    key: 'models',
    label: '模型版本',
    value: 0,
    icon: Box,
    color: '#fef0f0',
    iconColor: '#f56c6c'
  },
  {
    key: 'trainings',
    label: '训练任务',
    value: 0,
    icon: DataLine,
    color: '#fdf6ec',
    iconColor: '#e6a23c'
  },
  {
    key: 'alerts',
    label: '今日告警',
    value: 0,
    icon: Bell,
    color: '#fef0f0',
    iconColor: '#f56c6c'
  }
])

// 在线设备
const onlineDevices = ref<any[]>([])

// 最近训练任务
const recentTrainings = ref<any[]>([])

const deviceStatusChart = ref<HTMLElement>()
const inferenceTrendChart = ref<HTMLElement>()
const recentAlerts = ref<any[]>([])

// 设备状态统计

// 设备状态统计
const deviceStatusStats = ref({
  ONLINE: 0,
  OFFLINE: 0,
  UPGRADING: 0,
  ERROR: 0
})

// 加载统计数据
const loadStatistics = async () => {
  try {
    // 并行加载所有统计数据
    const [devicesRes, datasetsRes, modelsRes, trainingsRes] = await Promise.all([
      deviceApi.getList({ page: 1, pageSize: 1 }), // 只需要总数
      dataApi.getList({ page: 1, pageSize: 1 }),
      modelApi.getList({ page: 1, pageSize: 1 }),
      trainingApi.getList({ page: 1, pageSize: 5 }) // 获取最近5个训练任务
    ])

    // 更新统计数据
    statistics.value[0].value = devicesRes.data.total || 0
    statistics.value[1].value = datasetsRes.data.total || 0
    statistics.value[2].value = modelsRes.data.total || 0
    statistics.value[3].value = trainingsRes.data.total || 0

    // 加载告警统计
    try {
      const inferStatsRes = await inferenceResultApi.getStats() as any
      statistics.value[4].value = inferStatsRes.data?.totalAlerts || 0
    } catch {
      statistics.value[4].value = 0
    }

    // 加载最近告警
    try {
      const alertsRes = await inferenceResultApi.getAlerts({ page: 1, page_size: 10 }) as any
      recentAlerts.value = alertsRes.data?.items || []
    } catch {
      recentAlerts.value = []
    }

    // 更新训练任务列表
    recentTrainings.value = (trainingsRes.data.items || []).map((item: any) => ({
      jobId: item.jobId,
      jobName: item.jobName,
      status: item.status.toLowerCase(),
      progress: item.progress || 0
    }))

    // 获取设备状态统计
    const statsRes = await fetch('/api/v1/devices/stats').then(res => res.json())
    if (statsRes.code === 200 && statsRes.data.statusCounts) {
      deviceStatusStats.value = statsRes.data.statusCounts

      // 更新在线设备数量（使用ONLINE状态的数量）
      statistics.value[0].value = statsRes.data.statusCounts.ONLINE || 0
    }

  } catch (error: any) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载在线设备列表
const loadOnlineDevices = async () => {
  try {
    const response = await deviceApi.getList({
      page: 1,
      pageSize: 10,
      status: 'ONLINE'
    })

    onlineDevices.value = (response.data.items || []).map((item: any) => ({
      deviceId: item.deviceId,
      deviceName: item.deviceName,
      cpuUsage: item.cpuUsage || 0,
      gpuUsage: item.gpuUsage || 0,
      memoryUsage: (item.memoryUsage || 0).toFixed(1),
      lastHeartbeat: item.lastHeartbeat || '-'
    }))
  } catch (error: any) {
    console.error('加载在线设备失败:', error)
    onlineDevices.value = []
  }
}

// 获取状态类型
const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    running: 'primary',
    completed: 'success',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取进度状态
const getProgressStatus = (status: string) => {
  const statuses: Record<string, any> = {
    completed: 'success',
    failed: 'exception'
  }
  return statuses[status] || undefined
}

// 查看设备详情
const viewDevice = (deviceId: string) => {
  router.push(`/device/${deviceId}`)
}

// 初始化图表
const initChart = () => {
  if (!deviceStatusChart.value) return

  const chart = echarts.init(deviceStatusChart.value)

  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      top: '5%',
      left: 'center'
    },
    series: [
      {
        name: '设备状态',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: false,
          position: 'center'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 20,
            fontWeight: 'bold'
          }
        },
        labelLine: {
          show: false
        },
        data: [
          { value: deviceStatusStats.value.ONLINE, name: '在线', itemStyle: { color: '#67c23a' } },
          { value: deviceStatusStats.value.OFFLINE, name: '离线', itemStyle: { color: '#909399' } },
          { value: deviceStatusStats.value.UPGRADING, name: '升级中', itemStyle: { color: '#e6a23c' } },
          { value: deviceStatusStats.value.ERROR, name: '故障', itemStyle: { color: '#f56c6c' } }
        ]
      }
    ]
  }
  chart.setOption(option)

  // 响应式
  window.addEventListener('resize', () => {
    chart.resize()
  })
}

// 初始化推理趋势图
const initInferenceTrendChart = async () => {
  if (!inferenceTrendChart.value) return

  const chart = echarts.init(inferenceTrendChart.value)
  try {
    const res = await inferenceResultApi.getTrend() as any
    const hourly = res.data?.hourly || []
    const hours = hourly.map((d: any) => d.hour?.slice(-5) || '')
    const counts = hourly.map((d: any) => d.count || 0)
    const alertCounts = hourly.map((d: any) => d.alertCount || 0)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['推理总数', '告警数'] },
      grid: { left: 40, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: hours },
      yAxis: { type: 'value' },
      series: [
        { name: '推理总数', type: 'line', smooth: true, data: counts, itemStyle: { color: '#409eff' } },
        { name: '告警数', type: 'bar', data: alertCounts, itemStyle: { color: '#e6a23c' } }
      ]
    })
  } catch {
    chart.setOption({
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { color: '#909399', fontSize: 14 } }
    })
  }
  window.addEventListener('resize', () => chart.resize())
}

// 刷新所有数据
const refreshData = async () => {
  await loadStatistics()
  await loadOnlineDevices()
  // 更新图表
  if (deviceStatusChart.value) {
    initChart()
  }
  initInferenceTrendChart()
}

onMounted(() => {
  refreshData()
  // 每分钟刷新一次数据
  setInterval(refreshData, 60000)
})
</script>

<style scoped>
.home {
  padding: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>
