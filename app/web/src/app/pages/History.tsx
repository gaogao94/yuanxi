import { Search, Filter, FileText, Presentation, CheckSquare, Download } from "lucide-react";
import { clsx } from "clsx";

export function History() {
  const items: any[] = [];

  return (
    <div className="flex-1 flex flex-col h-full bg-white relative">
      <header className="h-[72px] border-b border-gray-100 flex items-center justify-between px-8">
        <h1 className="text-xl font-medium text-gray-800">历史文件与待办</h1>
        <div className="flex items-center gap-3">
           <div className="relative group">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2 group-focus-within:text-blue-500 transition-colors" />
              <input 
                type="text" 
                placeholder="搜索文件..." 
                className="pl-9 pr-4 py-2 bg-[#f4f7fc] border border-transparent hover:bg-gray-100 focus:bg-white focus:border-blue-200 rounded-full text-sm focus:outline-none focus:ring-[3px] focus:ring-blue-100/50 w-64 transition-all text-gray-700" 
              />
           </div>
           <button className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-200 hover:bg-gray-50 rounded-full transition-colors shadow-sm">
              <Filter className="w-4 h-4" /> 筛选
           </button>
        </div>
      </header>
      
      <div className="flex-1 overflow-y-auto p-8">
         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {items.map(item => (
               <div key={item.id} className="border border-gray-100 rounded-3xl p-5 hover:shadow-lg hover:border-gray-200 transition-all duration-300 group flex flex-col justify-between h-[150px] relative bg-white overflow-hidden cursor-pointer">
                  <div className="flex items-start justify-between">
                     <div className={clsx("w-12 h-12 rounded-2xl flex items-center justify-center shrink-0", item.bg, item.color)}>
                        <item.icon className="w-6 h-6" />
                     </div>
                     <button className="w-9 h-9 rounded-full bg-gray-50 text-gray-400 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-[#e8f0fe] hover:text-[#1a73e8]">
                        <Download className="w-4 h-4" />
                     </button>
                  </div>
                  <div className="mt-4">
                     <h3 className="text-[15px] font-medium text-gray-800 truncate mb-1.5" title={item.title}>{item.title}</h3>
                     <div className="flex items-center justify-between text-xs text-gray-500 font-medium">
                        <span>{item.date}</span>
                        <span className="bg-gray-50 px-2 py-0.5 rounded-md">{item.size}</span>
                     </div>
                  </div>
               </div>
            ))}
         </div>
      </div>
    </div>
  );
}
