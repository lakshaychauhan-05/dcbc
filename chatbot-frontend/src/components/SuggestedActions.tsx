import React from 'react';
import {
  CalendarDaysIcon,
  ClockIcon,
  UserGroupIcon,
  ArrowPathIcon,
  XCircleIcon,
  ClipboardDocumentListIcon,
} from '@heroicons/react/24/outline';

interface SuggestedActionsProps {
  actions: string[];
  onActionSelect: (action: string) => void;
}

interface ActionConfig {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  gradient: string;
  textColor: string;
  borderColor: string;
  bgColor: string;
}

const SuggestedActions: React.FC<SuggestedActionsProps> = ({ actions, onActionSelect }) => {
  const actionConfigs: Record<string, ActionConfig> = {
    'book_appointment': {
      label: 'Book Appointment',
      icon: CalendarDaysIcon,
      gradient: 'from-cyan-500 to-cyan-600',
      textColor: 'text-cyan-700',
      borderColor: 'border-cyan-200',
      bgColor: 'bg-cyan-50 hover:bg-cyan-100',
    },
    'check_availability': {
      label: 'Check Availability',
      icon: ClockIcon,
      gradient: 'from-indigo-500 to-indigo-600',
      textColor: 'text-indigo-700',
      borderColor: 'border-indigo-200',
      bgColor: 'bg-indigo-50 hover:bg-indigo-100',
    },
    'get_doctor_info': {
      label: 'Doctor Info',
      icon: UserGroupIcon,
      gradient: 'from-emerald-500 to-emerald-600',
      textColor: 'text-emerald-700',
      borderColor: 'border-emerald-200',
      bgColor: 'bg-emerald-50 hover:bg-emerald-100',
    },
    'reschedule_appointment': {
      label: 'Reschedule',
      icon: ArrowPathIcon,
      gradient: 'from-amber-500 to-amber-600',
      textColor: 'text-amber-700',
      borderColor: 'border-amber-200',
      bgColor: 'bg-amber-50 hover:bg-amber-100',
    },
    'cancel_appointment': {
      label: 'Cancel',
      icon: XCircleIcon,
      gradient: 'from-rose-500 to-rose-600',
      textColor: 'text-rose-700',
      borderColor: 'border-rose-200',
      bgColor: 'bg-rose-50 hover:bg-rose-100',
    },
    'get_my_appointments': {
      label: 'My Appointments',
      icon: ClipboardDocumentListIcon,
      gradient: 'from-slate-500 to-slate-600',
      textColor: 'text-slate-700',
      borderColor: 'border-slate-200',
      bgColor: 'bg-slate-50 hover:bg-slate-100',
    },
  };

  const getActionConfig = (action: string): ActionConfig => {
    return actionConfigs[action] || {
      label: action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      icon: CalendarDaysIcon,
      gradient: 'from-slate-500 to-slate-600',
      textColor: 'text-slate-700',
      borderColor: 'border-slate-200',
      bgColor: 'bg-slate-50 hover:bg-slate-100',
    };
  };

  if (actions.length === 0) return null;

  return (
    <div className="px-4 py-3 bg-slate-50/50 border-t border-slate-100">
      <p className="text-[11px] text-slate-500 mb-2 font-medium uppercase tracking-wide">
        Quick Actions
      </p>
      <div className="flex flex-wrap gap-2">
        {actions.map((action, index) => {
          const config = getActionConfig(action);
          const IconComponent = config.icon;

          return (
            <button
              key={index}
              onClick={() => onActionSelect(config.label.toLowerCase())}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 hover:scale-105 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-cyan-500 ${config.bgColor} ${config.borderColor} ${config.textColor}`}
            >
              <IconComponent className="w-3.5 h-3.5" />
              <span>{config.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default SuggestedActions;
