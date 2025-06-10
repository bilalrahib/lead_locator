import openai
import google.generativeai as genai
from django.conf import settings
from django.contrib.auth import get_user_model
from typing import Dict, Optional, List
import logging
import time
from ..models import GeneratedScript, ScriptTemplate

User = get_user_model()
logger = logging.getLogger(__name__)

# Configure AI APIs
openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')
if getattr(settings, 'GEMINI_API_KEY', ''):
    genai.configure(api_key=getattr(settings, 'GEMINI_API_KEY', ''))


class ScriptGeneratorService:
    """
    Service for generating AI-powered sales scripts.
    """
    
    def __init__(self):
        self.openai_api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.gemini_api_key = getattr(settings, 'GEMINI_API_KEY', '')
        self.default_model = 'gpt-3.5-turbo'
        
    def generate_script(self, user: User, script_type: str, target_location_name: str,
                       target_location_category: str, target_machine_type: str,
                       custom_requirements: str = "") -> GeneratedScript:
        """
        Generate a new sales script using AI.
        """
        # Check if user can generate scripts
        if not self._can_generate_script(user):
            raise ValueError("User subscription does not allow script generation")
        
        # Get user's script count for this month
        if not self._has_script_quota(user):
            raise ValueError("Monthly script generation limit reached")
        
        # Generate the script content
        script_content = self._generate_script_content(
            script_type=script_type,
            location_name=target_location_name,
            location_category=target_location_category,
            machine_type=target_machine_type,
            custom_requirements=custom_requirements
        )
        
        # Create and save the script
        script = GeneratedScript.objects.create(
            user=user,
            script_type=script_type,
            target_location_name=target_location_name,
            target_location_category=target_location_category,
            target_machine_type=target_machine_type,
            script_content=script_content,
            ai_model_used=self._get_preferred_model()
        )
        
        logger.info(f"Generated {script_type} script for {user.email}: {target_location_name}")
        return script
    
    def regenerate_script(self, script: GeneratedScript, 
                         custom_requirements: str = "") -> GeneratedScript:
        """
        Regenerate an existing script with variations.
        """
        if not script.can_regenerate:
            raise ValueError("User subscription does not allow script regeneration")
        
        # Generate new content with variation
        new_content = self._regenerate_script_content(
            original_script=script,
            custom_requirements=custom_requirements
        )
        
        # Update the script
        script.script_content = new_content
        script.regeneration_count += 1
        script.ai_model_used = self._get_preferred_model()
        script.save()
        
        logger.info(f"Regenerated script {script.id} for {script.user.email}")
        return script
    
    def get_available_templates(self, user: User) -> List[ScriptTemplate]:
        """
        Get script templates available to the user based on subscription.
        """
        templates = ScriptTemplate.objects.filter(is_active=True)
        
        # Filter based on user subscription
        if not hasattr(user, 'subscription') or not user.subscription or user.subscription.plan.name == 'FREE':
            # Free users only get non-premium templates
            templates = templates.filter(is_premium=False)
        
        return list(templates.order_by('script_type', 'name'))
    
    def use_template(self, user: User, template: ScriptTemplate, 
                    target_location_name: str, target_location_category: str = "",
                    target_machine_type: str = "") -> GeneratedScript:
        """
        Create a script from a template with customization.
        """
        if not template.can_access(user):
            raise ValueError("User subscription does not allow access to this template")
        
        # Customize template content
        customized_content = self._customize_template(
            template=template,
            location_name=target_location_name,
            location_category=target_location_category or template.location_category,
            machine_type=target_machine_type or template.machine_type
        )
        
        # Create script from template
        script = GeneratedScript.objects.create(
            user=user,
            script_type=template.script_type,
            target_location_name=target_location_name,
            target_location_category=target_location_category or template.location_category,
            target_machine_type=target_machine_type or template.machine_type,
            script_content=customized_content,
            is_template=True,
            ai_model_used='template'
        )
        
        # Update template usage count
        template.usage_count += 1
        template.save(update_fields=['usage_count'])
        
        logger.info(f"Created script from template {template.name} for {user.email}")
        return script
    
    def _can_generate_script(self, user: User) -> bool:
        """Check if user can generate scripts based on subscription."""
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
        
        subscription = user.subscription
        if not subscription.is_active:
            return False
        
        # All paid plans can generate scripts
        return subscription.plan.script_templates_count > 0
    
    def _has_script_quota(self, user: User) -> bool:
        """Check if user has remaining script quota this month."""
        if not hasattr(user, 'subscription') or not user.subscription:
            return False
        
        subscription = user.subscription
        plan = subscription.plan
        
        # Count scripts generated this billing period
        from django.utils import timezone
        
        billing_start = subscription.start_date
        scripts_this_period = GeneratedScript.objects.filter(
            user=user,
            created_at__gte=billing_start,
            is_template=False  # Don't count template usage
        ).count()
        
        return scripts_this_period < plan.script_templates_count
    
    def _generate_script_content(self, script_type: str, location_name: str,
                                location_category: str, machine_type: str,
                                custom_requirements: str = "") -> str:
        """Generate script content using AI."""
        try:
            # Try to generate with AI first
            if self.gemini_api_key:
                return self._generate_with_gemini(script_type, location_name, location_category, machine_type, custom_requirements)
            elif self.openai_api_key:
                return self._generate_with_openai(script_type, location_name, location_category, machine_type, custom_requirements)
            else:
                # Return fallback script if no API keys
                return self._get_fallback_script(script_type, location_name, machine_type)
        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return self._get_fallback_script(script_type, location_name, machine_type)
    
    def _regenerate_script_content(self, original_script: GeneratedScript,
                                  custom_requirements: str = "") -> str:
        """Regenerate script content with variations."""
        try:
            if self.gemini_api_key or self.openai_api_key:
                # Add variation to the original script
                variation_prompt = f"Please rewrite this script with different wording: {original_script.script_content}"
                if custom_requirements:
                    variation_prompt += f" Additional requirements: {custom_requirements}"
                
                if self.gemini_api_key:
                    model = genai.GenerativeModel('gemini-2.0-flash')
                    response = model.generate_content(variation_prompt)
                    return response.text.strip()
                elif self.openai_api_key:
                    response = openai.ChatCompletion.create(
                        model=self.default_model,
                        messages=[
                            {"role": "system", "content": "You are a professional sales script writer."},
                            {"role": "user", "content": variation_prompt}
                        ],
                        max_tokens=1500,
                        temperature=0.7
                    )
                    return response.choices[0].message.content.strip()
            
            return original_script.script_content  # Return original if no API
        except Exception as e:
            logger.error(f"Error regenerating script: {e}")
            return original_script.script_content
    
    def _generate_with_gemini(self, script_type: str, location_name: str, 
                             location_category: str, machine_type: str, custom_requirements: str) -> str:
        """Generate content using Google Gemini."""
        prompt = self._build_prompt(script_type, location_name, location_category, machine_type, custom_requirements)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        return response.text.strip()
    
    def _generate_with_openai(self, script_type: str, location_name: str,
                             location_category: str, machine_type: str, custom_requirements: str) -> str:
        """Generate content using OpenAI."""
        prompt = self._build_prompt(script_type, location_name, location_category, machine_type, custom_requirements)
        response = openai.ChatCompletion.create(
            model=self.default_model,
            messages=[
                {"role": "system", "content": "You are a professional sales script writer specializing in vending machine placements."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    
    def _build_prompt(self, script_type: str, location_name: str, location_category: str,
                     machine_type: str, custom_requirements: str = "") -> str:
        """Build AI prompt for script generation."""
        machine_type_map = {
            'snack_machine': 'snack vending machine',
            'drink_machine': 'beverage vending machine',
            'claw_machine': 'claw/crane game machine',
            'hot_food_kiosk': 'hot food kiosk',
            'ice_cream_machine': 'ice cream vending machine',
            'coffee_machine': 'coffee vending machine',
            'combo_machine': 'combination snack and drink vending machine',
            'healthy_snack_machine': 'healthy snack vending machine',
            'fresh_food_machine': 'fresh food vending machine',
            'toy_machine': 'toy/prize vending machine'
        }
        
        machine_description = machine_type_map.get(machine_type, machine_type.replace('_', ' '))
        
        base_prompts = {
            'cold_call': f"""Create a professional cold call script for reaching out to {location_name}, a {location_category}. 
The goal is to propose placing a {machine_description} at their location. Include value proposition, revenue sharing benefits, and a clear call to action.""",
            
            'email': f"""Create a professional email template for reaching out to {location_name}, a {location_category}.
Propose placing a {machine_description} at their location. Include subject line, benefits, and next steps.""",
            
            'in_person': f"""Create an in-person sales script for proposing a {machine_description} placement at {location_name}, a {location_category}.
Include rapport building, value proposition, objection handling, and closing."""
        }
        
        prompt = base_prompts.get(script_type, base_prompts['email'])
        
        if custom_requirements:
            prompt += f"\n\nAdditional requirements: {custom_requirements}"
        
        return prompt
    
    def _get_preferred_model(self) -> str:
        """Get preferred AI model for generation."""
        if self.gemini_api_key:
            return 'gemini-2.0-flash'
        elif self.openai_api_key:
            return self.default_model
        else:
            return 'fallback'
    
    def _customize_template(self, template: ScriptTemplate, location_name: str,
                           location_category: str, machine_type: str) -> str:
        """Customize template with specific details."""
        content = template.content
        
        # Replace placeholders
        replacements = {
            '{LOCATION_NAME}': location_name,
            '{LOCATION_CATEGORY}': location_category,
            '{MACHINE_TYPE}': machine_type.replace('_', ' ').title(),
            '{YOUR_NAME}': '[Your Name]',
            '{YOUR_COMPANY}': '[Your Company]',
            '{YOUR_PHONE}': '[Your Phone]',
            '{YOUR_EMAIL}': '[Your Email]'
        }
        
        for placeholder, replacement in replacements.items():
            content = content.replace(placeholder, replacement)
        
        return content
    
    def _get_fallback_script(self, script_type: str, location_name: str, machine_type: str) -> str:
        """Get fallback script when AI generation fails."""
        fallbacks = {
            'cold_call': f"""Hello, this is [Your Name] from [Your Company]. 

I'm reaching out to {location_name} because I believe we have an opportunity that could generate additional revenue for your business with zero upfront cost.

We specialize in placing {machine_type.replace('_', ' ')} units at local businesses, and we handle all the maintenance, restocking, and customer service. You would earn a percentage of all sales with no investment required from you.

Would you be interested in learning more about how this could work for {location_name}?""",

            'email': f"""Subject: Additional Revenue Opportunity for {location_name}

Hello,

I hope this email finds you well. My name is [Your Name], and I represent [Your Company], a local vending machine placement company.

I'm reaching out to {location_name} because I believe we have an excellent opportunity to generate additional revenue for your business with zero upfront investment.

We specialize in placing {machine_type.replace('_', ' ')} units at businesses like yours. Here's what makes this opportunity attractive:

- No upfront costs or investment required
- We handle all maintenance, restocking, and customer service  
- You earn a percentage of all sales
- Professional, reliable equipment

I'd love to schedule a brief meeting to discuss how this could work specifically for {location_name}.

Best regards,
[Your Name]
[Your Company]
[Your Phone]
[Your Email]""",

            'in_person': f"""Hi there! I'm [Your Name] from [Your Company]. Thank you for taking a few minutes to speak with me.

I wanted to talk with you about an opportunity that could generate some additional revenue for {location_name} without any investment on your part.

We place {machine_type.replace('_', ' ')} units at local businesses, and we've found that businesses like yours often see great results. The way it works is simple - we provide the machine, handle all the maintenance and restocking, and you earn a percentage of the sales.

What's really great about this is that there's no upfront cost to you, and if for any reason it doesn't work out, we simply remove the machine.

Would you be interested in learning more about the specific details?"""
        }
        
        return fallbacks.get(script_type, fallbacks['email'])