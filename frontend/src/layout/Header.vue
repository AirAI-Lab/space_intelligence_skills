<template>
  <el-header class="header" height="50px">
    <Breadcrumb />
    <div class="header-right">
      <el-badge :value="alarmCount" :hidden="alarmCount === 0" class="alarm-badge">
        <el-icon :size="18"><Bell /></el-icon>
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
  </el-header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Bell, User } from '@element-plus/icons-vue'
import Breadcrumb from './Breadcrumb.vue'

const alarmCount = ref(0)
</script>

<style scoped>
.header {
  background-color: #fff;
  border-bottom: 1px solid var(--art-gray-300);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: var(--header-height);
  flex-shrink: 0;
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
  font-size: 14px;
}

.alarm-badge {
  cursor: pointer;
}
</style>
