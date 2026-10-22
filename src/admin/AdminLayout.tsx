import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAdmin } from "./AdminContext";
import { CollectionsPage } from "./pages/CollectionsPage";
import { PhotosPage } from "./pages/PhotosPage";
import { SyncPage } from "./pages/SyncPage";

const tabs = [
  { to: "photos", label: "Photos" },
  { to: "collections", label: "Collections" },
  { to: "sync", label: "Sync" },
];

export function AdminLayout() {
  const { prefix, username, signOut } = useAdmin();
  return (
    <>
      <header className="sticky top-0 z-10 bg-white/85 backdrop-blur-[14px]">
        <div className="mx-auto flex h-16 max-w-[1520px] items-center justify-between px-4 sm:px-7">
          <nav className="flex items-center gap-5 text-[15px] sm:gap-8">
            <span className="hidden font-medium tracking-[-0.02em] sm:inline">Admin</span>
            {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={`/a/${prefix}/${tab.to}`}
                className={({ isActive }) =>
                  `inline-flex min-h-11 items-center transition-colors hover:text-ink ${
                    isActive ? "text-ink underline underline-offset-[6px]" : "text-[#6b6b6b]"
                  }`
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-4 text-[14px] text-[#6b6b6b]">
            <span className="hidden sm:inline">{username}</span>
            <Button variant="outline" size="sm" onClick={() => void signOut()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1520px] px-4 pb-24 pt-8 sm:px-7">
        <Routes>
          <Route index element={<Navigate to="photos" replace />} />
          <Route path="photos" element={<PhotosPage />} />
          <Route path="collections" element={<CollectionsPage />} />
          <Route path="sync" element={<SyncPage />} />
          <Route path="*" element={<Navigate to="photos" replace />} />
        </Routes>
      </main>
    </>
  );
}
