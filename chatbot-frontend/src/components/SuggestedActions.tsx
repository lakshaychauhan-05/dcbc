import React from 'react';

interface SuggestedActionsProps {
  actions: string[];
  onActionSelect: (action: string) => void;
}

const SuggestedActions: React.FC<SuggestedActionsProps> = ({ actions, onActionSelect }) => {
  const getActionLabel = (action: string): string => {
    const labels: Record<string, string> = {
      'book_appointment': 'Book Appointment',
      'check_availability': 'Check Availability',
      'get_doctor_info': 'Doctor Information',
      'reschedule_appointment': 'Reschedule',
      'cancel_appointment': 'Cancel Appointment',
      'get_my_appointments': 'My Appointments',
    };
    return labels[action] || action.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getActionColor = (action: string): string => {
    const colors: Record<string, string> = {
      'book_appointment': 'bg-accent-50 hover:bg-accent-100 text-accent-700 border-accent-200',
      'check_availability': 'bg-secondary-50 hover:bg-secondary-100 text-secondary-700 border-secondary-200',
      'get_doctor_info': 'bg-primary-50 hover:bg-primary-100 text-primary-600 border-primary-200',
      'reschedule_appointment': 'bg-amber-50 hover:bg-amber-100 text-amber-700 border-amber-200',
      'cancel_appointment': 'bg-rose-50 hover:bg-rose-100 text-rose-700 border-rose-200',
      'get_my_appointments': 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200',
    };
    return colors[action] || 'bg-gray-100 hover:bg-gray-200 text-gray-800 border-gray-300';
  };

  if (actions.length === 0) return null;

  return (
    <div className="border-t border-gray-200 p-3 bg-gray-50">
      <div className="text-xs text-gray-600 mb-2 font-medium">Suggested actions:</div>
      <div className="flex flex-wrap gap-2">
        {actions.map((action, index) => (
          <button
            key={index}
            onClick={() => onActionSelect(getActionLabel(action).toLowerCase())}
            className={`px-3 py-1 text-sm rounded-full border transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 ${getActionColor(action)}`}
          >
            {getActionLabel(action)}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SuggestedActions;