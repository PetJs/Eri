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

export interface VerifyDeliveryResponse {
  order_id: string
  verdict: 'green' | 'amber' | 'red'
  match_confidence: number
  delivered_brand: string | null
  delivered_dosage: string | null
  delivered_nafdac: string | null
  differences: string[]
  concerns: string[]
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

// ── Invoice extraction ───────────────────────────────────────────────────────

export interface InvoiceBankAccount {
  account_number: string
  account_name: string
  bank_name: string
  bank_code?: string
}

export interface InvoiceSupplier {
  name: string
  rc_number: string
  address: string
  phone: string
  email: string
  bank_account: InvoiceBankAccount
}

export interface InvoiceBuyer {
  name: string
  address: string
  phone: string
  email: string
}

export interface InvoiceMetadata {
  invoice_number: string
  invoice_date: string
  currency: string
  payment_terms: string
  confidence_score: number
  fraud_flags: string[]
}

export interface InvoiceLineItem {
  line_number: number
  description: string
  nafdac_registration: string | null
  manufacturer: string | null
  batch_number: string | null
  expiry_date: string | null
  quantity: number
  unit: string
  unit_price: number
  line_total: number
}

export interface InvoiceTotals {
  subtotal: number
  discount: number
  vat: number
  grand_total: number
}

export interface ExtractInvoiceResponse {
  supplier: InvoiceSupplier
  buyer: InvoiceBuyer
  invoice_metadata: InvoiceMetadata
  line_items: InvoiceLineItem[]
  totals: InvoiceTotals
}

export interface CreateOrderFromInvoiceRequest {
  supplier: InvoiceSupplier
  buyer: InvoiceBuyer
  invoice_metadata: InvoiceMetadata
  line_items: InvoiceLineItem[]
  totals: InvoiceTotals
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
  line_items?: InvoiceLineItem[]
  verification_status?: string
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
  order_id: string
  previous_status: string
  new_status: string
  message: string
}
