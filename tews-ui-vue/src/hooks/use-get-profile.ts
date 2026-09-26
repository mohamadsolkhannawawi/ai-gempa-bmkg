import { useQuery } from '@tanstack/vue-query'

import { APIResponse } from '../types/api'
import { User } from '../types/user'
import api from '../utils/api'

const useGetProfile = () =>
  useQuery({
    queryKey: ['profile'],
    queryFn: async (): Promise<User> => {
      const { data } = await api.get<APIResponse<User>>('/user/me')
      return data.data!
    }
  })

export default useGetProfile
