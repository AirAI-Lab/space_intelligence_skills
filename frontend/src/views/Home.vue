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
            <el-table-column prop="job_name" label="任务名称" />
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
            <el-table-column prop="device_id" label="设备ID" width="150" />
            <el-table-column prop="device_name" label="设备名称" />
            <el-table-column prop="cpu_usage" label="CPU使用率" width="120">
              <template #default="{ row }">
                {{ row.cpu_usage }}%
              </template>
            </el-table-column>
            <el-table-column prop="gpu_usage" label="GPU使用率" width="120">
              <template #default="{ row }">
                {{ row.gpu_usage }}%
              </template>
            </el-table-column>
            <el-table-column prop="memory_usage" label="内存使用" width="120">
              <template #default="{ row }">
                {{ row.memory_usage }}GB
              </template>
            </el-table-column>
            <el-table-column prop="last_heartbeat" label="最后心跳" width="180" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button size="small" @click="viewDevice(row.device_id)">
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
    device_id: 'EDGE_001',
    device_name: '机载设备1号',
    cpu_usage: 45.5,
    gpu_usage: 60.2,
    memory_usage: 12.5,
    last_heartbeat: '2025-01-26 10:00:00'
  },
  {
    device_id: 'EDGE_002',
    device_name: '机载设备2号',
    cpu_usage: 38.2,
    gpu_usage: 55.8,
    memory_usage: 10.2,
    last_heartbeat: '2025-01-26 10:00:05'
  }
])

// 最近训练任务
const recentTrainings = ref([
  {
    job_id: 'JOB001',
    job_name: '安全帽检测v2',
    status: 'running',
    progress: 65
  },
  {
    job_id: 'JOB002',
    job_name: '车辆检测训练',
    status: 'completed',
    progress: 100
  },
  {
    job_id: 'JOB003',
    job_name: '人员识别微调',
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
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '设备状态',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 42, name: '在线' },
          { value: 8, name: '离线' },
          { value: 2, name: '告警' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
  chart.setOption(option)
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
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 5px;
}
</style>
