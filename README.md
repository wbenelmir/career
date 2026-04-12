# PROJECT: Django Application System – Recruitment Platform (UPDATED v7)

## OVERVIEW

Arabic RTL recruitment platform for managing applications to:
→ jobs + senior positions

Public terminology currently adopted in the platform:
- وظائف عليا
- مناصب عليا
- رتب

Internal poste_type values remain:
- transfer
- detachment
- head_office

The platform is NOT limited to "Head of Office".
It supports a broader recruitment workflow for multiple categories of positions.

System split:
1. PUBLIC (candidate side)
2. ADMIN (management side)

No authentication for candidates.

Tracking is handled via:
- tracking_code
- direct tracking link
- QR code

Notifications handled via:
- NotificationService
- NotificationLog
- email templates
- Celery async queue

---

## CURRENT STATE

✔ End-to-end workflow fully functional
✔ UX significantly improved across all main public pages
✔ Upload system enhanced (auto + manual)
✔ Review page aligned with workflow
✔ Final submission secured
✔ Success page improved
✔ Tracking pages improved
✔ PDF receipt implemented
✔ Public pages unified visually
✔ Email templates redesigned with stronger official branding
✔ Notification logging introduced
✔ Celery prepared/used for async email sending
✔ Admin refined in several areas
✔ django-import-export introduced
✔ Legal references prepared for structured data management

Current phase:
→ admin area refinement + data consistency + notification monitoring + production readiness

---

## APPLICATION FLOW (FINAL)

1. start_application
2. candidate_information
3. upload_documents
4. review_application
5. submit_application
6. success
7. tracking

---

## SESSION KEYS

- selected_poste_id
- candidate_id
- draft_application_id

Rules:
- draft is session-driven
- no return after submission
- session is cleared after successful final submission

---

## POSTE MODEL

Public routing uses:
→ slug (NOT id)

Internal types:
- transfer
- detachment
- head_office

Public labels:
- transfer → وظائف عليا
- detachment → مناصب عليا
- head_office → رتب

Only public/open postes should appear when:
- is_open=True
- deadline valid

Poste pages improved:
- home filters updated
- poste_list filters updated
- poste_detail aligned with new terminology

---

## LEGAL REFERENCE MODEL

Legal references are now part of the active data strategy.

Current direction:
- legal references managed from DB
- import/export supported
- intended public page is dynamic

Recommended / current fields:
- title
- reference_number
- reference_type
- published_date
- description
- document_url
- is_active
- display_order

reference_type is used for:
- classification
- admin filtering
- public filtering in legal_text page

Current legal reference page direction:
- only active references displayed
- sorted by display_order then date
- filter buttons generated from available active reference types
- no empty categories should be shown to users

---

## CANDIDATE PROFILE

Key fields:
- first_name / last_name
- gender
- date_of_birth / place_of_birth
- national_id_number (18 digits, unique)
- email / phone_number
- address / wilaya / commune
- current_administration
- current_position_grade
- current_function
- tenure_decision_date
- years_of_seniority
- years_of_effective_service

Removed logic:
- is_tenured_employee (deprecated)

Rules:
- tenure_decision_date required
- not in future
- commune must belong to selected wilaya
- eligibility logic tied to current grade/service rules

---

## FORMS

### ApplicationForm
- selects poste only
- filtered by open + deadline

### CandidateProfileForm
- full validation implemented
- improved UX:
  - placeholders
  - helper text
  - JS wilaya/commune logic

### Start Step Additions
- declaration_confirmation (required)
- captcha (django-simple-captcha)

---

## START APPLICATION UX

Includes:
- poste selection
- legal declaration (mandatory)
- data protection consent (Law 18-07)
- captcha verification

UX improvements:
- clear CTA
- improved checkbox visibility
- improved captcha readability
- no duplicate titles
- poste terminology aligned with updated public labels

---

## DOCUMENT UPLOAD

- auto upload supported
- manual upload button supported
- file replacement enabled
- status updates in real-time
- file naming normalized
- validation:
  - size
  - format
  - requirement-based constraints

---

## REVIEW PAGE

Display only:
- candidate summary
- documents summary
- completeness state

Submission happens ONLY via:
→ submit_application

---

## SUBMISSION RULES

Allowed only if:
- status = DRAFT
- required documents complete

Then:
- status → SUBMITTED
- generate application_number
- generate tracking_code
- create tracking entry
- clear session
- send async notifications

Important:
- submitted email should be sent separately from generic status update
- generic status update should not be duplicated at submit time

---

## SUCCESS PAGE

Shows:
- application number
- tracking code
- poste
- QR code
- PDF receipt
- direct tracking link

UX improvements:
- clearer preservation of tracking data
- copy tracking code support
- better CTA hierarchy
- stronger post-submission guidance

---

## TRACKING

No login required

User sees:
- current status
- visible timeline only
- rejection reason when allowed / applicable

Tracking UX improvements:
- stronger status presentation
- timeline clarified
- direct access from success page
- better candidate-facing messaging

---

## EMAIL / NOTIFICATIONS

Notification architecture now matters as a first-class system area.

Current structure:
- NotificationService handles email building/sending
- NotificationLog stores delivery attempts and results
- Celery used/prepared for async dispatch
- management command used for template testing without repeating the application flow

Current email templates:
- application_submitted.html
- application_status_update.html
- interview_scheduled.html
- admin_new_application.html

Current template direction:
- Arabic RTL
- stronger ministry branding
- unified visual identity
- email_base.html introduced for shared structure
- public-facing templates are official, minimal, and ministry-aligned

Operational rules:
- candidate submission email sent after final submit
- admin new application email sent after final submit
- later lifecycle statuses may trigger status update emails
- interview scheduling has a dedicated email
- NotificationLog should remain tied to the related application when possible

---

## PUBLIC PAGES

Improved and visually unified:
- home
- poste_list
- poste_detail
- about_ministry
- legal_text
- success
- tracking form
- tracking result

Design principles:
- clean
- official
- Arabic RTL
- minimal
- consistent
- no unnecessary redesign

---

## ADMIN SIDE

Admin direction is now stronger and more data-oriented.

Current/admin improvements:
- Arabic-first wording in admin actions and labels where appropriate
- better PosteAdmin display
- improved LegalReferenceAdmin
- NotificationLog model/admin introduced and refined
- import/export support introduced
- structured handling for legal references
- legal visibility and ordering prepared
- legal reference import through Excel now part of workflow

django-import-export used/planned for:
- locations
- notifications
- legal references
- postes

Next main focus:
→ admin area refinement

Likely admin priorities next:
- usability of admin dashboards/forms
- NotificationLog visibility / filtering
- resend / monitoring options later if needed
- stronger legal/poste data management
- production-friendly data administration

---

## IMPORTANT RULES

- No return after submission
- incomplete = missing OR invalid
- rejection requires reason
- candidate sees only visible notes
- public legal page should not depend on hardcoded legal text anymore
- legal references should be controlled from DB
- only categories containing active legal references should be shown publicly
- email templates should remain unified and official
- avoid duplicate notification side effects

---

## CURRENT FOCUS

- admin refinement
- legal reference data quality
- notification monitoring consistency
- import/export workflow
- consistency across public/admin
- production readiness

END v7