<script setup lang="ts">
import { PutEventCommitAPIArrival } from '@src/api-service/event/types'
import { CommitConfirmationModal } from '@src/domain/picking/commit-confirmation-modal'
import usePutEventCommit from '@src/hooks/use-put-event-commit'
import { usePickerStore } from '@src/stores/picker'
import { Arrival } from '@src/types/arrival'
import { EarthQuakeEvent } from '@src/types/event'
import { Pick } from '@src/types/pick'
import { Station } from '@src/types/station'
import { formatDate } from '@src/utils/string'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { toast } from 'vue3-toastify'

interface SelectedPick {
  [pickId: string]: {
    selected: boolean
  }
}

const { event } = defineProps<{
  event: EarthQuakeEvent
}>()

const pickerStore = usePickerStore()
const { mutateAsync: commitEvent } = usePutEventCommit()
const router = useRouter()

const isConfirmationModalShow = ref(false)
const selectedPicks = ref<SelectedPick>({})

const updatedPick = pickerStore.events[event._id]
const arrivals = computed(() => event.arrivals ?? [])
const selectedPickIds = computed(() =>
  Object.keys(selectedPicks.value).filter((pickId) => selectedPicks.value[pickId].selected)
)

const groupedArrivals = computed(() => {
  const groupedArrival: Record<
    string,
    {
      pick: Pick
      station: Station
      phase: {
        p?: Arrival & {
          original: string
          updated?: string
        }
        s?: Arrival & {
          original: string
          updated?: string
        }
      }
    }
  > = {}

  for (const arrival of arrivals.value) {
    if (!arrival.pick_details?._id) {
      continue
    }

    if (!groupedArrival[arrival.pick_details._id]) {
      groupedArrival[arrival.pick_details._id] = {
        pick: arrival.pick_details,
        station: arrival.station_details,
        phase: {}
      }
    }

    if (arrival.phase_type === 'P') {
      groupedArrival[arrival.pick_details._id].phase['p'] = {
        ...arrival,
        ...getPickerTimestamp(arrival)
      }
    } else {
      groupedArrival[arrival.pick_details._id].phase['s'] = {
        ...arrival,
        ...getPickerTimestamp(arrival)
      }
    }
  }

  return Object.values(groupedArrival)
})

const getPickerTimestamp = (arrival: Arrival) => {
  if (!updatedPick || !updatedPick[arrival.pick_details._id]) {
    return {
      original: arrival.timestamp
    }
  }

  if (arrival.phase_type === 'P') {
    return {
      original: arrival.timestamp,
      updated: updatedPick[arrival.pick_details._id]?.p?.timestamp
    }
  }

  return {
    original: arrival.timestamp,
    updated: updatedPick[arrival.pick_details._id]?.s?.timestamp
  }
}

const toggleSelectedArrival = (pickId: string) => {
  selectedPicks.value = {
    ...selectedPicks.value,
    [pickId]: {
      selected: !selectedPicks.value[pickId].selected
    }
  }
}

const onConfirmCommit = async () => {
  const usedArrivals: PutEventCommitAPIArrival[] = []

  const filteredPicks = groupedArrivals.value.filter((arrival) => selectedPickIds.value.includes(arrival.pick._id))

  filteredPicks.forEach((pick) => {
    if (pick.phase.s) {
      usedArrivals.push({
        ...pick.phase.s,
        pick_source_id: pick.pick._id,
        station_id: pick.station._id,
        timestamp: pick.phase.s.updated ?? pick.phase.s.original
      })
    }
    if (pick.phase.p) {
      usedArrivals.push({
        ...pick.phase.p,
        pick_source_id: pick.pick._id,
        station_id: pick.station._id,
        timestamp: pick.phase.p.updated ?? pick.phase.p.original
      })
    }
  })

  try {
    isConfirmationModalShow.value = false

    const { status, data: newEventData } = await commitEvent({
      eventId: event._id,
      arrivals: usedArrivals
    })

    if (!status) {
      throw Error('unsuccessfull commit event')
    }

    toast.success('Successfully commit the event arrivals')
    if (newEventData._id === event._id) {
      window.location.reload()
    } else {
      router.replace(`/origin-locator-view/location/${newEventData._id}`)
    }
  } catch (e) {
    toast.error('Failed to commit the event arrivals')
  }
}

