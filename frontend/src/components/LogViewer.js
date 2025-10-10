import React, { useEffect, useState, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';

const LogViewer = ({ jobId, onStatusChange }) => {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('pending');
  const scrollRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;

    // Fetch existing logs from API first
    const fetchLogs = async () => {
      try {
        const response = await axios.get(`${process.env.REACT_APP_BACKEND_URL}/api/jobs/${jobId}`);
        if (response.data.logs && response.data.logs.length > 0) {
          setLogs(response.data.logs);
        }
        if (response.data.status) {
          setStatus(response.data.status);
          if (onStatusChange) {
            onStatusChange(response.data.status);
          }
        }
      } catch (error) {
        console.error('Failed to fetch logs:', error);
      }
    };
    
    fetchLogs();

    // Get backend URL from env
    const backendUrl = process.env.REACT_APP_BACKEND_URL;
    const wsUrl = backendUrl.replace('https://', 'wss://').replace('http://', 'ws://');
    
    // Connect to WebSocket
    const ws = new WebSocket(`${wsUrl}/ws/jobs/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'log') {
        setLogs((prev) => [...prev, data.message]);
      } else if (data.type === 'status') {
        setStatus(data.status);
        if (onStatusChange) {
          onStatusChange(data.status);
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [jobId, onStatusChange]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-zinc-950 rounded-lg border border-zinc-800 p-4 h-96" data-testid="log-viewer">
      <div
        ref={scrollRef}
        className="h-full overflow-y-auto log-viewer text-zinc-300 space-y-1"
      >
        {logs.length === 0 ? (
          <p className="text-zinc-500 italic">Waiting for logs...</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="hover:bg-zinc-900/50 px-2 py-0.5 rounded">
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LogViewer;
