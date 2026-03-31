import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { createRuleSet, getRuleSets } from "../api";
import { Plus, Trash, Save, Network, Play, CheckCircle } from "lucide-react";

type RuleNode = {
  id: string;
  type: "group" | "rule";
  condition?: "AND" | "OR" | "NOT";
  rules?: RuleNode[];
  field?: string;
  operator?: string;
  value?: string;
};

const generateId = () => Math.random().toString(36).substr(2, 9);

const RuleGroup = ({ node, updateNode, removeNode }: { node: RuleNode; updateNode: (n: RuleNode) => void; removeNode: () => void }) => {
  const addRule = () => {
    updateNode({
      ...node,
      rules: [...(node.rules || []), { id: generateId(), type: "rule", field: "", operator: "=", value: "" }]
    });
  };

  const addGroup = () => {
    updateNode({
      ...node,
      rules: [...(node.rules || []), { id: generateId(), type: "group", condition: "AND", rules: [] }]
    });
  };

  const updateChild = (id: string, updated: RuleNode) => {
    updateNode({ ...node, rules: node.rules?.map(r => r.id === id ? updated : r) });
  };

  const removeChild = (id: string) => {
    updateNode({ ...node, rules: node.rules?.filter(r => r.id !== id) });
  };

  return (
    <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-4 ml-2 mb-4 relative">
      <div className="flex items-center gap-3 mb-4">
        <select 
          value={node.condition} 
          onChange={(e) => updateNode({ ...node, condition: e.target.value as any })}
          className="bg-neutral-950 border border-neutral-700 text-sm rounded px-2 py-1 text-white focus:outline-none"
        >
          <option value="AND">AND</option>
          <option value="OR">OR</option>
          <option value="NOT">NOT</option>
        </select>
        <button onClick={addRule} className="text-sm bg-indigo-900/50 text-indigo-400 px-3 py-1 rounded hover:bg-indigo-900 transition-colors flex items-center gap-1"><Plus className="w-3 h-3"/> Rule</button>
        <button onClick={addGroup} className="text-sm bg-neutral-800 text-neutral-300 px-3 py-1 rounded hover:bg-neutral-700 transition-colors flex items-center gap-1"><Network className="w-3 h-3"/> Group</button>
        {removeNode && <button onClick={removeNode} className="ml-auto text-neutral-500 hover:text-red-400 p-1"><Trash className="w-4 h-4" /></button>}
      </div>
      
      <div className="pl-4 border-l-2 border-neutral-800 space-y-3">
        {node.rules?.map((child) => (
          child.type === "group" ? 
            <RuleGroup key={child.id} node={child} updateNode={(n) => updateChild(child.id, n)} removeNode={() => removeChild(child.id)} /> :
            <RuleItem key={child.id} node={child} updateNode={(n) => updateChild(child.id, n)} removeNode={() => removeChild(child.id)} />
        ))}
        {node.rules?.length === 0 && <span className="text-neutral-600 text-sm italic">Empty group</span>}
      </div>
    </div>
  );
};

const RuleItem = ({ node, updateNode, removeNode }: { node: RuleNode; updateNode: (n: RuleNode) => void; removeNode: () => void }) => {
  return (
    <div className="flex items-center gap-2 bg-neutral-950 p-2 rounded border border-neutral-800">
      <input 
        type="text" 
        placeholder="Dataset.Column (e.g. Criticality.Rating)" 
        value={node.field} 
        onChange={(e) => updateNode({ ...node, field: e.target.value })}
        className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-white focus:outline-none flex-1"
      />
      <select 
        value={node.operator} 
        onChange={(e) => updateNode({ ...node, operator: e.target.value })}
        className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-white focus:outline-none"
      >
        <option value="=">=</option>
        <option value="!=">!=</option>
        <option value="IN">IN</option>
        <option value="CONTAINS">CONTAINS</option>
        <option value=">">&gt;</option>
        <option value="<">&lt;</option>
      </select>
      <input 
        type="text" 
        placeholder="Value" 
        value={node.value} 
        onChange={(e) => updateNode({ ...node, value: e.target.value })}
        className="bg-neutral-900 border border-neutral-700 rounded px-2 py-1 text-sm text-white focus:outline-none flex-1"
      />
      <button onClick={removeNode} className="text-neutral-500 hover:text-red-400 p-1 ml-2"><Trash className="w-4 h-4" /></button>
    </div>
  );
};

