import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getProjects, createProject, deleteProject } from "../api";
import { PlusCircle, Folder, Trash2 } from "lucide-react";

export function ProjectsList() {
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState("");

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await getProjects();
      setProjects(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      await createProject({ name: newProjectName });
      setNewProjectName("");
      fetchProjects();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.preventDefault(); // prevent link click
    if (!window.confirm("Are you sure you want to delete this project? This will permanently delete all rules, datasets, and mappings.")) return;
    try {
      await deleteProject(id);
      fetchProjects();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-neutral-400 mt-2">Manage your shutdown equipment prioritization workspaces.</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
          <PlusCircle className="text-indigo-400 w-5 h-5" /> Create New Project
        </h2>
        <form onSubmit={handleCreate} className="flex gap-4 max-w-lg">
          <input
            type="text"
            className="flex-1 bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
            placeholder="Project Name..."
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
          />
          <button
            type="submit"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
          >
            Create
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((p: any) => (
          <Link
            key={p.project_id}
            to={`/project/${p.project_id}`}
            className="group block bg-neutral-900 border border-neutral-800 hover:border-indigo-500 rounded-xl p-6 transition-all shadow-sm hover:shadow-indigo-900/20"
          >
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-3 text-lg font-semibold text-white mb-2 group-hover:text-indigo-400 transition-colors">
                <Folder className="w-5 h-5 text-neutral-500 group-hover:text-indigo-400" />
                {p.name}
              </div>
              <button 
                onClick={(e) => handleDelete(e, p.project_id)} 
                className="text-neutral-500 hover:text-red-400 hover:bg-red-950/30 p-2 -mr-2 -mt-2 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <p className="text-sm text-neutral-500">
              Created at: {new Date(p.created_at).toLocaleDateString()}
            </p>
          </Link>
        ))}
      </div>
      
      {projects.length === 0 && (
        <div className="text-center py-16 bg-neutral-900 border-2 border-dashed border-neutral-800 rounded-xl text-neutral-500">
          No projects yet. Create one to get started!
        </div>
      )}
    </div>
  );
}
