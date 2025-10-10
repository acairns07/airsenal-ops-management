import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { PlayCircle, RefreshCw, Database, Loader2, CheckCircle2, XCircle, AlertTriangle, Zap } from 'lucide-react';
import LogViewer from '@/components/LogViewer';

const SetupPage = () => {
  const [pythonHealth, setPythonHealth] = useState(null);
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      const response = await axios.get(`${API}/health`);
      setPythonHealth(response.data);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const runCommand = async (command, label) => {
    try {
      const response = await axios.post(`${API}/jobs`, {
        command,
        parameters: {}
      });
      setCurrentJob(response.data);
      setJobStatus('running');
      toast.success(`${label} started`);
    } catch (error) {
      console.error(`${label} error:`, error);
      toast.error(error.response?.data?.detail || `Failed to start ${label}`);
    }
  };

  const handleJobComplete = (status) => {
    setJobStatus(status);
    if (status === 'completed') {
      toast.success('Command completed successfully!');
    } else if (status === 'failed') {
      toast.error('Command failed');
    }
  };

  return (
    <div className="max-w-6xl space-y-6" data-testid="setup-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Setup & Initialization</h1>
        <p className="text-zinc-400">Initialize and update your AIrsenal database</p>
      </div>

      {/* Python Version Warning */}
      {pythonHealth && !pythonHealth.python_version_valid && (
        <Card className="border-red-500/30 bg-red-500/5" data-testid="python-warning">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 mt-0.5" />
              <div>
                <p className="font-semibold text-red-400">Python Version Incompatible</p>
                <p className="text-sm text-zinc-400 mt-1">
                  AIrsenal requires Python &lt; 3.13. Current version: {pythonHealth.python_version}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Python Version Info */}
      {pythonHealth && pythonHealth.python_version_valid && (
        <Card className="border-green-500/30 bg-green-500/5" data-testid="python-info">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-400 mt-0.5" />
              <div>
                <p className="font-semibold text-green-400">Python Version Compatible</p>
                <p className="text-sm text-zinc-400 mt-1">
                  Python {pythonHealth.python_version} (AIrsenal compatible)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900/80 transition-colors">
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
                <Database className="w-5 h-5 text-blue-400" />
              </div>
              <CardTitle className="text-white">Create Database</CardTitle>
            </div>
            <CardDescription>Initialize the AIrsenal database from scratch</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runCommand('setup_db', 'Create Database')}
              disabled={jobStatus === 'running'}
              className="w-full bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30"
              data-testid="create-db-button"
            >
              {jobStatus === 'running' ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <PlayCircle className="w-4 h-4 mr-2" />
              )}
              Create DB
            </Button>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900/80 transition-colors">
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
                <RefreshCw className="w-5 h-5 text-cyan-400" />
              </div>
              <CardTitle className="text-white">Update Database</CardTitle>
            </div>
            <CardDescription>Fetch latest FPL data and update predictions</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runCommand('update_db', 'Update Database')}
              disabled={jobStatus === 'running'}
              className="w-full bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
              data-testid="update-db-button"
            >
              {jobStatus === 'running' ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Update DB
            </Button>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/50 hover:bg-zinc-900/80 transition-colors">
          <CardHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <CardTitle className="text-white">Run Pipeline</CardTitle>
            </div>
            <CardDescription>Full update + prediction + optimization cycle</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => runCommand('pipeline', 'Run Pipeline')}
              disabled={jobStatus === 'running'}
              className="w-full bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30"
              data-testid="run-pipeline-button"
            >
              {jobStatus === 'running' ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Zap className="w-4 h-4 mr-2" />
              )}
              Run Pipeline
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Log Viewer */}
      {currentJob && (
        <Card className="border-zinc-800 bg-zinc-900/50" data-testid="log-viewer-card">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              Live Logs
              {jobStatus === 'running' && (
                <span className="flex items-center gap-2 text-sm font-normal text-cyan-400">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  Running
                </span>
              )}
              {jobStatus === 'completed' && (
                <span className="flex items-center gap-2 text-sm font-normal text-green-400">
                  <CheckCircle2 className="w-4 h-4" />
                  Completed
                </span>
              )}
              {jobStatus === 'failed' && (
                <span className="flex items-center gap-2 text-sm font-normal text-red-400">
                  <XCircle className="w-4 h-4" />
                  Failed
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <LogViewer jobId={currentJob.id} onStatusChange={handleJobComplete} />
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default SetupPage;
