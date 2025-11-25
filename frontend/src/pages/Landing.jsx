import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Target, Zap, TrendingUp, Users, Shield, Clock } from 'lucide-react';

export const Landing = () => {
  const features = [
    {
      icon: <Target className="w-8 h-8 text-primary" />,
      title: "Hourly Discovery",
      description: "Automatically scans 10+ major channels every hour to find traffic opportunities"
    },
    {
      icon: <Zap className="w-8 h-8 text-primary" />,
      title: "AI-Powered Classification",
      description: "Advanced LLM agents analyze and score opportunities using Parlant architecture"
    },
    {
      icon: <TrendingUp className="w-8 h-8 text-primary" />,
      title: "Smart Scoring",
      description: "Intelligent scoring based on relevance, traffic potential, competition, and user intent"
    },
    {
      icon: <Users className="w-8 h-8 text-primary" />,
      title: "Actionable Recommendations",
      description: "Get ready-to-use content templates and step-by-step guidance"
    },
    {
      icon: <Shield className="w-8 h-8 text-primary" />,
      title: "Enterprise Ready",
      description: "JWT authentication, role-based access, and production-grade architecture"
    },
    {
      icon: <Clock className="w-8 h-8 text-primary" />,
      title: "Real-time Monitoring",
      description: "Track Reddit, HackerNews, Quora, Product Hunt, Google Trends, and more"
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="container mx-auto text-center">
          <div className="inline-block mb-4 px-4 py-2 bg-primary/10 border border-primary/20 rounded-full">
            <span className="text-sm font-medium text-primary">Production-Ready Traffic Engine</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight" data-testid="hero-title">
            Find Traffic
            <span className="block mt-2 gradient-primary bg-clip-text text-transparent">Opportunities Automatically</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-10 max-w-2xl mx-auto" data-testid="hero-description">
            Hourly scans across major platforms. AI-powered classification. Actionable recommendations.
            Built for scale with 10,000+ users in mind.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link to="/register">
              <Button size="lg" className="gradient-primary btn-primary text-lg px-8 h-14" data-testid="hero-cta-btn">
                Get Started Free
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline" className="text-lg px-8 h-14" data-testid="hero-login-btn">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Powerful Features</h2>
            <p className="text-xl text-muted-foreground">Everything you need to dominate traffic generation</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <Card key={index} className="glass border-white/10 card-hover" data-testid={`feature-card-${index}`}>
                <CardContent className="p-6">
                  <div className="mb-4">{feature.icon}</div>
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Channels Section */}
      <section className="py-20 px-4 bg-card/50">
        <div className="container mx-auto text-center">
          <h2 className="text-4xl font-bold mb-6">Monitored Channels</h2>
          <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto">
            Automatically scan these platforms every hour
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {['Reddit', 'Quora', 'Hacker News', 'Product Hunt', 'Google Trends', 'Exa Research', 'LinkedIn', 'YouTube'].map((channel, idx) => (
              <div key={idx} className="glass p-6 rounded-xl border border-white/10" data-testid={`channel-${idx}`}>
                <p className="font-semibold text-lg">{channel}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <Card className="glass border-primary/20 p-12 text-center">
            <h2 className="text-4xl font-bold mb-4">Ready to Scale Your Traffic?</h2>
            <p className="text-xl text-muted-foreground mb-8">
              Join now and get daily actionable recommendations
            </p>
            <Link to="/register">
              <Button size="lg" className="gradient-primary btn-primary text-lg px-12 h-14" data-testid="footer-cta-btn">
                Start Free Trial
              </Button>
            </Link>
          </Card>
        </div>
      </section>
    </div>
  );
};
