import { lazy, Suspense } from "react";
import {
  BrowserRouter,
  useLocation,
  Navigate,
  NavLink,
  Route,
  Routes,
} from "react-router-dom";
import { Database, Sparkles, TrendingUp } from "lucide-react";
import "./App.css";

const AllocationPage = lazy(() => import("./pages/AllocationPage"));
const DataWorkspace = lazy(() => import("./pages/DataWorkspace"));
const ModelAnalysis = lazy(() => import("./pages/ModelAnalysis"));
const DatasetPreview = lazy(() => import("./pages/DatasetPreview"));
const EDAPage = lazy(() => import("./EDAPage/EDAPage"));

const navigation = [
  { to: "/upload", label: "Data workspace", icon: Database },
  { to: "/uplift", label: "Uplift analysis", icon: TrendingUp },
  { to: "/allocation", label: "Budget allocation", icon: Sparkles },
];

function DashboardLayout() {
  const { pathname } = useLocation();
  const pageTitle = pathname.startsWith("/uplift")
    ? "Uplift analysis"
    : pathname.startsWith("/allocation")
      ? "Budget allocation"
      : "Data workspace";

  return (
    <div className="min-h-screen bg-[#f7f8fc] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-slate-200/80 bg-white px-5 py-6 lg:flex">
        <NavLink to="/upload" className="flex items-center gap-3 px-2" aria-label="EconoCausal home">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-lg shadow-indigo-200">
            <TrendingUp className="h-5 w-5" aria-hidden="true" />
          </span>
          <span>
            <span className="block text-[15px] font-bold tracking-tight text-slate-900">EconoCausal</span>
            <span className="block text-xs text-slate-500">Campaign intelligence</span>
          </span>
        </NavLink>

        <div className="mt-11 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
          Workspace
        </div>
        <nav className="mt-3 space-y-1" aria-label="Main navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`
              }
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {label}
              {pathname === to && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-indigo-600" />
              )}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-indigo-600 shadow-sm">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </div>
          <p className="mt-3 text-sm font-semibold text-slate-800">Make every campaign count</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Use causal insights to focus your budget on customers most likely to respond.
          </p>
        </div>
      </aside>

      <div className="min-h-screen lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-[68px] max-w-[1440px] items-center justify-between px-5 sm:px-8">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white lg:hidden">
                E
              </span>
              <div>
                <div className="text-sm font-semibold text-slate-800">{pageTitle}</div>
                <div className="hidden text-xs text-slate-500 sm:block">
                  Understand the incremental impact of your campaigns
                </div>
              </div>
            </div>
            <span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Workspace ready
            </span>
          </div>
          <nav
            className="flex gap-2 overflow-x-auto border-t border-slate-100 px-5 py-2 lg:hidden"
            aria-label="Main navigation"
          >
            {navigation.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${
                    isActive
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-600 hover:bg-slate-50"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-10">
          <Suspense
            fallback={
              <div className="rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">
                Loading workspace…
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Navigate to="/upload" replace />} />
              <Route path="/upload" element={<DataWorkspace />} />
              <Route path="/uplift" element={<ModelAnalysis />} />
              <Route path="/allocation" element={<AllocationPage />} />
              <Route path="/eda" element={<EDAPage />} />
              <Route path="/preview" element={<DatasetPreview />} />
              <Route path="/causal" element={<Navigate to="/uplift" replace />} />
              <Route path="*" element={<Navigate to="/upload" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <DashboardLayout />
    </BrowserRouter>
  );
}
