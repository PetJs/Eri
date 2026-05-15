import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { SimulatePaymentResponse } from './types'

export function useSimulatePayment(orderId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<SimulatePaymentResponse>('/webhooks/squad', {
        method: 'POST',
        body: JSON.stringify({
          event: 'charge.success',
          data: { transaction_ref: `txn_${orderId}`, amount: 0 },
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}
