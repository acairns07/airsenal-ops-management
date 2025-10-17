import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Target, PlayCircle, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import LogViewer from '@/components/LogViewer';

const OptimisationPage = () => {
  const [weeksAhead, setWeeksAhead] = useState(3);
  const [wildcardWeek, setWildcardWeek] = useState(0);
  const [freeHitWeek, setFreeHitWeek] = useState(0);
  const [tripleCaptainWeek, setTripleCaptainWeek] = useState(0);
  const [benchBoostWeek, setBenchBoostWeek] = useState(0);
  const [currentJob, setCurrentJob] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);

  const runOptimisation = async () => {
    try {
      const parameters = {
        weeks_ahead: parseInt(weeksAhead)
      };
      
      if (parseInt(wildcardWeek) > 0) parameters.wildcard_week = parseInt(wildcardWeek);
      if (parseInt(freeHitWeek) > 0) parameters.free_hit_week = parseInt(freeHitWeek);
      if (parseInt(tripleCaptainWeek) > 0) parameters.triple_captain_week = parseInt(tripleCaptainWeek);
      if (parseInt(benchBoostWeek) > 0) parameters.bench_boost_week = parseInt(benchBoostWeek);

      const response = await axios.post(`${API}/jobs`, {
        command: 'optimize',
        parameters
      });
      setCurrentJob(response.data);
      setJobStatus('running');
      setReport(null);
      setReportLoading(false);
      toast.success('Optimisation started');
    } catch (error) {
      console.error('Optimisation error:', error);
      toast.error(error.response?.data?.detail || 'Failed to start optimisation');
    }
  };

  const handleJobComplete = (status) => {
    setJobStatus(status);
    if (status === 'completed') {
      toast.success('Optimisation completed successfully!');
    } else if (status === 'failed') {
      toast.error('Optimisation failed');
    } else if (status === 'cancelled') {
      toast.warning('Optimisation cancelled');
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
        toast.error(error.response?.data?.detail || 'Unable to load optimisation report');
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
    <div className="max-w-6xl space-y-6" data-testid="optimisation-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Optimisation</h1>
        <p className="text-zinc-400">Multi-week team optimization with chip planning</p>
      </div>

      {/* Optimisation Form */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <Target className="w-5 h-5 text-purple-400" />
            </div>
            <CardTitle className="text-white">Run Optimisation</CardTitle>
          </div>
          <CardDescription>Generate optimal transfers and team selection</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="opt-weeks" className="text-zinc-300">Weeks Ahead (1-6)</Label>
            <Input
              id="opt-weeks"
              type="number"
              min="1"
              max="6"
              value={weeksAhead}
              onChange={(e) => setWeeksAhead(e.target.value)}
              className="bg-zinc-800/50 border-zinc-700 text-white w-32"
              data-testid="opt-weeks-ahead-input"
            />
          </div>

          <div className="border-t border-zinc-800 pt-6">
            <h3 className="text-lg font-semibold text-white mb-4">Chip Planning (optional)</h3>
            <p className="text-sm text-zinc-400 mb-4">Set to 0 for automatic planning or specify week number</p>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="wildcard" className="text-zinc-300">Wildcard Week</Label>
                <Input
                  id="wildcard"
                  type="number"
                  min="0"
                  value={wildcardWeek}
                  onChange={(e) => setWildcardWeek(e.target.value)}
                  className="bg-zinc-800/50 border-zinc-700 text-white"
                  data-testid="wildcard-week-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="freehit" className="text-zinc-300">Free Hit Week</Label>
                <Input
                  id="freehit"
                  type="number"
                  min="0"
                  value={freeHitWeek}
                  onChange={(e) => setFreeHitWeek(e.target.value)}
                  className="bg-zinc-800/50 border-zinc-700 text-white"
                  data-testid="freehit-week-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="triplecaptain" className="text-zinc-300">Triple Captain Week</Label>
                <Input
                  id="triplecaptain"
                  type="number"
                  min="0"
                  value={tripleCaptainWeek}
                  onChange={(e) => setTripleCaptainWeek(e.target.value)}
                  className="bg-zinc-800/50 border-zinc-700 text-white"
                  data-testid="triple-captain-week-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="benchboost" className="text-zinc-300">Bench Boost Week</Label>
                <Input
                  id="benchboost"
                  type="number"
                  min="0"
                  value={benchBoostWeek}
                  onChange={(e) => setBenchBoostWeek(e.target.value)}
                  className="bg-zinc-800/50 border-zinc-700 text-white"
                  data-testid="bench-boost-week-input"
                />
              </div>
            </div>
          </div>

          <Button
            onClick={runOptimisation}
            disabled={jobStatus === 'running'}
            className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
            data-testid="run-optimisation-button"
          >
            {jobStatus === 'running' ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <PlayCircle className="w-4 h-4 mr-2" />
                Run Optimisation
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
              Optimisation Logs
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
  <Card className="border-zinc-800 bg-zinc-900/50" data-testid="optimisation-report-card">
    <CardHeader>
      <CardTitle className="text-white">Optimisation Report</CardTitle>
      <CardDescription>Insights from the latest optimisation run</CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {reportLoading ? (
        <div className="flex items-center text-zinc-400">
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          Building report...
        </div>
      ) : report ? (
        <>
          {report.transfers && report.transfers.length > 0 ? (
            <div className="space-y-2">
              <h4 className="text-sm uppercase tracking-wide text-zinc-500">Recommended Transfers</h4>
              {report.transfers.map((move, index) => (
                <div
                  key={`${move.out}-${move.in}-${index}`}
                  className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 rounded-lg bg-zinc-900/60 border border-zinc-800"
                >
                  <div className="text-white font-medium">{move.out} -> {move.in}</div>
                  <div className="flex items-center gap-3 text-sm text-zinc-300">
                    <span>Cost: {move.cost}</span>
                    <span>Gain: {move.gain}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-500">No transfer recommendations captured in the output.</p>
          )}

          <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-300">
            {report.captain && (
              <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30">Captain: {report.captain}</Badge>
            )}
            {report.vice_captain && (
              <Badge className="bg-blue-500/20 text-blue-200 border-blue-500/30">Vice: {report.vice_captain}</Badge>
            )}
            {report.expected_points && (
              <Badge variant="outline" className="border-emerald-500/40 text-emerald-300">Expected: {report.expected_points}</Badge>
            )}
          </div>

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
          <CardTitle className="text-white">About Optimisation</CardTitle>
        </CardHeader>
        <CardContent className="text-zinc-400 space-y-2">
          <p>The optimisation engine will:</p>
          <ul className="list-disc list-inside space-y-1 ml-2">
            <li>Suggest optimal transfers to maximize expected points</li>
            <li>Plan chip usage across gameweeks</li>
            <li>Select the best starting XI and bench order</li>
            <li>Recommend captain and vice-captain choices</li>
            <li>Calculate expected points gain vs transfer hits</li>
          </ul>
          <p className="mt-4 text-sm">Results include detailed transfer suggestions and team lineup recommendations.</p>
        </CardContent>
      </Card>
    </div>
  );
};

export default OptimisationPage;
