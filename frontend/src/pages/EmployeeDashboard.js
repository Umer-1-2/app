import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { LogOut, Clock, Coffee, Play, Square, Calendar } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function EmployeeDashboard({ user, onLogout }) {
  const [todayStatus, setTodayStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [history, setHistory] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());

  const getToken = () => localStorage.getItem('token');

  const fetchTodayStatus = async () => {
    try {
      const response = await axios.get(`${API}/attendance/today-status`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      setTodayStatus(response.data);
    } catch (error) {
      toast.error('Failed to fetch today\'s status');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/attendance/my-history`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      setHistory(response.data);
    } catch (error) {
      toast.error('Failed to fetch history');
    }
  };

  useEffect(() => {
    const loadData = async () => {
      await Promise.all([fetchTodayStatus(), fetchHistory()]);
      setLoading(false);
    };
    loadData();

    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handlePunchIn = async () => {
    setActionLoading(true);
    try {
      await axios.post(`${API}/attendance/punch-in`, {}, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      toast.success('Punched in successfully!');
      await fetchTodayStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to punch in');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePunchOut = async () => {
    setActionLoading(true);
    try {
      const response = await axios.post(`${API}/attendance/punch-out`, {}, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      toast.success(`Punched out! Total: ${response.data.work_hours}h worked`);
      await Promise.all([fetchTodayStatus(), fetchHistory()]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to punch out');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStartBreak = async () => {
    setActionLoading(true);
    try {
      await axios.post(`${API}/attendance/start-break`, {}, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      toast.success('Break started');
      await fetchTodayStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to start break');
    } finally {
      setActionLoading(false);
    }
  };

  const handleEndBreak = async () => {
    setActionLoading(true);
    try {
      await axios.post(`${API}/attendance/end-break`, {}, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      toast.success('Break ended');
      await fetchTodayStatus();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to end break');
    } finally {
      setActionLoading(false);
    }
  };

  const calculateElapsedTime = () => {
    if (!todayStatus?.attendance?.punch_in) return '0h 0m';
    
    const punchIn = new Date(todayStatus.attendance.punch_in);
    const now = currentTime;
    const diff = now - punchIn;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m`;
  };

  const getStatusBadge = (status) => {
    const badges = {
      complete: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      incomplete: 'bg-amber-50 text-amber-700 border-amber-200',
      break_exceeded: 'bg-red-50 text-red-700 border-red-200',
      active: 'bg-blue-50 text-blue-700 border-blue-200'
    };
    return badges[status] || badges.active;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const attendance = todayStatus?.attendance;
  const isPunchedIn = attendance?.punch_in && !attendance?.punch_out;
  const onBreak = attendance?.break_start && !attendance?.break_end;

  return (
    <div className="min-h-screen bg-background p-6 md:p-12">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Welcome, {user.name}</h1>
            <p className="text-muted-foreground mt-1">Track your work hours</p>
          </div>
          <Button variant="outline" onClick={onLogout} data-testid="logout-btn">
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-8">
          <Card className="shadow-lg" data-testid="punch-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Today's Shift
              </CardTitle>
              <CardDescription>{format(new Date(), 'EEEE, MMMM d, yyyy')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {isPunchedIn && (
                <div className="p-6 bg-primary/5 rounded-xl border-2 border-primary/20">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-2">Time Elapsed</p>
                    <p className="text-4xl font-bold tracking-tight" data-testid="elapsed-time">{calculateElapsedTime()}</p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                {!isPunchedIn && !attendance?.punch_out ? (
                  <Button
                    onClick={handlePunchIn}
                    disabled={actionLoading}
                    className="col-span-2 h-16 text-lg rounded-full"
                    data-testid="punch-in-btn"
                  >
                    <Play className="mr-2 h-5 w-5" />
                    Punch In
                  </Button>
                ) : isPunchedIn ? (
                  <Button
                    onClick={handlePunchOut}
                    disabled={actionLoading}
                    variant="destructive"
                    className="col-span-2 h-16 text-lg rounded-full"
                    data-testid="punch-out-btn"
                  >
                    <Square className="mr-2 h-5 w-5" />
                    Punch Out
                  </Button>
                ) : (
                  <div className="col-span-2 text-center py-8 text-muted-foreground" data-testid="shift-complete-msg">
                    Shift completed for today
                  </div>
                )}
              </div>

              {isPunchedIn && (
                <div className="grid grid-cols-2 gap-4">
                  {!onBreak ? (
                    <Button
                      onClick={handleStartBreak}
                      disabled={actionLoading}
                      variant="outline"
                      className="h-14"
                      data-testid="start-break-btn"
                    >
                      <Coffee className="mr-2 h-4 w-4" />
                      Start Break
                    </Button>
                  ) : (
                    <Button
                      onClick={handleEndBreak}
                      disabled={actionLoading}
                      className="col-span-2 h-14"
                      data-testid="end-break-btn"
                    >
                      <Coffee className="mr-2 h-4 w-4" />
                      End Break
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="shadow-lg" data-testid="status-card">
            <CardHeader>
              <CardTitle>Today's Summary</CardTitle>
            </CardHeader>
            <CardContent>
              {attendance ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-3 border-b">
                    <span className="text-muted-foreground">Punch In</span>
                    <span className="font-semibold" data-testid="punch-in-time">
                      {attendance.punch_in ? format(parseISO(attendance.punch_in), 'hh:mm a') : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b">
                    <span className="text-muted-foreground">Punch Out</span>
                    <span className="font-semibold" data-testid="punch-out-time">
                      {attendance.punch_out ? format(parseISO(attendance.punch_out), 'hh:mm a') : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b">
                    <span className="text-muted-foreground">Total Hours</span>
                    <span className="font-semibold" data-testid="total-hours">
                      {attendance.total_hours ? `${attendance.total_hours}h` : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b">
                    <span className="text-muted-foreground">Break Duration</span>
                    <span className="font-semibold" data-testid="break-duration">
                      {attendance.break_duration ? `${attendance.break_duration}h` : '-'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Status</span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadge(attendance.status)}`} data-testid="attendance-status">
                      {attendance.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">No attendance for today</p>
              )}
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-lg" data-testid="history-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Attendance History
            </CardTitle>
            <CardDescription>Your recent work records</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-3 text-sm font-semibold">Date</th>
                    <th className="text-left p-3 text-sm font-semibold">Punch In</th>
                    <th className="text-left p-3 text-sm font-semibold">Punch Out</th>
                    <th className="text-left p-3 text-sm font-semibold">Hours</th>
                    <th className="text-left p-3 text-sm font-semibold">Break</th>
                    <th className="text-left p-3 text-sm font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.length > 0 ? (
                    history.map((record) => (
                      <tr key={record.attendance_id} className="border-b hover:bg-accent/50" data-testid="history-row">
                        <td className="p-3 text-sm">{format(parseISO(record.date), 'MMM d, yyyy')}</td>
                        <td className="p-3 text-sm">
                          {record.punch_in ? format(parseISO(record.punch_in), 'hh:mm a') : '-'}
                        </td>
                        <td className="p-3 text-sm">
                          {record.punch_out ? format(parseISO(record.punch_out), 'hh:mm a') : '-'}
                        </td>
                        <td className="p-3 text-sm font-medium">
                          {record.total_hours ? `${record.total_hours}h` : '-'}
                        </td>
                        <td className="p-3 text-sm">
                          {record.break_duration ? `${record.break_duration}h` : '-'}
                        </td>
                        <td className="p-3 text-sm">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadge(record.status)}`}>
                            {record.status.replace('_', ' ')}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="p-8 text-center text-muted-foreground">
                        No attendance history yet
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