export function RuleBuilder() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [mustHaveNode, setMustHaveNode] = useState<RuleNode>({ id: generateId(), type: "group", condition: "AND", rules: [] });
  const [goodToHaveNode, setGoodToHaveNode] = useState<RuleNode>({ id: generateId(), type: "group", condition: "AND", rules: [] });
  
  const [activeTab, setActiveTab] = useState<"mustHave" | "goodToHave">("mustHave");
  const [isSaving, setIsSaving] = useState(false);
  const [ruleSets, setRuleSets] = useState<any[]>([]);

  useEffect(() => {
    fetchRules();
  }, [id]);

  const fetchRules = async () => {
    try {
      const res = await getRuleSets(Number(id));
      setRuleSets(res.data);
      if (res.data.length > 0) {
        // Load latest
        const latest = res.data.reduce((prev: any, current: any) => (prev.version_no > current.version_no) ? prev : current);
        if (latest.ast_json) {
          if (latest.ast_json.mustHave) setMustHaveNode(latest.ast_json.mustHave);
          if (latest.ast_json.goodToHave) setGoodToHaveNode(latest.ast_json.goodToHave);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const ast_json = {
        mustHave: mustHaveNode,
        goodToHave: goodToHaveNode
      };
      await createRuleSet(Number(id), { ast_json, status: "active" });
      await fetchRules();
    } catch (err) {
      console.error(err);
      alert("Failed to save rule.");
    } finally {
      setIsSaving(false);
    }
  };
  
  const handleRunClassification = async () => {
    // First save the current state just in case
    await handleSave();
    navigate(`/project/${id}/results`);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Logic Rules</h1>
          <p className="text-neutral-400 mt-2">Build abstract syntax tree rules for classifications.</p>
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => navigate(`/project/${id}`)}
            className="bg-neutral-800 hover:bg-neutral-700 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors"
          >
            Back to Project
          </button>
          <button 
            onClick={handleSave}
            disabled={isSaving}
            className="bg-neutral-800 border-neutral-700 hover:bg-neutral-700 border disabled:opacity-50 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors"
          >
            <Save className="w-5 h-5"/>
            {isSaving ? "Saving..." : "Save Rule"}
          </button>
          <button 
            onClick={handleRunClassification}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors shadow-lg shadow-indigo-900/20"
          >
            <Play className="w-5 h-5"/>
            Run Classification
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-neutral-950 border border-neutral-800 rounded-xl shadow-sm overflow-hidden min-h-[600px] flex flex-col">
          <div className="flex bg-neutral-900 border-b border-neutral-800 p-2 gap-2">
            <button 
              onClick={() => setActiveTab("mustHave")}
              className={`flex-1 py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all ${activeTab === 'mustHave' ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30' : 'text-neutral-400 hover:bg-neutral-800'}`}
            >
               Must Have Logic
            </button>
            <button 
              onClick={() => setActiveTab("goodToHave")}
              className={`flex-1 py-3 px-4 rounded-lg font-medium flex items-center justify-center gap-2 transition-all ${activeTab === 'goodToHave' ? 'bg-teal-600/20 text-teal-400 border border-teal-500/30' : 'text-neutral-400 hover:bg-neutral-800'}`}
            >
               Good to Have Logic
            </button>
          </div>
          
          <div className="p-6 overflow-y-auto flex-1">
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Network className="w-5 h-5" /> 
              {activeTab === 'mustHave' ? "Must Have - AST Generator" : "Good to Have - AST Generator"}
            </h2>
            <div className="mb-6 p-3 bg-neutral-900/50 border border-neutral-800 rounded-lg text-sm text-neutral-400">
              <span className="text-indigo-400 font-medium">Evaluation Order:</span> Rows matching "Must Have" logic supersede "Good to Have". Rows matching neither are classified as "Not Needed".
            </div>
            
            {activeTab === 'mustHave' ? (
              <RuleGroup node={mustHaveNode} updateNode={setMustHaveNode} removeNode={() => {}} />
            ) : (
              <RuleGroup node={goodToHaveNode} updateNode={setGoodToHaveNode} removeNode={() => {}} />
            )}
          </div>
        </div>
        
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 h-fit sticky top-6">
          <h3 className="text-lg font-semibold mb-3">AST Preview</h3>
          <pre className="text-xs text-indigo-300 font-mono bg-neutral-950 p-4 rounded-lg overflow-x-auto border border-neutral-800 h-[450px] overflow-y-auto">
            {JSON.stringify({ mustHave: mustHaveNode, goodToHave: goodToHaveNode }, null, 2)}
          </pre>
          <div className="mt-4 pt-4 border-t border-neutral-800 flex justify-between items-center">
             <p className="text-sm text-neutral-400">Rule Versions: <span className="text-white font-semibold">{ruleSets.length}</span></p>
             {ruleSets.length > 0 && <span className="text-xs bg-emerald-900/30 text-emerald-400 px-2 py-1 rounded-full border border-emerald-800/50 flex items-center gap-1"><CheckCircle className="w-3 h-3"/> Active</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
