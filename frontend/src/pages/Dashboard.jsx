import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription } from '../components/ui/alert';
import { Skeleton } from '../components/ui/skeleton';
import { Target, TrendingUp, CheckCircle2, XCircle, Clock, ExternalLink, Copy } from 'lucide-react';
import api from '../utils/api';
import { getUser } from '../utils/auth';
import { toast } from 'sonner';

export const Dashboard = () => {
  const user = getUser();
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ pending: 0, completed: 0, ignored: 0 });

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async () => {
    try {
      const { data } = await api.get('/recommendations?limit=50');
      setRecommendations(data);
      
      const pending = data.filter(r => r.status === 'pending').length;
      const completed = data.filter(r => r.status === 'completed').length;
      const ignored = data.filter(r => r.status === 'ignored').length;
      
      setStats({ pending, completed, ignored });
    } catch (error) {
      console.error('Error fetching recommendations:', error);
      toast.error('Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (id) => {
    try {
      await api.post(`/recommendations/${id}/complete`);
      toast.success('Recommendation marked as completed!');
      fetchRecommendations();
    } catch (error) {
      toast.error('Failed to mark as completed');
    }
  };

  const handleIgnore = async (id) => {
    try {
      await api.post(`/recommendations/${id}/ignore`);
      toast.success('Recommendation ignored');
      fetchRecommendations();
    } catch (error) {
      toast.error('Failed to ignore recommendation');
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard!');
  };

  const getScoreColor = (score) => {
    if (score >= 80) return 'bg-green-500/20 text-green-400 border-green-500/30';
    if (score >= 60) return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
  };

  const renderRecommendationCard = (rec) => {
    const opp = rec.opportunity;
    if (!opp) return null;

    return (
      <Card key={rec.id} className="glass border-white/10 card-hover" data-testid={`recommendation-card-${rec.id}`}>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Badge className={`score-badge ${getScoreColor(opp.score)}`} data-testid="recommendation-score">
                  Score: {opp.score.toFixed(0)}
                </Badge>
                <Badge variant="outline" className="capitalize">{opp.type.replace('_', ' ')}</Badge>
              </div>
              <CardTitle className="text-lg mb-2">{rec.action_text}</CardTitle>
              {opp.signal_content && (
                <CardDescription className="line-clamp-2">{opp.signal_content}</CardDescription>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {rec.content_template && (
            <div className="p-4 bg-background/50 rounded-lg border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium">Content Template:</p>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => copyToClipboard(rec.content_template)}
                  data-testid="copy-template-btn"
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-4">
                {rec.content_template}
              </p>
            </div>
          )}
          
          {opp.signal_link && (
            <a
              href={opp.signal_link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-primary hover:underline"
              data-testid="signal-link"
            >
              <ExternalLink className="h-4 w-4" />
              View Original Post
            </a>
          )}

          <div className="flex items-center gap-2">
            {rec.status === 'pending' && (
              <>
                <Button
                  size="sm"
                  className="gradient-primary btn-primary flex-1"
                  onClick={() => handleComplete(rec.id)}
                  data-testid="complete-btn"
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  Mark as Done
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleIgnore(rec.id)}
                  data-testid="ignore-btn"
                >
                  <XCircle className="h-4 w-4" />
                </Button>
              </>
            )}
            {rec.status === 'completed' && (
              <Badge className="bg-green-500/20 text-green-400">Completed</Badge>
            )}
            {rec.status === 'ignored' && (
              <Badge variant="outline">Ignored</Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const pendingRecs = recommendations.filter(r => r.status === 'pending');
  const completedRecs = recommendations.filter(r => r.status === 'completed');
  const ignoredRecs = recommendations.filter(r => r.status === 'ignored');

  return (
    <div className="min-h-screen pt-20 pb-12 px-4">
      <div className="container mx-auto max-w-7xl">
        {/* Header */}
        <div className="mb-8 flex justify-between items-start">
          <div>
            <h1 className="text-4xl font-bold mb-2" data-testid="dashboard-title">
              Daily Traffic Plan
            </h1>
            <p className="text-muted-foreground">
              Welcome back, {user.email}! Here are your personalized recommendations.
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              onClick={() => window.location.href = '/leads'}
              variant="outline"
              className="bg-blue-600 text-white hover:bg-blue-700"
            >
              View Leads
            </Button>
            <Button
              onClick={() => window.location.href = '/settings'}
              variant="outline"
              className="flex items-center gap-2"
            >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </Button>
        </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Pending Actions</p>
                  <p className="text-3xl font-bold mt-1" data-testid="pending-count">{stats.pending}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                  <Clock className="w-6 h-6 text-yellow-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Completed</p>
                  <p className="text-3xl font-bold mt-1" data-testid="completed-count">{stats.completed}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="w-6 h-6 text-green-400" />
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Total Opportunities</p>
                  <p className="text-3xl font-bold mt-1" data-testid="total-count">{recommendations.length}</p>
                </div>
                <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Plan Limit Info */}
        {user.plan === 'free' && pendingRecs.length === 5 && (
          <Alert className="mb-6 border-primary/20 bg-primary/10">
            <Target className="h-4 w-4" />
            <AlertDescription>
              You're on the Free plan (5 opportunities/day). Upgrade to Pro for unlimited opportunities!
            </AlertDescription>
          </Alert>
        )}

        {/* Recommendations Tabs */}
        <Tabs defaultValue="pending" className="space-y-6">
          <TabsList className="glass">
            <TabsTrigger value="pending" data-testid="tab-pending">
              Pending ({stats.pending})
            </TabsTrigger>
            <TabsTrigger value="completed" data-testid="tab-completed">
              Completed ({stats.completed})
            </TabsTrigger>
            <TabsTrigger value="ignored" data-testid="tab-ignored">
              Ignored ({stats.ignored})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pending" className="space-y-6">
            {loading ? (
              <>
                {[1, 2, 3].map((i) => (
                  <Card key={i} className="glass border-white/10">
                    <CardContent className="p-6">
                      <Skeleton className="h-24 w-full" />
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : pendingRecs.length > 0 ? (
              pendingRecs.map(renderRecommendationCard)
            ) : (
              <Card className="glass border-white/10">
                <CardContent className="p-12 text-center">
                  <Target className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-lg text-muted-foreground">No pending recommendations</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Check back later for new opportunities
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="completed" className="space-y-6">
            {completedRecs.length > 0 ? (
              completedRecs.map(renderRecommendationCard)
            ) : (
              <Card className="glass border-white/10">
                <CardContent className="p-12 text-center">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-lg text-muted-foreground">No completed actions yet</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="ignored" className="space-y-6">
            {ignoredRecs.length > 0 ? (
              ignoredRecs.map(renderRecommendationCard)
            ) : (
              <Card className="glass border-white/10">
                <CardContent className="p-12 text-center">
                  <XCircle className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
                  <p className="text-lg text-muted-foreground">No ignored recommendations</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
