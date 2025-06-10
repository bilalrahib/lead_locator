import requests
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from ..models import SearchHistory, LocationData, ExcludedLocation
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class LocationFinderService:
    """
    Service for finding vending machine locations using OpenStreetMap and Google Places API.
    """
    
    def __init__(self):
        self.google_api_key = getattr(settings, 'GOOGLE_PLACES_API_KEY', '')
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.nominatim_url = "https://nominatim.openstreetmap.org"
        
        # Machine type to OSM tag mapping
        self.machine_type_osm_mapping = {
            'snack_machine': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=cafe',
                'shop=convenience', 'amenity=fuel', 'building=office',
                'amenity=hospital', 'amenity=school', 'leisure=fitness_centre'
            ],
            'drink_machine': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=cafe',
                'shop=convenience', 'amenity=fuel', 'building=office',
                'amenity=hospital', 'amenity=school', 'leisure=fitness_centre'
            ],
            'claw_machine': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=cafe',
                'shop=hairdresser', 'amenity=fuel', 'shop=convenience',
                'amenity=ice_cream', 'amenity=bar'
            ],
            'hot_food_kiosk': [
                'amenity=restaurant', 'amenity=fast_food', 'building=office',
                'amenity=hospital', 'amenity=school', 'building=industrial'
            ],
            'ice_cream_machine': [
                'amenity=restaurant', 'amenity=fast_food', 'amenity=cafe',
                'shop=convenience', 'tourism=attraction', 'leisure=park'
            ],
            'coffee_machine': [
                'building=office', 'amenity=hospital', 'amenity=school',
                'building=industrial', 'amenity=university', 'amenity=library'
            ],
        }
        
        # Building types for filtering
        self.building_types_mapping = {
            'churches': 'amenity=place_of_worship',
            'factories': 'building=industrial',
            'hotels': 'tourism=hotel',
            'rehabilitation_centers': 'healthcare=rehabilitation',
            'gyms': 'leisure=fitness_centre',
            'hospitals': 'amenity=hospital',
            'towing_companies': 'shop=car_repair',
            'laundromats': 'shop=laundry',
            'office_buildings': 'building=office',
            'industrial_facilities': 'building=industrial',
            'daycares': 'amenity=childcare',
            'ymcas': 'leisure=fitness_centre',
            'restaurants': 'amenity=restaurant',
            'fast_food': 'amenity=fast_food',
            'barbershops': 'shop=hairdresser',
            'gas_stations': 'amenity=fuel',
            'coffee_shops': 'amenity=cafe',
        }

    def validate_zip_code(self, zip_code: str) -> bool:
        """
        Validate ZIP code using Nominatim geocoding.
        
        Args:
            zip_code: ZIP code to validate
            
        Returns:
            Boolean indicating if ZIP code is valid
        """
        try:
            url = f"{self.nominatim_url}/search"
            params = {
                'q': zip_code,
                'format': 'json',
                'countrycodes': 'us',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return len(data) > 0
            
        except Exception as e:
            logger.error(f"Error validating ZIP code {zip_code}: {e}")
            return False

    def get_coordinates_from_zip(self, zip_code: str) -> Optional[Tuple[float, float]]:
        """
        Get latitude and longitude coordinates from ZIP code using Nominatim.
        
        Args:
            zip_code: ZIP code to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if failed
        """
        try:
            url = f"{self.nominatim_url}/search"
            params = {
                'q': zip_code,
                'format': 'json',
                'countrycodes': 'us',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data:
                location = data[0]
                return float(location['lat']), float(location['lon'])
            
            return None
            
        except Exception as e:
            logger.error(f"Error geocoding ZIP code {zip_code}: {e}")
            return None

    def _get_osm_place_types_for_machine(self, machine_type: str, 
                                       building_types_filter: List[str] = None) -> List[str]:
        """
        Get OSM query tags for machine type and building filters.
        
        Args:
            machine_type: Type of vending machine
            building_types_filter: Optional building types filter
            
        Returns:
            List of OSM query tags
        """
        tags = self.machine_type_osm_mapping.get(machine_type, [])
        
        if building_types_filter:
            filtered_tags = []
            for building_type in building_types_filter:
                building_tag = self.building_types_mapping.get(building_type)
                if building_tag and building_tag in tags:
                    filtered_tags.append(building_tag)
            
            # If filter resulted in tags, use them; otherwise use all tags
            if filtered_tags:
                tags = filtered_tags
        
        return tags

    def _query_overpass(self, latitude: float, longitude: float, radius_miles: int,
                       osm_tags: List[str]) -> List[Dict]:
        """
        Query Overpass API for POIs based on location and tags.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_miles: Search radius in miles
            osm_tags: List of OSM tags to search for
            
        Returns:
            List of POI dictionaries
        """
        try:
            # Convert miles to meters
            radius_meters = int(radius_miles * 1609.34)
            
            # Build Overpass query
            tag_queries = []
            for tag in osm_tags:
                if '=' in tag:
                    key, value = tag.split('=', 1)
                    tag_queries.append(f'["{key}"="{value}"]')
                else:
                    tag_queries.append(f'["{tag}"]')
            
            # Construct query for each tag type
            queries = []
            for tag_query in tag_queries:
                queries.append(f'node{tag_query}(around:{radius_meters},{latitude},{longitude});')
                queries.append(f'way{tag_query}(around:{radius_meters},{latitude},{longitude});')
            
            overpass_query = f"""
            [out:json][timeout:25];
            (
                {' '.join(queries)}
            );
            out center meta;
            """
            
            response = requests.post(
                self.overpass_url,
                data=overpass_query,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get('elements', [])
            
        except Exception as e:
            logger.error(f"Error querying Overpass API: {e}")
            return []

    def _get_place_details_from_google(self, osm_poi: Dict) -> Optional[Dict]:
        """
        Enrich OSM POI with Google Places API data.
        
        Args:
            osm_poi: OpenStreetMap POI data
            
        Returns:
            Enriched place data or None if failed
        """
        if not self.google_api_key:
            logger.warning("Google Places API key not configured")
            return None
        
        try:
            # Get coordinates from OSM data
            if 'lat' in osm_poi and 'lon' in osm_poi:
                lat, lon = osm_poi['lat'], osm_poi['lon']
            elif 'center' in osm_poi:
                lat, lon = osm_poi['center']['lat'], osm_poi['center']['lon']
            else:
                return None
            
            # Try to find place using coordinates
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lon}",
                'radius': 50,  # 50 meter radius
                'key': self.google_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('results'):
                place = data['results'][0]  # Get the closest match
                
                # Get detailed place information
                place_details = self._get_google_place_details(place['place_id'])
                
                if place_details:
                    return self._format_google_place_data(place_details, osm_poi)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Google Places data: {e}")
            return None

    def _get_google_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get detailed place information from Google Places API.
        
        Args:
            place_id: Google Places place ID
            
        Returns:
            Detailed place data or None if failed
        """
        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                'place_id': place_id,
                'fields': 'name,formatted_address,formatted_phone_number,website,rating,user_ratings_total,business_status,opening_hours,geometry,types,url',
                'key': self.google_api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('result')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting Google Place details: {e}")
            return None

    def _format_google_place_data(self, google_data: Dict, osm_data: Dict) -> Dict:
        """
        Format Google Places data into standardized format.
        
        Args:
            google_data: Google Places API response
            osm_data: OpenStreetMap data
            
        Returns:
            Formatted place data
        """
        # Extract coordinates
        if 'geometry' in google_data and 'location' in google_data['geometry']:
            location = google_data['geometry']['location']
            latitude = location['lat']
            longitude = location['lng']
        else:
            # Fallback to OSM coordinates
            if 'lat' in osm_data and 'lon' in osm_data:
                latitude = osm_data['lat']
                longitude = osm_data['lon']
            elif 'center' in osm_data:
                latitude = osm_data['center']['lat']
                longitude = osm_data['center']['lon']
            else:
                latitude = None
                longitude = None
        
        # Extract business hours
        business_hours = ""
        if 'opening_hours' in google_data and 'weekday_text' in google_data['opening_hours']:
            business_hours = "\n".join(google_data['opening_hours']['weekday_text'])
        
        # Determine business status
        status_mapping = {
            'OPERATIONAL': 'operational',
            'CLOSED_TEMPORARILY': 'closed_temporarily',
            'CLOSED_PERMANENTLY': 'closed_permanently'
        }
        business_status = status_mapping.get(
            google_data.get('business_status', 'UNKNOWN'),
            'unknown'
        )
        
        # Extract categories
        osm_category = self._extract_osm_category(osm_data)
        google_category = google_data.get('types', [])
        
        return {
            'name': google_data.get('name', osm_data.get('tags', {}).get('name', 'Unknown')),
            'address': google_data.get('formatted_address', ''),
            'latitude': latitude,
            'longitude': longitude,
            'phone': google_data.get('formatted_phone_number', ''),
            'website': google_data.get('website', ''),
            'business_hours_text': business_hours,
            'google_place_id': google_data.get('place_id', ''),
            'google_rating': google_data.get('rating'),
            'google_user_ratings_total': google_data.get('user_ratings_total'),
            'google_business_status': business_status,
            'maps_url': google_data.get('url', ''),
            'category': osm_category,
            'detailed_category': ', '.join(google_category[:3]) if google_category else '',
            'osm_data': osm_data,
            'google_data': google_data,
        }

    def _extract_osm_category(self, osm_data: Dict) -> str:
        """Extract category from OSM data."""
        tags = osm_data.get('tags', {})
        
        # Priority order for category extraction
        category_keys = ['amenity', 'shop', 'building', 'leisure', 'tourism', 'healthcare']
        
        for key in category_keys:
            if key in tags:
                return f"{key}:{tags[key]}"
        
        return 'unknown'

    def find_nearby_places(self, user: User, zip_code: str, radius: int,
                          machine_type: str, building_types_filter: List[str] = None,
                          max_results: int = 20) -> SearchHistory:
        """
        Main method to find nearby vending machine locations.
        
        Args:
            user: User performing the search
            zip_code: ZIP code for search center
            radius: Search radius in miles
            machine_type: Type of vending machine
            building_types_filter: Optional building types filter
            max_results: Maximum number of results to return
            
        Returns:
            SearchHistory instance with LocationData results
        """
        # Validate ZIP code and get coordinates
        coordinates = self.get_coordinates_from_zip(zip_code)
        if not coordinates:
            raise ValueError(f"Invalid ZIP code: {zip_code}")
        
        latitude, longitude = coordinates
        
        # Create search history record
        search_history = SearchHistory.objects.create(
            user=user,
            zip_code=zip_code,
            radius=radius,
            machine_type=machine_type,
            building_types_filter=building_types_filter or [],
            search_parameters={
                'latitude': latitude,
                'longitude': longitude,
                'max_results': max_results,
            }
        )
        
        try:
            # Get OSM tags for the machine type and filters
            osm_tags = self._get_osm_place_types_for_machine(
                machine_type, building_types_filter
            )
            
            # Query Overpass API for POIs
            logger.info(f"Searching for {machine_type} near {zip_code} within {radius} miles")
            osm_pois = self._query_overpass(latitude, longitude, radius, osm_tags)
            
            logger.info(f"Found {len(osm_pois)} POIs from OpenStreetMap")
            
            # Get excluded place IDs for this user
            excluded_place_ids = set(
                ExcludedLocation.objects.filter(user=user).values_list(
                    'google_place_id', flat=True
                )
            )
            
            # Get previously seen place IDs for duplicate prevention
            seen_place_ids = set(
                LocationData.objects.filter(
                    search_history__user=user
                ).exclude(
                    google_place_id=''
                ).values_list('google_place_id', flat=True)
            )
            
            locations = []
            processed_place_ids = set()
            
            for osm_poi in osm_pois:
                if len(locations) >= max_results:
                    break
                
                # Enrich with Google Places data
                place_data = self._get_place_details_from_google(osm_poi)
                
                if not place_data:
                    continue
                
                google_place_id = place_data.get('google_place_id', '')
                
                # Skip if no place ID or already processed
                if not google_place_id or google_place_id in processed_place_ids:
                    continue
                
                # Skip if excluded or already seen
                if google_place_id in excluded_place_ids or google_place_id in seen_place_ids:
                    continue
                
                processed_place_ids.add(google_place_id)
                
                # Check if location has contact information
                has_phone = bool(place_data.get('phone'))
                has_email = bool(place_data.get('email'))  # Note: Google rarely provides email
                
                # Skip locations without any contact info (as per requirements)
                if not (has_phone or has_email):
                    continue
                
                # Create LocationData instance
                location = LocationData(
                    search_history=search_history,
                    name=place_data['name'],
                    category=place_data['category'],
                    detailed_category=place_data['detailed_category'],
                    address=place_data['address'],
                    latitude=Decimal(str(place_data['latitude'])) if place_data['latitude'] else Decimal('0'),
                    longitude=Decimal(str(place_data['longitude'])) if place_data['longitude'] else Decimal('0'),
                    phone=place_data['phone'],
                    email=place_data.get('email', ''),
                    website=place_data['website'],
                    business_hours_text=place_data['business_hours_text'],
                    google_place_id=google_place_id,
                    google_rating=place_data['google_rating'],
                    google_user_ratings_total=place_data['google_user_ratings_total'],
                    google_business_status=place_data['google_business_status'],
                    maps_url=place_data['maps_url'],
                    osm_data=place_data['osm_data'],
                    google_data=place_data['google_data'],
                )
                
                # Estimate foot traffic
                location.foot_traffic_estimate = FootTrafficEstimator.estimate_traffic(place_data)
                
                # Calculate priority score
                location.calculate_priority_score()
                
                locations.append(location)
                
                # Add small delay to respect API limits
                time.sleep(0.1)
            
            # Sort locations by priority score (highest first)
            locations.sort(key=lambda x: x.priority_score, reverse=True)
            
            # Bulk create location records
            LocationData.objects.bulk_create(locations)
            
            # Update search history with results count
            search_history.results_count = len(locations)
            search_history.save()
            
            logger.info(f"Created {len(locations)} location records for search {search_history.id}")
            
            return search_history
            
        except Exception as e:
            logger.error(f"Error in find_nearby_places: {e}")
            search_history.results_count = 0
            search_history.save()
            raise


class FootTrafficEstimator:
    """
    Service for estimating foot traffic at locations.
    """
    
    @staticmethod
    def estimate_traffic(place_data: Dict) -> str:
        """
        Estimate foot traffic based on place data.
        
        Args:
            place_data: Combined OSM and Google Places data
            
        Returns:
            Traffic estimate string
        """
        score = 0
        
        # Google rating influence
        rating = place_data.get('google_rating', 0)
        if rating:
            if rating >= 4.5:
                score += 15
            elif rating >= 4.0:
                score += 10
            elif rating >= 3.5:
                score += 5
        
        # Review count influence
        review_count = place_data.get('google_user_ratings_total', 0)
        if review_count:
            if review_count >= 500:
                score += 20
            elif review_count >= 100:
                score += 15
            elif review_count >= 50:
                score += 10
            elif review_count >= 10:
                score += 5
        
        # Category-based scoring
        detailed_category = place_data.get('detailed_category', '').lower()
        osm_category = place_data.get('category', '').lower()
        
        high_traffic_categories = [
            'gas_station', 'convenience_store', 'grocery', 'shopping_mall',
            'hospital', 'school', 'university', 'restaurant', 'fast_food',
            'transit_station', 'airport'
        ]
        
        medium_traffic_categories = [
            'office', 'hotel', 'gym', 'fitness', 'cafe', 'bank'
        ]
        
        for category in high_traffic_categories:
            if category in detailed_category or category in osm_category:
                score += 15
                break
        else:
            for category in medium_traffic_categories:
                if category in detailed_category or category in osm_category:
                    score += 8
                    break
        
        # Business status influence
        if place_data.get('google_business_status') == 'operational':
            score += 10
        
        # Map score to traffic level
        if score >= 40:
            return 'very_high'
        elif score >= 25:
            return 'high'
        elif score >= 15:
            return 'moderate'
        elif score >= 5:
            return 'low'
        else:
            return 'very_low'