import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { LogOut, Users, Calendar, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { format, parseISO } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function EmployerDashboard({ user, onLogout }) {
  const [monthlyData, setMonthlyData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  const getToken = () => localStorage.getItem('token');

  const fetchMonthlyReport = async (month, year) => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${API}/attendance/monthly-report`,
        { month, year },
        { headers: { Authorization: `Bearer ${getToken()}` } }
      );
      setMonthlyData(response.data);
    } catch (error) {
      toast.error('Failed to fetch monthly report');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonthlyReport(selectedMonth, selectedYear);
  }, [selectedMonth, selectedYear]);

  const getStatusBadge = (status) => {
    const badges = {
      complete: { class: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Complete' },
      incomplete: { class: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Incomplete' },
      break_exceeded: { class: 'bg-red-50 text-red-700 border-red-200', label: 'Break Exceeded' },
      active: { class: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Active' }
    };
    return badges[status] || badges.active;
  };

  const getStats = () => {
    const totalRecords = monthlyData.length;
    const completeShifts = monthlyData.filter(r => r.is_complete).length;
    const incompleteShifts = monthlyData.filter(r => !r.is_complete && !r.is_weekend && r.punch_in).length;
    const breakExceeded = monthlyData.filter(r => r.status === 'break_exceeded').length;
    
    return { totalRecords, completeShifts, incompleteShifts, breakExceeded };
  };

  const stats = getStats();

  const months = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' }
  ];

  const years = [2024, 2025, 2026];

  return (
    <div className="min-h-screen bg-background p-6 md:p-12">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Employer Dashboard</h1>
            <p className="text-muted-foreground mt-1">Monitor employee attendance</p>
          </div>
          <Button variant="outline" onClick={onLogout} data-testid="logout-btn">
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="shadow-md" data-testid="stat-total-records">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Records</p>
                  <p className="text-3xl font-bold mt-1">{stats.totalRecords}</p>
                </div>
                <Users className="h-10 w-10 text-primary opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md" data-testid="stat-complete">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Complete</p>
                  <p className="text-3xl font-bold mt-1 text-emerald-600">{stats.completeShifts}</p>
                </div>
                <CheckCircle2 className="h-10 w-10 text-emerald-600 opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md" data-testid="stat-incomplete">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Incomplete</p>
                  <p className="text-3xl font-bold mt-1 text-amber-600">{stats.incompleteShifts}</p>
                </div>
                <AlertCircle className="h-10 w-10 text-amber-600 opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-md" data-testid="stat-break-exceeded">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Break Exceeded</p>
                  <p className="text-3xl font-bold mt-1 text-red-600">{stats.breakExceeded}</p>
                </div>
                <Clock className="h-10 w-10 text-red-600 opacity-20" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="shadow-lg" data-testid="monthly-report-card">
          <CardHeader>
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Monthly Attendance Report
                </CardTitle>
                <CardDescription>View employee attendance for selected month</CardDescription>
              </div>
              <div className="flex gap-3">
                <Select value={selectedMonth.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
                  <SelectTrigger className="w-[140px]" data-testid="month-selector">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {months.map((month) => (
                      <SelectItem key={month.value} value={month.value.toString()}>
                        {month.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
                  <SelectTrigger className="w-[100px]" data-testid="year-selector">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {years.map((year) => (
                      <SelectItem key={year} value={year.toString()}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-3 text-sm font-semibold">Date</th>
                      <th className="text-left p-3 text-sm font-semibold">Employee</th>
                      <th className="text-left p-3 text-sm font-semibold">Email</th>
                      <th className="text-left p-3 text-sm font-semibold">Punch In</th>
                      <th className="text-left p-3 text-sm font-semibold">Punch Out</th>
                      <th className="text-left p-3 text-sm font-semibold">Total Hours</th>
                      <th className="text-left p-3 text-sm font-semibold">Break</th>
                      <th className="text-left p-3 text-sm font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyData.length > 0 ? (
                      monthlyData.map((record) => {
                        const isIncomplete = !record.is_complete && !record.is_weekend && record.punch_in;
                        const isBreakExceeded = record.status === 'break_exceeded';
                        const rowClass = isIncomplete || isBreakExceeded ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-accent/50';
                        
                        return (
                          <tr key={record.attendance_id} className={`border-b ${rowClass}`} data-testid="attendance-row">
                            <td className="p-3 text-sm font-medium">{format(parseISO(record.date), 'MMM d, yyyy')}</td>
                            <td className="p-3 text-sm">{record.user_name}</td>
                            <td className="p-3 text-sm text-muted-foreground">{record.user_email}</td>
                            <td className="p-3 text-sm">
                              {record.punch_in ? format(parseISO(record.punch_in), 'hh:mm a') : '-'}
                            </td>
                            <td className="p-3 text-sm">
                              {record.punch_out ? format(parseISO(record.punch_out), 'hh:mm a') : '-'}
                            </td>
                            <td className="p-3 text-sm font-medium">
                              <span className={isIncomplete ? 'text-red-600 font-bold' : ''}>
                                {record.total_hours ? `${record.total_hours}h` : '-'}
                              </span>
                            </td>
                            <td className="p-3 text-sm">
                              <span className={isBreakExceeded ? 'text-red-600 font-bold' : ''}>
                                {record.break_duration ? `${record.break_duration}h` : '-'}
                              </span>
                            </td>
                            <td className="p-3 text-sm">
                              {record.is_weekend ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border bg-slate-50 text-slate-600 border-slate-200">
                                  Weekend
                                </span>
                              ) : (
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusBadge(record.status).class}`}>
                                  {getStatusBadge(record.status).label}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="8" className="p-8 text-center text-muted-foreground">
                          No attendance records for this month
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
