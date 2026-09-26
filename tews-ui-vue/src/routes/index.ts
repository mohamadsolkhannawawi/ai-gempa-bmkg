import { OLMap } from '@src/components/ol-map'
import { ConfigStationViewPage } from '@src/domain/config-view/station-view-page'
import { UserViewPage } from '@src/domain/config-view/user-view-page'
import { EQViewPage } from '@src/domain/eq-view/eq-view-page'
import { OriginLocatorViewPage } from '@src/domain/origin-locator-view/origin-locator-view-page'
import { createRouter, createWebHistory } from 'vue-router'

import { LoginPage } from '../domain/auth/login-page'
import { HomePage } from '../domain/home/home-page'
import { StationViewPage } from '../domain/station-view/station-view-page'
import { TraceViewPage } from '../domain/trace-view/trace-view-page'

const routes = [
  { path: '/', component: HomePage },
  { path: '/login', component: LoginPage },
  { path: '/trace-view', component: TraceViewPage },
  { path: '/station-view', component: StationViewPage },
  { path: '/eq-view', component: EQViewPage },
  { path: '/origin-locator-view/:tab', component: OriginLocatorViewPage },
  { path: '/origin-locator-view/:tab/:id', component: OriginLocatorViewPage },
  { path: '/config', component: UserViewPage },
  { path: '/config/user', name: 'config-user', component: UserViewPage },
  { path: '/config/station', name: 'config-station', component: ConfigStationViewPage },
  { path: '/ol-map', name: 'ol-map', component: OLMap }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
