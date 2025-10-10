import React, { useState, useEffect } from 'react';
import { API } from '@/App';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { toast } from 'sonner';
import { Settings, Lock, Key, Save, CheckCircle2 } from 'lucide-react';

const SettingsPage = () => {
  const [secrets, setSecrets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({
    APP_ADMIN_EMAIL: '',
    APP_ADMIN_PASSWORD_HASH: '',
    FPL_TEAM_ID: '',
    FPL_LOGIN: '',
    FPL_PASSWORD: '',
    AIRSENAL_HOME: '/data/airsenal'
  });
  const [newPassword, setNewPassword] = useState('');
  const [generatedHash, setGeneratedHash] = useState('');

  useEffect(() => {
    fetchSecrets();
  }, []);

  const fetchSecrets = async () => {
    try {
      const response = await axios.get(`${API}/secrets`);
      setSecrets(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch secrets:', error);
      setLoading(false);
    }
  };

  const isSecretSet = (key) => {
    const secret = secrets.find(s => s.key === key);
    return secret?.is_set || false;
  };

  const updateSecret = async (key, value) => {
    try {
      await axios.post(`${API}/secrets`, { key, value });
      toast.success(`${key} updated successfully`);
      fetchSecrets();
    } catch (error) {
      console.error(`Failed to update ${key}:`, error);
      toast.error(error.response?.data?.detail || `Failed to update ${key}`);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Update all non-empty fields
    for (const [key, value] of Object.entries(formData)) {
      if (value && value.trim()) {
        await updateSecret(key, value);
      }
    }
    
    // Clear form
    setFormData({
      APP_ADMIN_EMAIL: '',
      APP_ADMIN_PASSWORD_HASH: '',
      FPL_TEAM_ID: '',
      FPL_LOGIN: '',
      FPL_PASSWORD: '',
      AIRSENAL_HOME: '/data/airsenal'
    });
  };

  const generatePasswordHash = async () => {
    if (!newPassword) {
      toast.error('Please enter a password');
      return;
    }

    try {
      const response = await axios.post(`${API}/auth/hash-password`, { password: newPassword });
      setGeneratedHash(response.data.hash);
      toast.success('Hash generated! Copy it to the Password Hash field.');
    } catch (error) {
      console.error('Failed to generate hash:', error);
      toast.error('Failed to generate password hash');
    }
  };

  return (
    <div className="max-w-4xl space-y-6" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
        <p className="text-zinc-400">Manage secrets and application configuration</p>
      </div>

      {/* Password Hash Generator */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <Key className="w-5 h-5 text-purple-400" />
            </div>
            <CardTitle className="text-white">Password Hash Generator</CardTitle>
          </div>
          <CardDescription>Generate bcrypt hash for admin password</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="new-password" className="text-zinc-300">New Password</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="bg-zinc-800/50 border-zinc-700 text-white"
              placeholder="Enter password to hash"
              data-testid="new-password-input"
            />
          </div>
          <Button
            onClick={generatePasswordHash}
            className="bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30"
            data-testid="generate-hash-button"
          >
            <Key className="w-4 h-4 mr-2" />
            Generate Hash
          </Button>
          {generatedHash && (
            <div className="p-3 bg-zinc-800 rounded border border-zinc-700">
              <p className="text-xs text-zinc-500 mb-1">Generated Hash:</p>
              <code className="text-xs text-cyan-400 break-all">{generatedHash}</code>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Secrets Status */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
              <Lock className="w-5 h-5 text-cyan-400" />
            </div>
            <CardTitle className="text-white">Secrets Status</CardTitle>
          </div>
          <CardDescription>Current configuration status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {['APP_ADMIN_EMAIL', 'APP_ADMIN_PASSWORD_HASH', 'FPL_TEAM_ID', 'FPL_LOGIN', 'FPL_PASSWORD', 'AIRSENAL_HOME'].map((key) => (
              <div key={key} className="flex items-center justify-between p-3 bg-zinc-800/30 rounded border border-zinc-800">
                <span className="text-white font-mono text-sm">{key}</span>
                {isSecretSet(key) ? (
                  <span className="flex items-center gap-2 text-green-400 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    Set
                  </span>
                ) : (
                  <span className="text-zinc-500 text-sm">Not set</span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Update Secrets */}
      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
              <Settings className="w-5 h-5 text-cyan-400" />
            </div>
            <CardTitle className="text-white">Update Secrets</CardTitle>
          </div>
          <CardDescription>Update application secrets (leave empty to keep current value)</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="admin-email" className="text-zinc-300">Admin Email</Label>
                <Input
                  id="admin-email"
                  type="email"
                  value={formData.APP_ADMIN_EMAIL}
                  onChange={(e) => setFormData({ ...formData, APP_ADMIN_EMAIL: e.target.value })}
                  className="bg-zinc-800/50 border-zinc-700 text-white"
                  placeholder="admin@example.com"
                  data-testid="admin-email-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin-hash" className="text-zinc-300">Admin Password Hash</Label>
                <Input
                  id="admin-hash"
                  type="text"
                  value={formData.APP_ADMIN_PASSWORD_HASH}
                  onChange={(e) => setFormData({ ...formData, APP_ADMIN_PASSWORD_HASH: e.target.value })}
                  className="bg-zinc-800/50 border-zinc-700 text-white font-mono text-xs"
                  placeholder="$2b$12$..."
                  data-testid="admin-hash-input"
                />
              </div>

              <div className="border-t border-zinc-800 pt-4 mt-4">
                <h3 className="text-lg font-semibold text-white mb-4">FPL Credentials</h3>
                
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="fpl-team-id" className="text-zinc-300">FPL Team ID</Label>
                    <Input
                      id="fpl-team-id"
                      type="text"
                      value={formData.FPL_TEAM_ID}
                      onChange={(e) => setFormData({ ...formData, FPL_TEAM_ID: e.target.value })}
                      className="bg-zinc-800/50 border-zinc-700 text-white"
                      placeholder="123456"
                      data-testid="fpl-team-id-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="fpl-login" className="text-zinc-300">FPL Login Email</Label>
                    <Input
                      id="fpl-login"
                      type="email"
                      value={formData.FPL_LOGIN}
                      onChange={(e) => setFormData({ ...formData, FPL_LOGIN: e.target.value })}
                      className="bg-zinc-800/50 border-zinc-700 text-white"
                      placeholder="your@email.com"
                      data-testid="fpl-login-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="fpl-password" className="text-zinc-300">FPL Password</Label>
                    <Input
                      id="fpl-password"
                      type="password"
                      value={formData.FPL_PASSWORD}
                      onChange={(e) => setFormData({ ...formData, FPL_PASSWORD: e.target.value })}
                      className="bg-zinc-800/50 border-zinc-700 text-white"
                      placeholder="••••••••"
                      data-testid="fpl-password-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="airsenal-home" className="text-zinc-300">AIrsenal Home Directory</Label>
                    <Input
                      id="airsenal-home"
                      type="text"
                      value={formData.AIRSENAL_HOME}
                      onChange={(e) => setFormData({ ...formData, AIRSENAL_HOME: e.target.value })}
                      className="bg-zinc-800/50 border-zinc-700 text-white font-mono text-sm"
                      placeholder="/data/airsenal"
                      data-testid="airsenal-home-input"
                    />
                  </div>
                </div>
              </div>
            </div>

            <Button
              type="submit"
              className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
              data-testid="save-secrets-button"
            >
              <Save className="w-4 h-4 mr-2" />
              Save Secrets
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;
