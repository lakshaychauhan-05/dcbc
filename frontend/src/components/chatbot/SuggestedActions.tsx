interface SuggestedActionsProps {
  actions: string[];
  onActionSelect: (action: string) => void;
}

const SuggestedActions = ({ actions, onActionSelect }: SuggestedActionsProps) => {
  if (actions.length === 0) return null;

  return (
    <div className="px-4 pb-2 bg-white border-t border-slate-100">
      <p className="text-xs font-medium text-slate-400 mb-2">Suggested responses</p>
      <div className="flex flex-wrap gap-2">
        {actions.map((action, index) => (
          <button
            key={index}
            onClick={() => onActionSelect(action)}
            className="px-3 py-1.5 text-sm rounded-full bg-gradient-to-r from-cyan-50 to-blue-50 text-cyan-700 border border-cyan-200 hover:from-cyan-100 hover:to-blue-100 hover:border-cyan-300 transition-all duration-200"
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedActions;
