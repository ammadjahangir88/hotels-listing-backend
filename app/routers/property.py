from fastapi import Body, FastAPI, Response, status, HTTPException, Depends,APIRouter
from sqlalchemy.orm import Session
from ..database import get_db

from ..import models
import requests
import os
import pycountry


VFY_API_URL = "https://listofhousesv1.villaforyou.biz/cgi/jsonrpc-partner/listofhousesv1"
DATA_OF_HOUSES_URL = "https://dataofhousesv1.villaforyou.biz/cgi/jsonrpc-partner/dataofhousesv1"
AUTH_HEADER = {
    "Authorization": "Basic d2ludGVyc3BvcnRlbm5sOlBUY2Jza0c5YzFMSWJVbjFEeXVvSDh3VzFPQVR5TGk3",
    "Content-Type": "application/json"
}
PARTNER_CODE = "wintersportennl"
PARTNER_PASSWORD = "PTcbskG9c1LIbUn1DyuoH8wW1OATyLi7"

router=APIRouter(
    prefix='/property'
)
def get_country_name(code):
    try:
        return pycountry.countries.get(alpha_2=code.upper()).name
    except:
        return code

@router.get("/")
def intergerate_villa_for_you(db: Session = Depends(get_db)):
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

    # Extract all house codes
    house_codes = [house.get("HouseCode") for house in houses if house.get("HouseCode")]
    if not house_codes:
        raise HTTPException(status_code=404, detail="No house codes found")

    data_payload = {
        "jsonrpc": "2.0",
        "method": "DataOfHousesV1",
        "params": {
            "PartnerCode": "wintersportennl",
            "PartnerPassword": "PTcbskG9c1LIbUn1DyuoH8wW1OATyLi7",
            "HouseCodes": house_codes[:100],
            "Items": ["BasicInformationV1", "AvailabilityPeriodV1", "MediaV1"]
        },
        "id": 22770
    }
    print("House Code is", house_codes)

    detail_response = requests.post(DATA_OF_HOUSES_URL, headers=AUTH_HEADER, json=data_payload, timeout=(10, 600))
    print("Details response is", detail_response)
    if detail_response.status_code != 200:
        raise HTTPException(
            status_code=detail_response.status_code,
            detail="Failed to fetch house details"
        )

    details = detail_response.json()
    result = details.get("result")

    if result is None:
        raise HTTPException(status_code=502, detail="VillaForYou response missing 'result'")

    # Result may be a list of houses or a dict keyed by HouseCode
    if isinstance(result, dict):
        houses_details = list(result.values())
    else:
        houses_details = result

    saved = 0

    for house in houses_details:
        # Defensive extraction with fallbacks
        basic = house.get("BasicInformationV1", house)
        media = house.get("MediaV1", {})
        availability_data = house.get("AvailabilityPeriodV1", [])

        house_code = basic.get("HouseCode") or house.get("HouseCode")
        if not house_code:
            continue

        name = basic.get("Name") or basic.get("HouseName") or basic.get("Title") or ""
        location = basic.get("Location") or basic.get("Region") or basic.get("Area") or ""
        city = basic.get("City") or basic.get("Town") or ""
        country_code = basic.get("Country") or ""
        country = get_country_name(country_code)
        max_persons = basic.get("MaxNumberOfPersons") or basic.get("MaxOccupancy") or 0
        pets_allowed = bool(basic.get("MaxNumberOfPets") or basic.get("Pets") == True)
        price_per_night = basic.get("PricePerNight") or basic.get("PriceFrom") or 0.0
        bedrooms = basic.get("NumberOfBedrooms") or 0
        bathrooms = basic.get("NumberOfBedrooms") or basic.get("BathRooms") or 0

        # Media arrays
        images = []
        base_url = "https://media.villaforyou.net/photo/800/600/"

        if isinstance(media, list):
            for item in media:
                contents = item.get("TypeContents", [])
                if isinstance(contents, list):
                    for img in contents:
                        obj = img.get("Object")
                        if obj:
                            images.append(base_url + obj)

        amenities = []
        ams = basic.get("Amenities") or basic.get("Facilities") or []
        if isinstance(ams, list):
            amenities = [str(a) for a in ams]
        availability_list = []
        # Availability periods -> flatten to list of strings
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

        # Upsert by house_code
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
            db.flush()  # to get obj.id before adding Availability

            for a in availability_list:
                db.add(models.Availability(
                property_id=obj.id,
                start_date=a["start_date"],
                end_date=a["end_date"],
                price=a["price"]
                ))

            saved += 1

    db.commit()
    return {"saved": saved}





# @router.get("/")
# def read_property(db: Session = Depends(get_db)):
#     return {"message": "Hello, Ammad Here"}