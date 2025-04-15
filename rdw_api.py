import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RDWApi:
    """
    Klasse voor communicatie met de RDW Open Data API voor voertuiggegevens
    """
    
    BASE_URL_VEHICLES = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"
    BASE_URL_FUEL = "https://opendata.rdw.nl/resource/8ys7-d773.json"
    
    @classmethod
    def search_by_license_plate(cls, license_plate):
        """
        Zoek voertuiginformatie op basis van kenteken
        
        Args:
            license_plate (str): Kenteken zonder streepjes, niet hoofdlettergevoelig
        
        Returns:
            dict: Voertuiginformatie of None als er geen overeenkomend voertuig is gevonden
        """
        try:
            # Verwijder streepjes en maak hoofdletters
            clean_plate = license_plate.replace("-", "").replace(" ", "").upper()
            
            # Vraag voertuiggegevens op
            response = requests.get(f"{cls.BASE_URL_VEHICLES}?kenteken={clean_plate}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    vehicle_data = data[0]
                    
                    # Haal brandstofgegevens op
                    fuel_info = cls.get_fuel_info(clean_plate)
                    
                    # Combineer voertuig- en brandstofgegevens
                    if fuel_info:
                        vehicle_data.update(fuel_info)
                    
                    # Pas veldnamen aan naar bruikbaar formaat
                    return cls._format_vehicle_data(vehicle_data)
                else:
                    logger.warning(f"Geen voertuig gevonden met kenteken: {clean_plate}")
            else:
                logger.error(f"API fout bij opvragen voertuig: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.exception(f"Fout bij opvragen voertuiggegevens: {str(e)}")
        
        return None
    
    @classmethod
    def get_fuel_info(cls, license_plate):
        """
        Haal brandstofgegevens op voor een kenteken
        
        Args:
            license_plate (str): Kenteken zonder streepjes, hoofdletters
            
        Returns:
            dict: Brandstofgegevens of None als niet gevonden
        """
        try:
            response = requests.get(f"{cls.BASE_URL_FUEL}?kenteken={license_plate}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    return data[0]
            
        except Exception as e:
            logger.error(f"Fout bij opvragen brandstofgegevens: {str(e)}")
        
        return None
    
    @classmethod
    def _format_vehicle_data(cls, raw_data):
        """
        Formatteert de ruwe API data naar een bruikbaar formaat voor onze applicatie
        
        Args:
            raw_data (dict): Ruwe data van de API
            
        Returns:
            dict: Geformatteerde voertuiggegevens
        """
        data = {}
        
        # Basis voertuiggegevens
        try:
            data["license_plate"] = raw_data.get("kenteken", "Onbekend")
            data["make"] = raw_data.get("merk", "Onbekend")
            data["model"] = raw_data.get("handelsbenaming", "Onbekend")
            
            # Jaar van eerste toelating (formaat: YYYYMMDD)
            if "datum_eerste_toelating" in raw_data:
                year_str = raw_data["datum_eerste_toelating"][:4]
                data["year"] = int(year_str) if year_str.isdigit() else None
            else:
                data["year"] = None
            
            # Kleur
            data["color"] = raw_data.get("eerste_kleur", "Onbekend")
            
            # Brandstoftype
            if "brandstof_omschrijving" in raw_data:
                data["fuel_type"] = raw_data.get("brandstof_omschrijving", "Onbekend")
            
            # Extra gegevens die nuttig kunnen zijn
            data["body_type"] = raw_data.get("carrosserie", "")
            data["engine_capacity"] = raw_data.get("cilinderinhoud", "")
            data["number_of_seats"] = raw_data.get("aantal_zitplaatsen", "")
            data["weight"] = raw_data.get("massa_ledig_voertuig", "")
            
        except Exception as e:
            logger.error(f"Fout bij formatteren voertuiggegevens: {str(e)}")
        
        return data


# Test functie
def test_api():
    """Test de RDW API met een geldig Nederlands kenteken"""
    # Voorbeeld kenteken (moet een geldig kenteken zijn)
    test_kenteken = "G107LP"  # Een voorbeeld kenteken
    
    results = RDWApi.search_by_license_plate(test_kenteken)
    if results:
        print(f"Voertuig gevonden: {results['make']} {results['model']} ({results['year']})")
        print(f"Kleur: {results['color']}")
        if 'fuel_type' in results:
            print(f"Brandstof: {results['fuel_type']}")
        print("Alle gegevens:", results)
    else:
        print(f"Geen voertuig gevonden met kenteken {test_kenteken}")


if __name__ == "__main__":
    # Test de API-functionaliteit
    test_api()