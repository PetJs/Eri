import { useMutation } from '@tanstack/react-query'
import { apiFetch, apiFetchForm } from './client'
import type {
  VerifySupplierRequest,
  VerifySupplierResponse,
  VerifyDeliveryResponse,
} from './types'

export function useVerifySupplier() {
  return useMutation({
    mutationFn: (body: VerifySupplierRequest) =>
      apiFetch<VerifySupplierResponse>('/verify/supplier', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
  })
}

export interface VerifyDeliveryInput {
  orderId: string
  quoteImage: File
  deliveryImage: File
  expectedNafdac?: string
  expectedManufacturer?: string
  expectedProduct?: string
}

export function useVerifyDelivery() {
  return useMutation({
    mutationFn: ({ orderId, quoteImage, deliveryImage, expectedNafdac, expectedManufacturer, expectedProduct }: VerifyDeliveryInput) => {
      const form = new FormData()
      form.append('quote_image', quoteImage)
      form.append('delivery_image', deliveryImage)
      if (expectedNafdac) form.append('expected_nafdac', expectedNafdac)
      if (expectedManufacturer) form.append('expected_manufacturer', expectedManufacturer)
      if (expectedProduct) form.append('expected_product', expectedProduct)
      return apiFetchForm<VerifyDeliveryResponse>(`/verify/delivery/${orderId}`, form)
    },
  })
}
