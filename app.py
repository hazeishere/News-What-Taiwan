from flask import Flask, render_template, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime
import json
from urllib.parse import urlparse
import traceback
import re
import g4f
import random

# Global variables for tracking
LAST_USED_MODEL = "Unknown"
AVAILABLE_MODELS = []
USE_G4F_CLIENT = False
USE_G4F_LEGACY = False
USER_PREFERRED_MODEL = None  # Store user's preferred model

try:
    from g4f.client import Client
    USE_G4F_CLIENT = True
    client = Client()
        
except (ImportError, Exception) as e:
    print(f"g4f client not available: {e}")
    USE_G4F_CLIENT = False
    try:
        # Try legacy g4f interface
        USE_G4F_LEGACY = True
        print(f"Using legacy g4f interface")
            
    except (ImportError, Exception) as e:
        print(f"Legacy g4f not available: {e}")
        USE_G4F_LEGACY = False

app = Flask(__name__)

# Helper function to get available models
def get_available_g4f_models():
    models = ["gpt-4o-mini", "gemini-2.0-flash", "claude-3.7-sonnet"]
    return models

# Store crawled articles
class ArticleStore:
    def __init__(self, storage_file="articles.json"):
        self.storage_file = storage_file
        self.articles = self._load_articles()
    
    def _load_articles(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_articles(self):
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.articles, f)
            print(f"Successfully saved {len(self.articles)} articles to {self.storage_file}")
        except Exception as e:
            print(f"Error saving articles to file: {e}")
            traceback.print_exc()
    
    def add_article(self, article):
        self.articles.append(article)
        self.save_articles()
    
    def get_articles(self):
        return sorted(self.articles, key=lambda x: x.get('crawled_at', ''), reverse=True)
    
    def get_article_by_id(self, article_id):
        for article in self.articles:
            if article.get('id') == article_id:
                return article
        return None
        
    def update_article(self, article_id, updates):
        for i, article in enumerate(self.articles):
            if article.get('id') == article_id:
                print(f"Updating article {article_id}")
                print(f"Before update keys: {', '.join(self.articles[i].keys())}")
                print(f"Update keys: {', '.join(updates.keys())}")
                self.articles[i].update(updates)
                print(f"After update keys: {', '.join(self.articles[i].keys())}")
                print(f"has_summary: {self.articles[i].get('has_summary')}")
                print(f"summary: {self.articles[i].get('summary', '')[:50]}...")
                self.save_articles()
                return True
        print(f"Article {article_id} not found for update")
        return False

# Initialize article store
article_store = ArticleStore()

def crawl_yahoo_news_tw():
    url = "https://tw.news.yahoo.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_headlines = []
        
        # Yahoo News articles are typically in cards with links and headings
        # We'll try different selectors to find news articles
        article_elements = soup.select('li.js-stream-content')
        
        # If the above selector doesn't work, try alternative selectors
        if not article_elements:
            article_elements = soup.select('.StreamMegaItem, .js-content-viewer')
        
        if not article_elements:
            article_elements = soup.select('div[data-test-locator="stream-item"]')
            
        if not article_elements:
            # Last resort: find all articles or links that might be news items
            article_elements = soup.select('ul.stream li, .y-card')
            
        for article in article_elements:
            # Find headline - try different selectors
            headline_elem = article.select_one('h3, h4, .js-content-viewer')
            if not headline_elem:
                headline_elem = article.select_one('a[data-test-locator="stream-item-title-link"]')
            if not headline_elem:
                headline_elem = article.select_one('a.thmb')
                    
            if not headline_elem:
                continue
            
            headline = headline_elem.get_text(strip=True)
            
            # Find link - try different approaches
            if headline_elem.name == 'a':
                link_elem = headline_elem
            else:
                link_elem = article.select_one('a')
                
            if not link_elem:
                continue
                
            link = link_elem.get('href', '')
            
            # Handle relative URLs
            if link and link.startswith('/'):
                link = f"https://tw.news.yahoo.com{link}"
            elif link and not link.startswith(('http://', 'https://')):
                link = f"https://tw.news.yahoo.com/{link}"
            
            # Skip if no valid link or headline
            if not headline or not link:
                continue
                
            # Generate article ID from URL
            article_id = str(abs(hash(link)))[-10:]
            
            # Find source (news outlet)
            source_elem = article.select_one('.provider-name, .provider-link, .source')
            source = source_elem.get_text(strip=True) if source_elem else "Yahoo奇摩新聞"
            
            # Skip if already exists
            if any(a.get('url') == link for a in article_store.articles):
                continue
                
            all_headlines.append({
                'title': headline,
                'url': link,
                'id': article_id,
                'source': source
            })
        
        # Randomly select up to 9 articles
        if all_headlines:
            selected_headlines = random.sample(all_headlines, min(9, len(all_headlines)))
            return selected_headlines
        return []
    except Exception as e:
        print(f"Error crawling Yahoo News TW: {e}")
        traceback.print_exc()
        return []

