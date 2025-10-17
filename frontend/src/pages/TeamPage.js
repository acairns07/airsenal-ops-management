import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { API } from '@/App';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Users, RefreshCcw, Calendar, Shield } from 'lucide-react';
import { format } from 'date-fns';

const positionLabels = {
  GK: 'Goalkeeper',
  DEF: 'Defender',
  MID: 'Midfielder',
  FWD: 'Forward'
};

const TeamPage = () => {
  const [teamData, setTeamData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTeam = async (showToast = false) => {
    setRefreshing(true);
    try {
      const response = await axios.get(`${API}/team/current`);
      setTeamData(response.data);
      if (showToast) {
        toast.success('Team updated');
      }
    } catch (error) {
      const detail = error.response?.data?.detail || 'Unable to load team details';
      toast.error(detail);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchTeam();
  }, []);

  const renderPlayers = (players) => (
    <div className="space-y-2">
      {players.map((player) => (
        <div
          key={`${player.player_id}-${player.position_slot}`}
          className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 rounded-lg bg-zinc-900/60 border border-zinc-800"
        >
          <div>
            <p className="text-white font-medium">{player.name}</p>
            <p className="text-sm text-zinc-500">{player.team} • {positionLabels[player.position] || player.position}</p>
          </div>
          <div className="flex items-center gap-2">
            {player.is_captain && <Badge className="bg-amber-500/20 text-amber-300 border-amber-500/30">Captain</Badge>}
            {player.is_vice_captain && <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30">Vice</Badge>}
            <Badge variant="outline" className="border-zinc-700 text-zinc-300">x{player.multiplier}</Badge>
          </div>
          <div className="text-right">
            <p className="text-sm text-zinc-400">Price: £{player.now_cost?.toFixed(1) ?? '—'}m</p>
            <p className="text-xs text-zinc-600">PPG: {player.points_per_game?.toFixed(1) ?? '—'}</p>
          </div>
        </div>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh] text-zinc-400">
        Loading team...
      </div>
    );
  }

  if (!teamData) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh] text-zinc-400">
        No team data available. Configure your FPL team ID in Settings.
      </div>
    );
  }

  const players = teamData.players || [];
  const starting = players.filter((player) => (player.position_slot || 0) <= 11);
  const bench = players.filter((player) => (player.position_slot || 0) > 11);

  const deadline = teamData.gameweek?.deadline
    ? format(new Date(teamData.gameweek.deadline), 'PPpp')
    : 'Unknown';

  return (
    <div className="max-w-6xl space-y-6" data-testid="team-page">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Current Gameweek Team</h1>
          <p className="text-zinc-400">Live snapshot from your official FPL entry (team {teamData.team_id})</p>
        </div>
        <Button
          onClick={() => fetchTeam(true)}
          disabled={refreshing}
          className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
        >
          <RefreshCcw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
              <Calendar className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <CardTitle className="text-white">Gameweek</CardTitle>
              <CardDescription>{teamData.gameweek?.name || 'Unknown'}</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="text-zinc-300">
            <p className="text-sm">Deadline: {deadline}</p>
            <p className="text-sm text-zinc-500">Current: {teamData.gameweek?.is_current ? 'Yes' : 'No'}</p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <Shield className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <CardTitle className="text-white">Squad Value</CardTitle>
              <CardDescription>Funds and squad worth</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="text-zinc-300 space-y-2">
            <p>Team value: £{teamData.entry_summary?.team_value?.toFixed(1) ?? '—'}m</p>
            <p>Bank: £{teamData.entry_summary?.bank?.toFixed(1) ?? '—'}m</p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/60">
          <CardHeader className="flex flex-row items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
              <Users className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <CardTitle className="text-white">GW Performance</CardTitle>
              <CardDescription>Latest scores</CardDescription>
            </div>
          </CardHeader>
          <CardContent className="text-zinc-300 space-y-2">
            <p>GW points: {teamData.entry_summary?.event_points ?? '—'}</p>
            <p>Total points: {teamData.entry_summary?.total_points ?? '—'}</p>
            <p>Transfers: {teamData.entry_summary?.event_transfers ?? 0} (cost {teamData.entry_summary?.event_transfers_cost ?? 0})</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-zinc-800 bg-zinc-900/60">
        <CardHeader>
          <CardTitle className="text-white">Starting XI</CardTitle>
          <CardDescription>Your lineup for this gameweek</CardDescription>
        </CardHeader>
        <CardContent>
          {starting.length === 0 ? (
            <p className="text-sm text-zinc-500">No players found.</p>
          ) : (
            renderPlayers(starting)
          )}
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-900/60">
        <CardHeader>
          <CardTitle className="text-white">Bench</CardTitle>
          <CardDescription>Substitutes for the current week</CardDescription>
        </CardHeader>
        <CardContent>
          {bench.length === 0 ? (
            <p className="text-sm text-zinc-500">No bench players found.</p>
          ) : (
            renderPlayers(bench)
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TeamPage;
