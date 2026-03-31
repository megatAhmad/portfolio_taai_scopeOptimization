import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { getProject, getDatasets, uploadDataset, getMapping, createMapping, deleteDataset } from "../api";
import { UploadCloud, FileText, Database, GitMerge, Settings, CheckCircle2, Trash2 } from "lucide-react";

export function ProjectDetails() {
  const { id } = useParams();
  const [project, setProject] = useState<any>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  
  const [expandedDataset, setExpandedDataset] = useState<number | null>(null);
  const [mappingForm, setMappingForm] = useState<{equipment_id_col: string, category_col: string, mapping_rules: any[], derived_column_name: string, data_type: string, default_output: string, empty_output: string}>({ equipment_id_col: "", category_col: "", mapping_rules: [], derived_column_name: "", data_type: "text", default_output: "N/A", empty_output: "N/A" });
  const [useAdvanced, setUseAdvanced] = useState(false);
  const [isSavingMapping, setIsSavingMapping] = useState(false);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      const pRes = await getProject(Number(id));
      setProject(pRes.data);
      const dRes = await getDatasets(Number(id));
      setDatasets(dRes.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadClick = () => {
    fileRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("name", file.name);
      
      // If this is the first dataset, let's treat it as the original
      fd.append("is_original", datasets.length === 0 ? "true" : "false");

      await uploadDataset(Number(id), fd);
      await fetchData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleConfigureClick = async (dataset: any) => {
    if (expandedDataset === dataset.dataset_id) {
      setExpandedDataset(null);
      return;
    }
    setExpandedDataset(dataset.dataset_id);
    setMappingForm({ equipment_id_col: "", category_col: "", mapping_rules: [], derived_column_name: "", data_type: "text", default_output: "N/A", empty_output: "N/A" });
    setUseAdvanced(false);
    try {
      const res = await getMapping(Number(id), dataset.dataset_id);
      const rules = res.data.mapping_rules || [];
      setMappingForm({
        equipment_id_col: res.data.equipment_id_col || "",
        category_col: res.data.category_col || "",
        mapping_rules: rules,
        derived_column_name: res.data.derived_column_name || "",
        data_type: res.data.data_type || "text",
        default_output: res.data.default_output || "N/A",
        empty_output: res.data.empty_output || "N/A"
      });
      setUseAdvanced(rules.length > 0);
    } catch (err) {
      // It's normal if mapping doesn't exist yet
    }
  };

  const handleSaveMapping = async (datasetId: number) => {
    setIsSavingMapping(true);
    try {
      const payload = {
        ...mappingForm,
        mapping_rules: useAdvanced ? mappingForm.mapping_rules : []
      };
      await createMapping(Number(id), datasetId, payload);
      setExpandedDataset(null);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSavingMapping(false);
    }
  };

  const handleDeleteDataset = async (datasetId: number) => {
    if (!window.confirm("Are you sure you want to delete this dataset? This will remove its files and mappings.")) return;
    try {
      await deleteDataset(Number(id), datasetId);
      await fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  if (!project) return <div className="p-8 text-neutral-400">Loading workspace...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Database className="w-8 h-8 text-indigo-400" />
            {project.name}
          </h1>
          <p className="text-neutral-400 mt-2">Upload datasets and map column schemas.</p>
        </div>
        <div className="flex gap-3">
          <Link to={`/project/${id}/rules`} className="bg-neutral-800 hover:bg-neutral-700 border border-neutral-700 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors">
            <GitMerge className="w-5 h-5 text-purple-400" /> Manage Rules
          </Link>
          <button 
            onClick={handleUploadClick}
            disabled={isUploading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors disabled:opacity-50"
          >
            <UploadCloud className="w-5 h-5" /> 
            {isUploading ? "Uploading..." : "Upload Dataset"}
          </button>
          <input type="file" ref={fileRef} className="hidden" onChange={handleFileChange} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {datasets.length === 0 && (
          <div className="text-center py-20 bg-neutral-900 border border-neutral-800 rounded-xl text-neutral-500 shadow-inner">
            <UploadCloud className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p className="text-lg">No datasets uploaded yet.</p>
            <p className="text-sm mt-1">First dataset uploaded will act as the canonical source.</p>
          </div>
        )}
        
        {datasets.map(d => (
          <div key={d.dataset_id} className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-sm overflow-hidden">
            <div className="p-5 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${d.is_original ? "bg-indigo-900/50 text-indigo-400" : "bg-neutral-800 text-neutral-400"}`}>
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg text-white flex items-center gap-2">
                    {d.name} {d.is_original && <span className="text-[10px] uppercase font-bold tracking-wider bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded-full">Canonical</span>}
                  </h3>
                  <p className="text-sm text-neutral-500 mt-1">
                    Rows: <span className="text-neutral-300 font-mono">{d.dataset_schema?.total_rows || '?'}</span> 
                    <span className="mx-2">•</span> 
                    Columns: <span className="text-neutral-300 font-mono">{d.dataset_schema?.columns?.length || '?'}</span>
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => handleDeleteDataset(d.dataset_id)}
                  className="flex items-center justify-center p-2 text-neutral-500 hover:text-red-400 bg-neutral-800/50 hover:bg-neutral-800 border border-neutral-700 rounded-md transition-colors" 
                  title="Delete Dataset"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button 
                  onClick={() => handleConfigureClick(d)}
                  className="flex items-center gap-2 text-sm font-medium hover:text-white px-4 py-2 border border-neutral-700 rounded-md bg-neutral-800/50 hover:bg-neutral-800 transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  {expandedDataset === d.dataset_id ? "Close Mapping" : "Configure Mapping"}
                </button>
              </div>
            </div>
            
            {expandedDataset === d.dataset_id && (
              <div className="bg-neutral-950 p-5 border-t border-neutral-800">
                <h4 className="text-sm font-semibold text-neutral-300 mb-4">Column Mapping Configuration</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl">
                  <div>
                    <label className="block text-sm font-medium text-neutral-400 mb-1">Equipment ID Column</label>
                    <select 
                      className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      value={mappingForm.equipment_id_col}
                      onChange={(e) => setMappingForm({...mappingForm, equipment_id_col: e.target.value})}
                    >
                      <option value="">Select column...</option>
                      {d.dataset_schema?.columns?.map((c: any) => (
                        <option key={c.name} value={c.name}>{c.name}</option>
                      ))}
                    </select>
                  </div>
                  
                  {!d.is_original && (
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-sm font-medium text-neutral-400">{useAdvanced ? "Source Column" : "Category Column"}</label>
                        <button 
                          onClick={() => setUseAdvanced(!useAdvanced)} 
                          className={`text-xs px-2 py-0.5 rounded border transition-colors ${useAdvanced ? 'bg-indigo-900/50 text-indigo-400 border-indigo-500/50' : 'bg-neutral-800 text-neutral-400 border-neutral-700'}`}
                        >
                          Advanced Rules
                        </button>
                      </div>
                      <select 
                        className="w-full bg-neutral-900 border border-neutral-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        value={mappingForm.category_col}
                        onChange={(e) => setMappingForm({...mappingForm, category_col: e.target.value})}
                      >
                        <option value="">Select column...</option>
                        {d.dataset_schema?.columns?.map((c: any) => (
                          <option key={c.name} value={c.name}>{c.name}</option>
                        ))}
                      </select>
                    </div>
                  )}

                  {useAdvanced && !d.is_original && (
                    <div className="col-span-1 md:col-span-2 mt-2 p-5 bg-indigo-950/20 border border-indigo-900/50 rounded-xl">
                       <div className="grid grid-cols-2 gap-4 mb-5">
                         <div>
                           <label className="block text-xs font-semibold text-indigo-300 mb-1">Derived Column Name</label>
                           <input 
                             placeholder="e.g. Age Category" 
                             className="w-full bg-neutral-900 border border-neutral-800 text-white text-sm rounded px-3 py-2 outline-none"
                             value={mappingForm.derived_column_name || ""}
                             onChange={(e) => setMappingForm({...mappingForm, derived_column_name: e.target.value})}
                           />
                         </div>
                         <div>
                           <label className="block text-xs font-semibold text-indigo-300 mb-1">Data Type for Evaluation</label>
                           <select 
                             className="w-full bg-neutral-900 border border-neutral-800 text-white text-sm rounded px-3 py-2 outline-none"
                             value={mappingForm.data_type || "text"}
                             onChange={(e) => setMappingForm({...mappingForm, data_type: e.target.value})}
                           >
                             <option value="text">Text (String)</option>
                             <option value="numeric">Float / Int (Numeric)</option>
                             <option value="date">Date</option>
                           </select>
                         </div>
                       </div>
                       
                       <div className="flex justify-between items-center mb-4 border-t border-indigo-900/30 pt-4">
                         <div>
                           <h5 className="text-sm font-semibold text-indigo-300">Derived Category Rules</h5>
                           <p className="text-xs text-indigo-300/60 mt-1">Evaluates the Source Column sequentially using the above Data Type.</p>
                         </div>
                         <button 
                           onClick={() => setMappingForm({...mappingForm, mapping_rules: [...mappingForm.mapping_rules, {operator: '>', value: '', output: ''}]})}
                           className="bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 text-xs px-3 py-1.5 rounded transition-colors border border-indigo-500/30"
                         >
                           + Add Rule
                         </button>
                       </div>
                       
                       <div className="space-y-3">
                         {mappingForm.mapping_rules.map((rule, i) => (
                           <div key={i} className="flex gap-2 items-center bg-neutral-900 border border-neutral-800 p-2 rounded-lg">
                             <select 
                               className="bg-neutral-950 text-sm border border-neutral-800 text-white rounded px-2 py-1.5 outline-none"
                               value={rule.operator}
                               onChange={(e) => {
                                 const nr = [...mappingForm.mapping_rules];
                                 nr[i].operator = e.target.value;
                                 setMappingForm({...mappingForm, mapping_rules: nr});
                               }}
                             >
                                <option value=">">&gt;</option>
                                <option value="<">&lt;</option>
                                <option value=">=">&gt;=</option>
                                <option value="<=">&lt;=</option>
                                <option value="=">=</option>
                                <option value="!=">!=</option>
                                <option value="BETWEEN">BETWEEN</option>
                             </select>
                             
                             {rule.operator === "BETWEEN" ? (
                                <div className="flex flex-1 items-center gap-2">
                                  <input 
                                    placeholder="Start" 
                                    className="bg-neutral-950 text-sm border flex-1 border-neutral-800 text-white rounded px-3 py-1.5 outline-none w-full"
                                    value={rule.value} 
                                    onChange={(e) => {
                                      const nr = [...mappingForm.mapping_rules];
                                      nr[i].value = e.target.value;
                                      setMappingForm({...mappingForm, mapping_rules: nr});
                                    }} 
                                  />
                                  <span className="text-neutral-500 text-xs">AND</span>
                                  <input 
                                    placeholder="End" 
                                    className="bg-neutral-950 text-sm border flex-1 border-neutral-800 text-white rounded px-3 py-1.5 outline-none w-full"
                                    value={rule.value_end || ""} 
                                    onChange={(e) => {
                                      const nr = [...mappingForm.mapping_rules];
                                      nr[i].value_end = e.target.value;
                                      setMappingForm({...mappingForm, mapping_rules: nr});
                                    }} 
                                  />
                                </div>
                             ) : (
                               <input 
                                 placeholder="Target condition (e.g. 2024-01-01 or 5.0)" 
                                 className="bg-neutral-950 text-sm border flex-1 border-neutral-800 text-white rounded px-3 py-1.5 outline-none"
                                 value={rule.value}
                                 onChange={(e) => {
                                   const nr = [...mappingForm.mapping_rules];
                                   nr[i].value = e.target.value;
                                   setMappingForm({...mappingForm, mapping_rules: nr});
                                 }}
                               />
                             )}
                             
                             <span className="text-neutral-500 font-mono text-xs text-center w-8">➔</span>
                             <input 
                               placeholder="Output (e.g. Late)" 
                               className="bg-neutral-950 text-sm border flex-[0.5] border-neutral-800 text-emerald-400 rounded px-3 py-1.5 outline-none font-medium"
                               value={rule.output}
                               onChange={(e) => {
                                 const nr = [...mappingForm.mapping_rules];
                                 nr[i].output = e.target.value;
                                 setMappingForm({...mappingForm, mapping_rules: nr});
                               }}
                             />
                             <button 
                               onClick={() => {
                                 const nr = [...mappingForm.mapping_rules];
                                 nr.splice(i, 1);
                                 setMappingForm({...mappingForm, mapping_rules: nr});
                               }}
                               className="text-neutral-500 hover:text-red-400 p-1.5 px-2"
                             >×</button>
                           </div>
                         ))}
                         {mappingForm.mapping_rules.length === 0 && (
                           <div className="text-center p-4 border border-dashed border-indigo-900/50 rounded-lg text-indigo-400/50 text-sm">No rules defined.</div>
                         )}
                       </div>
                       
                       <div className="grid grid-cols-2 gap-4 mt-6 pt-4 border-t border-indigo-900/30">
                         <div>
                           <label className="block text-xs font-semibold text-indigo-300 mb-1">Output when Not Fulfilled (Default)</label>
                           <input 
                             placeholder="e.g. N/A" 
                             className="w-full bg-neutral-900 border border-neutral-800 text-white text-sm rounded px-3 py-2 outline-none"
                             value={mappingForm.default_output}
                             onChange={(e) => setMappingForm({...mappingForm, default_output: e.target.value})}
                           />
                         </div>
                         <div>
                           <label className="block text-xs font-semibold text-indigo-300 mb-1">Output when Empty (No Data)</label>
                           <input 
                             placeholder="e.g. N/A" 
                             className="w-full bg-neutral-900 border border-neutral-800 text-white text-sm rounded px-3 py-2 outline-none"
                             value={mappingForm.empty_output}
                             onChange={(e) => setMappingForm({...mappingForm, empty_output: e.target.value})}
                           />
                         </div>
                       </div>
                    </div>
                  )}
                </div>
                <div className="mt-5 flex justify-end">
                  <button 
                    onClick={() => handleSaveMapping(d.dataset_id)}
                    disabled={isSavingMapping || !mappingForm.equipment_id_col || (!d.is_original && !mappingForm.category_col)}
                    className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-neutral-800 disabled:text-neutral-500 text-white px-5 py-2 rounded-lg flex items-center gap-2 font-medium transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Save Mapping
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
