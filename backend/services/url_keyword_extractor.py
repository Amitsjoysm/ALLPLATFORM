"""
URL Keyword Extractor Service
Extracts keywords and SEO insights from URLs using AI
"""
import logging
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from groq import Groq
from config import settings

logger = logging.getLogger(__name__)


class URLKeywordExtractor:
    """Extract keywords and analyze SEO from URLs"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"
    
    async def fetch_url_content(self, url: str) -> Dict[str, Any]:
        """Fetch and parse URL content"""
        try:
            # Normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            logger.info(f"Fetching content from: {url}")
            
            # Fetch URL with timeout
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = await client.get(url, headers=headers)
                response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract metadata
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ''
            
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '').strip() if meta_desc else ''
            
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            meta_keywords_text = meta_keywords.get('content', '').strip() if meta_keywords else ''
            
            # Extract headings
            h1_tags = [h1.get_text().strip() for h1 in soup.find_all('h1')]
            h2_tags = [h2.get_text().strip() for h2 in soup.find_all('h2')]
            
            # Extract main content (paragraphs)
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 50]
            content_text = ' '.join(paragraphs[:10])  # First 10 paragraphs
            
            # Extract links
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            internal_links = [link for link in links if urlparse(url).netloc in link]
            external_links = [link for link in links if urlparse(url).netloc not in link and link.startswith('http')]
            
            # Social media detection
            social_platforms = {
                'instagram': 'instagram.com' in url.lower(),
                'linkedin': 'linkedin.com' in url.lower(),
                'facebook': 'facebook.com' in url.lower(),
                'twitter': 'twitter.com' in url.lower() or 'x.com' in url.lower(),
                'youtube': 'youtube.com' in url.lower(),
            }
            
            return {
                'url': url,
                'title': title_text,
                'description': description,
                'meta_keywords': meta_keywords_text,
                'h1_tags': h1_tags,
                'h2_tags': h2_tags,
                'content': content_text[:3000],  # Limit to 3000 chars
                'internal_links_count': len(internal_links),
                'external_links_count': len(external_links),
                'social_platforms': social_platforms,
                'is_social_media': any(social_platforms.values())
            }
        
        except Exception as e:
            logger.error(f"Error fetching URL content: {e}")
            raise Exception(f"Failed to fetch URL: {str(e)}")
    
    async def extract_keywords(self, url: str) -> Dict[str, Any]:
        """Extract keywords from URL using AI"""
        try:
            # Fetch content
            content_data = await self.fetch_url_content(url)
            
            # Prepare prompt for AI
            prompt = f"""Analyze this webpage and extract important keywords for traffic opportunity scanning.

URL: {content_data['url']}
Title: {content_data['title']}
Description: {content_data['description']}
Meta Keywords: {content_data['meta_keywords']}
H1 Tags: {', '.join(content_data['h1_tags'][:3])}
H2 Tags: {', '.join(content_data['h2_tags'][:5])}
Content Preview: {content_data['content'][:1500]}

Extract:
1. Primary business/product keywords (5-10 keywords)
2. Industry/niche keywords
3. Target audience keywords
4. Problem/solution keywords
5. Competitor-related keywords

Return a JSON object with:
{{
    "primary_keywords": ["keyword1", "keyword2", ...],
    "industry": "industry name",
    "niche": "specific niche",
    "target_audience": ["audience1", "audience2"],
    "problems_solving": ["problem1", "problem2"],
    "business_type": "SaaS/E-commerce/Blog/Service/etc",
    "recommended_search_terms": ["search term 1", "search term 2", ...]
}}

