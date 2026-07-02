import { useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function fetchJson(url: string, signal?: AbortSignal) {
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export function useLatestDemand() {
  return useQuery({
    queryKey: ['demand', 'latest'],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/demand/latest`, signal),
    refetchInterval: 30000,
  })
}

export function useDemandHistory(regionId: string, hours: number = 24) {
  return useQuery({
    queryKey: ['demand', 'history', regionId, hours],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/demand/history?region_id=${regionId}&hours=${hours}`, signal),
    enabled: !!regionId,
  })
}

export function usePredictions(regionId: string) {
  return useQuery({
    queryKey: ['predictions', 'latest', regionId],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/predictions/latest?region_id=${regionId}`, signal),
    enabled: !!regionId,
  })
}

export function useAccuracy(regionId: string) {
  return useQuery({
    queryKey: ['predictions', 'accuracy', regionId],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/predictions/accuracy?region_id=${regionId}`, signal),
    enabled: !!regionId,
  })
}

export function useGlobalMetrics() {
  return useQuery({
    queryKey: ['metrics', 'global'],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/metrics/global`, signal),
    refetchInterval: 60000,
  })
}

export function useInvalidateQueries() {
  const queryClient = useQueryClient()

  return {
    invalidateDemand: () => queryClient.invalidateQueries({ queryKey: ['demand'] }),
    invalidatePredictions: () => queryClient.invalidateQueries({ queryKey: ['predictions'] }),
  }
}

export function useInsightData(
  regionIds: string[],
  startDate: string,
  endDate: string,
  granularity: string = 'daily'
) {
  const params = new URLSearchParams()
  regionIds.forEach(id => params.append('region_id', id))
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  params.set('granularity', granularity)

  return useQuery({
    queryKey: ['insight', 'data', ...regionIds, startDate, endDate, granularity],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/insight/data?${params}`, signal),
    enabled: regionIds.length > 0,
  })
}

export function useCorrelation(
  regionIds: string[],
  startDate: string,
  endDate: string
) {
  const params = new URLSearchParams()
  regionIds.forEach(id => params.append('region_id', id))
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)

  return useQuery({
    queryKey: ['insight', 'correlation', ...regionIds, startDate, endDate],
    queryFn: ({ signal }) => fetchJson(`${API_BASE}/insight/correlation?${params}`, signal),
    enabled: regionIds.length > 0,
  })
}
