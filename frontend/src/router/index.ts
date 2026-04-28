import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/device',
    name: 'Device',
    component: () => import('../views/device/DeviceList.vue')
  },
  {
    path: '/device/:id',
    name: 'DeviceDetail',
    component: () => import('../views/device/DeviceDetail.vue')
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('../views/data/DatasetList.vue')
  },
  {
    path: '/data/datasets/:id',
    name: 'DatasetDetail',
    component: () => import('../views/data/DatasetDetail.vue')
  },
  {
    path: '/training',
    name: 'Training',
    component: () => import('../views/training/TrainingJob.vue')
  },
  {
    path: '/training/:id',
    name: 'TrainingDetail',
    component: () => import('../views/training/TrainingDetail.vue')
  },
  {
    path: '/model',
    name: 'Model',
    component: () => import('../views/model/ModelList.vue')
  },
  {
    path: '/model/:id',
    name: 'ModelDetail',
    component: () => import('../views/model/ModelDetail.vue')
  },
  {
    path: '/ota',
    name: 'OTA',
    component: () => import('../views/ota/OtaTask.vue')
  },
  {
    path: '/deployment',
    name: 'Deployment',
    component: () => import('../views/deployment/DeploymentRecord.vue')
  },
  {
    path: '/inference',
    name: 'InferenceResult',
    component: () => import('../views/inference/InferenceResultList.vue')
  },
  {
    path: '/alerts',
    name: 'AlertCenter',
    component: () => import('../views/inference/AlertCenter.vue')
  },
  {
    path: '/webhooks',
    name: 'WebhookManage',
    component: () => import('../views/inference/WebhookManage.vue')
  },
  {
    path: '/alert-rules',
    name: 'AlertRuleManage',
    component: () => import('../views/inference/AlertRuleManage.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
