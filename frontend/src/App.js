import React, { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import LoginPage from "@/pages/LoginPage";
import DashboardLayout from "@/components/DashboardLayout";
import SetupPage from "@/pages/SetupPage";
import PredictionsPage from "@/pages/PredictionsPage";
import OptimisationPage from "@/pages/OptimisationPage";
import TeamPage from "@/pages/TeamPage";
import JobsPage from "@/pages/JobsPage";
import SettingsPage from "@/pages/SettingsPage";
import { Toaster } from "@/components/ui/sonner";

const normalizeBackendUrl = (value) => {
  if (!value) {
    return '';
  }
  return value.replace(/\/+$/, '');
};

const resolveBackendUrl = () => {
  const envUrl = normalizeBackendUrl(process.env.REACT_APP_BACKEND_URL?.trim());
  if (envUrl) {
    return envUrl;
  }

  if (typeof window !== 'undefined') {
    const { protocol, hostname, port } = window.location;
    const host = port ? `${hostname}:${port}` : hostname;

    if (host.includes('frontend')) {
      return `${protocol}//${host.replace('frontend', 'backend')}`;
    }

    return '';
  }

  return '';
};

const BACKEND_URL = resolveBackendUrl();
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

axios.defaults.baseURL = BACKEND_URL || axios.defaults.baseURL;

// Auth context
export const AuthContext = React.createContext(null);

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

function App() {
  const [authToken, setAuthToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (authToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${authToken}`;
      checkAuth();
    }
  }, [authToken]);

  const checkAuth = async () => {
    try {
      const response = await axios.get(`${API}/auth/check`);
      setUser(response.data);
    } catch (error) {
      console.error('Auth check failed:', error);
      logout();
    }
  };

  const login = (token, email) => {
    localStorage.setItem('token', token);
    setAuthToken(token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    setUser({ email });
  };

  const logout = () => {
    localStorage.removeItem('token');
    setAuthToken(null);
    setUser(null);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/setup" replace />} />
              <Route path="setup" element={<SetupPage />} />
              <Route path="predictions" element={<PredictionsPage />} />
              <Route path="optimisation" element={<OptimisationPage />} />
              <Route path="team" element={<TeamPage />} />
              <Route path="jobs" element={<JobsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