watch(
  groupedArrivals,
  (newGroupedArrivals) => {
    const newSelectedPicks: SelectedPick = {}

    for (const groupedArrival of newGroupedArrivals) {
      const isPChecked = groupedArrival.phase.p?.checked ?? false
      const isSChecked = groupedArrival.phase.s?.checked ?? false
      newSelectedPicks[groupedArrival.pick._id] = {
        selected: isPChecked || isSChecked || false
      }
    }

    selectedPicks.value = newSelectedPicks
  },
  { immediate: true }
)
</script>

<template>
  <div v-if="arrivals.length > 0" class="flex flex-col flex-1 w-full md:h-full">
    <div class="flex-1 flex flex-col w-full h-full max-h-[265px] md:overflow-y-auto max-md:overflow-x-auto">
      <table class="table table-sm">
        <thead class="bg-base-200 sticky top-0">
          <tr>
            <th width="30">Used</th>
            <th width="50">Station</th>
            <th width="50">Network</th>
            <th class="text-right">P</th>
            <th class="text-right">S</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="groupedArrival in groupedArrivals"
            :key="groupedArrival.pick._id"
            class="cursor-pointer"
            @click="toggleSelectedArrival(groupedArrival.pick._id)">
            <td>
              <input
                v-if="typeof selectedPicks[groupedArrival.pick._id]?.selected === 'boolean'"
                :id="groupedArrival.pick._id"
                v-model="selectedPicks[groupedArrival.pick._id].selected"
                type="checkbox"
                class="checkbox checkbox-primary" />
            </td>
            <td>{{ groupedArrival.station.code }}</td>
            <td>{{ groupedArrival.station.network }}</td>
            <td class="text-right">
              <div v-if="groupedArrival.phase.p">
                <div
                  :class="{
                    'line-through': !!groupedArrival.phase.p.updated
                  }">
                  {{ formatDate(groupedArrival.phase.p.original) }}
                </div>
                <div v-if="groupedArrival.phase.p.updated">
                  <div className="badge badge-sm badge-warning">changed</div>
                  {{ formatDate(groupedArrival.phase.p.updated) }}
                </div>
              </div>
            </td>
            <td class="text-right">
              <div v-if="groupedArrival.phase.s">
                <div
                  :class="{
                    'line-through': !!groupedArrival.phase.s.updated
                  }">
                  {{ formatDate(groupedArrival.phase.s.original) }}
                </div>
                <div v-if="groupedArrival.phase.s.updated">
                  <div className="badge badge-sm badge-warning">changed</div>
                  {{ formatDate(groupedArrival.phase.s.updated!) }}
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="flex justify-end items-center gap-2 py-4">
      <RouterLink :to="`/origin-locator-view/picking/${event._id}`" class="btn btn-sm btn-primary">Picker</RouterLink>
      <div
        :class="{
          'tooltip tooltip-left tooltip-error': selectedPickIds.length < 4
        }"
        data-tip="Must be pick at least 4 arrivals">
        <button
          class="btn btn-sm btn-success relative -top-0.5"
          :class="{
            'btn-disabled btn-outline': selectedPickIds.length < 4
          }"
          @click="isConfirmationModalShow = true">
          Commit
        </button>
      </div>
    </div>
  </div>

  <CommitConfirmationModal
    :total-arrivals="selectedPickIds.length"
    :is-open="isConfirmationModalShow"
    @close="isConfirmationModalShow = false"
    @confirm="onConfirmCommit()" />
</template>
