<template>
  <el-breadcrumb separator="/" class="breadcrumb">
    <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
    <el-breadcrumb-item v-for="item in items" :key="item.path">
      <router-link v-if="item.to" :to="item.to">{{ item.title }}</router-link>
      <span v-else>{{ item.title }}</span>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const titleMap: Record<string, string> = {
  '/device': '设备管理',
  '/data': '数据管理',
  '/training': '训练管理',
  '/model': '模型管理',
  '/ota': 'OTA升级',
  '/deployment': '部署记录',
  '/inference': '推理结果',
  '/alerts': '告警中心',
  '/alert-rules': '告警规则',
  '/webhooks': 'Webhook管理'
}

const items = computed(() => {
  const path = route.path
  if (path === '/') return []

  const result: { path: string; title: string; to?: string }[] = []

  // 一级页面
  const firstSegment = '/' + path.split('/')[1]
  if (titleMap[firstSegment]) {
    // 如果是详情页，显示列表页链接 + 详情标题
    if (path.split('/').length > 2) {
      result.push({ path: firstSegment, title: titleMap[firstSegment], to: firstSegment })
      result.push({ path, title: route.query.name as string || '详情' })
    } else {
      result.push({ path, title: titleMap[firstSegment] })
    }
  }

  return result
})
</script>

<style scoped>
.breadcrumb {
  font-size: 14px;
}

.breadcrumb a {
  color: var(--el-text-color-regular);
  text-decoration: none;
}

.breadcrumb a:hover {
  color: var(--el-color-primary);
}
</style>
