from enum import Enum

class ServiceCategory(Enum):
    """Service categories for faceted search"""
    HOUSING = "Housing & Registration"
    IDENTITY = "Identity & Travel"
    VEHICLES = "Vehicles & Driving"
    BUSINESS = "Business & Trade"
    FAMILY = "Family & Civil Status"
    IMMIGRATION = "Immigration & Visa"
    SOCIAL = "Social Services"
    EDUCATION = "Education"
    HEALTH = "Health & Insurance"
    OTHER = "Other Services"

class FormType(Enum):
    """Detected form types based on naming patterns"""
    APPLICATION = "Application Form"
    CERTIFICATE = "Certificate/Proof"
    INFORMATION = "Information Sheet"
    INCOME_PROOF = "Income Documentation"
    CHECKLIST = "Checklist/Requirements"
    SUPPORTING_DOC = "Supporting Document"
    UNKNOWN = "Other Form"

CATEGORY_KEYWORDS = {
    ServiceCategory.HOUSING: ["anmeldung", "ummeldung", "abmeldung", "wohnung", "wohngeld"],
    ServiceCategory.IDENTITY: ["reisepass", "passport", "ausweis", "id card"],
    ServiceCategory.VEHICLES: ["führerschein", "fahrzeug", "kfz", "driving"],
    ServiceCategory.BUSINESS: ["gewerbe", "business", "trade"],
    ServiceCategory.FAMILY: ["geburt", "heirat", "ehe", "marriage", "family"],
    ServiceCategory.IMMIGRATION: ["visum", "visa", "aufenthalt", "immigration"],
    ServiceCategory.SOCIAL: ["sozial", "unemployment", "benefit"],
    ServiceCategory.EDUCATION: ["schule", "universität", "education"],
    ServiceCategory.HEALTH: ["gesund", "health", "insurance"],
}
