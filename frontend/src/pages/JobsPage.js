import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FolderOpen, Clock, CheckCircle2, XCircle, Loader2, Eye, StopCircle, Ban, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import LogViewer from '@/components/LogViewer';

const JobsPage = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [actionJobId, setActionJobId] = useState(null);
  const [clearingAll, setClearingAll] = useState(false);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const selectedJobData = jobs.find((job) => job.id === selectedJob);

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
      case 'cancelling':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'cancelled':
        return <Ban className="w-4 h-4" />;
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
      case 'cancelling':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'completed':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'failed':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'cancelled':
        return 'bg-zinc-500/10 text-zinc-300 border-zinc-500/30';
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


const cancelJob = async (jobId) => {
  try {
    setActionJobId(jobId);
    await axios.post(`${API}/jobs/${jobId}/cancel`);
    toast.info('Cancellation requested');
    fetchJobs();
  } catch (error) {
    toast.error(error.response?.data?.detail || 'Failed to cancel job');
  } finally {
    setActionJobId(null);
  }
};

const clearJobLogs = async (jobId) => {
  try {
    setActionJobId(jobId);
    await axios.delete(`${API}/jobs/${jobId}/logs`);
    if (selectedJob === jobId) {
      setSelectedJob(null);
    }
    fetchJobs();
    toast.success('Logs cleared');
  } catch (error) {
    toast.error(error.response?.data?.detail || 'Failed to clear logs');
  } finally {
    setActionJobId(null);
  }
};

const clearAllLogs = async () => {
  try {
    setClearingAll(true);
    await axios.delete(`${API}/jobs/logs`);
    setSelectedJob(null);
    fetchJobs();
    toast.success('All logs cleared');
  } catch (error) {
    toast.error(error.response?.data?.detail || 'Failed to clear logs');
  } finally {
    setClearingAll(false);
  }
};

const renderJobOutput = (output) => {
  if (!output) {
    return null;
  }
  if (output.type === 'prediction') {
    return (
      <div className="space-y-2">
        {output.headline && <p className="text-zinc-200 font-medium">{output.headline}</p>}
        {output.players && output.players.length > 0 ? (
          <div className="space-y-2">
            {output.players.map((player) => (
              <div
                key={`${player.rank}-${player.player}`}
                className="flex items-center justify-between gap-3 px-3 py-2 bg-zinc-900/50 border border-zinc-800 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="border-zinc-700 text-zinc-300">#{player.rank}</Badge>
                  <span className="text-white">{player.player}</span>
                </div>
                <span className="text-sm text-zinc-300">{player.expected_points}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">No player list captured.</p>
        )}
      </div>
    );
  }
  if (output.type === 'optimisation') {
    return (
      <div className="space-y-3">
        {output.transfers && output.transfers.length > 0 ? (
          <div className="space-y-2">
            {output.transfers.map((move, index) => (
              <div
                key={`${move.out}-${move.in}-${index}`}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 bg-zinc-900/50 border border-zinc-800 rounded-lg"
              >
                <div className="text-white">{move.out} -> {move.in}</div>
                <div className="flex items-center gap-3 text-sm text-zinc-300">
                  <span>{move.cost}</span>
                  <span>{move.gain}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-zinc-500">No transfers captured.</p>
        )}
        <div className="flex items-center gap-3 text-sm text-zinc-300">
          {output.captain && <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30">Captain: {output.captain}</Badge>}
          {output.vice_captain && <Badge className="bg-blue-500/20 text-blue-200 border-blue-500/30">Vice: {output.vice_captain}</Badge>}
          {output.expected_points && <Badge variant="outline" className="border-emerald-500/40 text-emerald-300">Expected: {output.expected_points}</Badge>}
        </div>
      </div>
    );
  }
  return (
    <pre className="text-xs text-zinc-400 bg-zinc-950/60 border border-zinc-800 rounded-lg p-3 overflow-x-auto">
      {output.summary_text || JSON.stringify(output, null, 2)}
    </pre>
  );
};

  return (
    <div className="max-w-6xl space-y-6" data-testid="jobs-page">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Jobs & Logs</h1>
          <p className="text-zinc-400">View job history and execution logs</p>
        </div>
        <Button
          onClick={clearAllLogs}
          variant="outline"
          className="border-zinc-700 text-zinc-200 hover:border-zinc-500"
          disabled={clearingAll}
          size="sm"
          data-testid="clear-all-logs"
        >
          {clearingAll ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Clearing...
            </>
          ) : (
            <>
              <Trash2 className="w-4 h-4 mr-2" />
              Clear All Logs
            </>
          )}
        </Button>
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

                  <div className="flex items-center gap-2">
                    {(job.status === 'running' || job.status === 'cancelling') && (
                      <Button
                        onClick={() => cancelJob(job.id)}
                        variant="destructive"
                        size="sm"
                        disabled={actionJobId === job.id || job.status === 'cancelling'}
                        className="hover:bg-red-600"
                        data-testid={`cancel-job-${job.id}`}
                      >
                        <StopCircle className="w-4 h-4 mr-2" />
                        Cancel
                      </Button>
                    )}
                    <Button
                      onClick={() => clearJobLogs(job.id)}
                      variant="outline"
                      size="sm"
                      disabled={actionJobId === job.id}
                      className="border-zinc-700 text-zinc-300 hover:border-zinc-500"
                      data-testid={`clear-job-logs-${job.id}`}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Clear Logs
                    </Button>
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

      {selectedJobData?.output && (
        <Card className="border-zinc-800 bg-zinc-900/50" data-testid="job-output-card">
          <CardHeader>
            <CardTitle className="text-white">Job Summary</CardTitle>
            <CardDescription>Structured output captured for this job</CardDescription>
          </CardHeader>
          <CardContent>
            {renderJobOutput(selectedJobData.output) || (
              <p className="text-sm text-zinc-500">No structured output was captured. Check the logs for details.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default JobsPage;