Focus on keywords that would help find traffic opportunities on Reddit, Quora, Twitter, LinkedIn, etc."""

            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SEO and keyword research specialist. Extract relevant keywords for traffic opportunity scanning. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            import json
            # Remove markdown code blocks if present
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            extracted_data = json.loads(result_text)
            
            # Compile all keywords
            all_keywords = []
            all_keywords.extend(extracted_data.get('primary_keywords', []))
            all_keywords.extend(extracted_data.get('recommended_search_terms', []))
            all_keywords.extend(extracted_data.get('problems_solving', []))
            
            # Remove duplicates and clean
            all_keywords = list(set([kw.strip().lower() for kw in all_keywords if kw]))
            
            return {
                'url': url,
                'extracted_keywords': all_keywords[:20],  # Top 20
                'industry': extracted_data.get('industry', ''),
                'niche': extracted_data.get('niche', ''),
                'target_audience': extracted_data.get('target_audience', []),
                'problems_solving': extracted_data.get('problems_solving', []),
                'business_type': extracted_data.get('business_type', ''),
                'metadata': content_data
            }
        
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            raise Exception(f"Failed to extract keywords: {str(e)}")
    
    async def analyze_seo(self, url: str) -> Dict[str, Any]:
        """Comprehensive SEO analysis with recommendations"""
        try:
            # Fetch content
            content_data = await self.fetch_url_content(url)
            
            # Basic SEO checks
            seo_issues = []
            seo_warnings = []
            seo_good = []
            
            # Title analysis
            if not content_data['title']:
                seo_issues.append("Missing page title")
            elif len(content_data['title']) < 30:
                seo_warnings.append("Page title is too short (< 30 chars)")
            elif len(content_data['title']) > 60:
                seo_warnings.append("Page title is too long (> 60 chars)")
            else:
                seo_good.append("Page title length is optimal")
            
            # Meta description
            if not content_data['description']:
                seo_issues.append("Missing meta description")
            elif len(content_data['description']) < 120:
                seo_warnings.append("Meta description is too short")
            elif len(content_data['description']) > 160:
                seo_warnings.append("Meta description is too long")
            else:
                seo_good.append("Meta description length is optimal")
            
            # H1 tags
            if not content_data['h1_tags']:
                seo_issues.append("Missing H1 tag")
            elif len(content_data['h1_tags']) > 1:
                seo_warnings.append("Multiple H1 tags found (should have only one)")
            else:
                seo_good.append("Single H1 tag found")
            
            # H2 tags
            if len(content_data['h2_tags']) < 2:
                seo_warnings.append("Very few H2 tags (content structure could be improved)")
            
            # Content length
            if len(content_data['content']) < 300:
                seo_warnings.append("Content is too short for good SEO")
            
            # Links
            if content_data['internal_links_count'] < 3:
                seo_warnings.append("Few internal links (improve site structure)")
            
            # Use AI for deeper analysis
            prompt = f"""Analyze this webpage for SEO and provide specific recommendations for improving organic traffic.

URL: {content_data['url']}
Title: {content_data['title']}
Description: {content_data['description']}
H1s: {', '.join(content_data['h1_tags'])}
H2s: {', '.join(content_data['h2_tags'][:5])}
Content: {content_data['content'][:1000]}

Provide actionable SEO recommendations in JSON format:
{{
    "content_gaps": ["gap1", "gap2", ...],
    "keyword_opportunities": ["keyword1", "keyword2", ...],
    "content_suggestions": ["Create blog post about X", "Add FAQ section", ...],
    "technical_recommendations": ["Add schema markup", "Optimize images", ...],
    "traffic_strategies": ["Answer questions on Reddit about X", "Create comparison content", ...]
}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert SEO consultant. Provide specific, actionable recommendations. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON
            import json
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            ai_recommendations = json.loads(result_text)
            
            # Calculate SEO score
            total_checks = len(seo_issues) + len(seo_warnings) + len(seo_good)
            seo_score = int((len(seo_good) / total_checks * 100)) if total_checks > 0 else 50
            
            return {
                'url': url,
                'seo_score': seo_score,
                'issues': seo_issues,
                'warnings': seo_warnings,
                'good_practices': seo_good,
                'content_gaps': ai_recommendations.get('content_gaps', []),
                'keyword_opportunities': ai_recommendations.get('keyword_opportunities', []),
                'content_suggestions': ai_recommendations.get('content_suggestions', []),
                'technical_recommendations': ai_recommendations.get('technical_recommendations', []),
                'traffic_strategies': ai_recommendations.get('traffic_strategies', []),
                'metadata': {
                    'title': content_data['title'],
                    'description': content_data['description'],
                    'h1_count': len(content_data['h1_tags']),
                    'h2_count': len(content_data['h2_tags']),
                    'internal_links': content_data['internal_links_count'],
                    'external_links': content_data['external_links_count']
                }
            }
        
        except Exception as e:
            logger.error(f"Error analyzing SEO: {e}")
            raise Exception(f"Failed to analyze SEO: {str(e)}")
