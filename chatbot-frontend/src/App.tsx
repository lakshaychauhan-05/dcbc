import Navbar from './components/Navbar';
import Chatbot from './components/Chatbot';
import { CalendarDaysIcon, ClockIcon, UserGroupIcon, ShieldCheckIcon, SparklesIcon } from '@heroicons/react/24/outline';
import './App.css';

function App() {
  const features = [
    {
      icon: SparklesIcon,
      title: 'AI-Powered Booking',
      description: 'Natural conversation to book appointments instantly',
      gradient: 'from-cyan-500 to-blue-600'
    },
    {
      icon: CalendarDaysIcon,
      title: 'Smart Scheduling',
      description: 'Find available slots that fit your schedule',
      gradient: 'from-emerald-500 to-teal-600'
    },
    {
      icon: ClockIcon,
      title: '24/7 Availability',
      description: 'Book appointments anytime, anywhere',
      gradient: 'from-purple-500 to-indigo-600'
    }
  ];

  const stats = [
    { value: '50+', label: 'Doctors' },
    { value: '10k+', label: 'Appointments' },
    { value: '98%', label: 'Satisfaction' },
    { value: '24/7', label: 'Support' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-cyan-500/5 to-indigo-500/5 rounded-full blur-3xl"></div>
      </div>

      {/* Navbar */}
      <Navbar />

      {/* Main Content */}
      <main className="relative z-10">
        {/* Hero Section */}
        <section className="py-16 lg:py-24">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-4xl mx-auto">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-cyan-500/10 to-indigo-500/10 border border-cyan-500/20 mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-sm text-cyan-300 font-medium">AI Assistant Online</span>
              </div>

              {/* Main Heading */}
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6">
                <span className="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                  Book Your Medical
                </span>
                <br />
                <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 bg-clip-text text-transparent">
                  Appointments Smarter
                </span>
              </h1>

              {/* Subtitle */}
              <p className="text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
                Experience the future of healthcare scheduling. Our AI assistant helps you find the right doctor and book appointments in seconds.
              </p>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
                <button
                  onClick={() => {
                    const chatButton = document.querySelector('[aria-label="Open chat"]') as HTMLButtonElement;
                    if (chatButton) chatButton.click();
                  }}
                  className="group px-8 py-4 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold text-lg shadow-xl shadow-cyan-500/25 hover:shadow-2xl hover:shadow-cyan-500/30 transition-all duration-300 hover:scale-105 flex items-center gap-2"
                >
                  <SparklesIcon className="w-5 h-5 group-hover:animate-pulse" />
                  Start Booking Now
                </button>
                <a
                  href="http://localhost:5175"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-8 py-4 rounded-2xl border border-slate-600 hover:border-slate-500 text-slate-300 hover:text-white font-semibold text-lg transition-all duration-300 hover:bg-slate-800/50 flex items-center gap-2"
                >
                  <UserGroupIcon className="w-5 h-5" />
                  Doctor Login
                </a>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
                {stats.map((stat, index) => (
                  <div
                    key={index}
                    className="text-center p-4 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm"
                  >
                    <div className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
                      {stat.value}
                    </div>
                    <div className="text-sm text-slate-400 mt-1">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-16 border-t border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-white mb-4">Why Choose MediBook?</h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Our intelligent system makes healthcare accessible and convenient
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="group p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 backdrop-blur-sm transition-all duration-300 hover:bg-white/10"
                >
                  <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300 shadow-lg`}>
                    <feature.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-slate-400">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Portals Section */}
        <section className="py-16 border-t border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-white mb-4">Access Portals</h2>
              <p className="text-slate-400 max-w-2xl mx-auto">
                Quick access to our management systems
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {/* Doctor Portal Card */}
              <a
                href="http://localhost:5175"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-600/10 border border-cyan-500/20 hover:border-cyan-500/40 p-8 transition-all duration-300 hover:scale-[1.02]"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-blue-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mb-6 shadow-xl shadow-cyan-500/25 group-hover:scale-110 transition-transform duration-300">
                    <UserGroupIcon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">Doctor Portal</h3>
                  <p className="text-slate-400 mb-4">Manage your appointments, view patient details, and handle your schedule efficiently.</p>
                  <span className="inline-flex items-center gap-1 text-cyan-400 font-medium group-hover:gap-2 transition-all duration-200">
                    Access Portal
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </span>
                </div>
              </a>

              {/* Admin Portal Card */}
              <a
                href="http://localhost:5500"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-purple-500/10 to-indigo-600/10 border border-purple-500/20 hover:border-purple-500/40 p-8 transition-all duration-300 hover:scale-[1.02]"
              >
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-indigo-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                <div className="relative">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center mb-6 shadow-xl shadow-purple-500/25 group-hover:scale-110 transition-transform duration-300">
                    <ShieldCheckIcon className="w-8 h-8 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">Admin Portal</h3>
                  <p className="text-slate-400 mb-4">System administration, manage doctors, clinics, and monitor overall platform health.</p>
                  <span className="inline-flex items-center gap-1 text-purple-400 font-medium group-hover:gap-2 transition-all duration-200">
                    Access Portal
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </span>
                </div>
              </a>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="py-8 border-t border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center">
                  <CalendarDaysIcon className="w-4 h-4 text-white" />
                </div>
                <span className="text-slate-400 text-sm">MediBook AI Appointment System</span>
              </div>
              <div className="flex items-center gap-6 text-sm text-slate-500">
                <span>Powered by AI</span>
                <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                <span>Secure & HIPAA Compliant</span>
              </div>
            </div>
          </div>
        </footer>
      </main>

      {/* Chatbot Widget */}
      <Chatbot />
    </div>
  );
}

export default App;
