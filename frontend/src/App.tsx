import { useState} from "react";
import TrustLockSidebar from "./component/sidebar";
import VerifySupplierPage from "./pages/user/VerifySupplier";


export default function App() {
  const [activePage] = useState("verify");

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      <TrustLockSidebar />
      <main className="flex-1 overflow-y-auto">
        {activePage === "verify" && <VerifySupplierPage />}
      </main>
    </div>
  );
}