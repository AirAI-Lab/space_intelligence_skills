<template>
  <div class="webhook-manage">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>Webhook 配置</span>
          <el-button type="primary" size="small" @click="openDialog()">新增 Webhook</el-button>
        </div>
      </template>

      <el-table :data="webhooks" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="名称" width="160" />
        <el-table-column prop="url" label="URL" min-width="250" />
        <el-table-column prop="events" label="事件" width="200">
          <template #default="{ row }">
            <el-tag v-for="e in (row.events || '').split(',').filter(Boolean)" :key="e" size="small" style="margin-right: 4px">
              {{ e.trim() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
              {{ row.enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="triggerCount" label="触发次数" width="100" />
        <el-table-column prop="lastTriggerTime" label="最后触发" width="170">
          <template #default="{ row }">
            {{ row.lastTriggerTime?.replace('T', ' ').substring(0, 19) || '-' }}
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑 Webhook' : '新增 Webhook'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="例如：智飞平台推送" />
        </el-form-item>
        <el-form-item label="URL">
          <el-input v-model="form.url" placeholder="https://example.com/webhook" />
        </el-form-item>
        <el-form-item label="Secret">
          <el-input v-model="form.secret" placeholder="可选，用于验证" />
        </el-form-item>
        <el-form-item label="事件">
          <el-input v-model="form.events" placeholder="alert.*,result.edge,alert.critical" />
          <div style="font-size: 12px; color: #909399; margin-top: 4px">
            支持通配符，如 alert.* 匹配所有告警，多个事件用逗号分隔
          </div>
        </el-form-item>
        <el-form-item label="自定义Headers">
          <el-input v-model="form.headers" type="textarea" :rows="2" placeholder='{"Authorization": "Bearer xxx"}' />
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
import { webhookApi } from '../../api'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const webhooks = ref<any[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref<any>({
  name: '', url: '', secret: '', events: 'alert.*', headers: '', enabled: true
})

async function loadWebhooks() {
  loading.value = true
  try {
    const res = await webhookApi.getList() as any
    webhooks.value = res.data || []
  } catch (e) {
    console.error('加载Webhook失败', e)
  } finally {
    loading.value = false
  }
}

function openDialog(row?: any) {
  if (row) {
    editingId.value = row.id
    form.value = { name: row.name, url: row.url, secret: row.secret || '', events: row.events || '', headers: row.headers || '', enabled: row.enabled }
  } else {
    editingId.value = null
    form.value = { name: '', url: '', secret: '', events: 'alert.*', headers: '', enabled: true }
  }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (editingId.value) {
      await webhookApi.update(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await webhookApi.create(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadWebhooks()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  }
}

async function handleDelete(id: number) {
  try {
    await webhookApi.delete(id)
    ElMessage.success('删除成功')
    loadWebhooks()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(() => loadWebhooks())
</script>

<style scoped>
.webhook-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
