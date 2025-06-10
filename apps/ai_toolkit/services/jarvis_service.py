# import logging
# from django.conf import settings
# from django.contrib.auth import get_user_model
# from typing import Dict, Optional, List
# import uuid
# import time
# from ..models import JarvisConversation

# User = get_user_model()
# logger = logging.getLogger(__name__)


# class JarvisService:
#     """
#     JARVIS AI Assistant service for paid plan users.
#     """
    
#     def __init__(self):
#         self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')
#         self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', '')
        
#     def chat(self, user: User, message: str, session_id: Optional[str] = None,
#              conversation_type: str = 'general') -> Dict:
#         """
#         Process a chat message with JARVIS.
#         """
#         # Check if user has access to JARVIS
#         if not self._can_access_jarvis(user):
#             raise ValueError("JARVIS AI Assistant is available for paid plan users only")
        
#         # Generate session ID if not provided
#         if not session_id:
#             session_id = str(uuid.uuid4())
        
#         start_time = time.time()
        
#         # For now, return a simple response
#         response = f"Hello! I'm JARVIS, your AI assistant. You asked: '{message}'. I'm here to help you with your vending machine business!"
        
#         # Calculate response time
#         response_time = int((time.time() - start_time) * 1000)
        
#         # Save conversation
#         conversation = JarvisConversation.objects.create(
#             user=user,
#             session_id=session_id,
#             user_message=message,
#             jarvis_response=response,
#             conversation_type=conversation_type,
#             ai_model_used='basic',
#             response_time_ms=response_time
#         )
        
#         return {
#             'response': response,
#             'session_id': session_id,
#             'conversation_id': str(conversation.id),
#             'conversation_type': conversation_type,
#             'response_time_ms': response_time
#         }
    
#     def generate_logo_prompt(self, user: User, business_name: str, style_preferences: str = "",
#                             color_preferences: str = "") -> Dict:
#         """Generate a logo creation prompt."""
#         if not self._can_access_jarvis(user):
#             raise ValueError("Logo generation is available for paid plan users only")
        
#         prompt = f"Create a professional logo for '{business_name}', a vending machine business."
#         if style_preferences:
#             prompt += f" Style: {style_preferences}."
#         if color_preferences:
#             prompt += f" Colors: {color_preferences}."
        
#         return {
#             'business_name': business_name,
#             'dall_e_prompt': prompt,
#             'style_suggestions': ['Modern', 'Classic', 'Playful', 'Bold'],
#             'color_suggestions': [
#                 {"name": "Professional Blue", "colors": ["#2563EB", "#FFFFFF"]},
#                 {"name": "Trust Green", "colors": ["#059669", "#FFFFFF"]}
#             ]
#         }
    
#     def generate_social_media_content(self, user: User, platform: str, content_type: str,
#                                     business_focus: str = "", target_audience: str = "") -> Dict:
#         """Generate social media content."""
#         if not self._can_access_jarvis(user):
#             raise ValueError("Social media content generation is available for paid plan users only")
        
#         content = f"🎯 Growing your vending machine business! {business_focus} #VendingMachine #SmallBusiness #Entrepreneur"
        
#         return {
#             'platform': platform,
#             'content_type': content_type,
#             'content': content,
#             'conversation_id': str(uuid.uuid4()),
#             'hashtag_suggestions': ["#VendingMachine", "#SmallBusiness", "#Entrepreneur"]
#         }
    
#     def _can_access_jarvis(self, user: User) -> bool:
#         """Check if user can access JARVIS based on subscription."""
#         if not hasattr(user, 'subscription') or not user.subscription:
#             return False
        
#         subscription = user.subscription
#         if not subscription.is_active:
#             return False
        
#         # JARVIS is available for paid plans only
#         return subscription.plan.name != 'FREE'

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from typing import Dict, Optional, List
import uuid
import time
from ..models import JarvisConversation

# Handle AI API imports with graceful fallbacks
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

User = get_user_model()
logger = logging.getLogger(__name__)

# Configure AI APIs if available
if OPENAI_AVAILABLE:
    openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')

if GENAI_AVAILABLE and getattr(settings, 'GEMINI_API_KEY', ''):
    genai.configure(api_key=getattr(settings, 'GEMINI_API_KEY', ''))


