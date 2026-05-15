// ── Supplier verification ────────────────────────────────────────────────────

export interface VerifySupplierRequest {
  business_name: string
  rc_number: string
  bank_account_number: string
  bank_code: string
  supplier_type: 'healthcare' | 'general'
  expected_nafdac_number?: string
  expected_manufacturer?: string
  expected_product?: string
}

export type CheckStatus = 'pass' | 'warn' | 'fail' | 'unverified'

export interface VerificationCheck {
  name: string
  status: CheckStatus
  weight: number
  detail: string
}

export interface VerifySupplierResponse {
  verdict: 'green' | 'amber' | 'red'
  score: number
  checks: VerificationCheck[]
  raw_concerns: string[]
}

// ── Delivery verification ────────────────────────────────────────────────────

export interface DeliveryVerificationCheck {
  name: string
  status: CheckStatus
  weight: number
  detail: string
}

export interface VerifyDeliveryResponse {
  order_id: string
  verdict: 'green' | 'amber' | 'red'
  score: number
  checks: DeliveryVerificationCheck[]
  concerns: string[]
  detected_nafdac_number: string | null
  nafdac_lookup_result: Record<string, unknown> | null
  ocr_source: 'tesseract' | 'llm'
  duration_ms: number
}

// ── Orders ───────────────────────────────────────────────────────────────────

export type OrderStatus =
  | 'pending_payment'
  | 'funded'
  | 'delivered_pending'
  | 'released'
  | 'disputed'
  | 'refunded'
  | 'cancelled'

export interface CreateOrderRequest {
  supplier_id: string
  amount_ngn: number
  description: string
  buyer_email: string
  expected_delivery_days?: number
}

export interface OrderResponse {
  id: string
  status: OrderStatus
  supplier_id: string
  supplier_name: string
  amount_ngn: number
  description: string
  created_at: string
  expected_delivery_by: string | null
  virtual_account_number: string | null
  virtual_account_name: string | null
  virtual_account_bank: string | null
  trust_score_at_creation: number | null
  trust_verdict_at_creation: string | null
}

export interface ReleaseOrderRequest {
  confirmation_note?: string
}

export interface DisputeOrderRequest {
  reason: 'product_mismatch' | 'not_delivered' | 'wrong_quantity' | 'damaged' | 'other'
  description: string
}

export interface OrderActionResponse {
  order_id: string
  new_status: OrderStatus
  message: string
}

// ── Admin ────────────────────────────────────────────────────────────────────

export interface SimulatePaymentResponse {
  received: boolean
  event: string
}
