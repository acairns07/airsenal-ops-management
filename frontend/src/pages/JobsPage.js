import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FolderOpen, Clock, CheckCircle2, XCircle, Loader2, Eye } from 'lucide-react';
import { format } from 'date-fns';
import LogViewer from '@/components/LogViewer';

const JobsPage = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await axios.get(`${API}/jobs`);
      setJobs(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4" />;
      case 'running':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'completed':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'failed':
        return <XCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'running':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'completed':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'failed':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      default:
        return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/30';
    }
  };

  const getCommandLabel = (command) => {
    const labels = {
      setup_db: 'Create Database',
      update_db: 'Update Database',
      predict: 'Run Prediction',
      optimize: 'Run Optimisation',
      pipeline: 'Run Pipeline'
    };
    return labels[command] || command;
  };

  return (
    <div className="max-w-6xl space-y-6" data-testid="jobs-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Jobs & Logs</h1>
        <p className="text-zinc-400">View job history and execution logs</p>
      </div>

      {/* Job List */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
              <FolderOpen className="w-5 h-5 text-cyan-400" />
            </div>
            <CardTitle className="text-white">Recent Jobs</CardTitle>
          </div>
          <CardDescription>Last 50 job executions</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-zinc-500">
              <Loader2 className="w-6 h-6 animate-spin mr-2" />
              Loading jobs...
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-8 text-zinc-500">
              No jobs found. Start by running a command from the Setup page.
            </div>
          ) : (
            <div className="space-y-2">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/30 border border-zinc-800 hover:bg-zinc-800/50 transition-colors"
                  data-testid={`job-item-${job.id}`}
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${getStatusColor(job.status)}`}>
                      {getStatusIcon(job.status)}
                      <span className="text-sm font-medium capitalize">{job.status}</span>
                    </div>
                    
                    <div>
                      <p className="text-white font-medium">{getCommandLabel(job.command)}</p>
                      <p className="text-sm text-zinc-500">
                        {job.created_at && format(new Date(job.created_at), 'PPpp')}
                      </p>
                      {job.parameters && Object.keys(job.parameters).length > 0 && (
                        <p className="text-xs text-zinc-600 mt-1">
                          {JSON.stringify(job.parameters)}
                        </p>
                      )}
                    </div>
                  </div>

                  <Button
                    onClick={() => setSelectedJob(job.id === selectedJob ? null : job.id)}
                    variant="ghost"
                    size="sm"
                    className="text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/10"
                    data-testid={`view-job-logs-${job.id}`}
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    {selectedJob === job.id ? 'Hide' : 'View'} Logs
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Selected Job Logs */}
      {selectedJob && (
        <Card className="border-zinc-800 bg-zinc-900/50" data-testid="selected-job-logs">
          <CardHeader>
            <CardTitle className="text-white">Job Logs</CardTitle>
            <CardDescription>Job ID: {selectedJob}</CardDescription>
          </CardHeader>
          <CardContent>
            <LogViewer jobId={selectedJob} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default JobsPage;