class JarvisService:
    """
    JARVIS AI Assistant service for paid plan users.
    """
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.system_prompt = """You are JARVIS, an AI assistant specialized in helping vending machine and arcade operators grow their business. You are knowledgeable about:

- Vending machine placement strategies
- Location analysis and lead generation
- Sales techniques and customer outreach
- Revenue optimization and pricing
- Market research and competition analysis
- Business development for vending operations
- Arcade and entertainment machine operations

You provide practical, actionable advice while maintaining a professional yet friendly tone. Keep responses concise but informative, and always focus on helping users achieve their business goals."""

    def chat(self, user: User, message: str, session_id: Optional[str] = None,
             conversation_type: str = 'general') -> Dict:
        """
        Process a chat message with JARVIS.
        
        Args:
            user: User sending the message
            message: User's message
            session_id: Optional session ID for conversation continuity
            conversation_type: Type of conversation
            
        Returns:
            Dict with response and conversation details
        """
        # Check if user has access to JARVIS
        if not self._can_access_jarvis(user):
            raise ValueError("JARVIS AI Assistant is available for paid plan users only")
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        start_time = time.time()
        
        try:
            # Get conversation context
            context = self._get_conversation_context(user, session_id)
            
            # Generate response
            response = self._generate_response(message, context, conversation_type)
            
            # Calculate response time
            response_time = int((time.time() - start_time) * 1000)
            
            # Save conversation
            conversation = JarvisConversation.objects.create(
                user=user,
                session_id=session_id,
                user_message=message,
                jarvis_response=response,
                conversation_type=conversation_type,
                ai_model_used=self._get_preferred_model(),
                response_time_ms=response_time
            )
            
            logger.info(f"JARVIS conversation for {user.email}: {len(message)} chars in, {len(response)} chars out")
            
            return {
                'response': response,
                'session_id': session_id,
                'conversation_id': str(conversation.id),
                'conversation_type': conversation_type,
                'response_time_ms': response_time
            }
            
        except Exception as e:
            logger.error(f"JARVIS error for {user.email}: {e}")
            return {
                'response': "I'm experiencing some technical difficulties right now. Please try again in a moment.",
                'session_id': session_id,
                'error': True
            }
    
    def generate_logo_prompt(self, user: User, business_name: str, style_preferences: str = "",
                            color_preferences: str = "") -> Dict:
        """
        Generate a logo creation prompt for DALL-E or other image AI.
        
        Args:
            user: User requesting logo
            business_name: Name of the business
            style_preferences: Style preferences
            color_preferences: Color preferences
            
        Returns:
            Dict with logo prompt and suggestions
        """
        if not self._can_access_jarvis(user):
            raise ValueError("Logo generation is available for paid plan users only")
        
        prompt = self._build_logo_prompt(business_name, style_preferences, color_preferences)
        
        return {
            'business_name': business_name,
            'dall_e_prompt': prompt,
            'style_suggestions': self._get_logo_style_suggestions(),
            'color_suggestions': self._get_logo_color_suggestions()
        }
    
    def generate_social_media_content(self, user: User, platform: str, content_type: str,
                                    business_focus: str = "", target_audience: str = "") -> Dict:
        """
        Generate social media content.
        
        Args:
            user: User requesting content
            platform: Social media platform (facebook, instagram, twitter, linkedin)
            content_type: Type of content (post, story, caption)
            business_focus: Focus of the business
            target_audience: Target audience description
            
        Returns:
            Dict with generated content
        """
        if not self._can_access_jarvis(user):
            raise ValueError("Social media content generation is available for paid plan users only")
        
        content = self._generate_social_content(platform, content_type, business_focus, target_audience)
        
        # Save as JARVIS conversation
        session_id = str(uuid.uuid4())
        conversation = JarvisConversation.objects.create(
            user=user,
            session_id=session_id,
            user_message=f"Generate {content_type} for {platform}: {business_focus}",
            jarvis_response=content,
            conversation_type='social_media',
            ai_model_used=self._get_preferred_model()
        )
        
        return {
            'platform': platform,
            'content_type': content_type,
            'content': content,
            'conversation_id': str(conversation.id),
            'hashtag_suggestions': self._get_hashtag_suggestions(platform, business_focus)
        }
    
    def get_conversation_history(self, user: User, session_id: Optional[str] = None,
                               limit: int = 50) -> List[JarvisConversation]:
        """
        Get conversation history for a user.
        
        Args:
            user: User requesting history
            session_id: Optional specific session
            limit: Maximum number of conversations
            
        Returns:
            List of JarvisConversation objects
        """
        queryset = JarvisConversation.objects.filter(user=user)
        
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def _can_access_jarvis(self, user: User) -> bool:
        """Check if user can access JARVIS based on subscription."""
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
        
        subscription = user.subscription
        if not subscription.is_active:
            return False
        
        # JARVIS is available for paid plans only
        return subscription.plan.name != 'FREE'
    
    def _get_conversation_context(self, user: User, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversation context for continuity."""
        recent_conversations = JarvisConversation.objects.filter(
            user=user,
            session_id=session_id
        ).order_by('-created_at')[:limit]
        
        context = []
        for conv in reversed(recent_conversations):
            context.extend([
                {"role": "user", "content": conv.user_message},
                {"role": "assistant", "content": conv.jarvis_response}
            ])
        
        return context
    
    def _generate_response(self, message: str, context: List[Dict], 
                          conversation_type: str = 'general') -> str:
        """Generate AI response to user message."""
        # Build messages for AI
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add context if available
        if context:
            messages.extend(context[-10:])  # Last 10 exchanges
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Try Gemini first
            if GENAI_AVAILABLE and self.gemini_api_key:
                return self._generate_with_gemini(messages)
            
            # Fallback to OpenAI
            elif OPENAI_AVAILABLE and self.openai_api_key:
                return self._generate_with_openai(messages)
            
            else:
                # Intelligent fallback response based on message content
                return self._generate_fallback_response(message, conversation_type)
                
        except Exception as e:
            logger.error(f"Error generating JARVIS response: {e}")
            return self._generate_fallback_response(message, conversation_type)
    
    def _generate_with_gemini(self, messages: List[Dict]) -> str:
        """Generate response using Gemini."""
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Convert messages to Gemini format
            conversation_text = self.system_prompt + "\n\n"
            for msg in messages[1:]:  # Skip system message
                role = "Human" if msg["role"] == "user" else "Assistant"
                conversation_text += f"{role}: {msg['content']}\n"
            
            conversation_text += "Assistant:"
            
            response = model.generate_content(conversation_text)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _generate_with_openai(self, messages: List[Dict]) -> str:
        """Generate response using OpenAI."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _generate_fallback_response(self, message: str, conversation_type: str) -> str:
        """Generate intelligent fallback response when AI APIs are unavailable."""
        message_lower = message.lower()
        
        # Script generation responses
        if 'script' in message_lower or conversation_type == 'script_generation':
            return """I can help you create effective sales scripts! For vending machine placements, focus on these key elements:

1. **Value Proposition**: Emphasize no upfront costs and additional revenue
2. **Revenue Sharing**: Explain the commission structure clearly  
3. **Maintenance**: Highlight that you handle all servicing and restocking
4. **Risk-Free**: Mention that machines can be removed if not working out

Would you like me to help you craft a specific script for cold calls, emails, or in-person meetings?"""
        
        # Business advice responses
        elif any(word in message_lower for word in ['business', 'revenue', 'profit', 'location', 'placement']):
            return """Great question about vending business strategy! Here are some key insights:

**Location Success Factors:**
- High foot traffic (offices, schools, hospitals)
- Limited competition from nearby food options
- Stable business hours and customer base

**Revenue Optimization:**
- Research local preferences for product selection
- Monitor performance and adjust pricing regularly
- Build strong relationships with location owners

**Growth Strategies:**
- Focus on high-performing machine types in your area
- Reinvest profits into additional quality locations
- Consider seasonal product rotations

What specific aspect of your vending business would you like to explore further?"""
        
        # Pricing and financial responses
        elif any(word in message_lower for word in ['price', 'cost', 'money', 'commission', 'roi']):
            return """Smart to focus on the financial side! Here's what successful vending operators typically see:

**Typical Commission Rates:**
- Offices: 15-25% to location
- High-traffic venues: 25-35% to location  
- Premium locations: Up to 40% to location

**Key Metrics to Track:**
- Revenue per machine per month
- Restocking frequency and costs
- Location performance trends

**Pricing Strategy:**
- Research competitor pricing in your area
- Factor in location demographics
- Test price points and monitor sales impact

Would you like help calculating potential ROI for specific locations or machine types?"""
        
        # General business questions
        elif any(word in message_lower for word in ['help', 'advice', 'start', 'begin']):
            return """Hello! I'm JARVIS, your AI assistant for vending machine business success. I can help you with:

🎯 **Location Strategy** - Finding and evaluating potential placement sites
📝 **Sales Scripts** - Crafting effective outreach messages  
💰 **Financial Planning** - ROI calculations and pricing strategies
📊 **Business Growth** - Scaling and optimization tactics
🤝 **Relationship Building** - Maintaining location partnerships

What aspect of your vending business would you like to focus on today?"""
        
        # Default response
        else:
            return f"""I understand you're asking about: "{message}"

As your vending business AI assistant, I'm here to help with strategy, scripts, financial planning, and growth tactics. While my advanced AI features require API connectivity, I can still provide valuable insights based on industry best practices.

Could you tell me more specifically what aspect of your vending machine business you'd like assistance with? For example:
- Location prospecting and evaluation
- Sales script development  
- Revenue optimization
- Operational efficiency

Let me know how I can best support your business goals!"""
    
    def _get_preferred_model(self) -> str:
        """Get preferred AI model."""
        if GENAI_AVAILABLE and self.gemini_api_key:
            return 'gemini-2.0-flash'
        elif OPENAI_AVAILABLE and self.openai_api_key:
            return 'gpt-3.5-turbo'
        else:
            return 'fallback'
    
    def _build_logo_prompt(self, business_name: str, style_preferences: str, 
                          color_preferences: str) -> str:
        """Build DALL-E prompt for logo generation."""
        base_prompt = f"Professional logo design for '{business_name}', a vending machine business."
        
        style_elements = []
        if style_preferences:
            style_elements.append(f"Style: {style_preferences}")
        else:
            style_elements.append("clean, modern, professional style")
        
        if color_preferences:
            style_elements.append(f"Colors: {color_preferences}")
        else:
            style_elements.append("professional color scheme")
        
        style_elements.extend([
            "simple and memorable design",
            "suitable for business cards and signage",
            "vector-style illustration",
            "white background",
            "high contrast for visibility",
            "scalable design elements"
        ])
        
        return base_prompt + ", " + ", ".join(style_elements)
    
    def _get_logo_style_suggestions(self) -> List[str]:
        """Get logo style suggestions."""
        return [
            "Modern and minimalist",
            "Classic and professional", 
            "Playful and approachable",
            "Bold and strong",
            "Elegant and sophisticated",
            "Tech-inspired",
            "Retro/vintage style",
            "Industrial and robust",
            "Clean geometric",
            "Friendly and approachable"
        ]
    
    def _get_logo_color_suggestions(self) -> List[Dict]:
        """Get logo color suggestions."""
        return [
            {"name": "Professional Blue", "colors": ["#2563EB", "#FFFFFF"], "description": "Trustworthy and reliable"},
            {"name": "Trust Green", "colors": ["#059669", "#FFFFFF"], "description": "Growth and prosperity"},
            {"name": "Energy Orange", "colors": ["#EA580C", "#FFFFFF"], "description": "Dynamic and energetic"},
            {"name": "Classic Navy", "colors": ["#1E293B", "#FFFFFF"], "description": "Professional and timeless"},
            {"name": "Modern Purple", "colors": ["#7C3AED", "#FFFFFF"], "description": "Innovation and creativity"},
            {"name": "Bold Red", "colors": ["#DC2626", "#FFFFFF"], "description": "Attention-grabbing and powerful"},
            {"name": "Tech Teal", "colors": ["#0891B2", "#FFFFFF"], "description": "Modern and tech-forward"},
            {"name": "Warm Gray", "colors": ["#6B7280", "#FFFFFF"], "description": "Sophisticated and neutral"}
        ]
    
    def _generate_social_content(self, platform: str, content_type: str,
                                business_focus: str, target_audience: str) -> str:
        """Generate social media content."""
        platform_specs = {
            'facebook': {'max_length': 2000, 'tone': 'conversational', 'hashtag_limit': 5},
            'instagram': {'max_length': 2200, 'tone': 'visual', 'hashtag_limit': 30},
            'twitter': {'max_length': 280, 'tone': 'concise', 'hashtag_limit': 3},
            'linkedin': {'max_length': 1300, 'tone': 'professional', 'hashtag_limit': 5}
        }
        
        spec = platform_specs.get(platform, platform_specs['facebook'])
        
        # Generate content based on platform and type
        if GENAI_AVAILABLE and self.gemini_api_key:
            return self._generate_social_with_ai(platform, content_type, business_focus, target_audience, spec)
        elif OPENAI_AVAILABLE and self.openai_api_key:
            return self._generate_social_with_ai(platform, content_type, business_focus, target_audience, spec)
        else:
            return self._generate_social_fallback(platform, content_type, business_focus, target_audience, spec)
    
    def _generate_social_with_ai(self, platform: str, content_type: str,
                                business_focus: str, target_audience: str, spec: Dict) -> str:
        """Generate social content using AI."""
        prompt = f"""Create a {content_type} for {platform} about {business_focus}.

Target audience: {target_audience}
Tone: {spec['tone']}
Max length: {spec['max_length']} characters
Focus: Vending machine business

The content should be engaging, relevant to the vending machine industry, and encourage engagement. Include relevant emojis and a call-to-action."""

        try:
            if GENAI_AVAILABLE and self.gemini_api_key:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                return response.text.strip()
            elif OPENAI_AVAILABLE and self.openai_api_key:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a social media content creator specializing in business content for the vending machine industry."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.8
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating social content: {e}")
            return self._generate_social_fallback(platform, content_type, business_focus, target_audience, spec)
    
    def _generate_social_fallback(self, platform: str, content_type: str,
                                 business_focus: str, target_audience: str, spec: Dict) -> str:
        """Generate social content fallback."""
        focus_lower = business_focus.lower() if business_focus else "vending machine business"
        
        templates = {
            'facebook_post': f"""🎯 Growing your {focus_lower}? Here's what successful operators know:

✅ Location is everything - high foot traffic = higher profits
✅ Customer service builds long-term relationships  
✅ Regular restocking keeps machines profitable
✅ Data tracking helps optimize product selection

Ready to take your vending business to the next level? What's your biggest challenge right now? Drop a comment below! 👇

#VendingBusiness #SmallBusiness #Entrepreneur #PassiveIncome""",

            'instagram_post': f"""💡 {focus_lower.title()} Success Tips

🎯 Find high-traffic locations
💰 Negotiate fair revenue splits  
📊 Track performance metrics
🔄 Rotate products based on sales data
🤝 Build strong location relationships

What's your #1 vending machine tip? Share below! ⬇️

#VendingMachine #BusinessTips #Entrepreneur #SideHustle #PassiveIncome #SmallBiz #MoneyMaking #BusinessOwner #Success #VendingLife""",

            'twitter_post': f"""🎯 {focus_lower.title()} tip: Location beats everything else. 

High foot traffic + limited competition = 💰

What's your best performing location type?

#VendingBusiness #SmallBiz #Tips""",

            'linkedin_post': f"""The {focus_lower} industry continues to evolve with changing consumer preferences and technology.

Key success factors I've observed:
- Strategic location selection and relationship building
- Data-driven product mix optimization  
- Consistent service and maintenance schedules
- Understanding local market demographics

For {target_audience}, this represents an opportunity for diversified revenue streams with relatively low operational overhead.

What trends are you seeing in your market?

#VendingIndustry #SmallBusiness #Entrepreneurship #BusinessStrategy"""
        }
        
        key = f"{platform}_{content_type}"
        return templates.get(key, templates.get(f"{platform}_post", templates['facebook_post']))
    
    def _get_hashtag_suggestions(self, platform: str, business_focus: str) -> List[str]:
        """Get hashtag suggestions for social media content."""
        base_hashtags = [
            "#VendingMachine", "#SmallBusiness", "#Entrepreneur", 
            "#PassiveIncome", "#BusinessOwner", "#VendingBusiness"
        ]
        
        platform_specific = {
            'instagram': [
                "#BusinessLife", "#Hustle", "#SideHustle", "#MoneyMaking",
                "#Success", "#BusinessTips", "#VendingLife", "#SmallBiz",
                "#Entrepreneurship", "#BusinessGrowth"
            ],
            'twitter': ["#Business", "#StartUp", "#Success", "#SmallBiz"],
            'linkedin': [
                "#Business", "#Entrepreneurship", "#Investment", "#ROI",
                "#BusinessStrategy", "#SmallBusiness", "#Leadership"
            ],
            'facebook': [
                "#LocalBusiness", "#Community", "#SmallBiz", "#BusinessTips",
                "#Entrepreneurship"
            ]
        }
        
        hashtags = base_hashtags + platform_specific.get(platform, [])
        
        # Add focus-specific hashtags
        if business_focus:
            focus_lower = business_focus.lower()
            if "claw" in focus_lower:
                hashtags.extend(["#ClawMachine", "#ArcadeGames", "#Entertainment", "#Gaming"])
            elif "snack" in focus_lower:
                hashtags.extend(["#SnackVending", "#OfficeSnacks", "#ConvenienceFood"])
            elif "coffee" in focus_lower:
                hashtags.extend(["#CoffeeVending", "#OfficeCoffee", "#CoffeeLovers"])
            elif "healthy" in focus_lower:
                hashtags.extend(["#HealthySnacks", "#Wellness", "#HealthyEating"])
        
        # Return appropriate number for platform
        platform_limits = {
            'instagram': 20,
            'facebook': 8,
            'twitter': 5,
            'linkedin': 8
        }
        
        limit = platform_limits.get(platform, 8)
        return hashtags[:limit]