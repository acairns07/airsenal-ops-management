import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '@/App';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { AlertCircle, TrendingUp, TrendingDown, Activity, Sparkles, Clock } from 'lucide-react';
import { toast } from 'sonner';

const AIRecommendationsPage = () => {
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [gameweek, setGameweek] = useState(1);
  const [intelligenceFeed, setIntelligenceFeed] = useState(null);

  useEffect(() => {
    fetchIntelligenceFeed();
  }, []);

  const fetchIntelligenceFeed = async () => {
    try {
      const response = await axios.get(`${API}/ai/intelligence/feed?hours=24`);
      setIntelligenceFeed(response.data);
    } catch (error) {
      console.error('Failed to fetch intelligence feed:', error);
    }
  };

  const generateAnalysis = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/ai/analyze`, {
        gameweek: gameweek,
        include_transfers: true,
        include_captaincy: true,
        focus_players: null
      });
      setAnalysis(response.data);
      toast.success('AI analysis generated successfully!');
    } catch (error) {
      console.error('Failed to generate analysis:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate AI analysis');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getRiskColor = (risk) => {
    if (risk === 'low') return 'bg-green-500';
    if (risk === 'medium') return 'bg-yellow-500';
    return 'bg-red-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">AI-Powered Recommendations</h1>
        <p className="text-muted-foreground mt-2">
          Get intelligent insights combining AIrsenal predictions with real-time news, community sentiment, and tactical analysis
        </p>
      </div>

      {/* Generate Analysis Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Generate Analysis
          </CardTitle>
          <CardDescription>
            Combine statistical predictions with live intelligence for data-driven decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div>
              <label className="text-sm font-medium">Gameweek</label>
              <input
                type="number"
                min="1"
                max="38"
                value={gameweek}
                onChange={(e) => setGameweek(parseInt(e.target.value))}
                className="flex h-10 w-20 rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
            <Button
              onClick={generateAnalysis}
              disabled={loading}
              className="mt-6"
            >
              {loading ? 'Analyzing...' : 'Generate AI Analysis'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* AI Analysis Results */}
      {analysis && (
        <div className="space-y-6">
          {/* Overall Summary */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Summary</CardTitle>
              <CardDescription>Gameweek {analysis.gameweek}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Overall Confidence:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-32 bg-gray-200 rounded-full h-2.5">
                      <div
                        className={`h-2.5 rounded-full ${getConfidenceColor(analysis.overall_confidence)}`}
                        style={{ width: `${analysis.overall_confidence * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium">
                      {(analysis.overall_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <p className="text-sm text-muted-foreground">{analysis.summary}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  {new Date(analysis.generated_at).toLocaleString()}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Transfer Recommendations */}
          {analysis.transfers && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Transfer Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                {analysis.transfers.recommended_transfers && analysis.transfers.recommended_transfers.length > 0 ? (
                  <div className="space-y-4">
                    {analysis.transfers.recommended_transfers.map((transfer, index) => (
                      <div key={index} className="border rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-red-600">
                                Out: {transfer.player_out}
                              </span>
                              <span>→</span>
                              <span className="font-medium text-green-600">
                                In: {transfer.player_in}
                              </span>
                            </div>
                            <Badge className={getRiskColor(transfer.risk_level)}>
                              {transfer.risk_level} risk
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-gray-200 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${getConfidenceColor(transfer.confidence)}`}
                                style={{ width: `${transfer.confidence * 100}%` }}
                              ></div>
                            </div>
                            <span className="text-xs font-medium">
                              {(transfer.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">
                          {transfer.reasoning}
                        </p>
                        {transfer.sources && transfer.sources.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {transfer.sources.map((source, idx) => (
                              <Badge key={idx} variant="outline" className="text-xs">
                                {source}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}

                    {analysis.transfers.total_cost !== undefined && (
                      <div className="pt-2 border-t">
                        <div className="flex justify-between text-sm">
                          <span className="font-medium">Total Cost:</span>
                          <span>£{analysis.transfers.total_cost}m</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground">No transfers recommended at this time.</p>
                )}

                {/* Players to Avoid */}
                {analysis.transfers.avoid_transfers && analysis.transfers.avoid_transfers.length > 0 && (
                  <div className="mt-6">
                    <h4 className="font-medium mb-3 flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-red-500" />
                      Players to Avoid
                    </h4>
                    <div className="space-y-2">
                      {analysis.transfers.avoid_transfers.map((avoid, index) => (
                        <div key={index} className="bg-red-50 border border-red-200 rounded p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">{avoid.player}</span>
                            <Badge variant="destructive" className="text-xs">
                              {avoid.severity}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{avoid.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Captaincy Recommendation */}
          {analysis.captaincy && analysis.captaincy.recommended_captain && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Captaincy Recommendation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Main Captain */}
                  <div className="border-2 border-green-500 rounded-lg p-4 bg-green-50">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg font-bold">
                            {analysis.captaincy.recommended_captain.player}
                          </span>
                          <Badge className="bg-green-600">CAPTAIN</Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Expected: {analysis.captaincy.recommended_captain.expected_points?.toFixed(1)} pts
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-600">
                          {(analysis.captaincy.recommended_captain.confidence * 100).toFixed(0)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Confidence</div>
                      </div>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {analysis.captaincy.recommended_captain.reasoning}
                    </p>
                    {analysis.captaincy.recommended_captain.risk_factors &&
                      analysis.captaincy.recommended_captain.risk_factors.length > 0 && (
                        <div className="mt-3 pt-3 border-t">
                          <div className="text-xs font-medium mb-1">Risk Factors:</div>
                          <ul className="list-disc list-inside text-xs text-muted-foreground">
                            {analysis.captaincy.recommended_captain.risk_factors.map((risk, idx) => (
                              <li key={idx}>{risk}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                  </div>

                  {/* Alternatives */}
                  {analysis.captaincy.alternatives && analysis.captaincy.alternatives.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">Alternative Options:</h4>
                      <div className="space-y-2">
                        {analysis.captaincy.alternatives.map((alt, index) => (
                          <div key={index} className="border rounded p-3">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium">{alt.player}</span>
                              <span className="text-sm text-muted-foreground">
                                {alt.expected_points?.toFixed(1)} pts ({(alt.confidence * 100).toFixed(0)}%)
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground">{alt.reasoning}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Intelligence Feed */}
      {intelligenceFeed && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5" />
              Latest Intelligence Feed
            </CardTitle>
            <CardDescription>Last 24 hours</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Breaking News */}
              {intelligenceFeed.breaking_news && intelligenceFeed.breaking_news.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Breaking News:</h4>
                  <div className="space-y-2">
                    {intelligenceFeed.breaking_news.slice(0, 5).map((news, index) => (
                      <div key={index} className="text-sm border-l-2 border-blue-500 pl-3">
                        <div className="font-medium">{news.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {news.source} • {news.category}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              {/* Top Reddit Topics */}
              {intelligenceFeed.top_reddit_topics && intelligenceFeed.top_reddit_topics.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Community Discussions:</h4>
                  <div className="space-y-2">
                    {intelligenceFeed.top_reddit_topics.slice(0, 5).map((topic, index) => (
                      <div key={index} className="text-sm border-l-2 border-purple-500 pl-3">
                        <div className="font-medium">{topic.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {topic.score} upvotes • {topic.num_comments} comments
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AIRecommendationsPage;
