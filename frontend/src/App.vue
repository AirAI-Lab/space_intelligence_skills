<template>
  <el-config-provider :locale="locale">
    <el-container class="app-container">
      <!-- 侧边栏 -->
      <el-aside width="200px">
        <div class="logo">
          <h2>edge_infer_cloud</h2>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409eff"
        >
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/device">
            <el-icon><Monitor /></el-icon>
            <span>设备管理</span>
          </el-menu-item>
          <el-menu-item index="/data">
            <el-icon><FolderOpened /></el-icon>
            <span>数据管理</span>
          </el-menu-item>
          <el-menu-item index="/training">
            <el-icon><DataLine /></el-icon>
            <span>训练管理</span>
          </el-menu-item>
          <el-menu-item index="/model">
            <el-icon><Box /></el-icon>
            <span>模型管理</span>
          </el-menu-item>
          <el-menu-item index="/ota">
            <el-icon><Download /></el-icon>
            <span>OTA升级</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header>
          <div class="header-content">
            <h3>{{ pageTitle }}</h3>
            <div class="header-right">
              <el-badge :value="alarmCount" :hidden="alarmCount === 0" class="alarm-badge">
                <el-icon :size="20"><Bell /></el-icon>
              </el-badge>
              <el-dropdown>
                <span class="user-dropdown">
                  <el-icon><User /></el-icon>
                  管理员
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item>个人设置</el-dropdown-item>
                    <el-dropdown-item divided>退出登录</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </el-header>

        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import {
  House,
  Monitor,
  FolderOpened,
  DataLine,
  Box,
  Download,
  Bell,
  User
} from '@element-plus/icons-vue'

const route = useRoute()
const locale = zhCn
const alarmCount = ref(0)

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': '首页',
    '/device': '设备管理',
    '/data': '数据管理',
    '/training': '训练管理',
    '/model': '模型管理',
    '/ota': 'OTA升级'
  }
  return titles[route.path] || 'edge_infer_cloud'
})
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  background-color: #2b2f3a;
  color: #fff;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
}

.el-aside {
  background-color: #304156;
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