def extract_article_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # For Yahoo News URLs, we can use them directly
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title - Yahoo News specific selectors first
        title = None
        title_elem = soup.select_one('h1.caas-title-wrapper')
        if title_elem:
            title = title_elem.get_text(strip=True)
        
        # If Yahoo specific selector fails, try common patterns
        if not title:
            title_elem = soup.find('h1')
            if not title_elem:
                title_elem = soup.select_one('header h1, header h2')
            title = title_elem.get_text(strip=True) if title_elem else "無法找到標題"  # "Title not found" in Traditional Chinese
        
        # Extract content - Yahoo News specific selectors first
        paragraphs = []
        
        # Try the main article body selector for Yahoo News
        article_body = soup.select_one('.caas-body')
        if article_body:
            paragraphs = article_body.find_all('p')
        
        # If Yahoo specific selector fails, fall back to common patterns
        if not paragraphs:
            article_body = soup.find('article')
            if article_body:
                paragraphs = article_body.find_all('p')
            else:
                # Try common content div classes
                content_div = soup.find(['div', 'section'], class_=lambda c: c and any(x in str(c).lower() for x in ['content', 'article', 'story', 'text']))
                if content_div:
                    paragraphs = content_div.find_all('p')
                else:
                    # Fallback to all paragraphs
                    paragraphs = soup.find_all('p')
        
        content = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        return {
            'title': title,
            'content': content[:8000]  # Limit content length
        }
    except Exception as e:
        print(f"Error extracting content from {url}: {e}")
        traceback.print_exc()
        return {'title': '錯誤', 'content': f'無法擷取內容: {str(e)}'}  # Error message in Traditional Chinese

