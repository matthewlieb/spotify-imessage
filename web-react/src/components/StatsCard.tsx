import React from 'react';
import { BarChart3, CheckCircle, XCircle, Clock, Activity } from 'lucide-react';
import { AppStats } from '../types';

interface StatsCardProps {
  stats: AppStats;
}

export const StatsCard: React.FC<StatsCardProps> = ({ stats }) => {
  const statItems = [
    {
      label: 'Total Jobs',
      value: stats.total_jobs,
      icon: BarChart3,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
    },
    {
      label: 'Completed',
      value: stats.completed_jobs,
      icon: CheckCircle,
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
    },
    {
      label: 'Errors',
      value: stats.error_jobs,
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
    },
    {
      label: 'Processing',
      value: stats.processing_jobs,
      icon: Clock,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {statItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <div
            key={item.label}
            className="glass-card p-6 animate-fade-in"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-full ${item.bgColor}`}>
                <Icon className={`w-6 h-6 ${item.color}`} />
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-white">
                  {item.value.toLocaleString()}
                </div>
                <div className="text-sm text-white/60">{item.label}</div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 text-xs text-white/40">
              <Activity className="w-3 h-3" />
              <span>Live updates</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
