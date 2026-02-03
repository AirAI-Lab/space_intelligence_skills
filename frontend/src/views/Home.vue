<template>
  <div class="home">
    <el-row :gutter="20">
      <!-- 统计卡片 -->
      <el-col :span="6" v-for="stat in statistics" :key="stat.key">
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
import { Monitor, DataLine, Box, FolderOpened } from '@element-plus/icons-vue'

const router = useRouter()

// 统计数据
const statistics = ref([
  {
    key: 'devices',
    label: '在线设备',
    value: 42,
    icon: Monitor,
    color: '#ecf5ff',
    iconColor: '#409eff'
  },
  {
    key: 'datasets',
    label: '数据集',
    value: 18,
    icon: FolderOpened,
    color: '#f0f9ff',
    iconColor: '#67c23a'
  },
  {
    key: 'models',
    label: '模型版本',
    value: 35,
    icon: Box,
    color: '#fef0f0',
    iconColor: '#f56c6c'
  },
  {
    key: 'trainings',
    label: '训练任务',
    value: 7,
    icon: DataLine,
    color: '#fdf6ec',
    iconColor: '#e6a23c'
  }
])

// 在线设备
const onlineDevices = ref([
  {
    deviceId: 'EDGE_001',
    deviceName: '机载设备1号',
    cpuUsage: 45.5,
    gpuUsage: 60.2,
    memoryUsage: 12.5,
    lastHeartbeat: '2025-01-26 10:00:00'
  },
  {
    deviceId: 'EDGE_002',
    deviceName: '机载设备2号',
    cpuUsage: 38.2,
    gpuUsage: 55.8,
    memoryUsage: 10.2,
    lastHeartbeat: '2025-01-26 10:00:05'
  }
])

// 最近训练任务
const recentTrainings = ref([
  {
    jobId: 'JOB001',
    jobName: '安全帽检测v2',
    status: 'running',
    progress: 65
  },
  {
    jobId: 'JOB002',
    jobName: '车辆检测训练',
    status: 'completed',
    progress: 100
  },
  {
    jobId: 'JOB003',
    jobName: '人员识别微调',
    status: 'pending',
    progress: 0
  }
])

const deviceStatusChart = ref<HTMLElement>()

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
          { value: 35, name: '在线', itemStyle: { color: '#67c23a' } },
          { value: 5, name: '离线', itemStyle: { color: '#909399' } },
          { value: 2, name: '故障', itemStyle: { color: '#f56c6c' } }
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

onMounted(() => {
  initChart()
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
