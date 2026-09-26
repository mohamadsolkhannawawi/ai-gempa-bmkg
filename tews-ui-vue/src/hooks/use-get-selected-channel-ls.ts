import useGetProfile from './use-get-profile'

const LOCAL_STORAGE_KEY = 'selected-stations'

const getDataFromLocalStorage = (): string[] => {
  try {
    const localStorageItem = window.localStorage.getItem(LOCAL_STORAGE_KEY)

    if (!localStorageItem) return []

    const parsedLocalStorageData = JSON.parse(localStorageItem) as string[]

    return parsedLocalStorageData
  } catch (e) {
    return []
  }
}

function useGetSelectedChannelsFromLocalStorage() {
  const { data: profile } = useGetProfile()

  if (!profile.value) {
    return []
  }

  const stationIds = profile.value.stations
  const dataFromLocalStorage = getDataFromLocalStorage() ?? []

  return dataFromLocalStorage.filter((data) => stationIds.includes(data))
}

export default useGetSelectedChannelsFromLocalStorage
