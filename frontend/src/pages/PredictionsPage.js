import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { TrendingUp, PlayCircle, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import LogViewer from '@/components/LogViewer';

const PredictionsPage = () => {
  const [weeksAhead, setWeeksAhead] = useState(3);
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);

  const runPrediction = async () => {
    try {
      const response = await axios.post(`${API}/jobs`, {
        command: 'predict',
        parameters: { weeks_ahead: parseInt(weeksAhead) }
      });
      setCurrentJob(response.data);
      setJobStatus('running');
      setReport(null);
      setReportLoading(false);
      toast.success('Prediction started');
    } catch (error) {
      console.error('Prediction error:', error);
      toast.error(error.response?.data?.detail || 'Failed to start prediction');
    }
  };

  useEffect(() => {
    let cancelled = false;

    const fetchLatestReport = async () => {
      try {
        setReportLoading(true);
        const response = await axios.get(`${API}/reports/latest`);
        if (!cancelled) {
          const latestReport = response.data?.prediction || null;
          setReport(latestReport);
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Latest prediction report load failed:', error);
        }
      } finally {
        if (!cancelled) {
          setReportLoading(false);
        }
      }
    };

    if (!currentJob) {
      fetchLatestReport();
    }

    return () => {
      cancelled = true;
    };
  }, [currentJob]);

  const handleJobComplete = (status) => {
    setJobStatus(status);
    if (status === 'completed') {
      toast.success('Prediction completed successfully!');
    } else if (status === 'failed') {
      toast.error('Prediction failed');
    } else if (status === 'cancelled') {
      toast.warning('Prediction cancelled');
    }
  };

  useEffect(() => {
    const jobId = currentJob?.id;
    if (!jobId) {
      setReport(null);
      setReportLoading(false);
      return;
    }

    if (jobStatus === 'running' || jobStatus === 'cancelling') {
      setReport(null);
      setReportLoading(false);
      return;
    }

    if (jobStatus === 'failed' || jobStatus === 'cancelled') {
      setReport(null);
      setReportLoading(false);
      return;
    }

    if (jobStatus !== 'completed') {
      return;
    }

    let cancelled = false;

    const loadReport = async () => {
      try {
        setReportLoading(true);
        const response = await axios.get(`${API}/jobs/${jobId}/output`);
        if (!cancelled) {
          setReport(response.data.output || null);
        }
      } catch (error) {
        if (!cancelled) {
          setReport(null);
          toast.error(error.response?.data?.detail || 'Unable to load prediction report');
        }
      } finally {
        if (!cancelled) {
          setReportLoading(false);
        }
      }
    };

    loadReport();

    return () => {
      cancelled = true;
    };
  }, [currentJob?.id, jobStatus]);

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

      {(reportLoading || report || jobStatus === 'completed') && (
        <Card className="border-zinc-800 bg-zinc-900/50" data-testid="prediction-report-card">
          <CardHeader>
            <CardTitle className="text-white">Prediction Report</CardTitle>
            <CardDescription>Summary extracted from the latest prediction job</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {reportLoading ? (
              <div className="flex items-center text-zinc-400">
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Building report...
              </div>
            ) : report ? (
              <>
                {report.headline && (
                  <p className="text-zinc-200 font-medium">{report.headline}</p>
                )}
                {report.players && report.players.length > 0 ? (
                  <div className="space-y-2">
                    {report.players.map((player) => (
                      <div
                        key={player.rank}
                        className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg bg-zinc-900/60 border border-zinc-800"
                      >
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="border-zinc-700 text-zinc-300">#{player.rank}</Badge>
                          <span className="text-white">{player.player}</span>
                        </div>
                        <div className="text-zinc-300">{Number.isFinite(Number(player.expected_points)) ? Number(player.expected_points).toFixed(1) : player.expected_points} pts</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">No structured player list captured. Check the job logs for details.</p>
                )}
                {report.summary_text && (
                  <pre className="text-xs text-zinc-400 bg-zinc-950/60 border border-zinc-800 rounded-lg p-3 overflow-x-auto">{report.summary_text}</pre>
                )}
              </>
            ) : (
              <p className="text-sm text-zinc-500">Report not available yet. The job may still be processing output.</p>
            )}
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
