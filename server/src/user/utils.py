# user/utils/crs_risk.py


# from user.models import CRSRiskAuditLog


def calculate_crs_risk_score(profile):
    """
    Calculate CRS risk score and risk level from a Profile instance.
    Returns a tuple: (score, level)
    """
    score = 1

    # 1. Country risk
    high_risk_countries = {"IR", "PK", "NG", "SY", "RU", "UA", "KP"}
    if profile.tax_residency_country in high_risk_countries:
        score += 30

    # 2. Multiple citizenships
    if profile.has_multiple_citizenships:
        score += 30

    # 3. Politically Exposed Person
    if profile.is_pep:
        score += 40

    # 4. Source of funds
    risky_sources = {"crypto", "gambling", "unverifiable"}
    if (profile.source_of_funds or "").strip().lower() in risky_sources:
        score += 25

    # 5. Manual KYC
    if profile.manual_kyc_required:
        score += 20

    # Risk level
    if score > 75:
        level = "Very High"
    elif score > 50:
        level = "High"
    elif score > 25:
        level = "Medium"
    else:
        level = "Low"

    return score, level

# def update_crs_risk(self, changed_by=None, reason=None):
#     old_score = self.crs_risk_score
#     old_level = self.crs_risk_level

#     new_score, new_level = calculate_crs_risk_score(self)

#     if new_score != old_score or new_level != old_level:
#         # Save audit log
#         CRSRiskAuditLog.objects.create(
#             user=self,
#             changed_by=changed_by,
#             previous_score=old_score,
#             new_score=new_score,
#             previous_level=old_level,
#             new_level=new_level,
#             reason=reason
#         )

#     self.crs_risk_score = new_score
#     self.crs_risk_level = new_level
#     self.save()
