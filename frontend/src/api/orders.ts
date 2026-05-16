import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, apiFetchForm } from './client'
import type {
  CreateOrderRequest,
  CreateOrderFromInvoiceRequest,
  ExtractInvoiceResponse,
  OrderResponse,
  ReleaseOrderRequest,
  DisputeOrderRequest,
  OrderActionResponse,
} from './types'

export function useOrder(id: string | undefined) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => apiFetch<OrderResponse>(`/orders/${id}`),
    enabled: !!id,
  })
}

export function useCreateOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateOrderRequest) =>
      apiFetch<OrderResponse>('/orders', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useExtractInvoice() {
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return apiFetchForm<ExtractInvoiceResponse>('/orders/extract-invoice', fd)
    },
  })
}

export function useCreateOrderFromInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateOrderFromInvoiceRequest) =>
      apiFetch<OrderResponse>('/orders', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['orders'] }),
  })
}

export function useReleaseOrder(orderId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReleaseOrderRequest) =>
      apiFetch<OrderActionResponse>(`/orders/${orderId}/release`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}

export function useDisputeOrder(orderId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: DisputeOrderRequest) =>
      apiFetch<OrderActionResponse>(`/orders/${orderId}/dispute`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['order', orderId] }),
  })
}
