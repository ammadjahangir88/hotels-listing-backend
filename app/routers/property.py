from fastapi import Body, FastAPI, Response, status, HTTPException, Depends,APIRouter, Query
from sqlalchemy.orm import Session, joinedload,selectinload
from sqlalchemy import func
from ..database import get_db
from datetime import datetime, timedelta
from .. import models
import requests
import os
import pycountry
from sqlalchemy import asc
from fastapi_cache.decorator import cache
VFY_API_URL = "https://listofhousesv1.villaforyou.biz/cgi/jsonrpc-partner/listofhousesv1"
DATA_OF_HOUSES_URL = "https://dataofhousesv1.villaforyou.biz/cgi/jsonrpc-partner/dataofhousesv1"
AUTH_HEADER = {
    "Authorization": "Basic d2ludGVyc3BvcnRlbm5sOlBUY2Jza0c5YzFMSWJVbjFEeXVvSDh3VzFPQVR5TGk3",
    "Content-Type": "application/json"
}
PARTNER_CODE = "wintersportennl"
PARTNER_PASSWORD = "PTcbskG9c1LIbUn1DyuoH8wW1OATyLi7"


INTERHOME_API_URL = "https://ws.interhome.com/ih/b2b/V0100/accommodation/list"


INTERHOME_BASE_URL = "https://ws.interhome.com/ih/b2b/V0100/accommodation"
HEADERS = {
    "Accept": "application/json",
    "Token": "4qiaeFZnIm",
    "PartnerId": "NL1001715",
    "Cookie": "sap-usercontext=sap-client=051"
}
router=APIRouter(
    prefix='/property'
)
def get_country_name(code):
    try:
        return pycountry.countries.get(alpha_2=code.upper()).name
    except:
        return code

