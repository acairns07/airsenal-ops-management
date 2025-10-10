import React, { useState } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { TrendingUp, PlayCircle, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import LogViewer from '@/components/LogViewer';

const PredictionsPage = () => {
  const [weeksAhead, setWeeksAhead] = useState(3);
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);

  const runPrediction = async () => {
    try {
      const response = await axios.post(`${API}/jobs`, {
        command: 'predict',
        parameters: { weeks_ahead: parseInt(weeksAhead) }
      });
      setCurrentJob(response.data);
      setJobStatus('running');
      toast.success('Prediction started');
    } catch (error) {
      console.error('Prediction error:', error);
      toast.error(error.response?.data?.detail || 'Failed to start prediction');
    }
  };

  const handleJobComplete = (status) => {
    setJobStatus(status);
    if (status === 'completed') {
      toast.success('Prediction completed successfully!');
    } else if (status === 'failed') {
      toast.error('Prediction failed');
    }
  };

  return (
    <div className="max-w-6xl space-y-6" data-testid="predictions-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Predictions</h1>
        <p className="text-zinc-400">Run player predictions for upcoming gameweeks</p>
      </div>

      {/* Prediction Form */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
            </div>
            <CardTitle className="text-white">Run Prediction</CardTitle>
          </div>
          <CardDescription>Generate expected points predictions for players</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="weeks" className="text-zinc-300">Weeks Ahead (1-6)</Label>
            <Input
              id="weeks"
              type="number"
              min="1"
              max="6"
              value={weeksAhead}
              onChange={(e) => setWeeksAhead(e.target.value)}
              className="bg-zinc-800/50 border-zinc-700 text-white w-32"
              data-testid="weeks-ahead-input"
            />
          </div>
          <Button
            onClick={runPrediction}
            disabled={jobStatus === 'running'}
            className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
            data-testid="run-prediction-button"
          >
            {jobStatus === 'running' ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <PlayCircle className="w-4 h-4 mr-2" />
                Run Prediction
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Log Viewer */}
      {currentJob && (
        <Card className="border-zinc-800 bg-zinc-900/50" data-testid="log-viewer-card">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              Prediction Logs
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

      {/* Results Info */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <CardTitle className="text-white">About Predictions</CardTitle>
        </CardHeader>
        <CardContent className="text-zinc-400 space-y-2">
          <p>The prediction engine analyzes:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Player form and historical performance</li>
            <li>Upcoming fixture difficulty</li>
            <li>Team statistics and trends</li>
            <li>Injury and suspension data</li>
          </ul>
          <p className="mt-4 text-sm">Results are stored in the AIrsenal database and can be viewed in the Jobs & Logs section.</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default PredictionsPage;