def analyze_with_claude(title, content):
    global USE_G4F_CLIENT, USE_G4F_LEGACY, LAST_USED_MODEL, AVAILABLE_MODELS
    
    prompt = f"""
    你是一位專業的新聞分析師，具有優秀的幽默感。以下是一則新聞文章。
    標題: {title}
    
    內容: {content}
    
    請提供:
    1. 一個諷刺幽默的翻譯版本，讓文章更容易理解且更有趣（200-500字元）
    2. 一個簡潔的3-5句話大綱
    3. 主要話題類別（政治、科技、健康等）
    4. 整體情感（正面、負面或中性）
    5. 提及的主要實體（人物、組織、地點）
    6. 使用markdown格式的核心要點，用3-5個要點突出最重要的資訊
    
    請以JSON格式提供回應，結構如下:
    {{
        "funny_translation": "你的幽默簡化版本",
        "summary": "你的摘要",
        "topic": "主要話題",
        "sentiment": "情感",
        "key_entities": ["實體1", "實體2", "實體3"],
        "core_points_markdown": "- 第一個要點\\n- 第二個要點\\n- 第三個要點"
    }}
    """
    
    try:
        response_text = ""
        
        # Get available models
        available_models = get_available_g4f_models()
        AVAILABLE_MODELS = available_models  # Update global list
        
        # Find the best available model
        selected_model = None
        
        # Use user preferred model if set and available
        if USER_PREFERRED_MODEL and USER_PREFERRED_MODEL in available_models:
            selected_model = USER_PREFERRED_MODEL
        else:
            # Otherwise use default selection logic
            for model in available_models:
                if any(model in avail_model for avail_model in available_models):
                    selected_model = next((avail_model for avail_model in available_models if model in avail_model), None)
                    break
        
        if not selected_model and available_models:
            selected_model = available_models[0]  # Use first available
        
        print(f"Selected model: {selected_model}")
        LAST_USED_MODEL = selected_model  # Update global tracking
        
        # Try g4f client if available
        if USE_G4F_CLIENT:
            try:
                response = client.chat.completions.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Handle different response formats
                if hasattr(response, 'choices') and response.choices:
                    response_text = response.choices[0].message.content
                else:
                    response_text = str(response)

                print("Used g4f client successfully")
                print(f"Response text: {response_text}")
            except Exception as e:
                print(f"g4f client error: {e}")
                USE_G4F_CLIENT = False  # Disable for next calls
        
        # Try legacy g4f as fallback
        if not response_text and USE_G4F_LEGACY:
            try:
                response_text = g4f.ChatCompletion.create(
                    model=selected_model,
                    messages=[{"role": "user", "content": prompt}],
                )
                print("Used legacy g4f successfully")
                print(f"Response text: {response_text}")
            except Exception as e:
                print(f"Legacy g4f error: {e}")
                USE_G4F_LEGACY = False  # Disable for next calls
        
        # If all methods failed, create a fallback response
        if not response_text:
            response_text = json.dumps({
                "funny_translation": "抱歉，無法生成幽默翻譯。AI模型目前無法使用。",
                "summary": "無法生成摘要。AI模型目前無法使用。",
                "topic": "未知",
                "sentiment": "中性",
                "key_entities": [],
                "core_points_markdown": "- 無法生成要點\\n- AI模型目前無法使用\\n- 請稍後再試"
            }, ensure_ascii=False)
            
        # Try to parse JSON from the response
        try:
            # Clean up response text by removing markdown code block markers if present
            if isinstance(response_text, str):
                # First try: Direct JSON parsing
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    # Second try: Remove markdown code block markers
                    cleaned_text = re.sub(r'^```(?:json)?\s*', '', response_text, flags=re.MULTILINE)
                    cleaned_text = re.sub(r'\s*```$', '', cleaned_text, flags=re.MULTILINE)
                    print(f"Cleaned text (removed code blocks): {cleaned_text[:100]}...")
                    
                    try:
                        result = json.loads(cleaned_text)
                    except json.JSONDecodeError:
                        # Third try: Extract JSON object with regex
                        json_match = re.search(r'(\{[\s\S]*\})', response_text)
                        if json_match:
                            extracted_json = json_match.group(1)
                            print(f"Extracted JSON: {extracted_json[:100]}...")
                            result = json.loads(extracted_json)
                        else:
                            # If all parsing attempts fail, raise to fall back to error handling
                            raise
            else:
                # If response_text is not a string, try direct parsing
                result = json.loads(response_text)
            
            # Validate all required fields are present
            required_fields = ["funny_translation", "summary", "topic", "sentiment", "key_entities", "core_points_markdown"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                for field in missing_fields:
                    if field == "funny_translation":
                        result[field] = "未提供幽默翻譯。"
                    elif field == "summary":
                        result[field] = "未提供摘要。"
                    elif field == "topic":
                        result[field] = "未知"
                    elif field == "sentiment":
                        result[field] = "中性"
                    elif field == "key_entities":
                        result[field] = []
                    elif field == "core_points_markdown":
                        result[field] = "- 未提供核心要點"
            
            if not response_text.strip():
                print(f"Empty response from model: {selected_model}")
                
            print(f"Response text: {response_text}")
            return result
        except:
            # If JSON parsing failed, return a formatted error response
            return {
                "funny_translation": "無法解析模型回應。似乎出現了技術問題。",
                "summary": "無法生成摘要，因為模型回應無法解析。",
                "topic": "未知",
                "sentiment": "中性",
                "key_entities": [],
                "core_points_markdown": "- 無法解析AI模型回應\\n- 可能是格式錯誤\\n- 請稍後再試"
            }
    except Exception as e:
        print(f"Error in analyze_with_claude: {e}")
        traceback.print_exc()
        return {
            "funny_translation": f"分析過程中出現錯誤: {str(e)}",
            "summary": "無法生成摘要，因為分析過程中出現錯誤。",
            "topic": "未知",
            "sentiment": "中性",
            "key_entities": [],
            "core_points_markdown": f"- 分析過程中出現錯誤\\n- 錯誤訊息: {str(e)}\\n- 請稍後再試"
        }

@app.route('/')
def home():
    return render_template('introduction.html')

@app.route('/articles')
def articles():
    return render_template('index.html', articles=article_store.get_articles())

@app.route('/article/<article_id>')
def view_article(article_id):
    article = article_store.get_article_by_id(article_id)
    if not article:
        return redirect(url_for('articles'))
    
    # Print article state before analysis
    print(f"Article before analysis: has_summary={article.get('has_summary')}, id={article_id}")
    
    # If article doesn't have a summary yet, fetch and analyze it
    if not article.get('has_summary'):
        try:
            # Fetch article content
            content_data = extract_article_content(article['url'])
            article['extracted_title'] = content_data['title']
            article['content'] = content_data['content']
            
            print(f"Extracted content length: {len(article['content'])}")
            
            # Analyze with AI
            if article['content']:
                def sanitize_text(text, max_length=3000):
                    if not text:
                        return ""
                    # Trim text if needed
                    if len(text) > max_length:
                        text = text[:max_length] + "..."
                    return text
                
                analysis = analyze_with_claude(sanitize_text(article['extracted_title']), sanitize_text(article['content']))
                
                # Print the analysis results
                print(f"Analysis results: {json.dumps(analysis, ensure_ascii=False)}")
                
                # Update article with analysis
                article.update({
                    'summary': analysis.get('summary', '無法生成摘要'),
                    'funny_translation': analysis.get('funny_translation', '無法生成幽默翻譯'),
                    'topic': analysis.get('topic', '未知'),
                    'sentiment': analysis.get('sentiment', '中性').lower(),
                    'key_entities': analysis.get('key_entities', []),
                    'core_points_markdown': analysis.get('core_points_markdown', '- 無法生成核心要點'),
                    'has_summary': True
                })
                
                # Save updated article
                update_success = article_store.update_article(article_id, article)
                print(f"Article update success: {update_success}")
                
                # Get updated article
                updated_article = article_store.get_article_by_id(article_id)
                print(f"Article after analysis: has_summary={updated_article.get('has_summary')}, summary={updated_article.get('summary')[:50]}...")
        except Exception as e:
            print(f"Error analyzing article: {e}")
            traceback.print_exc()
    
    # Check if the article has the required fields populated
    print(f"Article being sent to template: has_summary={article.get('has_summary')}")
    print(f"Article keys: {', '.join(article.keys())}")
    
    return render_template('article.html', article=article, ai_model=LAST_USED_MODEL, available_models=AVAILABLE_MODELS)

@app.route('/crawl', methods=['POST'])
def crawl():
    # Redirect to crawling page, which will handle the actual crawling process
    return redirect(url_for('perform_crawl'))

@app.route('/perform_crawl')
def perform_crawl():
    # Fetch latest headlines
    articles = crawl_yahoo_news_tw()
    
    # Process each headline
    for article in articles:
        # Skip if article already exists in store
        if any(a.get('url') == article['url'] for a in article_store.articles):
            continue
        
        # Parse domain from URL
        parsed_url = urlparse(article['url'])
        domain = parsed_url.netloc
        
        # Add article to store
        article_store.add_article({
            'id': article['id'],
            'title': article['title'],
            'url': article['url'],
            'domain': domain,
            'source': article.get('source', 'Yahoo奇摩新聞'),
            'has_summary': False,
            'summary': '點擊生成摘要',  # "Click to generate summary" in Traditional Chinese
            'topic': '未知',  # "Unknown" in Traditional Chinese
            'sentiment': '未知',  # "Unknown" in Traditional Chinese
            'key_entities': [],
            'crawled_at': datetime.now().isoformat()
        })
    
    return render_template('crawling.html', 
                          new_articles=articles, 
                          total_count=len(article_store.articles),
                          ai_model=LAST_USED_MODEL,
                          available_models=AVAILABLE_MODELS)

@app.route('/clear', methods=['POST'])
def clear_articles():
    article_store.articles = []
    article_store.save_articles()
    return redirect(url_for('articles'))

@app.route('/debug')
def debug_articles():
    return render_template('debug.html', 
                          articles=article_store.articles, 
                          ai_model=LAST_USED_MODEL,
                          available_models=AVAILABLE_MODELS)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global USER_PREFERRED_MODEL
    
    if request.method == 'POST':
        selected_model = request.form.get('selected_model')
        if selected_model:
            USER_PREFERRED_MODEL = selected_model
            return redirect(url_for('settings'))
    
    available_models = get_available_g4f_models()
    return render_template('settings.html', 
                          available_models=available_models,
                          preferred_model=USER_PREFERRED_MODEL,
                          last_used_model=LAST_USED_MODEL)

if __name__ == '__main__':
    app.run(debug=True)
