import { Outlet } from "react-router";

export function Layout() {
  return (
    <div className="flex h-screen bg-[#f8fafd] font-sans text-gray-800 selection:bg-blue-100 selection:text-blue-900 p-4">
      <main className="flex-1 w-full max-w-[1440px] mx-auto h-full">
        <div className="bg-white h-full rounded-[32px] shadow-sm overflow-hidden flex flex-col relative border border-gray-100/60 ring-1 ring-gray-900/5">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
