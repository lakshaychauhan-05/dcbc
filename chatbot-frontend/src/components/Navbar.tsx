import React, { useState } from 'react';
import {
  Bars3Icon,
  XMarkIcon,
  UserGroupIcon,
  ShieldCheckIcon,
  CalendarDaysIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline';

const Navbar: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const portalLinks = [
    {
      name: 'Doctor Portal',
      href: 'http://localhost:5175',
      icon: UserGroupIcon,
      description: 'Manage appointments & patients',
      gradient: 'from-cyan-500 to-blue-600',
      hoverGradient: 'hover:from-cyan-600 hover:to-blue-700'
    },
    {
      name: 'Admin Portal',
      href: 'http://localhost:5500',
      icon: ShieldCheckIcon,
      description: 'System administration',
      gradient: 'from-purple-500 to-indigo-600',
      hoverGradient: 'hover:from-purple-600 hover:to-indigo-700'
    }
  ];

  const openPortal = (href: string) => {
    window.open(href, '_blank', 'noopener,noreferrer');
  };

  return (
    <nav className="glass-dark border-b border-white/10 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/25">
                <CalendarDaysIcon className="w-6 h-6 text-white" />
              </div>
              <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-900"></span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                MediBook
              </h1>
              <p className="text-xs text-slate-400 -mt-0.5">AI Appointment System</p>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-3">
            {portalLinks.map((link) => (
              <button
                key={link.name}
                onClick={() => openPortal(link.href)}
                className={`group flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r ${link.gradient} ${link.hoverGradient} text-white font-medium text-sm transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-cyan-500/25`}
              >
                <link.icon className="w-4 h-4" />
                <span>{link.name}</span>
                <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5 opacity-0 -ml-1 group-hover:opacity-100 group-hover:ml-0 transition-all duration-200" />
              </button>
            ))}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              {isMobileMenuOpen ? (
                <XMarkIcon className="w-6 h-6" />
              ) : (
                <Bars3Icon className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="md:hidden pb-4 pt-2 border-t border-white/10 mt-2 animate-slide-up">
            <div className="space-y-2">
              {portalLinks.map((link) => (
                <button
                  key={link.name}
                  onClick={() => {
                    openPortal(link.href);
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r ${link.gradient} text-white transition-all duration-200 active:scale-98`}
                >
                  <div className="w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center">
                    <link.icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 text-left">
                    <p className="font-medium">{link.name}</p>
                    <p className="text-xs text-white/70">{link.description}</p>
                  </div>
                  <ArrowTopRightOnSquareIcon className="w-4 h-4 opacity-70" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
