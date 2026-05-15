import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import Login from './pages/auth/Login'
import Layout from './component/Layout'
import DashboardPage from './pages/user/DashboardPage'
import VerifySupplier from './pages/user/VerifySupplier'
import SupplierList from './pages/user/SupplierList'
import OrderList from './pages/user/OrderList'
import OrderNew from './pages/user/OrderNew'
import OrderDetail from './pages/user/OrderDetail'
import VerifyDelivery from './pages/user/VerifyDelivery'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/verify-supplier" element={<VerifySupplier />} />
          <Route path="/orders" element={<OrderList />} />
          <Route path="/suppliers" element={<SupplierList />} />
          <Route path="/orders/new" element={<OrderNew />} />
          <Route path="/orders/:id" element={<OrderDetail />} />
          <Route path="/orders/:id/verify" element={<VerifyDelivery />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