# @router.get("/")
# def intergerate_villa_for_you(db: Session = Depends(get_db)):
    list_payload = {
        "jsonrpc": "2.0",
        "method": "ListOfHousesV1",
        "params": {
            "PartnerCode": PARTNER_CODE,
            "PartnerPassword": PARTNER_PASSWORD
        },
        "id": 9206
    }

    list_response = requests.post(VFY_API_URL, headers=AUTH_HEADER, json=list_payload)
    if list_response.status_code != 200:
        raise HTTPException(
            status_code=list_response.status_code,
            detail=f"VillaForYou API error: {list_response.text}"
        )

    list_data = list_response.json()
    houses = list_data.get("result", [])
    house_codes = [house.get("HouseCode") for house in houses if house.get("HouseCode")]

    if not house_codes:
        raise HTTPException(status_code=404, detail="No house codes found")

    batch_size = 100
    saved_total = 0

    def chunks(lst, n):
        """Yield successive n-sized chunks from list."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    for batch_index, house_batch in enumerate(chunks(house_codes, batch_size), start=1):
        print(f"Processing batch {batch_index}: {len(house_batch)} houses")

        data_payload = {
            "jsonrpc": "2.0",
            "method": "DataOfHousesV1",
            "params": {
                "PartnerCode": PARTNER_CODE,
                "PartnerPassword": PARTNER_PASSWORD,
                "HouseCodes": house_batch,
                "Items": ["BasicInformationV1", "AvailabilityPeriodV1", "MediaV1"]
            },
            "id": 22770
        }

        try:
            detail_response = requests.post(
                DATA_OF_HOUSES_URL,
                headers=AUTH_HEADER,
                json=data_payload,
                timeout=(10, 600)
            )
        except requests.exceptions.RequestException as e:
            print(f"Batch {batch_index} failed: {e}")
            continue

        if detail_response.status_code != 200:
            print(f"Batch {batch_index} API error: {detail_response.text}")
            continue

        details = detail_response.json()
        result = details.get("result")
        if not result:
            print(f"Batch {batch_index} missing result, skipping...")
            continue

        houses_details = list(result.values()) if isinstance(result, dict) else result
        saved = 0

        for house in houses_details:
            basic = house.get("BasicInformationV1", house)
            media = house.get("MediaV1", {})
            availability_data = house.get("AvailabilityPeriodV1", [])

            house_code = basic.get("HouseCode") or house.get("HouseCode")
            if not house_code:
                continue

            name = basic.get("Name") or basic.get("HouseName") or ""
            location = basic.get("Location") or ""
            city = basic.get("City") or ""
            country_code = basic.get("Country") or ""
            country = get_country_name(country_code)
            max_persons = basic.get("MaxNumberOfPersons") or 0
            pets_allowed = bool(basic.get("MaxNumberOfPets") or basic.get("Pets") == True)
            price_per_night = basic.get("PricePerNight") or basic.get("PriceFrom") or 0.0
            bedrooms = basic.get("NumberOfBedrooms") or 0
            bathrooms = basic.get("BathRooms") or 0

            # Media
            images = []
            base_url = "https://media.villaforyou.net/photo/800/600/"
            if isinstance(media, list):
                for item in media:
                    contents = item.get("TypeContents", [])
                    for img in contents:
                        obj = img.get("Object")
                        if obj:
                            images.append(base_url + obj)

            # Amenities
            amenities = []
            ams = basic.get("Amenities") or basic.get("Facilities") or []
            if isinstance(ams, list):
                amenities = [str(a) for a in ams]

            # Availability
            availability_list = []
            for a in availability_data:
                start_date = a.get("ArrivalDate")
                end_date = a.get("DepartureDate")
                price = a.get("RentOnlyPrice")
                if start_date and end_date:
                    availability_list.append({
                        "start_date": start_date,
                        "end_date": end_date,
                        "price": price
                    })

            existing = db.query(models.Property).filter(models.Property.house_code == house_code).first()
            if existing:
                existing.name = name
                existing.location = location
                existing.city = city
                existing.country = country
                existing.max_persons = max_persons
                existing.pets_allowed = pets_allowed
                existing.price_per_night = float(price_per_night)
                existing.bedrooms = bedrooms
                existing.bathrooms = bathrooms
                existing.amenities = amenities
                existing.images = images
                existing.source = "VillaForYou"
                db.query(models.Availability).filter(models.Availability.property_id == existing.id).delete()
            else:
                obj = models.Property(
                    house_code=house_code,
                    name=name,
                    location=location,
                    city=city,
                    country=country,
                    max_persons=max_persons,
                    pets_allowed=pets_allowed,
                    price_per_night=float(price_per_night),
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                    amenities=amenities,
                    images=images,
                    source="VillaForYou",
                )
                db.add(obj)
                db.flush()

                for a in availability_list:
                    db.add(models.Availability(
                        property_id=obj.id,
                        start_date=a["start_date"],
                        end_date=a["end_date"],
                        price=a["price"]
                    ))

                saved += 1

        db.commit()
        saved_total += saved
        print(f"✅ Batch {batch_index} saved {saved} new records")

    return {"saved_total": saved_total, "total_batches": (len(house_codes) // batch_size) + 1}
TYPE_MAP = {
    "A": "Apartment",
    "H": "House",
    "B": "Boat",
    "G": "Guestroom"
}

DETAIL_TYPE_MAP = {
    "A": "Apartment/Hotel",
    "B": "Bungalow",
    "C": "Chalet",
    "D": "Divers",
    "F": "Farmhouse",
    "H": "Holiday village",
    "R": "Residence",
    "S": "Castle/Mansion",
    "V": "Villa",
    "Y": "Yacht"
}




@router.get("/")
def import_interhome_properties(db: Session = Depends(get_db)):
    list_url = f"{INTERHOME_BASE_URL}/list"
    response = requests.get(list_url, headers=HEADERS)

    if response.status_code != 200:
        return {"error": f"Failed to fetch accommodation list ({response.status_code})"}

    data = response.json()
    accommodation_list = data.get("accommodationItem", [])
    if not accommodation_list:
        return {"error": "No accommodations found"}

    code = [item.get("code") for item in accommodation_list if item.get("code")]
    codes= code[:1000]

    saved_properties = []

    for code in codes:
        detail_url = f"{INTERHOME_BASE_URL}/{code}"
        detail_response = requests.get(detail_url, headers=HEADERS)
        if detail_response.status_code != 200:
            print(f"Failed to fetch details for {code}")
            continue

        accommodation = detail_response.json().get("accommodation", {})
        if not accommodation:
            continue

        # 🏠 Prepare property object
        region = accommodation.get("region", [{}])[0].get("content") if accommodation.get("region") else None
        country = accommodation.get("country", [{}])[0].get("content") if accommodation.get("country") else None
        latitude = accommodation.get("address", {}).get("latitude")
        longitude = accommodation.get("address", {}).get("longitude")

        attributes = accommodation.get("attributes", {}).get("attribute", [])
        amenities = [a.get("name") for a in attributes if a.get("name")]

        images = [
            m.get("uri")
            for m in accommodation.get("media", {}).get("mediaItem", [])
            if m.get("uri")
        ]

        property_obj = models.Property(
            house_code=accommodation.get("code"),
            name=accommodation.get("name"),
            region=region,
            country=country,
            postal_code=accommodation.get("address", {}).get("postalCode"),
            latitude=latitude,
            longitude=longitude,
            type=accommodation.get("type"),
            type_name=TYPE_MAP.get(accommodation.get("type"), "Unknown"),
            detail_type=accommodation.get("detailType"),
            detail_type_name=DETAIL_TYPE_MAP.get(accommodation.get("detailType"), "Unknown"),
            max_persons=accommodation.get("pax"),
            bedrooms=accommodation.get("bedRooms", {}).get("number") if accommodation.get("bedRooms") else None,
            bathrooms=accommodation.get("bathRooms", {}).get("number") if accommodation.get("bathRooms") else None,
            toilets=accommodation.get("toilets", {}).get("number") if accommodation.get("toilets") else None,
            amenities=amenities,
            attributes=attributes,
            images=images,
            stars=float(accommodation.get("evaluation", {}).get("stars", 0)) if accommodation.get("evaluation") else None,
            location_rating=float(accommodation.get("evaluation", {}).get("location", 0)) if accommodation.get("evaluation") else None,
            outdoor_area_rating=float(accommodation.get("evaluation", {}).get("outdoorArea", 0)) if accommodation.get("evaluation") else None,
            interior_rating=float(accommodation.get("evaluation", {}).get("interior", 0)) if accommodation.get("evaluation") else None,
            tranquility_rating=float(accommodation.get("evaluation", {}).get("tranquility", 0)) if accommodation.get("evaluation") else None,
            kitchen_rating=float(accommodation.get("evaluation", {}).get("kitchen", 0)) if accommodation.get("evaluation") else None,
            access_road_rating=float(accommodation.get("evaluation", {}).get("accessRoad", 0)) if accommodation.get("evaluation") else None,
            inside_description=next(
                (d.get("value") for d in accommodation.get("descriptions", {}).get("description", []) if d.get("type") == "inside"),
                None
            ),
            outside_description=next(
                (d.get("value") for d in accommodation.get("descriptions", {}).get("description", []) if d.get("type") == "outside"),
                None
            ),
            brand=accommodation.get("brand"),
            domestic_currency=accommodation.get("domesticCurrency"),
            source="Interhome"
        )

        existing = db.query(models.Property).filter_by(house_code=property_obj.house_code).first()
        if not existing:
            db.add(property_obj)
            db.commit()
            db.refresh(property_obj)
            saved_properties.append(property_obj.house_code)
        else:
            property_obj = existing
            print(f"Property {code} already exists, updating availability.")

        # 💶 Fetch price list (availability) for this property
        price_list_url = f"{INTERHOME_BASE_URL}/pricelistalldur/{code}?SalesOffice=4040"
        price_response = requests.get(price_list_url, headers=HEADERS)

        if price_response.status_code == 200:
            price_data = price_response.json().get("priceList", {}).get("prices", {}).get("price", [])
            for p in price_data:
                check_in = p.get("checkInDate")
                duration = p.get("duration")
                price_value = p.get("price")
                check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
                end_date = check_in_date + timedelta(days=duration)
                if check_in and price_value and duration:
                    availability = models.Availability(
                        property_id=property_obj.id,
                        start_date=check_in,
                        end_date=end_date,  # Optional, can be calculated if needed
                        price=price_value,
                        duration=duration,
                        
                    )
                    db.add(availability)
        else:
            print(f"Failed to fetch price list for {code}")

    db.commit()

    return {
        "message": f"{len(saved_properties)} properties imported successfully with availabilities",
        "codes": saved_properties
    }



@router.get("/list-property")
@cache(expire=300) 
def property_listing(db: Session = Depends(get_db), limit: int = 6, offset: int = 0):
    """
    Fetch properties with only the first availability for each property.
    Paginated to avoid memory issues.
    """
    # Step 1: Fetch properties (paginated)
    properties = db.query(models.Property).limit(limit).offset(offset).all()

    result = []
    for prop in properties:
        # Step 2: Fetch only the first availability for this property
        first_avail = (
            db.query(models.Availability)
            .filter(models.Availability.property_id == prop.id)
            .order_by(asc(models.Availability.start_date))
            .first()
        )

        result.append({
            "id": prop.id,
            "house_code": prop.house_code,
            "name": prop.name,
            "region": prop.region,
            "country": prop.country,
            "postal_code": prop.postal_code,
            "latitude": prop.latitude,
            "longitude": prop.longitude,
            "type": prop.type,
            "detail_type": prop.detail_type,
            "type_name": prop.type_name,
            "detail_type_name": prop.detail_type_name,
            "max_persons": prop.max_persons,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "toilets": prop.toilets,
            "pets_allowed": prop.pets_allowed,
            "amenities": prop.amenities,
            "attributes": prop.attributes,
            "images": prop.images,
            "stars": prop.stars,
            "location_rating": prop.location_rating,
            "outdoor_area_rating": prop.outdoor_area_rating,
            "interior_rating": prop.interior_rating,
            "tranquility_rating": prop.tranquility_rating,
            "kitchen_rating": prop.kitchen_rating,
            "access_road_rating": prop.access_road_rating,
            "inside_description": prop.inside_description,
            "outside_description": prop.outside_description,
            "brand": prop.brand,
            "domestic_currency": prop.domestic_currency,
            "source": prop.source,
            "first_availability": {
                "id": first_avail.id,
                "start_date": first_avail.start_date,
                "end_date": first_avail.end_date,
                "price": first_avail.price,
                "duration": first_avail.duration
            } if first_avail else None
        })

    return {"properties": result}





@router.get("/{house_code}")
def property_details(house_code: str, db: Session = Depends(get_db)):
    # Query property by house_code
    property_obj = db.query(models.Property).filter(models.Property.house_code == house_code).first()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    return property_obj

@router.get("/api/check-availability")
def check_availability(
    range_from: str = Query(..., alias="range_from"),
    range_to: str = Query(..., alias="range_to")
):
    url = "https://ws.interhome.com/ih/b2b/V0100/accommodation/pricelistalldur/FR9340.300.4"
    params = {
        "SalesOffice": 4040,
        "RangeFromDate": range_from,
        "RangeToDate": range_to,
    }
    headers = {
        "Accept": "application/json",
        "Token": "4qiaeFZnIm",
        "PartnerId": "NL1001715",
    }

    response = requests.get(url, headers=headers, params=params)
    return response.json()

    
# @router.get("/")
# def read_property(db: Session = Depends(get_db)):
#     return {"message": "Hello, Ammad Here"}