<template>
  <el-aside :width="collapsed ? '64px' : '200px'" class="sidebar">
    <div class="logo" @click="router.push('/')">
      <el-icon :size="24"><Monitor /></el-icon>
      <span v-show="!collapsed" class="logo-text">SkyEdge AI</span>
    </div>
    <el-scrollbar class="menu-scrollbar">
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        router
        background-color="var(--sidebar-bg)"
        text-color="var(--sidebar-text)"
        active-text-color="var(--sidebar-active-text)"
      >
        <el-menu-item index="/">
          <el-icon><House /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/device">
          <el-icon><Monitor /></el-icon>
          <template #title>设备管理</template>
        </el-menu-item>
        <el-menu-item index="/data">
          <el-icon><FolderOpened /></el-icon>
          <template #title>数据管理</template>
        </el-menu-item>
        <el-menu-item index="/training">
          <el-icon><DataLine /></el-icon>
          <template #title>训练管理</template>
        </el-menu-item>
        <el-menu-item index="/model">
          <el-icon><Box /></el-icon>
          <template #title>模型管理</template>
        </el-menu-item>
        <el-menu-item index="/ota">
          <el-icon><Download /></el-icon>
          <template #title>OTA升级</template>
        </el-menu-item>
        <el-menu-item index="/deployment">
          <el-icon><Document /></el-icon>
          <template #title>部署记录</template>
        </el-menu-item>
        <el-menu-item index="/inference">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>推理结果</template>
        </el-menu-item>
        <el-menu-item index="/alerts">
          <el-icon><Warning /></el-icon>
          <template #title>告警中心</template>
        </el-menu-item>
        <el-menu-item index="/alert-rules">
          <el-icon><SetUp /></el-icon>
          <template #title>告警规则</template>
        </el-menu-item>
        <el-menu-item index="/webhooks">
          <el-icon><Link /></el-icon>
          <template #title>Webhook</template>
        </el-menu-item>
      </el-menu>
    </el-scrollbar>
    <div class="collapse-btn" @click="appStore.toggleSidebar()">
      <el-icon :size="18">
        <DArrowLeft v-if="!collapsed" />
        <DArrowRight v-else />
      </el-icon>
    </div>
  </el-aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import {
  House, Monitor, FolderOpened, DataLine, Box, Download,
  Document, DataAnalysis, Warning, SetUp, Link,
  DArrowLeft, DArrowRight
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()

const collapsed = computed(() => appStore.sidebarCollapsed)
const activeMenu = computed(() => {
  // /device/xxx → /device
  const path = route.path
  if (path.startsWith('/device/')) return '/device'
  if (path.startsWith('/data/')) return '/data'
  if (path.startsWith('/training/')) return '/training'
  if (path.startsWith('/model/')) return '/model'
  return path
})
</script>

<style scoped>
.sidebar {
  background-color: var(--sidebar-bg);
  transition: width 0.28s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-color: var(--sidebar-logo-bg);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}

.menu-scrollbar {
  flex: 1;
}

:deep(.el-menu) {
  border-right: none;
}

:deep(.el-menu--collapse) {
  width: 64px;
}

:deep(.el-menu-item) {
  transition: background 0.2s, color 0.2s;
}

.collapse-btn {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--sidebar-logo-bg);
  color: var(--sidebar-text);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.2s;
}

.collapse-btn:hover {
  color: var(--sidebar-active-text);
}
</style>
