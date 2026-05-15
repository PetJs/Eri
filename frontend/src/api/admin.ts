import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { SimulatePaymentResponse } from './types'

export function useSimulatePayment(orderId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<SimulatePaymentResponse>('/admin/demo/simulate-payment', {
        method: 'POST',
        body: JSON.stringify({
          order_id: orderId,
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}
