import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { runClassification, getProject, getRuleSets } from "../api";
import { CheckCircle2, XCircle, HelpCircle, Loader2, ArrowLeft, Network } from "lucide-react";

export const RuleTreeView = ({ node }: { node: any }) => {
  if (!node) return null;
  if (node.type === "rule") {
    return (
      <div className="bg-neutral-800/80 border border-neutral-700/50 p-2 rounded-md inline-flex items-center gap-2 text-sm shadow-sm hover:border-neutral-600 transition-colors">
        <span className="text-indigo-300 font-mono px-1.5 py-0.5 bg-indigo-950/50 rounded">{node.field}</span>
        <span className="text-neutral-400 font-bold text-xs">{node.operator}</span>
        <span className="text-emerald-300 font-mono px-1.5 py-0.5 bg-emerald-950/50 rounded">"{node.value}"</span>
      </div>
    );
  }
  
  if (node.type === "group" && (!node.rules || node.rules.length === 0)) {
    return <span className="text-neutral-600 italic text-sm">Empty Condition Group</span>;
  }
  
  return (
    <div className="border-l-2 border-indigo-500/30 pl-4 py-2 mt-2 relative">
      <div className="absolute -left-[11px] top-3 w-[20px] h-[20px] rounded bg-indigo-900 border border-indigo-500/50 flex items-center justify-center text-[9px] font-bold text-indigo-200">
        {node.condition}
      </div>
      <div className="flex flex-col gap-2 ml-4">
        {node.rules?.map((r: any, i: number) => <RuleTreeView key={i} node={r} />)}
      </div>
    </div>
  );
};

export function ProjectResults() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [results, setResults] = useState<{ summary: any; rows: any[] } | null>(null);
  const [project, setProject] = useState<any>(null);
  const [ruleAst, setRuleAst] = useState<any>(null);

  useEffect(() => {
    fetchData();
  }, [id]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [projRes, classRes, rulesRes] = await Promise.all([
        getProject(Number(id)),
        runClassification(Number(id)),
        getRuleSets(Number(id))
      ]);
      setProject(projRes.data);
      setResults(classRes.data);
      if (rulesRes.data.length > 0) {
        const latest = rulesRes.data.reduce((prev: any, current: any) => (prev.version_no > current.version_no) ? prev : current);
        if (latest.ast_json) setRuleAst(latest.ast_json);
      }
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || "Failed to run classification. Ensure you have mapped datasets and columns.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] text-neutral-400">
        <Loader2 className="w-12 h-12 mb-4 animate-spin text-indigo-500" />
        <h2 className="text-xl font-semibold text-white mb-2">Running Classification Engine...</h2>
        <p>Combining datasets and evaluating your logic rules. This might take a moment.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="bg-red-900/20 border border-red-900 rounded-xl p-6 text-center">
          <h2 className="text-xl font-semibold text-red-500 mb-2">Classification Failed</h2>
          <p className="text-red-400 mb-6">{error}</p>
          <Link to={`/project/${id}/rules`} className="bg-neutral-800 text-white px-5 py-2.5 rounded-lg flex items-center justify-center gap-2 font-medium w-fit mx-auto hover:bg-neutral-700 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Go back and fix setup
          </Link>
        </div>
      </div>
    );
  }

  if (!results) return null;

  const summary = results.summary || {};
  const total = Object.values(summary).reduce((a: any, b: any) => a + b, 0) as number;
  const getPct = (cat: string) => total > 0 ? Math.round(((summary[cat] || 0) / total) * 100) : 0;

  const tableHeaders = results.rows.length > 0 ? Object.keys(results.rows[0]) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-neutral-800">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            Classification Results
          </h1>
          <p className="text-neutral-400 mt-2">Dashboard for {project?.name || "Project"}. Evaluated {total} rows.</p>
        </div>
        <Link to={`/project/${id}/rules`} className="bg-neutral-800 hover:bg-neutral-700 text-white px-5 py-2.5 rounded-lg flex items-center gap-2 font-medium transition-colors">
          <ArrowLeft className="w-4 h-4" /> Edit Rules
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex flex-col items-center justify-center shadow-sm">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mb-3" />
          <h3 className="text-4xl font-bold text-white mb-1">{summary["Must Have"] || 0}</h3>
          <p className="font-medium text-emerald-500">Must Have</p>
          <p className="text-neutral-500 text-sm mt-1">{getPct("Must Have")}% of total</p>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex flex-col items-center justify-center shadow-sm">
          <HelpCircle className="w-10 h-10 text-teal-500 mb-3" />
          <h3 className="text-4xl font-bold text-white mb-1">{summary["Good to Have"] || 0}</h3>
          <p className="font-medium text-teal-500">Good to Have</p>
          <p className="text-neutral-500 text-sm mt-1">{getPct("Good to Have")}% of total</p>
        </div>
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex flex-col items-center justify-center shadow-sm">
          <XCircle className="w-10 h-10 text-neutral-500 mb-3" />
          <h3 className="text-4xl font-bold text-white mb-1">{summary["Not Needed"] || 0}</h3>
          <p className="font-medium text-neutral-400">Not Needed</p>
          <p className="text-neutral-500 text-sm mt-1">{getPct("Not Needed")}% of total</p>
        </div>
      </div>

      {ruleAst && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-sm overflow-hidden flex flex-col md:flex-row">
          <div className="flex-1 p-6 border-b md:border-b-0 md:border-r border-neutral-800">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
              <Network className="text-emerald-500 w-5 h-5" /> Must Have Logic Tree
            </h3>
            <div className="bg-neutral-950 rounded-lg p-4 border border-neutral-800 overflow-x-auto">
               <RuleTreeView node={ruleAst.mustHave} />
            </div>
          </div>
          <div className="flex-1 p-6">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
              <Network className="text-teal-500 w-5 h-5" /> Good to Have Logic Tree
            </h3>
            <div className="bg-neutral-950 rounded-lg p-4 border border-neutral-800 overflow-x-auto">
               <RuleTreeView node={ruleAst.goodToHave} />
            </div>
          </div>
        </div>
      )}

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl shadow-sm overflow-hidden">
        <div className="p-5 border-b border-neutral-800">
          <h3 className="text-lg font-semibold text-white">Row Level Output Preview</h3>
          <p className="text-sm text-neutral-400 mt-1">Showing first 1,000 evaluated records.</p>
        </div>
        <div className="overflow-x-auto w-full max-h-[600px] overflow-y-auto">
          <table className="w-full text-left text-sm text-neutral-300">
            <thead className="text-xs uppercase bg-neutral-950 text-neutral-400 sticky top-0 z-10 border-b border-neutral-800 shadow-sm">
              <tr>
                {tableHeaders.map((h) => (
                  <th key={h} className="px-6 py-4 font-semibold whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {results.rows.map((row, i) => (
                <tr key={i} className="hover:bg-neutral-800/50 transition-colors">
                  {tableHeaders.map((h) => (
                    <td key={h} className="px-6 py-3 whitespace-nowrap">
                      {h === "Classification" ? (
                        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                          row[h] === 'Must Have' ? 'bg-emerald-500/20 text-emerald-400' :
                          row[h] === 'Good to Have' ? 'bg-teal-500/20 text-teal-400' :
                          'bg-neutral-800 text-neutral-400'
                        }`}>
                          {row[h]}
                        </span>
                      ) : (
                        row[h]
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {results.rows.length === 0 && (
             <div className="p-8 text-center text-neutral-500">No data found to display.</div>
          )}
        </div>
      </div>
    </div>
  );
}
