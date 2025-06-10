import requests
from django.conf import settings
from django.core.cache import cache
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for fetching weather data from OpenWeatherMap API.
    """
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache_timeout = 1800  # 30 minutes

    def get_weather_by_zip(self, zip_code: str, country_code: str = "US") -> Optional[Dict]:
        """
        Get current weather data by ZIP code.
        
        Args:
            zip_code: ZIP code to get weather for
            country_code: Country code (default: US)
            
        Returns:
            Dict with weather data or None if error
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None

        cache_key = f"weather_zip_{zip_code}_{country_code}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        try:
            url = f"{self.base_url}/weather"
            params = {
                'zip': f"{zip_code},{country_code}",
                'appid': self.api_key,
                'units': 'imperial'  # Fahrenheit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            weather_data = self._format_weather_data(data)
            
            # Cache the result
            cache.set(cache_key, weather_data, self.cache_timeout)
            
            return weather_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching weather data for {zip_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in weather service: {e}")
            return None

    def get_weather_by_coordinates(self, latitude: float, longitude: float) -> Optional[Dict]:
        """
        Get current weather data by coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Dict with weather data or None if error
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None

        cache_key = f"weather_coords_{latitude}_{longitude}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'imperial'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            weather_data = self._format_weather_data(data)
            
            # Cache the result
            cache.set(cache_key, weather_data, self.cache_timeout)
            
            return weather_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching weather data for {latitude},{longitude}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in weather service: {e}")
            return None

    def get_forecast(self, zip_code: str, country_code: str = "US", days: int = 5) -> Optional[Dict]:
        """
        Get weather forecast by ZIP code.
        
        Args:
            zip_code: ZIP code to get forecast for
            country_code: Country code (default: US)
            days: Number of days for forecast (max 5 for free API)
            
        Returns:
            Dict with forecast data or None if error
        """
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
            return None

        cache_key = f"forecast_zip_{zip_code}_{country_code}_{days}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        try:
            url = f"{self.base_url}/forecast"
            params = {
                'zip': f"{zip_code},{country_code}",
                'appid': self.api_key,
                'units': 'imperial',
                'cnt': days * 8  # 8 forecasts per day (every 3 hours)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            forecast_data = self._format_forecast_data(data)
            
            # Cache the result
            cache.set(cache_key, forecast_data, self.cache_timeout)
            
            return forecast_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching forecast data for {zip_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in forecast service: {e}")
            return None

    def _format_weather_data(self, raw_data: Dict) -> Dict:
        """Format raw API response into standardized format."""
        try:
            return {
                'location': raw_data['name'],
                'temperature': round(raw_data['main']['temp']),
                'temperature_unit': 'F',
                'description': raw_data['weather'][0]['description'].title(),
                'humidity': raw_data['main']['humidity'],
                'wind_speed': round(raw_data.get('wind', {}).get('speed', 0), 1),
                'wind_unit': 'mph',
                'icon': raw_data['weather'][0]['icon'],
                'feels_like': round(raw_data['main']['feels_like']),
                'pressure': raw_data['main']['pressure'],
                'visibility': raw_data.get('visibility', 0) / 1000,  # Convert to km
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Error formatting weather data: {e}")
            return {}

    def _format_forecast_data(self, raw_data: Dict) -> Dict:
        """Format raw forecast API response into standardized format."""
        try:
            forecasts = []
            for item in raw_data['list'][:40]:  # Limit to 5 days
                forecasts.append({
                    'datetime': item['dt_txt'],
                    'temperature': round(item['main']['temp']),
                    'description': item['weather'][0]['description'].title(),
                    'icon': item['weather'][0]['icon'],
                    'humidity': item['main']['humidity'],
                    'wind_speed': round(item.get('wind', {}).get('speed', 0), 1),
                })
            
            return {
                'city': raw_data['city']['name'],
                'country': raw_data['city']['country'],
                'forecasts': forecasts
            }
        except (KeyError, TypeError) as e:
            logger.error(f"Error formatting forecast data: {e}")
            return {}