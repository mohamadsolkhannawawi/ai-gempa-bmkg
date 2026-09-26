import './style.css'
import 'vue3-toastify/dist/index.css'

import { VueQueryPlugin } from '@tanstack/vue-query'
import { addIcons, OhVueIcon } from 'oh-vue-icons'
import {
  BiPinAngle,
  FaCalendar,
  FaList,
  FaMap,
  FaRegularTrashAlt,
  FaSearch,
  GiSoundWaves,
  HiPencilAlt,
  IoCalendarOutline,
  IoCheckmark,
  IoCloseSharp,
  IoHomeOutline,
  LaDotCircle,
  LaFilterSolid,
  MdClose,
  MdHomeOutlined,
  MdSettings,
  RiBaseStationLine,
  WiEarthquake
} from 'oh-vue-icons/icons'
import { createPinia } from 'pinia'
import { setupCalendar } from 'v-calendar'
import { createApp } from 'vue'

import App from './App.vue'
import router from './routes'

addIcons(
  BiPinAngle,
  FaCalendar,
  FaList,
  FaMap,
  FaRegularTrashAlt,
  FaSearch,
  GiSoundWaves,
  HiPencilAlt,
  IoCalendarOutline,
  IoCheckmark,
  IoCloseSharp,
  IoHomeOutline,
  LaDotCircle,
  LaFilterSolid,
  MdClose,
  MdHomeOutlined,
  MdSettings,
  RiBaseStationLine,
  WiEarthquake
)

const pinia = createPinia()
const app = createApp(App)
app.component('VIcon', OhVueIcon)

app.use(pinia)
app.use(setupCalendar, {})
app.use(VueQueryPlugin, {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        staleTime: Infinity,
        refetchOnWindowFocus: false,
        retry: false
      }
    }
  }
})
app.use(router)
app.mount('#app')
