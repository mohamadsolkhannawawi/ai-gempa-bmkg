// stores/counter.js
import { Arrival } from '@src/types/arrival'
import { defineStore } from 'pinia'

export interface SelectedArrival {
  p?: Arrival
  s?: Arrival
}

interface PickerState {
  [eventId: string]: {
    [pickId: string]: SelectedArrival
  }
}

export const usePickerStore = defineStore('picker', {
  state: () => {
    return {
      events: {} as PickerState
    }
  },
  actions: {
    updateEventPick(newPickerState: PickerState) {
      this.events = {
        ...this.events,
        ...newPickerState
      }
    }
  }
})
