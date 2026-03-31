import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { ProjectsList } from "./pages/ProjectsList";
import { ProjectDetails } from "./pages/ProjectDetails";
import { RuleBuilder } from "./pages/RuleBuilder";
import { ProjectResults } from "./pages/ProjectResults";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-neutral-950 text-neutral-50 flex flex-col font-sans">
        <header className="border-b border-neutral-800 bg-neutral-900 px-6 py-4 flex items-center justify-between">
          <Link to="/" className="text-xl font-bold tracking-tight text-white hover:text-neutral-300 transition-colors">
            ScopeOpti <span className="text-neutral-500 font-normal">| Shutdown Equiment</span>
          </Link>
          <nav className="flex gap-4 text-sm font-medium">
            <Link to="/" className="hover:text-white text-neutral-400 transition-colors">Projects</Link>
          </nav>
        </header>

        <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8">
          <Routes>
             <Route path="/" element={<ProjectsList />} />
             <Route path="/project/:id" element={<ProjectDetails />} />
             <Route path="/project/:id/rules" element={<RuleBuilder />} />
             <Route path="/project/:id/results" element={<ProjectResults />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
