import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '../components/ui/alert-dialog';
import { Skeleton } from '../components/ui/skeleton';
import { Users, TrendingUp, Target, Zap, PlayCircle, Trash2, Settings } from 'lucide-react';
import api from '../utils/api';
import { toast } from 'sonner';
import { isSuperAdmin } from '../utils/auth';

export const AdminDashboard = () => {
  const [stats, setStats] = useState({});
  const [users, setUsers] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const isSuper = isSuperAdmin();

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const [statsRes, usersRes, oppsRes, channelsRes] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/users'),
        api.get('/opportunities?limit=100'),
        api.get('/admin/channels')
      ]);

      setStats(statsRes.data);
      setUsers(usersRes.data);
      setOpportunities(oppsRes.data);
      setChannels(channelsRes.data);
    } catch (error) {
      console.error('Error fetching admin data:', error);
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateUserPlan = async (userId, plan) => {
    try {
      await api.put(`/admin/users/${userId}/plan?plan=${plan}`);
      toast.success('User plan updated');
      fetchAdminData();
    } catch (error) {
      toast.error('Failed to update plan');
    }
  };

  const handleUpdateUserRole = async (userId, role) => {
    try {
      await api.put(`/admin/users/${userId}/role?role=${role}`);
      toast.success('User role updated');
      fetchAdminData();
    } catch (error) {
      toast.error('Failed to update role');
    }
  };

  const handleDeleteUser = async (userId) => {
    try {
      await api.delete(`/admin/users/${userId}`);
      toast.success('User deleted');
      fetchAdminData();
    } catch (error) {
      toast.error('Failed to delete user');
    }
  };

  const handleToggleChannel = async (channelId) => {
    try {
      await api.put(`/admin/channels/${channelId}/toggle`);
      toast.success('Channel status updated');
      fetchAdminData();
    } catch (error) {
      toast.error('Failed to toggle channel');
    }
  };

  const handleTriggerScan = async () => {
    try {
      await api.post('/admin/trigger-scan');
      toast.success('Scan triggered! This may take a few minutes.');
    } catch (error) {
      toast.error('Failed to trigger scan');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'bg-green-500/20 text-green-400';
    if (score >= 60) return 'bg-yellow-500/20 text-yellow-400';
    return 'bg-blue-500/20 text-blue-400';
  };

  return (
    <div className="min-h-screen pt-20 pb-12 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold mb-2" data-testid="admin-dashboard-title">
              Admin Dashboard
            </h1>
            <p className="text-muted-foreground">Manage users, opportunities, and system settings</p>
          </div>
          {isSuper && (
            <Button
              className="gradient-primary btn-primary"
              onClick={handleTriggerScan}
              data-testid="trigger-scan-btn"
            >
              <PlayCircle className="mr-2 h-4 w-4" />
              Trigger Manual Scan
            </Button>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Users</p>
                  <p className="text-3xl font-bold mt-1" data-testid="admin-total-users">{stats.total_users || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                  <Users className="w-6 h-6 text-blue-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Opportunities</p>
                  <p className="text-3xl font-bold mt-1" data-testid="admin-total-opportunities">{stats.total_opportunities || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
                  <Target className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">High Value</p>
                  <p className="text-3xl font-bold mt-1" data-testid="admin-high-value">{stats.high_value_opportunities || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-3xl font-bold mt-1" data-testid="admin-completed">{stats.completed_recommendations || 0}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <Tabs defaultValue="users" className="space-y-6">
          <TabsList className="glass">
            <TabsTrigger value="users" data-testid="admin-tab-users">Users</TabsTrigger>
            <TabsTrigger value="opportunities" data-testid="admin-tab-opportunities">Opportunities</TabsTrigger>
            <TabsTrigger value="channels" data-testid="admin-tab-channels">Channels</TabsTrigger>
          </TabsList>

          {/* Users Tab */}
          <TabsContent value="users">
            <Card className="glass border-white/10">
              <CardHeader>
                <CardTitle>User Management</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-64 w-full" />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Plan</TableHead>
                        <TableHead>Status</TableHead>
                        {isSuper && <TableHead>Actions</TableHead>}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {users.map((user) => (
                        <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                          <TableCell className="font-medium">{user.email}</TableCell>
                          <TableCell>
                            {isSuper ? (
                              <Select
                                value={user.role}
                                onValueChange={(value) => handleUpdateUserRole(user.id, value)}
                              >
                                <SelectTrigger className="w-32">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="user">User</SelectItem>
                                  <SelectItem value="admin">Admin</SelectItem>
                                  <SelectItem value="superadmin">Superadmin</SelectItem>
                                </SelectContent>
                              </Select>
                            ) : (
                              <Badge variant="outline" className="capitalize">{user.role}</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {isSuper ? (
                              <Select
                                value={user.plan}
                                onValueChange={(value) => handleUpdateUserPlan(user.id, value)}
                              >
                                <SelectTrigger className="w-24">
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="free">Free</SelectItem>
                                  <SelectItem value="pro">Pro</SelectItem>
                                </SelectContent>
                              </Select>
                            ) : (
                              <Badge className="capitalize">{user.plan}</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge className={user.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                              {user.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          {isSuper && (
                            <TableCell>
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button size="sm" variant="destructive" data-testid={`delete-user-btn-${user.id}`}>
                                    <Trash2 className="h-4 w-4" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Delete User</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Are you sure you want to delete {user.email}? This action cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction onClick={() => handleDeleteUser(user.id)}>
                                      Delete
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            </TableCell>
                          )}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Opportunities Tab */}
          <TabsContent value="opportunities">
            <Card className="glass border-white/10">
              <CardHeader>
                <CardTitle>Recent Opportunities</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-64 w-full" />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Score</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Action</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Created</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {opportunities.slice(0, 20).map((opp) => (
                        <TableRow key={opp.id} data-testid={`opportunity-row-${opp.id}`}>
                          <TableCell>
                            <Badge className={getScoreColor(opp.score)}>{opp.score.toFixed(0)}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="capitalize">{opp.type.replace('_', ' ')}</Badge>
                          </TableCell>
                          <TableCell className="max-w-md truncate">{opp.suggested_action}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="capitalize">{opp.status}</Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {new Date(opp.created_at).toLocaleDateString()}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Channels Tab */}
          <TabsContent value="channels">
            <Card className="glass border-white/10">
              <CardHeader>
                <CardTitle>Channel Management</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-64 w-full" />
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {channels.map((channel) => (
                      <Card key={channel.id} className="glass border-white/10" data-testid={`channel-card-${channel.id}`}>
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-semibold text-lg">{channel.name}</p>
                              <p className="text-sm text-muted-foreground capitalize">{channel.type}</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge className={channel.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}>
                                {channel.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                              {isSuper && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleToggleChannel(channel.id)}
                                  data-testid={`toggle-channel-${channel.id}`}
                                >
                                  <Settings className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
