import { useState, useRef } from "react";

const industryOptions = [
  "Healthcare", "Agriculture", "Manufacturing", "Technology",
  "Energy", "Construction", "Logistics", "Finance",
];

type CheckStatus = "pending" | "loading" | "success" | "failed";

type VerificationCheck = {
  id: string;
  label: string;
  detail: string;
};

const checks: VerificationCheck[] = [
  { id: "cac", label: "CAC Registration", detail: 'Active, registered as "XYZ Pharmaceuticals Ltd" since 2019' },
  { id: "nafdac", label: "NAFDAC License", detail: "License active until 2026" },
  { id: "bank", label: "Bank Name Match", detail: "Verifying account holder name..." },
  { id: "phone", label: "Phone Verification", detail: "Pending..." },
  { id: "performance", label: "Prior Performance", detail: "Pending..." },
  { id: "invoice", label: "Invoice Consistency", detail: "Pending..." },
];

const CheckIcon = ({ status }: { status: CheckStatus }) => {
  if (status === "success")
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-green-100 flex-shrink-0">
        <svg width="11" height="11" viewBox="0 0 12 12" fill="none">
          <path d="M2 6l3 3 5-5" stroke="#16a34a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  if (status === "loading")
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full border-2 border-blue-400 flex-shrink-0 animate-spin"
        style={{ borderTopColor: "transparent" }} />
    );
  if (status === "failed")
    return (
      <span className="flex items-center justify-center w-5 h-5 rounded-full bg-red-100 flex-shrink-0">
        <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
          <path d="M3 3l6 6M9 3l-6 6" stroke="#dc2626" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </span>
    );
  return (
    <span className="flex items-center justify-center w-5 h-5 rounded-full border-2 flex-shrink-0"
      style={{ borderColor: "#d1d5db" }} />
  );
};

