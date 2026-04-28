<template>
  <div class="alert-rule-manage">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>告警规则配置</span>
          <el-button type="primary" size="small" @click="openDialog()">新增规则</el-button>
        </div>
      </template>

      <el-table :data="rules" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column label="匹配条件" min-width="250">
          <template #default="{ row }">
            <span v-if="row.deviceId">{{ row.deviceId }} / </span>
            <span v-if="row.source">{{ row.source }} / </span>
            <span v-if="row.className">{{ row.className }}</span>
            <span v-if="!row.deviceId && !row.source && !row.className">所有</span>
          </template>
        </el-table-column>
        <el-table-column label="触发条件" width="200">
          <template #default="{ row }">
            {{ conditionTypeMap[row.conditionType] || row.conditionType }}
            <span v-if="row.thresholdValue != null"> &ge; {{ row.thresholdValue }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="alertLevel" label="告警级别" width="100">
          <template #default="{ row }">
            <el-tag :type="alertTagType(row.alertLevel)" size="small" effect="dark">
              {{ alertLevelMap[row.alertLevel] || row.alertLevel }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发云端推理" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.triggerCloudInfer" type="warning" size="small">是</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button size="small" text @click="openDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button size="small" text type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑规则' : '新增规则'" width="650px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="规则名称">
          <el-input v-model="form.name" placeholder="例如：黑水区域告警" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备ID">
              <el-input v-model="form.device_id" placeholder="留空=所有设备" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="来源">
              <el-select v-model="form.source" clearable placeholder="留空=所有来源">
                <el-option label="边缘端" value="edge" />
                <el-option label="云端" value="cloud" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="目标类别">
              <el-input v-model="form.class_name" placeholder="例如：black_water" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型">
              <el-input v-model="form.model_name" placeholder="留空=所有模型" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="条件类型">
              <el-select v-model="form.condition_type">
                <el-option label="面积阈值" value="area_threshold" />
                <el-option label="数量阈值" value="count_threshold" />
                <el-option label="置信度阈值" value="confidence_threshold" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="阈值">
              <el-input-number v-model="form.threshold_value" :min="0" :precision="2" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="告警级别">
              <el-select v-model="form.alert_level">
                <el-option label="严重" value="critical" />
                <el-option label="警告" value="warning" />
                <el-option label="信息" value="info" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="触发云端推理">
              <el-switch v-model="form.trigger_cloud_infer" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="告警消息">
          <el-input v-model="form.alert_message" placeholder="自定义告警消息" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { alertRuleApi } from '../../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const rules = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)

const conditionTypeMap: Record<string, string> = {
  area_threshold: '面积阈值',
  count_threshold: '数量阈值',
  confidence_threshold: '置信度阈值'
}
const alertLevelMap: Record<string, string> = { critical: '严重', warning: '警告', info: '信息' }

function alertTagType(level: string) {
  const map: Record<string, string> = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || 'info'
}

const defaultForm = () => ({
  name: '', device_id: '', source: '', class_name: '', model_name: '',
  condition_type: 'count_threshold', threshold_value: 1,
  alert_level: 'warning', alert_message: '', trigger_cloud_infer: false, enabled: true
})
const form = ref<any>(defaultForm())

async function loadRules() {
  loading.value = true
  try {
    const res = await alertRuleApi.getList() as any
    rules.value = res.data || []
  } catch (e) {
    console.error('加载规则失败', e)
  } finally {
    loading.value = false
  }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = {
      name: row.name, device_id: row.deviceId || '', source: row.source || '',
      class_name: row.className || '', model_name: row.modelName || '',
      condition_type: row.conditionType, threshold_value: row.thresholdValue,
      alert_level: row.alertLevel, alert_message: row.alertMessage || '',
      trigger_cloud_infer: row.triggerCloudInfer || false, enabled: row.enabled
    }
  } else {
    editingId.value = null
    form.value = defaultForm()
  }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (editingId.value) {
      await alertRuleApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await alertRuleApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadRules()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function handleDelete(id: number) {
  try {
    await alertRuleApi.delete(id)
    ElMessage.success('删除成功')
    loadRules()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => loadRules())
</script>

<style scoped>
.alert-rule-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.text-muted { color: #909399; }
</style>
