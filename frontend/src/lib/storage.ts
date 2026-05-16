import type { OrderResponse } from '../api/types'

// ── Persisted orders ─────────────────────────────────────────────────────────

const ORDERS_KEY = 'eri_orders'

export interface StoredOrder {
  id: string
  supplier_name: string
  description: string
  amount_ngn: number
  status: string
  created_at: string
  virtual_account_number: string | null
  expected_nafdac?: string
  expected_manufacturer?: string
  expected_product?: string
}

export interface OrderMeta {
  expected_nafdac?: string
  expected_manufacturer?: string
  expected_product?: string
}

export function saveOrder(order: OrderResponse, meta?: OrderMeta) {
  const existing = getStoredOrders()
  const updated = [
    {
      id: order.id, supplier_name: order.supplier_name, description: order.description,
      amount_ngn: order.amount_ngn, status: order.status, created_at: order.created_at,
      virtual_account_number: order.virtual_account_number,
      ...meta,
    },
    ...existing.filter((o) => o.id !== order.id),
  ]
  localStorage.setItem(ORDERS_KEY, JSON.stringify(updated))
}

export function getStoredOrder(id: string): StoredOrder | undefined {
  return getStoredOrders().find((o) => o.id === id)
}

export function getStoredOrders(): StoredOrder[] {
  try {
    return JSON.parse(localStorage.getItem(ORDERS_KEY) ?? '[]') as StoredOrder[]
  } catch {
    return []
  }
}

export function updateStoredOrderStatus(id: string, status: string) {
  const orders = getStoredOrders()
  const updated = orders.map((o) => (o.id === id ? { ...o, status } : o))
  localStorage.setItem(ORDERS_KEY, JSON.stringify(updated))
}

// ── Persisted verified suppliers ─────────────────────────────────────────────

const SUPPLIERS_KEY = 'eri_suppliers'

export interface StoredSupplier {
  name: string
  rc: string
  bank: string
  account: string
  score: number
  verdict: string
  verifiedAt: string
}

export function saveSupplier(s: StoredSupplier) {
  const existing = getStoredSuppliers()
  const updated = [s, ...existing.filter((x) => x.rc !== s.rc)]
  localStorage.setItem(SUPPLIERS_KEY, JSON.stringify(updated))
}

export function getStoredSuppliers(): StoredSupplier[] {
  try {
    return JSON.parse(localStorage.getItem(SUPPLIERS_KEY) ?? '[]') as StoredSupplier[]
  } catch {
    return []
  }
}