export default function VerifySupplierPage() {
  const [form, setForm] = useState({
    companyName: "MedTrust Nigeria Ltd",
    rcNumber: "RC-1234567",
    industry: "Healthcare",
    bankPartner: "GTBank",
    accountNumber: "0123456789",
    contactNumber: "+234 801 234 5678",
  });
  const [fileName, setFileName] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [statuses, setStatuses] = useState<Record<string, CheckStatus>>({});
  const [verifyingText, setVerifyingText] = useState("Verifying...");
  const [allDone, setAllDone] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const dragRef = useRef<HTMLDivElement>(null);

  const handleField = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) setFileName(file.name);
  };

  const runVerification = () => {
    setVerifying(true);
    setStatuses({});
    setAllDone(false);
    setVerifyingText("Verifying...");

    const sequence: Array<{ id: string; status: CheckStatus; delay: number }> = [
      { id: "cac", status: "loading", delay: 600 },
      { id: "cac", status: "success", delay: 1600 },
      { id: "nafdac", status: "loading", delay: 1800 },
      { id: "nafdac", status: "success", delay: 2700 },
      { id: "bank", status: "loading", delay: 2900 },
      { id: "bank", status: "success", delay: 3900 },
      { id: "phone", status: "loading", delay: 4100 },
      { id: "phone", status: "success", delay: 5000 },
      { id: "performance", status: "loading", delay: 5200 },
      { id: "performance", status: "success", delay: 6000 },
      { id: "invoice", status: "loading", delay: 6200 },
      { id: "invoice", status: "success", delay: 7100 },
    ];

    sequence.forEach(({ id, status, delay }) => {
      setTimeout(() => setStatuses((prev) => ({ ...prev, [id]: status })), delay);
    });

    setTimeout(() => {
      setVerifyingText("Verification Complete");
      setAllDone(true);
    }, 7300);
  };

  const completedCount = Object.values(statuses).filter((s) => s === "success").length;

  return (
    <div className="min-h-screen bg-gray-50 px-8 py-8" style={{ fontFamily: "'DM Sans', 'Segoe UI', sans-serif" }}>

      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Verify Supplier</h1>
        <p className="text-sm text-gray-500 mt-0.5">Institutional KYC &amp; AML Due Diligence</p>
      </div>

      <div className="flex gap-6 items-start">

        {/* ─── LEFT: Entity Form ─── */}
        <div className="flex-1 min-w-0 bg-white rounded-2xl border border-gray-200 p-7 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-5">Entity Information</h2>

          <div className="space-y-4">
            {/* Company Name */}
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Company Registered Name</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition"
                value={form.companyName}
                onChange={(e) => handleField("companyName", e.target.value)}
              />
            </div>

            {/* RC + Industry */}
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1.5">RC Number</label>
                <input
                  className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition"
                  value={form.rcNumber}
                  onChange={(e) => handleField("rcNumber", e.target.value)}
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs text-gray-500 mb-1.5">Industry Segment</label>
                <div className="relative">
                  <select
                    className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition appearance-none pr-8"
                    value={form.industry}
                    onChange={(e) => handleField("industry", e.target.value)}
                  >
                    {industryOptions.map((o) => <option key={o}>{o}</option>)}
                  </select>
                  <svg className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Bank Partner */}
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Bank Partner</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition"
                value={form.bankPartner}
                onChange={(e) => handleField("bankPartner", e.target.value)}
              />
            </div>

            {/* Account Number */}
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Account Number (Settlement)</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition"
                value={form.accountNumber}
                onChange={(e) => handleField("accountNumber", e.target.value)}
              />
            </div>

            {/* Contact Number */}
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Verified Contact Number</label>
              <input
                className="w-full border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-800 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition"
                value={form.contactNumber}
                onChange={(e) => handleField("contactNumber", e.target.value)}
              />
            </div>

            {/* Invoice Upload */}
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Invoice upload</label>
              <div
                ref={dragRef}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileRef.current?.click()}
                className="border border-dashed border-gray-300 rounded-xl p-6 flex flex-col items-center justify-center gap-1.5 cursor-pointer hover:border-blue-400 hover:bg-blue-50/40 transition-all"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
                <p className="text-sm text-gray-500">
                  {fileName
                    ? <span className="text-blue-600 font-medium">{fileName}</span>
                    : <><span className="text-gray-600">Drag and drop your invoice PDF here, or </span><span className="text-blue-500 underline">browse files</span></>
                  }
                </p>
                <p className="text-xs text-gray-400">MAX SIZE: 5MB</p>
                <input ref={fileRef} type="file" accept=".pdf" className="hidden"
                  onChange={(e) => e.target.files?.[0] && setFileName(e.target.files[0].name)} />
              </div>
            </div>
          </div>

          {/* CTA Button */}
          <button
            onClick={runVerification}
            disabled={verifying && !allDone}
            className="mt-6 w-full flex items-center justify-center gap-2 bg-gray-900 hover:bg-gray-800 disabled:bg-gray-400 text-white text-sm font-semibold rounded-xl py-3.5 transition-all duration-200 active:scale-[0.99]"
          >
            {verifying && !allDone ? (
              <>
                <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
                Running verification...
              </>
            ) : allDone ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Verification Complete
              </>
            ) : (
              <>
                Run verification
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </>
            )}
          </button>
        </div>

        {/* ─── RIGHT: Verification Panel ─── */}
        <div
          className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden transition-all duration-500"
          style={{
            width: verifying ? "340px" : "0px",
            minWidth: verifying ? "340px" : "0px",
            opacity: verifying ? 1 : 0,
            padding: verifying ? "28px" : "0px",
          }}
        >
          {verifying && (
            <>
              {/* Spinner / Complete circle */}
              <div className="flex flex-col items-center mb-6">
                <div className="relative w-24 h-24 flex items-center justify-center mb-3">
                  {/* Track ring */}
                  <svg className="absolute inset-0 w-full h-full" viewBox="0 0 96 96">
                    <circle cx="48" cy="48" r="40" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                    {allDone ? (
                      <circle cx="48" cy="48" r="40" fill="none" stroke="#16a34a" strokeWidth="3"
                        strokeDasharray="251" strokeDashoffset="0"
                        style={{ transition: "stroke-dashoffset 0.8s ease", transformOrigin: "center", transform: "rotate(-90deg)" }} />
                    ) : (
                      <circle cx="48" cy="48" r="40" fill="none" stroke="#3b82f6" strokeWidth="3"
                        strokeDasharray="251"
                        strokeDashoffset={Math.max(251 - (completedCount / checks.length) * 251, 0)}
                        style={{ transition: "stroke-dashoffset 0.6s ease", transformOrigin: "center", transform: "rotate(-90deg)" }} />
                    )}
                  </svg>
                  <span className={`text-base font-semibold ${allDone ? "text-green-600" : "text-gray-700"}`}>
                    {allDone ? "✓" : `${completedCount}/${checks.length}`}
                  </span>
                </div>

                <p className={`text-xl font-bold tracking-tight ${allDone ? "text-green-700" : "text-gray-800"}`}>
                  {verifyingText}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {allDone ? "All 6 checks passed successfully" : "Cross-checking 6 public registries..."}
                </p>

                {/* Animated underline */}
                {!allDone && (
                  <div className="mt-2 h-0.5 w-10 bg-blue-400 rounded-full"
                    style={{ animation: "pulse 1.2s ease-in-out infinite" }} />
                )}
              </div>

              {/* Divider */}
              <div className="h-px bg-gray-100 mb-4" />

              {/* Check list */}
              <div className="space-y-3.5">
                {checks.map((check) => {
                  const status: CheckStatus = statuses[check.id] ?? "pending";
                  const isDone = status === "success";
                  const isLoading = status === "loading";
                  return (
                    <div key={check.id} className="flex items-start gap-3">
                      <CheckIcon status={status} />
                      <div>
                        <p className={`text-sm font-medium leading-tight ${isDone ? "text-gray-800" : isLoading ? "text-blue-700" : "text-gray-400"}`}>
                          {check.label}
                        </p>
                        <p className={`text-xs mt-0.5 leading-snug ${isDone ? "text-gray-500" : isLoading ? "text-blue-500" : "text-gray-300"}`}>
                          {isLoading && check.id === "bank" ? "Verifying account holder name..." :
                           isLoading ? `Checking ${check.label.toLowerCase()}...` :
                           isDone ? check.detail : "Pending..."}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Final action */}
              {allDone && (
                <div className="mt-6 pt-5 border-t border-gray-100">
                  <div className="rounded-xl bg-green-50 border border-green-200 px-4 py-3 flex items-center gap-3">
                    <span className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5">
                        <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </span>
                    <div>
                      <p className="text-sm font-semibold text-green-800">Supplier Verified</p>
                      <p className="text-xs text-green-600">Ready to proceed with onboarding</p>
                    </div>
                  </div>
                  <button className="mt-3 w-full text-sm font-semibold text-white bg-green-600 hover:bg-green-700 rounded-xl py-3 transition-all active:scale-[0.99]">
                    Proceed to Onboarding →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scaleX(1); }
          50% { opacity: 0.4; transform: scaleX(0.6); }
        }
      `}</style>
    </div>
  );
}