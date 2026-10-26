import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/pipeline-builder'
  },
  {
    path: '/pipeline-builder',
    name: 'PipelineBuilder',
    component: () => import('@/views/PipelineBuilder.vue'),
    meta: { title: 'Pipeline Builder' }
  },
  {
    path: '/billing',
    name: 'Billing',
    component: () => import('@/views/Billing.vue'),
    meta: { title: 'Billing & Invoices' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || 'AI-GEMPA'} | AI-GEMPA BMKG`
  next()
})

export default router
